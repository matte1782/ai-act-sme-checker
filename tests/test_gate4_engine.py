# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
"""Gate-4 engine extensions X1-X5 (ADR-009 vocabulary; X1-X5 design).

TDD RED first. Covers, per PROMPT 6 Phase C:
- X1 STATUS_NOT_APPLICABLE constant + render support;
- X2 applicable_if predicate tree (loader-validated like logic), ADR-008 classes;
- X3 applies_from-as-branch-list (no default / two defaults / default not
  last / overlapping whens / when UNKNOWN fail-closed / invalid date);
- X4 precedence: temporal -> INACTIVE beats scope; applicable_if FALSE ->
  NOT_APPLICABLE (op=='scope' citation leaf); UNKNOWN -> UNDETERMINED named;
- X5 NOT_APPLICABLE never rests on UNKNOWN scope facts (that path is UNDETERMINED);
- INV-5 non-vacuous scope leaf; render of NOT_APPLICABLE.

Synthetic fixtures only (no legal content).
"""
import datetime as dt

import pytest

from engine import core
from engine.core import evaluate
from engine.loader import RuleValidationError, parse_rule
from engine.render import DISCLAIMER, render_report

CV = "test-corpus-v1"
ACTIVE = dt.date(2026, 9, 1)      # >= applies_from 2026-08-02
PRE = dt.date(2026, 7, 15)        # < applies_from 2026-08-02

LEAF_X = {"fact": "x", "op": "eq", "value": True}
IN_SCOPE = {"fact": "personal_use", "op": "eq", "value": False}


def make_rule(**over):
    data = {
        "id": "r-g4",
        "legal_source": {
            "corpus_id": "TEST-ACT-1",
            "article": "Art. 50",
            "paragraph": "1",
        },
        "applies_from": "2026-08-02",
        "logic": LEAF_X,
        "verdict": "COMPLIANT",
        "rationale_key": "test.g4",
    }
    data.update(over)
    return parse_rule(data)


def walk(node):
    yield node
    for child in node.get("children", []):
        yield from walk(child)


def ops(verdict):
    return {n.get("op") for n in walk(verdict.explanation)}


# --- X1: NOT_APPLICABLE status --------------------------------------------

def test_x1_status_constant_exists():
    assert core.STATUS_NOT_APPLICABLE == "NOT_APPLICABLE"


# --- X2: applicable_if loads & validates like logic -----------------------

def test_x2_applicable_if_loads():
    r = make_rule(applicable_if=IN_SCOPE)
    assert r.applicable_if == IN_SCOPE


def test_x2_absent_applicable_if_is_none():
    assert make_rule().applicable_if is None


def test_x2_applicable_if_empty_rejected():          # ADR-008 (2)
    with pytest.raises(RuleValidationError):
        make_rule(applicable_if={})


def test_x2_applicable_if_missing_op_rejected():     # ADR-008 (1)
    with pytest.raises(RuleValidationError):
        make_rule(applicable_if={"fact": "personal_use", "value": False})


def test_x2_applicable_if_two_kinds_rejected():      # ADR-008 (5)
    with pytest.raises(RuleValidationError):
        make_rule(applicable_if={"all": [LEAF_X], "any": [LEAF_X]})


def test_x2_applicable_if_unknown_leaf_key_rejected():   # ADR-008 (5)
    with pytest.raises(RuleValidationError):
        make_rule(applicable_if={"fact": "p", "op": "eq", "value": False, "z": 1})


# --- X4 step 2: applicable_if FALSE -> NOT_APPLICABLE ----------------------

def test_applicable_if_false_is_not_applicable():
    r = make_rule(applicable_if=IN_SCOPE)
    v = evaluate([r], {"personal_use": True, "x": True}, ACTIVE, CV)[0]
    assert v.status == core.STATUS_NOT_APPLICABLE


