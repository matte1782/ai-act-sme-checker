# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
"""Gate-6 render_structured (PROMPT 8 Phase C): TDD RED first.

render_structured is the ADR-012(2) 'successor with the same structural
refusal': identical exact-disclaimer + R4 as_of gates as render_report, but
returns a plain-data dict (disclaimer, as_of, corpus_version, corpus_status,
deadlines[], verdicts[]) for the web path. Tests: refusal classes (ADR-008),
parity with render_report (same verdict set + deadline set), corpus_status
propagation, INV-4/INV-5 preserved.
"""
import datetime as dt

import pytest

from engine.core import evaluate
from engine.loader import parse_rule
from engine.render import (
    DISCLAIMER,
    AsOfMismatchError,
    MissingDisclaimerError,
    render_report,
    render_structured,
)

CV_PROV = "aia-omnibus-preOJ-9247-26"
CV_FINAL = "aia-1689-2024-final"
ACTIVE = dt.date(2026, 9, 1)


def _rule(rid, applies_from, verdict="NON_COMPLIANT"):
    return parse_rule({
        "id": rid,
        "legal_source": {"corpus_id": "aia-2024-1689-en", "article": "Art. 9", "paragraph": "1"},
        "applies_from": applies_from,
        "logic": {"fact": "f", "op": "eq", "value": True},
        "verdict": verdict,
        "rationale_key": rid.lower(),
    })


def _verdicts(as_of=ACTIVE, cv=CV_PROV):
    rules = [_rule("A", "2025-01-01"), _rule("B_FUTURE", "2027-01-01")]
    return evaluate(rules, {"f": True}, as_of, cv)


def _walk(node):
    yield node
    for child in node.get("children", []):
        yield from _walk(child)


# --- refusal classes (ADR-008), same as render_report --------------------

def test_wrong_disclaimer_refused():
    with pytest.raises(MissingDisclaimerError):
        render_structured(_verdicts(), ACTIVE, CV_PROV, "not the block")


def test_datetime_as_of_refused():
    with pytest.raises(AsOfMismatchError):
        render_structured(_verdicts(), dt.datetime(2026, 9, 1), CV_PROV, DISCLAIMER)


def test_stale_as_of_cross_check_refused():
    # verdicts evaluated at ACTIVE, report stamped a different date (R4)
    with pytest.raises(AsOfMismatchError):
        render_structured(_verdicts(), dt.date(2026, 9, 2), CV_PROV, DISCLAIMER)


# --- shape + parity with render_report -----------------------------------

def test_structure_keys_present():
    out = render_structured(_verdicts(), ACTIVE, CV_PROV, DISCLAIMER)
    assert set(out) == {"disclaimer", "as_of", "corpus_version", "corpus_status",
                        "deadlines", "verdicts"}
    assert out["disclaimer"] == DISCLAIMER          # INV-4 verbatim block
    assert out["as_of"] == "2026-09-01"
    assert out["corpus_version"] == CV_PROV


def test_verdict_set_parity_with_render_report():
    verdicts = _verdicts()
    out = render_structured(verdicts, ACTIVE, CV_PROV, DISCLAIMER)
    assert [v["rule_id"] for v in out["verdicts"]] == [v.rule_id for v in verdicts]
    assert [v["status"] for v in out["verdicts"]] == [v.status for v in verdicts]
    # and every verdict rendered as text by render_report mentions the same status
    text = render_report(verdicts, ACTIVE, CV_PROV, DISCLAIMER)
    for v in verdicts:
        assert f"[{v.status}] {v.rule_id}" in text


def test_deadline_set_parity():
    verdicts = _verdicts()
    out = render_structured(verdicts, ACTIVE, CV_PROV, DISCLAIMER)
    inactive = [v.rule_id for v in verdicts
                if v.status == "UNDETERMINED"
                and any(n.get("op") == "applicability" for n in _walk(v.explanation))]
    assert [d["rule_id"] for d in out["deadlines"]] == inactive
    assert out["deadlines"][0]["rule_id"] == "B_FUTURE"
    assert out["deadlines"][0]["applies_from"] == "2027-01-01"
    assert out["deadlines"][0]["citation"]["corpus_id"] == "aia-2024-1689-en"


# --- corpus_status propagation -------------------------------------------

def test_corpus_status_provisional_on_preoj():
    out = render_structured(_verdicts(cv=CV_PROV), ACTIVE, CV_PROV, DISCLAIMER)
    assert out["corpus_status"] == "PROVISIONAL"


def test_corpus_status_final_otherwise():
    out = render_structured(_verdicts(cv=CV_FINAL), ACTIVE, CV_FINAL, DISCLAIMER)
    assert out["corpus_status"] == "FINAL"


# --- INV-5: every verdict's explanation carries citation leaves -----------

def test_explanation_is_plain_data_with_citations():
    out = render_structured(_verdicts(), ACTIVE, CV_PROV, DISCLAIMER)
    for v in out["verdicts"]:
        leaves = [n for n in _walk(v["explanation"])
                  if n.get("op") in ("fact", "applicability", "scope")]
        assert leaves
        assert all(isinstance(n["citation"], dict) for n in leaves)


def test_returned_explanation_not_aliased():
    verdicts = _verdicts()
    out = render_structured(verdicts, ACTIVE, CV_PROV, DISCLAIMER)
    out["verdicts"][0]["explanation"]["value"] = "TAMPERED"
    assert verdicts[0].explanation["value"] != "TAMPERED"
