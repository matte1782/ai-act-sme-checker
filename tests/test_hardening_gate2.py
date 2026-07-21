# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
"""Pinning tests for the Gate-2 adversarial bypass hunt findings.

Every test here encodes a confirmed attack from the post-GREEN hunt:
if one regresses, a real bypass reopens. Synthetic fixtures only.
"""
import copy
import datetime as dt

import pytest

from engine.core import EvaluationError, evaluate
from engine.loader import Rule, RuleValidationError, load_rules_file, parse_rule
from engine.render import DISCLAIMER, render_report

AS_OF = dt.date(2026, 7, 1)


def base(**overrides):
    data = {
        "id": "r-hard",
        "legal_source": {
            "corpus_id": "TEST-ACT-1",
            "article": "Art. 9",
            "paragraph": "1",
        },
        "applies_from": "2026-01-01",
        "logic": {"fact": "f_true", "op": "eq", "value": True},
        "verdict": "COMPLIANT",
        "rationale_key": "test.hard",
    }
    data.update(overrides)
    return data


# --- INV-2: citation gate must reject non-substantive citations ---------

@pytest.mark.parametrize("field", ["corpus_id", "article", "paragraph"])
@pytest.mark.parametrize("value", ["  ", "\n", "\t "])
def test_whitespace_citation_rejected(field, value):
    data = base()
    data["legal_source"][field] = value
    with pytest.raises(RuleValidationError):
        parse_rule(data)


@pytest.mark.parametrize("field", ["corpus_id", "article", "paragraph"])
@pytest.mark.parametrize("value", [True, 1, ["a"], {"x": 1}])
def test_non_string_citation_rejected(field, value):
    data = base()
    data["legal_source"][field] = value
    with pytest.raises(RuleValidationError):
        parse_rule(data)


def test_unknown_legal_source_key_rejected():
    data = base()
    data["legal_source"]["note"] = "extra"
    with pytest.raises(RuleValidationError):
        parse_rule(data)


# --- INV-2: unknown keys must never be silently dropped ------------------

def test_misspelled_applies_until_rejected():
    with pytest.raises(RuleValidationError):
        parse_rule(base(applies_untill="2026-06-30"))


def test_unknown_top_level_key_rejected():
    with pytest.raises(RuleValidationError):
        parse_rule(base(extra_key=1))


@pytest.mark.parametrize("value", ["  ", True, ["a"]])
def test_bad_id_rejected(value):
    with pytest.raises(RuleValidationError):
        parse_rule(base(id=value))


@pytest.mark.parametrize("value", ["  ", 1])
def test_bad_rationale_key_rejected(value):
    with pytest.raises(RuleValidationError):
        parse_rule(base(rationale_key=value))


# --- Loader: logic tree is structurally validated at load time ----------

def test_dual_key_logic_node_rejected():
    logic = {
        "fact": "f_true",
        "op": "eq",
        "value": True,
        "any": [{"fact": "f_unknown", "op": "eq", "value": True}],
    }
    with pytest.raises(RuleValidationError):
        parse_rule(base(logic=logic))


def test_in_op_with_string_value_rejected():
    with pytest.raises(RuleValidationError):
        parse_rule(base(logic={"fact": "b", "op": "in", "value": "xyz"}))


def test_in_op_with_non_list_value_rejected():
    with pytest.raises(RuleValidationError):
        parse_rule(base(logic={"fact": "a", "op": "in", "value": 5}))


def test_unknown_logic_node_rejected():
    with pytest.raises(RuleValidationError):
        parse_rule(base(logic={"garbage": None}))


def test_empty_combiner_rejected():
    with pytest.raises(RuleValidationError):
        parse_rule(base(logic={"all": []}))


def test_nested_invalid_leaf_rejected():
    logic = {"all": [{"fact": "a", "op": "bogus", "value": True}]}
    with pytest.raises(RuleValidationError):
        parse_rule(base(logic=logic))


# --- Loader: file-level integrity ----------------------------------------

def test_duplicate_rule_ids_rejected(tmp_path):
    path = tmp_path / "rules.yaml"
    entry = (
        "  - id: r-dup\n"
        "    legal_source: {corpus_id: TEST-ACT-1, article: Art. 1, paragraph: '1'}\n"
        "    applies_from: 2026-01-01\n"
        "    logic: {fact: f_true, op: eq, value: true}\n"
        "    verdict: COMPLIANT\n"
        "    rationale_key: k\n"
    )
    path.write_text("rules:\n" + entry + entry, encoding="utf-8")
    with pytest.raises(RuleValidationError):
        load_rules_file(str(path))