def test_not_applicable_carries_scope_leaf_with_citation():   # INV-5 non-vacuous
    r = make_rule(applicable_if=IN_SCOPE)
    v = evaluate([r], {"personal_use": True, "x": True}, ACTIVE, CV)[0]
    scope = [n for n in walk(v.explanation) if n.get("op") == "scope"]
    assert scope, "NOT_APPLICABLE must carry an op=='scope' leaf"
    assert scope[0]["citation"]["corpus_id"] == "TEST-ACT-1"
    assert scope[0]["citation"]["article"] == "Art. 50"


def test_not_applicable_is_not_inactive_shape():
    # a scope leaf is NOT an applicability leaf: must not read as INACTIVE.
    r = make_rule(applicable_if=IN_SCOPE)
    v = evaluate([r], {"personal_use": True, "x": True}, ACTIVE, CV)[0]
    assert "applicability" not in ops(v)


def test_applicable_if_true_proceeds_to_logic():
    r = make_rule(applicable_if=IN_SCOPE)
    v = evaluate([r], {"personal_use": False, "x": True}, ACTIVE, CV)[0]
    assert v.status == "COMPLIANT"


# --- X4 step 2 / X5: applicable_if UNKNOWN -> UNDETERMINED named -----------

def test_applicable_if_unknown_is_undetermined_named():
    r = make_rule(applicable_if=IN_SCOPE)
    v = evaluate([r], {"x": True}, ACTIVE, CV)[0]   # personal_use omitted
    assert v.status == core.STATUS_UNDETERMINED
    assert "personal_use" in v.unknown_facts


def test_x5_unknown_scope_never_not_applicable():
    r = make_rule(applicable_if=IN_SCOPE)
    v = evaluate([r], {"x": True}, ACTIVE, CV)[0]
    assert v.status != core.STATUS_NOT_APPLICABLE


def test_x5_unknown_scope_is_not_inactive_either():
    # named unknowns, no applicability leaf -> UNDETERMINED, disjoint from INACTIVE
    r = make_rule(applicable_if=IN_SCOPE)
    v = evaluate([r], {"x": True}, ACTIVE, CV)[0]
    assert "applicability" not in ops(v)


# --- X4 step 1: temporal precedence ---------------------------------------

def test_precedence_temporal_beats_scope():
    # out of scope AND pre-applicability -> temporal wins -> INACTIVE shape.
    r = make_rule(applicable_if=IN_SCOPE)
    v = evaluate([r], {"personal_use": True, "x": True}, PRE, CV)[0]
    assert v.status == core.STATUS_UNDETERMINED
    assert "applicability" in ops(v)
    assert v.status != core.STATUS_NOT_APPLICABLE


def test_precedence_temporal_beats_logic():
    r = make_rule(logic=LEAF_X)   # logic would be TRUE -> COMPLIANT if active
    v = evaluate([r], {"x": True}, PRE, CV)[0]
    assert v.status == core.STATUS_UNDETERMINED
    assert "applicability" in ops(v)


# --- X3: applies_from as branch list --------------------------------------

def branches():
    return [
        {"when": {"fact": "legacy", "op": "eq", "value": True}, "date": "2026-12-02"},
        {"default": "2026-08-02"},
    ]


def test_x3_when_true_selects_branch_date():
    r = make_rule(applies_from=branches())
    # legacy True -> date 2026-12-02; as_of 2026-10-01 < that -> INACTIVE
    v = evaluate([r], {"legacy": True, "x": True}, dt.date(2026, 10, 1), CV)[0]
    assert v.status == core.STATUS_UNDETERMINED
    assert "applicability" in ops(v)
    # after that date -> active -> logic evaluates
    v2 = evaluate([r], {"legacy": True, "x": True}, dt.date(2027, 1, 15), CV)[0]
    assert v2.status == "COMPLIANT"


def test_x3_default_when_all_false():
    r = make_rule(applies_from=branches())
    # legacy False -> default 2026-08-02; as_of 2026-09-01 active
    v = evaluate([r], {"legacy": False, "x": True}, ACTIVE, CV)[0]
    assert v.status == "COMPLIANT"


