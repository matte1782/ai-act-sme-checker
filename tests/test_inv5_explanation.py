# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
"""INV-5 explanation: every verdict carries a non-empty dependency tree
whose leaves cite corpus ids; UNDETERMINED explanations name the UNKNOWN
facts responsible.
"""
import datetime as dt

import pytest

from engine.core import evaluate
from engine.facts import UNKNOWN
from engine.loader import parse_rule

AS_OF = dt.date(2026, 7, 1)
CORPUS_V = "test-corpus-v1"

LEAF_T = {"fact": "f_true", "op": "eq", "value": True}
LEAF_U = {"fact": "f_unknown", "op": "eq", "value": True}


def rule(logic, verdict="COMPLIANT"):
    return parse_rule(
        {
            "id": "r-inv5",
            "legal_source": {
                "corpus_id": "TEST-ACT-1",
                "article": "Art. 5",
                "paragraph": "4",
            },
            "applies_from": "2026-01-01",
            "logic": logic,
            "verdict": verdict,
            "rationale_key": "test.inv5",
        }
    )


def leaves(node):
    if node.get("op") in ("fact", "applicability"):
        return [node]
    return [leaf for child in node.get("children", []) for leaf in leaves(child)]


CASES = [
    ({"all": [LEAF_T]}, {"f_true": True}, "COMPLIANT"),
    ({"all": [LEAF_T]}, {"f_true": False}, "NON_COMPLIANT"),
    ({"all": [LEAF_T, LEAF_U]}, {"f_true": True, "f_unknown": UNKNOWN}, "UNDETERMINED"),
]


@pytest.mark.parametrize("logic,facts,expected", CASES)
def test_every_verdict_has_nonempty_explanation(logic, facts, expected):
    verdict = evaluate([rule(logic)], facts, AS_OF, CORPUS_V)[0]
    assert verdict.status == expected
    assert verdict.explanation
    assert leaves(verdict.explanation), "explanation tree has no leaves"


@pytest.mark.parametrize("logic,facts,expected", CASES)
def test_every_leaf_cites_corpus_id_and_article(logic, facts, expected):
    verdict = evaluate([rule(logic)], facts, AS_OF, CORPUS_V)[0]
    for leaf in leaves(verdict.explanation):
        assert leaf["citation"]["corpus_id"] == "TEST-ACT-1"
        assert leaf["citation"]["article"] == "Art. 5"


def test_undetermined_names_unknown_facts():
    verdict = evaluate(
        [rule({"all": [LEAF_T, LEAF_U]})],
        {"f_true": True, "f_unknown": UNKNOWN},
        AS_OF,
        CORPUS_V,
    )[0]
    assert verdict.status == "UNDETERMINED"
    assert verdict.unknown_facts == ["f_unknown"]
    assert "f_unknown" in str(verdict.explanation)


def test_temporal_inactive_explanation_is_nonempty_and_cites():
    # INV-5 has no vacuous pass: even a not-yet-applicable rule must
    # explain itself with a citation-bearing leaf.
    inactive = parse_rule(
        {
            "id": "r-future",
            "legal_source": {
                "corpus_id": "TEST-ACT-1",
                "article": "Art. 99",
                "paragraph": "2",
            },
            "applies_from": "2027-01-01",
            "logic": {"all": [LEAF_T]},
            "verdict": "COMPLIANT",
            "rationale_key": "test.future",
        }
    )
    verdict = evaluate([inactive], {"f_true": True}, AS_OF, CORPUS_V)[0]
    assert verdict.status == "UNDETERMINED"
    found = leaves(verdict.explanation)
    assert found, "temporal-inactive explanation has no leaves (vacuous INV-5)"
    assert found[0]["citation"]["corpus_id"] == "TEST-ACT-1"
    assert "not yet applicable" in str(verdict.explanation)


def test_multiple_unknowns_all_named():
    logic = {"all": [{"fact": "a", "op": "eq", "value": True},
                     {"fact": "b", "op": "in", "value": ["x", "y"]}]}
    verdict = evaluate([rule(logic)], {}, AS_OF, CORPUS_V)[0]
    assert verdict.status == "UNDETERMINED"
    assert verdict.unknown_facts == ["a", "b"]
