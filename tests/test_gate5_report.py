"""Gate-5 report foundations (PROMPT 7 Phase C): TDD RED first.

C1: the op=='applicability' leaf gains a RESOLVED "applies_from" ISO field
    (X3 branch already selected by core) - additive.
C2: render_report gains an OPTIONAL deadlines section, built only from the
    C1 field (never parsed from reason strings); default (no i18n) keeps the
    old output byte-for-byte.
C3: i18n/messages.yaml + engine/i18n.py: strict load, ADR-008 classes,
    completeness (every rule rationale_key + all four statuses, it AND en).
"""
import datetime as dt

import pytest

from engine import core
from engine.core import evaluate
from engine.loader import load_rules_dir, parse_rule
from engine.render import DISCLAIMER, render_report

CV = "test-corpus-v1"


def _walk(node):
    yield node
    for child in node.get("children", []):
        yield from _walk(child)


def _applic_leaf(verdict):
    for n in _walk(verdict.explanation):
        if n.get("op") == "applicability":
            return n
    return None


def _x3_rule():
    return parse_rule({
        "id": "R_X3",
        "legal_source": {"corpus_id": "TEST-ACT-1", "article": "Art. 9", "paragraph": "1"},
        "applies_from": [
            {"when": {"fact": "legacy", "op": "eq", "value": True}, "date": "2026-12-02"},
            {"default": "2026-08-02"},
        ],
        "logic": {"fact": "x", "op": "eq", "value": True},
        "verdict": "COMPLIANT",
        "rationale_key": "test.x3",
    })


# --- C1: resolved applies_from on the applicability leaf -------------------

def test_c1_leaf_carries_resolved_legacy_branch_date():
    v = evaluate([_x3_rule()], {"legacy": True, "x": True}, dt.date(2026, 10, 1), CV)[0]
    leaf = _applic_leaf(v)
    assert leaf is not None
    assert leaf["applies_from"] == "2026-12-02"


def test_c1_leaf_carries_resolved_default_branch_date():
    v = evaluate([_x3_rule()], {"legacy": False, "x": True}, dt.date(2026, 7, 1), CV)[0]
    assert _applic_leaf(v)["applies_from"] == "2026-08-02"


def test_c1_scalar_rule_leaf_carries_its_date():
    r = parse_rule({
        "id": "R_S", "legal_source": {"corpus_id": "T", "article": "Art. 1", "paragraph": "1"},
        "applies_from": "2027-01-01", "logic": {"fact": "x", "op": "eq", "value": True},
        "verdict": "COMPLIANT", "rationale_key": "t",
    })
    v = evaluate([r], {"x": True}, dt.date(2026, 1, 1), CV)[0]
    assert _applic_leaf(v)["applies_from"] == "2027-01-01"


def test_c1_inactive_oracle_shape_unbroken():
    # still UNDETERMINED + applicability leaf (the INACTIVE matcher contract)
    v = evaluate([_x3_rule()], {"legacy": True, "x": True}, dt.date(2026, 10, 1), CV)[0]
    assert v.status == core.STATUS_UNDETERMINED
    assert _applic_leaf(v) is not None


# --- C2: deadlines section (render_report, additive) ----------------------

LABELS = {
    "status_labels": {s: s for s in
                      ("COMPLIANT", "NON_COMPLIANT", "UNDETERMINED", "NOT_APPLICABLE")},
    "rationales": {"test.x3": "rationale", "t": "rationale"},
    "ui": {"deadlines_header": "UPCOMING DEADLINES",
           "deadlines_none": "No upcoming deadlines."},
}


def test_c2_default_no_i18n_has_no_deadlines_section():
    v = evaluate([_x3_rule()], {"legacy": True, "x": True}, dt.date(2026, 10, 1), CV)[0]
    out = render_report([v], dt.date(2026, 10, 1), CV, DISCLAIMER)
    assert "DEADLINE" not in out.upper() and "SCADENZ" not in out.upper()


def test_c2_deadlines_section_lists_inactive_with_resolved_date():
    v = evaluate([_x3_rule()], {"legacy": True, "x": True}, dt.date(2026, 10, 1), CV)[0]
    out = render_report([v], dt.date(2026, 10, 1), CV, DISCLAIMER, i18n=LABELS)
    assert "UPCOMING DEADLINES" in out
    assert "R_X3" in out
    assert "2026-12-02" in out          # the resolved legacy branch, not the default
    assert "2026-08-02" not in out


def test_c2_deadlines_none_when_no_inactive():
    v = evaluate([_x3_rule()], {"legacy": True, "x": True}, dt.date(2027, 1, 1), CV)[0]
    assert v.status == "COMPLIANT"
    out = render_report([v], dt.date(2027, 1, 1), CV, DISCLAIMER, i18n=LABELS)
    assert "No upcoming deadlines." in out


def test_c2_status_label_localized_through_render():
    labels = {**LABELS, "status_labels": {**LABELS["status_labels"],
                                           "COMPLIANT": "CONFORME"}}
    v = evaluate([_x3_rule()], {"legacy": True, "x": True}, dt.date(2027, 1, 1), CV)[0]
    out = render_report([v], dt.date(2027, 1, 1), CV, DISCLAIMER, i18n=labels)
    assert "[CONFORME]" in out


# --- C3: i18n catalog + loader --------------------------------------------

def test_c3_catalog_complete_for_all_rules():
    from engine.i18n import check_completeness, load_i18n
    cat = load_i18n("i18n/messages.yaml")
    keys = [r.rationale_key for r in load_rules_dir("rules")]
    check_completeness(cat, keys)   # must not raise


def test_c3_all_four_statuses_labeled_both_langs():
    from engine.i18n import load_i18n
    cat = load_i18n("i18n/messages.yaml")
    for s in ("COMPLIANT", "NON_COMPLIANT", "UNDETERMINED", "NOT_APPLICABLE"):
        assert cat["status_labels"][s]["it"].strip()
        assert cat["status_labels"][s]["en"].strip()


def test_c3_bundle_localizes_to_italian():
    from engine.i18n import bundle, load_i18n
    b = bundle(load_i18n("i18n/messages.yaml"), "it")
    assert b["status_labels"]["NON_COMPLIANT"]
    assert b["ui"]["deadlines_header"]


def test_c3_missing_rationale_key_is_error(tmp_path):
    from engine.i18n import I18nError, check_completeness, load_i18n
    cat = load_i18n("i18n/messages.yaml")
    with pytest.raises(I18nError):
        check_completeness(cat, ["nonexistent.key"])


@pytest.mark.parametrize("body,match", [
    ("status_labels: {}\nrationales: {}\nui: {}\n", "status"),          # missing statuses
    ("", "mapping"),                                                     # empty file
])
def test_c3_adr008_malformed_catalog(tmp_path, body, match):
    from engine.i18n import I18nError, load_i18n
    p = tmp_path / "m.yaml"
    p.write_text(body, encoding="utf-8")
    with pytest.raises(I18nError):
        load_i18n(str(p))


def test_c3_whitespace_label_rejected(tmp_path):
    from engine.i18n import I18nError, load_i18n
    p = tmp_path / "m.yaml"
    p.write_text(
        "status_labels:\n  COMPLIANT: {it: '  ', en: x}\n"
        "  NON_COMPLIANT: {it: a, en: b}\n  UNDETERMINED: {it: a, en: b}\n"
        "  NOT_APPLICABLE: {it: a, en: b}\nrationales: {}\nui: {}\n",
        encoding="utf-8",
    )
    with pytest.raises(I18nError):
        load_i18n(str(p))