def test_x3_when_unknown_fail_closed_named():
    r = make_rule(applies_from=branches())
    v = evaluate([r], {"x": True}, dt.date(2026, 10, 1), CV)[0]  # legacy omitted
    assert v.status == core.STATUS_UNDETERMINED
    assert "legacy" in v.unknown_facts


def test_x3_overlapping_whens_first_true_wins():
    af = [
        {"when": {"fact": "a", "op": "eq", "value": True}, "date": "2026-12-02"},
        {"when": {"fact": "b", "op": "eq", "value": True}, "date": "2027-06-01"},
        {"default": "2026-08-02"},
    ]
    r = make_rule(applies_from=af)
    # both true; first branch (2026-12-02) must win -> active at 2026-12-15
    v = evaluate([r], {"a": True, "b": True, "x": True}, dt.date(2026, 12, 15), CV)[0]
    assert v.status == "COMPLIANT"  # would be INACTIVE if 2027-06-01 had won


def test_x3_no_default_rejected():                    # ADR-008 (1)
    with pytest.raises(RuleValidationError):
        make_rule(applies_from=[
            {"when": {"fact": "legacy", "op": "eq", "value": True}, "date": "2026-12-02"}
        ])


def test_x3_two_defaults_rejected():                  # ADR-008 (7)
    with pytest.raises(RuleValidationError):
        make_rule(applies_from=[{"default": "2026-08-02"}, {"default": "2026-12-02"}])


def test_x3_default_not_last_rejected():              # ADR-008 (6) ordering
    with pytest.raises(RuleValidationError):
        make_rule(applies_from=[
            {"default": "2026-08-02"},
            {"when": {"fact": "legacy", "op": "eq", "value": True}, "date": "2026-12-02"},
        ])


def test_x3_invalid_date_in_branch_rejected():        # ADR-008 (6)
    with pytest.raises(RuleValidationError):
        make_rule(applies_from=[
            {"when": {"fact": "legacy", "op": "eq", "value": True}, "date": "2026-02-30"},
            {"default": "2026-08-02"},
        ])


def test_x3_branch_when_must_be_predicate():          # ADR-008 (4)
    with pytest.raises(RuleValidationError):
        make_rule(applies_from=[
            {"when": {"fact": "legacy"}, "date": "2026-12-02"},
            {"default": "2026-08-02"},
        ])


def test_x3_branch_missing_date_rejected():           # ADR-008 (1)
    with pytest.raises(RuleValidationError):
        make_rule(applies_from=[
            {"when": {"fact": "legacy", "op": "eq", "value": True}},
            {"default": "2026-08-02"},
        ])


def test_x3_empty_branch_list_rejected():             # ADR-008 (2)
    with pytest.raises(RuleValidationError):
        make_rule(applies_from=[])


# --- timeline_ref (ADR-011(4)) --------------------------------------------

def test_timeline_ref_loads_as_list():
    r = make_rule(timeline_ref=["Art. 50(1),(3),(4) transparency"])
    assert r.timeline_ref == ["Art. 50(1),(3),(4) transparency"]


def test_timeline_ref_absent_is_none():
    assert make_rule().timeline_ref is None


def test_timeline_ref_wrong_type_rejected():          # ADR-008 (4)
    with pytest.raises(RuleValidationError):
        make_rule(timeline_ref="not-a-list")


def test_timeline_ref_non_string_entry_rejected():    # ADR-008 (4)
    with pytest.raises(RuleValidationError):
        make_rule(timeline_ref=[123])


# --- X1 render support -----------------------------------------------------

def test_render_not_applicable_verdict():
    r = make_rule(applicable_if=IN_SCOPE)
    v = evaluate([r], {"personal_use": True, "x": True}, ACTIVE, CV)[0]
    out = render_report([v], ACTIVE, CV, DISCLAIMER)
    assert "[NOT_APPLICABLE]" in out
    assert "scope" in out
