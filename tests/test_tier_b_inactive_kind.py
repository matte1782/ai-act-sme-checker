# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
"""Tier B (2026-09-02, after the persona test; ADR-017): structured INACTIVE
sub-state (render_structured) and the presentation-only rule 'kind' (loader +
webapi). ADR-008 classes for 'kind': missing (defaults), unknown value, empty,
whitespace, explicit null, wrong type. Verify 2026-09-02 (B1) added the
discriminator cases: UNDETERMINED-for-missing-answers is NOT inactive, and an
EXPIRED window is neither inactive nor a deadline."""
import datetime as dt
import json

import pytest
import yaml

from engine.core import evaluate
from engine.loader import RuleValidationError, load_rules_dir, parse_rule
from engine.render import DISCLAIMER, render_structured
from engine.webapi import evaluate_answers

BAR = {  # a business with no AI system at all, evaluated after 2026-08-02
    "is_ai_system": False, "in_eu_market": True, "personal_nonprofessional_use": False,
    "operator_role": None, "interacts_with_persons": False, "interaction_disclosed": None,
    "deepfake_published": False, "deepfake_disclosed": None, "generates_synthetic_content": False,
    "content_marked_machine_readable": None, "system_on_market_before_2026_08_02": False,
    "practice_social_scoring": False, "emotion_recognition_workplace": False,
    "emotion_medical_safety_exception": None, "ncii_generation_capability": False,
    "ncii_safeguards_state_of_art": None, "ncii_intended_purpose": None,
    "annex_iii_use_case": "none", "chapter_iii_obligations_met": None,
}


def _rule(**over):
    data = {
        "id": "r-kind", "legal_source": {"corpus_id": "c", "article": "Art. 1", "paragraph": "1"},
        "applies_from": "2025-01-01", "logic": {"fact": "is_ai_system", "op": "eq", "value": True},
        "verdict": "NON_COMPLIANT", "rationale_key": "k",
    }
    data.update(over)
    return data


# --- B1: inactive sub-state is structured, never a parsed reason string ------

def test_structured_inactive_fields_present_and_consistent():
    out = json.loads(evaluate_answers(json.dumps(BAR), "2026-09-02", "it"))
    by_id = {v["rule_id"]: v for v in out["structured"]["verdicts"]}
    for v in by_id.values():
        assert set(v) >= {"inactive", "applies_from", "status"}
        if v["inactive"]:
            assert v["status"] == "UNDETERMINED"          # status untouched (oracle)
            assert v["applies_from"] and len(v["applies_from"]) == 10
        else:
            assert v["applies_from"] is None
    assert by_id["HR_ANNEX_III"]["inactive"] and by_id["HR_ANNEX_III"]["applies_from"] == "2027-12-02"
    assert by_id["ART5_NCII"]["inactive"] and by_id["ART5_NCII"]["applies_from"] == "2026-12-02"
    assert not by_id["ART50_1"]["inactive"]
    # every inactive verdict also has its deadline row, and vice versa; the
    # expected set is derived INDEPENDENTLY by walking the explanation trees
    # for a future applicability leaf (not from _deadline_of itself).
    inactive = {v["rule_id"] for v in by_id.values() if v["inactive"]}
    future_leaf = {rid for rid, v in by_id.items()
                   if any(n.get("op") == "applicability" and n.get("applies_from", "") > "2026-09-02"
                          for n in _walk(v["explanation"]))}
    assert inactive == future_leaf == {"HR_ANNEX_III", "ART5_NCII"}
    assert inactive == {d["rule_id"] for d in out["structured"]["deadlines"]}


def _walk(node):
    yield node
    for child in node.get("children", []):
        yield from _walk(child)


def test_undetermined_for_missing_answers_is_not_inactive():
    # verify 2026-09-02 (B1): the discriminator the field exists for. A rule in
    # force whose verdict is UNDETERMINED because an answer is missing must not
    # read as "not yet applicable" (mutant inactive := status == UNDETERMINED).
    answers = dict(BAR, is_ai_system=True, operator_role="provider",
                   interacts_with_persons=True, interaction_disclosed=None)
    out = json.loads(evaluate_answers(json.dumps(answers), "2028-01-01", "it"))
    by_id = {v["rule_id"]: v for v in out["structured"]["verdicts"]}
    v = by_id["ART50_1"]
    assert v["status"] == "UNDETERMINED" and "interaction_disclosed" in v["unknown_facts"]
    assert v["inactive"] is False and v["applies_from"] is None
    assert out["structured"]["deadlines"] == []       # everything is in force by 2028


