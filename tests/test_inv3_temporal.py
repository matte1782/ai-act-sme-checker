# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
"""INV-3 temporal: identical facts, different as_of_date across an
applicability boundary => verdicts change accordingly.

Synthetic rule: applies_from 2026-12-02 (fake date, no legal content).
"""
import datetime as dt

from engine.core import evaluate
from engine.loader import parse_rule

CORPUS_V = "test-corpus-v1"
FACTS = {"f_true": True}
LEAF_T = {"fact": "f_true", "op": "eq", "value": True}


def rule(applies_from="2026-12-02", applies_until=None):
    data = {
        "id": "r-inv3",
        "legal_source": {
            "corpus_id": "TEST-ACT-1",
            "article": "Art. 3",
            "paragraph": "2",
        },
        "applies_from": applies_from,
        "logic": LEAF_T,
        "verdict": "COMPLIANT",
        "rationale_key": "test.inv3",
    }
    if applies_until:
        data["applies_until"] = applies_until
    return parse_rule(data)


def explanation_text(verdict):
    return str(verdict.explanation)


def test_before_applies_from_is_undetermined():
    verdict = evaluate([rule()], FACTS, dt.date(2026, 11, 1), CORPUS_V)[0]
    assert verdict.status == "UNDETERMINED"
    assert "not yet applicable" in explanation_text(verdict)


def test_after_applies_from_evaluates():
    verdict = evaluate([rule()], FACTS, dt.date(2026, 12, 15), CORPUS_V)[0]
    assert verdict.status == "COMPLIANT"


def test_on_applies_from_boundary_is_active():
    verdict = evaluate([rule()], FACTS, dt.date(2026, 12, 2), CORPUS_V)[0]
    assert verdict.status == "COMPLIANT"


def test_after_applies_until_is_undetermined():
    verdict = evaluate(
        [rule(applies_until="2027-06-01")],
        FACTS,
        dt.date(2027, 7, 1),
        CORPUS_V,
    )[0]
    assert verdict.status == "UNDETERMINED"
    assert "no longer applicable" in explanation_text(verdict)


def test_on_applies_until_boundary_is_active():
    # Pinned semantics: applies_until is INCLUSIVE (last day of validity).
    verdict = evaluate(
        [rule(applies_until="2027-06-01")],
        FACTS,
        dt.date(2027, 6, 1),
        CORPUS_V,
    )[0]
    assert verdict.status == "COMPLIANT"


def test_within_validity_window_evaluates():
    verdict = evaluate(
        [rule(applies_until="2027-06-01")],
        FACTS,
        dt.date(2027, 1, 15),
        CORPUS_V,
    )[0]
    assert verdict.status == "COMPLIANT"


def test_identical_facts_flip_across_boundary():
    rules = [rule()]
    before = evaluate(rules, FACTS, dt.date(2026, 12, 1), CORPUS_V)[0]
    after = evaluate(rules, FACTS, dt.date(2026, 12, 2), CORPUS_V)[0]
    assert before.status == "UNDETERMINED"
    assert after.status == "COMPLIANT"
    assert before.status != after.status
