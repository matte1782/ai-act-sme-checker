"""INV-2 statute gate: loader rejects rules without citation or validity dates.

Synthetic fixtures only (TEST-ACT-1).
"""
import copy
import datetime as dt

import pytest

from engine.loader import RuleValidationError, load_rules_file, parse_rule

VALID = {
    "id": "r-inv2",
    "legal_source": {
        "corpus_id": "TEST-ACT-1",
        "article": "Art. 2",
        "paragraph": "3",
    },
    "applies_from": "2026-01-01",
    "applies_until": "2027-01-01",
    "logic": {"fact": "f_true", "op": "eq", "value": True},
    "verdict": "COMPLIANT",
    "rationale_key": "test.inv2",
}


def test_valid_rule_loads():
    rule = parse_rule(copy.deepcopy(VALID))
    assert rule.id == "r-inv2"
    assert rule.legal_source["corpus_id"] == "TEST-ACT-1"
    assert rule.applies_from == dt.date(2026, 1, 1)
    assert rule.applies_until == dt.date(2027, 1, 1)


def test_missing_legal_source_rejected():
    bad = copy.deepcopy(VALID)
    del bad["legal_source"]
    with pytest.raises(RuleValidationError):
        parse_rule(bad)


def test_missing_applies_from_rejected():
    bad = copy.deepcopy(VALID)
    del bad["applies_from"]
    with pytest.raises(RuleValidationError):
        parse_rule(bad)


@pytest.mark.parametrize("field", ["corpus_id", "article", "paragraph"])
def test_empty_citation_field_rejected(field):
    bad = copy.deepcopy(VALID)
    bad["legal_source"][field] = ""
    with pytest.raises(RuleValidationError):
        parse_rule(bad)


@pytest.mark.parametrize("field", ["corpus_id", "article", "paragraph"])
def test_missing_citation_field_rejected(field):
    bad = copy.deepcopy(VALID)
    del bad["legal_source"][field]
    with pytest.raises(RuleValidationError):
        parse_rule(bad)


def test_load_rules_file_valid(tmp_path):
    path = tmp_path / "rules.yaml"
    path.write_text(
        "rules:\n"
        "  - id: r-file-1\n"
        "    legal_source:\n"
        "      corpus_id: TEST-ACT-1\n"
        "      article: Art. 4\n"
        "      paragraph: '1'\n"
        "    applies_from: 2026-02-01\n"
        "    logic: {fact: f_true, op: eq, value: true}\n"
        "    verdict: COMPLIANT\n"
        "    rationale_key: test.file\n",
        encoding="utf-8",
    )
    rules = load_rules_file(str(path))
    assert len(rules) == 1
    assert rules[0].applies_from == dt.date(2026, 2, 1)


def test_load_rules_file_rejects_invalid(tmp_path):
    path = tmp_path / "rules.yaml"
    path.write_text(
        "rules:\n"
        "  - id: r-file-bad\n"
        "    legal_source:\n"
        "      corpus_id: TEST-ACT-1\n"
        "      article: Art. 4\n"
        "      paragraph: '1'\n"
        "    logic: {fact: f_true, op: eq, value: true}\n"
        "    verdict: COMPLIANT\n"
        "    rationale_key: test.file\n",
        encoding="utf-8",
    )
    with pytest.raises(RuleValidationError):
        load_rules_file(str(path))
