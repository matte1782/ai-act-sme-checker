"""L4 engine core: pure trivalent evaluation (ADR-003).

evaluate() is a pure function: no I/O, no clock reads - as_of_date and
corpus_version are arguments. Kleene K3 over {all, any, not, fact-leaf};
UNKNOWN propagates; the default verdict is UNDETERMINED.

INV-1 keystone: a COMPLIANT verdict may never rest on a dependency set
containing an UNKNOWN fact - even when K3 masks it (any(TRUE, UNKNOWN)
is TRUE); such outcomes are demoted to UNDETERMINED.

Hardened after the Gate-2 adversarial bypass hunt: strict as_of_date
type gate (a duck-typed non-date silently bypassed the temporal window);
exactly-one-kind logic nodes (defense in depth behind the loader);
outputs never alias rule state; temporal-inactive verdicts still carry
a citation-bearing explanation leaf (INV-5 has no vacuous pass).
"""
import copy
import dataclasses
import datetime as dt

from engine.facts import UNKNOWN, k3_all, k3_any, k3_not

STATUS_COMPLIANT = "COMPLIANT"
STATUS_NON_COMPLIANT = "NON_COMPLIANT"
STATUS_UNDETERMINED = "UNDETERMINED"

_LOGIC_KINDS = ("fact", "all", "any", "not")


class EvaluationError(ValueError):
    """Malformed input reaching the core (the loader should prevent this)."""


def _label(value):
    if value is True:
        return "TRUE"
    if value is False:
        return "FALSE"
    return "UNKNOWN"


@dataclasses.dataclass
class Verdict:
    rule_id: str
    status: str
    citation: dict
    explanation: dict
    unknown_facts: list
    rationale_key: str
    as_of: dt.date
    corpus_version: str


def _eval_node(node, facts, citation, unknowns):
    if not isinstance(node, dict):
        raise EvaluationError(f"logic node must be a mapping: {node!r}")
    kinds = [k for k in _LOGIC_KINDS if k in node]
    if len(kinds) != 1:
        raise EvaluationError(
            f"logic node must have exactly one of {_LOGIC_KINDS}: {sorted(node)}"
        )
    kind = kinds[0]
    if kind == "fact":
        name = node["fact"]
        op = node.get("op")
        expected = node.get("value")
        if op not in ("eq", "in"):
            raise EvaluationError(f"unsupported op {op!r} on fact {name}")
        if op == "in" and not isinstance(expected, list):
            raise EvaluationError(f"'in' value must be a list on fact {name}")
        actual = facts.get(name, UNKNOWN)
        if actual is UNKNOWN or actual is None:
            unknowns.add(name)
            value = UNKNOWN
        elif op == "eq":
            value = bool(actual == expected)
        else:
            value = bool(actual in expected)
        leaf = {
            "op": "fact",
            "fact": name,
            "test": {"op": op, "value": copy.deepcopy(expected)},
            "value": _label(value),
            "citation": {
                "corpus_id": citation["corpus_id"],
                "article": citation["article"],
            },
        }
        return value, leaf
    if kind in ("all", "any"):
        combiner = k3_all if kind == "all" else k3_any
        children = node[kind]
        if not isinstance(children, list) or not children:
            raise EvaluationError(f"'{kind}' requires a non-empty list")
        results = [_eval_node(child, facts, citation, unknowns) for child in children]
        value = combiner(result for result, _ in results)
        return value, {
            "op": kind,
            "value": _label(value),
            "children": [tree for _, tree in results],
        }
    child_value, child_tree = _eval_node(node["not"], facts, citation, unknowns)
    value = k3_not(child_value)
    return value, {"op": "not", "value": _label(value), "children": [child_tree]}


def _applicability_reason(rule, as_of):
    if as_of < rule.applies_from:
        return f"not yet applicable (applies_from {rule.applies_from.isoformat()})"
    # applies_until is INCLUSIVE: the rule is active through its last day.
    if rule.applies_until is not None and as_of > rule.applies_until:
        return f"no longer applicable (applies_until {rule.applies_until.isoformat()})"
    return None


def evaluate(rules, facts, as_of_date, corpus_version):
    if isinstance(as_of_date, dt.datetime) or not isinstance(as_of_date, dt.date):
        raise EvaluationError(
            f"as_of_date must be a datetime.date, got {as_of_date!r}"
        )
    verdicts = []
    for rule in rules:
        citation = rule.legal_source
        reason = _applicability_reason(rule, as_of_date)
        if reason is not None:
            explanation = {
                "op": "rule",
                "rule_id": rule.id,
                "value": "UNKNOWN",
                "reason": reason,
                "unknown_facts": [],
                "children": [
                    {
                        "op": "applicability",
                        "value": "UNKNOWN",
                        "reason": reason,
                        "citation": {
                            "corpus_id": citation["corpus_id"],
                            "article": citation["article"],
                        },
                    }
                ],
            }
            verdicts.append(
                Verdict(
                    rule_id=rule.id,
                    status=STATUS_UNDETERMINED,
                    citation=dict(citation),
                    explanation=explanation,
                    unknown_facts=[],
                    rationale_key=rule.rationale_key,
                    as_of=as_of_date,
                    corpus_version=corpus_version,
                )
            )
            continue
        unknowns = set()
        value, tree = _eval_node(rule.logic, facts, citation, unknowns)
        unknown_facts = sorted(unknowns)
        if value is UNKNOWN:
            status = STATUS_UNDETERMINED
        elif value is True:
            status = rule.verdict
        else:
            status = (
                STATUS_NON_COMPLIANT
                if rule.verdict == STATUS_COMPLIANT
                else STATUS_COMPLIANT
            )
        # INV-1 keystone (see module docstring): never COMPLIANT on unknowns.
        if status == STATUS_COMPLIANT and unknown_facts:
            status = STATUS_UNDETERMINED
        explanation = {
            "op": "rule",
            "rule_id": rule.id,
            "value": tree["value"],
            "unknown_facts": list(unknown_facts),
            "children": [tree],
        }
        if status == STATUS_UNDETERMINED and unknown_facts:
            explanation["reason"] = "unknown facts: " + ", ".join(unknown_facts)
        verdicts.append(
            Verdict(
                rule_id=rule.id,
                status=status,
                citation=dict(citation),
                explanation=explanation,
                unknown_facts=unknown_facts,
                rationale_key=rule.rationale_key,
                as_of=as_of_date,
                corpus_version=corpus_version,
            )
        )
    return verdicts