def test_non_utf8_file_raises_domain_error(tmp_path):
    path = tmp_path / "rules.yaml"
    path.write_bytes(b"rules:\n  - id: r\xff\xfe1\n")
    with pytest.raises(RuleValidationError):
        load_rules_file(str(path))


def test_multi_document_yaml_raises_domain_error(tmp_path):
    path = tmp_path / "rules.yaml"
    path.write_text("rules: []\n---\nrules: []\n", encoding="utf-8")
    with pytest.raises(RuleValidationError):
        load_rules_file(str(path))


def test_missing_file_raises_domain_error(tmp_path):
    with pytest.raises(RuleValidationError):
        load_rules_file(str(tmp_path / "absent.yaml"))


# --- Core: as_of_date type gate (INV-3 bypass) ---------------------------

class _NotADate:
    __lt__ = staticmethod(lambda *a: False)
    __gt__ = staticmethod(lambda *a: False)


@pytest.mark.parametrize(
    "bad",
    [
        dt.datetime(2026, 12, 15, 10, 0),
        dt.datetime(2026, 12, 15, tzinfo=dt.timezone.utc),
        "2026-12-15",
        None,
        True,
        _NotADate(),
    ],
)
def test_non_date_as_of_rejected(bad):
    rule = parse_rule(base())
    with pytest.raises(EvaluationError):
        evaluate([rule], {"f_true": True}, bad, "v1")


def test_plain_date_as_of_accepted():
    rule = parse_rule(base())
    assert evaluate([rule], {"f_true": True}, AS_OF, "v1")[0].status == "COMPLIANT"


# --- Core: no live-state aliasing in outputs -----------------------------

def test_explanation_does_not_alias_rule_logic():
    rule = parse_rule(base(logic={"fact": "b", "op": "in", "value": ["x", "y"]}))
    facts = {"b": "z"}
    first = evaluate([rule], facts, AS_OF, "v1")[0]
    assert first.status == "NON_COMPLIANT"
    leaf = first.explanation["children"][0]
    assert leaf["test"]["value"] is not rule.logic["value"]
    leaf["test"]["value"].append("z")  # tampering with the OUTPUT
    again = evaluate([rule], facts, AS_OF, "v1")[0]
    assert again.status == "NON_COMPLIANT"


def test_unknown_facts_not_shared_with_explanation():
    rule = parse_rule(base())
    verdict = evaluate([rule], {}, AS_OF, "v1")[0]
    assert verdict.unknown_facts is not verdict.explanation["unknown_facts"]
    verdict.explanation["unknown_facts"].clear()
    assert verdict.unknown_facts == ["f_true"]


# --- Core: defense in depth against hand-built malformed trees -----------

def test_core_rejects_dual_key_node_directly():
    rule = Rule(
        id="r-hand",
        legal_source={"corpus_id": "C", "article": "A", "paragraph": "1"},
        applies_from=dt.date(2026, 1, 1),
        applies_until=None,
        logic={"fact": "x", "op": "eq", "value": True, "any": []},
        verdict="COMPLIANT",
        rationale_key="k",
    )
    with pytest.raises(EvaluationError):
        evaluate([rule], {"x": True}, AS_OF, "v1")


# --- Renderer: no line injection via author-controlled strings -----------

def test_fact_name_newline_cannot_forge_verdict_line():
    injected = "x\n[COMPLIANT] FAKE-RULE (C A(1))"
    rule = Rule(
        id="r-inj",
        legal_source={"corpus_id": "C", "article": "A", "paragraph": "1"},
        applies_from=dt.date(2026, 1, 1),
        applies_until=None,
        logic={"fact": injected, "op": "eq", "value": True},
        verdict="COMPLIANT",
        rationale_key="k",
    )
    verdicts = evaluate([rule], {injected: True}, AS_OF, "v1")
    out = render_report(verdicts, AS_OF, "v1", disclaimer=DISCLAIMER)
    forged = [ln for ln in out.splitlines() if ln.startswith("[COMPLIANT] FAKE-RULE")]
    assert forged == []
