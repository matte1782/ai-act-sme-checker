# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
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
# X1 (Gate-4, ADR-009): a rule outside its material scope (Art. 2) is
# NOT_APPLICABLE - distinct from UNDETERMINED (we lack a fact) and from
# the temporal-INACTIVE shape (UNDETERMINED + applicability leaf).
STATUS_NOT_APPLICABLE = "NOT_APPLICABLE"

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


def _applicability_reason(applies_from, applies_until, as_of):
    if as_of < applies_from:
        return f"not yet applicable (applies_from {applies_from.isoformat()})"
    # applies_until is INCLUSIVE: the rule is active through its last day.
    if applies_until is not None and as_of > applies_until:
        return f"no longer applicable (applies_until {applies_until.isoformat()})"
    return None


def _resolve_applies_from(applies_from, facts, citation):
    """X3 fail-closed date selection. Returns (date|None, when_children,
    unknown_facts). A scalar resolves immediately. For a branch list the
    first branch whose 'when' is TRUE wins; a 'when' that is UNKNOWN
    stops selection (date is None, facts named) rather than skipping to
    the default - a wrong-deadline verdict is never rendered on a guess."""
    if isinstance(applies_from, dt.date):
        return applies_from, [], []
    unknowns = set()
    children = []
    for branch in applies_from:
        if "default" in branch:
            return branch["default"], children, []
        value, tree = _eval_node(branch["when"], facts, citation, unknowns)
        children.append(tree)
        if value is True:
            return branch["date"], children, []
        if value is UNKNOWN:
            return None, children, sorted(unknowns)
        # value is False: this window does not apply; try the next branch.
    # The loader guarantees a trailing default, so this is unreachable.
    raise EvaluationError("applies_from branch list without a default")


def evaluate(rules, facts, as_of_date, corpus_version):
    if isinstance(as_of_date, dt.datetime) or not isinstance(as_of_date, dt.date):
        raise EvaluationError(
            f"as_of_date must be a datetime.date, got {as_of_date!r}"
        )
    verdicts = []
    for rule in rules:
        citation = rule.legal_source
        cite_leaf = {
            "corpus_id": citation["corpus_id"],
            "article": citation["article"],
        }

        def _verdict(status, explanation, unknown_facts):
            return Verdict(
                rule_id=rule.id,
                status=status,
                citation=dict(citation),
                explanation=explanation,
                unknown_facts=unknown_facts,
                rationale_key=rule.rationale_key,
                as_of=as_of_date,
                corpus_version=corpus_version,
            )

        # X3: resolve the temporal window (may consult facts; fail-closed).
        resolved_from, when_children, from_unknowns = _resolve_applies_from(
            rule.applies_from, facts, citation
        )
        if resolved_from is None:
            reason = "date selection needs unknown facts: " + ", ".join(from_unknowns)
            explanation = {
                "op": "rule",
                "rule_id": rule.id,
                "value": "UNKNOWN",
                "reason": reason,
                "unknown_facts": list(from_unknowns),
                "children": when_children,
            }
            verdicts.append(_verdict(STATUS_UNDETERMINED, explanation, list(from_unknowns)))
            continue

        # X4 precedence (1): temporal beats scope and logic -> INACTIVE shape.
        reason = _applicability_reason(resolved_from, rule.applies_until, as_of_date)
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
                        # C1 (Gate-5): the RESOLVED window date (X3 branch
                        # already selected) as structured data - the deadlines
                        # renderer reads this, never the reason string.
                        "applies_from": resolved_from.isoformat(),
                        "citation": dict(cite_leaf),
                    }
                ],
            }
            verdicts.append(_verdict(STATUS_UNDETERMINED, explanation, []))
            continue

        # X4 precedence (2): applicable_if scope gate.
        if rule.applicable_if is not None:
            scope_unknowns = set()
            scope_value, scope_tree = _eval_node(
                rule.applicable_if, facts, citation, scope_unknowns
            )
            if scope_value is UNKNOWN:
                # X5: unknown scope is UNDETERMINED (named), never NOT_APPLICABLE.
                named = sorted(scope_unknowns)
                explanation = {
                    "op": "rule",
                    "rule_id": rule.id,
                    "value": "UNKNOWN",
                    "reason": "unknown scope facts: " + ", ".join(named),
                    "unknown_facts": named,
                    "children": [
                        {
                            "op": "scope",
                            "value": "UNKNOWN",
                            "reason": "material scope undetermined",
                            "citation": dict(cite_leaf),
                            "children": [scope_tree],
                        }
                    ],
                }
                verdicts.append(_verdict(STATUS_UNDETERMINED, explanation, named))
                continue
            if scope_value is False:
                explanation = {
                    "op": "rule",
                    "rule_id": rule.id,
                    "value": "NOT_APPLICABLE",
                    "reason": "out of material scope (applicable_if is false)",
                    "unknown_facts": [],
                    "children": [
                        {
                            "op": "scope",
                            "value": "FALSE",
                            "reason": "rule not applicable (applicable_if is false)",
                            "citation": dict(cite_leaf),
                            "children": [scope_tree],
                        }
                    ],
                }
                verdicts.append(_verdict(STATUS_NOT_APPLICABLE, explanation, []))
                continue
            # scope_value is True: in scope; fall through to logic.

        # X4 precedence (3): logic.
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
        verdicts.append(_verdict(status, explanation, unknown_facts))
    return verdicts
