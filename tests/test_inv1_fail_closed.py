# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
"""INV-1 fail-closed: no COMPLIANT verdict may depend on any UNKNOWN fact.

Synthetic fixtures only (TEST-ACT-1). Covers >=6 all/any/not tree shapes
with one UNKNOWN leaf, including the K3-masked shape any(TRUE, UNKNOWN),
which must be demoted to UNDETERMINED at the verdict layer.
"""
import datetime as dt

import pytest

from engine.core import evaluate
from engine.facts import UNKNOWN
from engine.loader import parse_rule

AS_OF = dt.date(2026, 7, 1)
CORPUS_V = "test-corpus-v1"

LEAF_T = {"fact": "f_true", "op": "eq", "value": True}
LEAF_F = {"fact": "f_false", "op": "eq", "value": True}
LEAF_U = {"fact": "f_unknown", "op": "eq", "value": True}

FACTS = {"f_true": True, "f_false": False, "f_unknown": UNKNOWN}


def rule(logic, verdict="COMPLIANT"):
    return parse_rule(
        {
            "id": "r-inv1",
            "legal_source": {
                "corpus_id": "TEST-ACT-1",
                "article": "Art. 1",
                "paragraph": "1",
            },
            "applies_from": "2026-01-01",
            "logic": logic,
            "verdict": verdict,
            "rationale_key": "test.inv1",
        }
    )


TREES = [
    LEAF_U,
    {"all": [LEAF_T, LEAF_U]},
    {"any": [LEAF_F, LEAF_U]},
    {"not": LEAF_U},
    {"all": [{"any": [LEAF_F, LEAF_U]}, LEAF_T]},
    {"any": [{"all": [LEAF_T, LEAF_U]}, LEAF_F]},
    {"not": {"all": [LEAF_T, {"not": LEAF_U}]}},
    {"any": [LEAF_T, LEAF_U]},
]


@pytest.mark.parametrize("tree", TREES)
def test_unknown_dependency_never_compliant(tree):
    verdict = evaluate([rule(tree)], FACTS, AS_OF, CORPUS_V)[0]
    assert verdict.status != "COMPLIANT"


@pytest.mark.parametrize("tree", TREES)
def test_unknown_dependency_is_reported(tree):
    verdict = evaluate([rule(tree)], FACTS, AS_OF, CORPUS_V)[0]
    if verdict.status == "UNDETERMINED":
        assert "f_unknown" in verdict.unknown_facts


def test_masked_unknown_demoted_to_undetermined():
    verdict = evaluate(
        [rule({"any": [LEAF_T, LEAF_U]})], FACTS, AS_OF, CORPUS_V
    )[0]
    assert verdict.status == "UNDETERMINED"
    assert "f_unknown" in verdict.unknown_facts


def test_missing_fact_is_unknown():
    facts = {"f_true": True, "f_false": False}  # f_unknown absent entirely
    verdict = evaluate([rule(LEAF_U)], facts, AS_OF, CORPUS_V)[0]
    assert verdict.status == "UNDETERMINED"
    assert "f_unknown" in verdict.unknown_facts


def test_all_known_true_is_compliant():
    verdict = evaluate(
        [rule({"all": [LEAF_T, {"not": LEAF_F}]})], FACTS, AS_OF, CORPUS_V
    )[0]
    assert verdict.status == "COMPLIANT"
    assert verdict.unknown_facts == []