def test_expired_window_is_neither_inactive_nor_a_deadline():
    # verify 2026-09-02 (B1): core emits the same applicability leaf for a rule
    # PAST its applies_until; that is expired, never "not yet applicable (from
    # 2020-01-01)" and never an upcoming deadline row.
    rule = parse_rule(_rule(applies_from="2020-01-01", applies_until="2021-01-01"))
    as_of = dt.date(2026, 9, 2)
    v = evaluate([rule], {"is_ai_system": True}, as_of, "test-corpus-v1")[0]
    assert v.status == "UNDETERMINED"                  # fail-closed status untouched
    out = render_structured([v], as_of, "test-corpus-v1", DISCLAIMER)
    assert out["deadlines"] == []
    assert out["verdicts"][0]["inactive"] is False
    assert out["verdicts"][0]["applies_from"] is None


def test_future_window_is_inactive_with_its_date():
    # control for the test above: the not-yet-applicable case still reports.
    rule = parse_rule(_rule(applies_from="2030-01-01"))
    as_of = dt.date(2026, 9, 2)
    v = evaluate([rule], {"is_ai_system": True}, as_of, "test-corpus-v1")[0]
    out = render_structured([v], as_of, "test-corpus-v1", DISCLAIMER)
    assert out["verdicts"][0]["inactive"] is True
    assert out["verdicts"][0]["applies_from"] == "2030-01-01"
    assert [d["rule_id"] for d in out["deadlines"]] == ["r-kind"]


# --- B2: rule kind ---------------------------------------------------------

def test_kind_defaults_to_obligation():
    assert parse_rule(_rule()).kind == "obligation"


def test_kind_prohibition_accepted():
    assert parse_rule(_rule(kind="prohibition")).kind == "prohibition"


@pytest.mark.parametrize("value", [
    "ban", "Prohibition",            # unknown value (case matters)
    "",                              # empty
    "   ", " prohibition", "prohibition ",   # whitespace-only / padded
    None,                            # explicit `kind:` with no scalar
    True, ["prohibition"], 1, {"kind": "prohibition"},   # wrong type
])
def test_kind_unknown_or_wrong_type_rejected(value):
    with pytest.raises(RuleValidationError):
        parse_rule(_rule(kind=value))


def test_engine_never_branches_on_kind():
    # ADR-017: 'kind' is presentation-only. core and render must not read it;
    # the only consumers are the loader (validation) and webapi (exposure).
    for path in ("engine/core.py", "engine/render.py"):
        src = open(path, encoding="utf-8").read()
        assert ".kind" not in src and "rule_kinds" not in src, path


def test_dependent_helpers_gate_questions_are_adjacent():
    # The dependent helpers say "the previous question" / "two questions ago";
    # pin the schema order those words rely on (verify 2026-09-02).
    with open("schema/facts.yaml", encoding="utf-8") as fh:
        names = [f["name"] for f in yaml.safe_load(fh)["facts"]]
    assert names.index("deepfake_disclosed") == names.index("deepfake_published") + 1
    assert names.index("emotion_medical_safety_exception") == names.index("emotion_recognition_workplace") + 1
    assert names.index("ncii_safeguards_state_of_art") == names.index("ncii_generation_capability") + 1
    assert names.index("ncii_intended_purpose") == names.index("ncii_generation_capability") + 2


def test_shipped_rules_kinds_match_article_5():
    rules = load_rules_dir("rules")
    kinds = {r.id: r.kind for r in rules}
    assert {k for k, v in kinds.items() if v == "prohibition"} == {
        "ART5_SOCIAL_SCORING", "ART5_EMOTION_WORKPLACE", "ART5_NCII"}
    assert all(v == "obligation" for k, v in kinds.items() if not k.startswith("ART5_"))


def test_webapi_exposes_rule_kinds():
    out = json.loads(evaluate_answers(json.dumps(BAR), "2026-09-02", "it"))
    assert out["rule_kinds"]["ART5_NCII"] == "prohibition"
    assert out["rule_kinds"]["ART50_1"] == "obligation"
    assert set(out["rule_kinds"]) == {v["rule_id"] for v in out["structured"]["verdicts"]}
