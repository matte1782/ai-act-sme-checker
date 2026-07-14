"""L2 YAML rule loader with the INV-2 statute gate.

A rule without a citation (corpus_id + article + paragraph) or without
applies_from does not load. Ever. (ADR-002, ADR-005; architecture INV-2.)

Hardened after the Gate-2 adversarial bypass hunt: citations must be
non-empty strings; unknown keys are rejected (a typo like applies_untill
must never silently produce a perpetual rule); the logic tree is
structurally validated at load time; file-level errors surface as
RuleValidationError; rule ids are unique per file.
"""
import dataclasses
import datetime as dt
from typing import Optional

import yaml

VERDICTS = ("COMPLIANT", "NON_COMPLIANT")
CITATION_FIELDS = ("corpus_id", "article", "paragraph")
_RULE_KEYS = {
    "id",
    "legal_source",
    "applies_from",
    "applies_until",
    "logic",
    "verdict",
    "rationale_key",
}
_LOGIC_KINDS = ("fact", "all", "any", "not")


class RuleValidationError(ValueError):
    """Raised when a rule is missing citation, validity dates, or logic."""


@dataclasses.dataclass(frozen=True)
class Rule:
    id: str
    legal_source: dict
    applies_from: dt.date
    applies_until: Optional[dt.date]
    logic: dict
    verdict: str
    rationale_key: str


def _req_str(value, rule_id, field):
    if not isinstance(value, str) or not value.strip():
        raise RuleValidationError(
            f"rule {rule_id}: {field} must be a non-empty string, got {value!r}"
        )
    return value


def _to_date(value, rule_id, field):
    if isinstance(value, dt.datetime):
        raise RuleValidationError(
            f"rule {rule_id}: {field} must be a date, not datetime"
        )
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        try:
            return dt.date.fromisoformat(value)
        except ValueError as exc:
            raise RuleValidationError(
                f"rule {rule_id}: {field} {value!r} is not an ISO date"
            ) from exc
    raise RuleValidationError(f"rule {rule_id}: {field} {value!r} is not a date")


def _validate_logic(node, rule_id, path="logic"):
    if not isinstance(node, dict):
        raise RuleValidationError(f"rule {rule_id}: {path} must be a mapping")
    kinds = [k for k in _LOGIC_KINDS if k in node]
    if len(kinds) != 1:
        raise RuleValidationError(
            f"rule {rule_id}: {path} must have exactly one of "
            f"{_LOGIC_KINDS}, got {sorted(node)}"
        )
    kind = kinds[0]
    if kind == "fact":
        extra = set(node) - {"fact", "op", "value"}
        if extra:
            raise RuleValidationError(
                f"rule {rule_id}: {path} unexpected keys {sorted(extra)}"
            )
        _req_str(node["fact"], rule_id, f"{path}.fact")
        if node.get("op") not in ("eq", "in"):
            raise RuleValidationError(f"rule {rule_id}: {path}.op must be eq or in")
        if "value" not in node:
            raise RuleValidationError(f"rule {rule_id}: {path} missing value")
        if node["op"] == "in" and not isinstance(node["value"], list):
            raise RuleValidationError(
                f"rule {rule_id}: {path} 'in' value must be a list "
                f"(strings would use substring semantics)"
            )
    elif kind in ("all", "any"):
        extra = set(node) - {kind}
        if extra:
            raise RuleValidationError(
                f"rule {rule_id}: {path} unexpected keys {sorted(extra)}"
            )
        children = node[kind]
        if not isinstance(children, list) or not children:
            raise RuleValidationError(
                f"rule {rule_id}: {path} '{kind}' requires a non-empty list"
            )
        for index, child in enumerate(children):
            _validate_logic(child, rule_id, f"{path}.{kind}[{index}]")
    else:  # not
        extra = set(node) - {"not"}
        if extra:
            raise RuleValidationError(
                f"rule {rule_id}: {path} unexpected keys {sorted(extra)}"
            )
        _validate_logic(node["not"], rule_id, f"{path}.not")


def parse_rule(data):
    if not isinstance(data, dict):
        raise RuleValidationError(f"rule must be a mapping, got {type(data).__name__}")
    rule_id = data.get("id")
    _req_str(rule_id, rule_id, "id")
    extra = set(data) - _RULE_KEYS
    if extra:
        raise RuleValidationError(
            f"rule {rule_id}: unknown keys {sorted(extra)} "
            f"(refusing to silently ignore; check spelling)"
        )
    source = data.get("legal_source")
    if not isinstance(source, dict):
        raise RuleValidationError(f"rule {rule_id}: missing legal_source")
    extra = set(source) - set(CITATION_FIELDS)
    if extra:
        raise RuleValidationError(
            f"rule {rule_id}: legal_source unknown keys {sorted(extra)}"
        )
    for field in CITATION_FIELDS:
        _req_str(source.get(field), rule_id, f"legal_source.{field}")
    if data.get("applies_from") is None:
        raise RuleValidationError(f"rule {rule_id}: missing applies_from")
    applies_from = _to_date(data["applies_from"], rule_id, "applies_from")
    applies_until = None
    if data.get("applies_until") is not None:
        applies_until = _to_date(data["applies_until"], rule_id, "applies_until")
        if applies_until < applies_from:
            raise RuleValidationError(
                f"rule {rule_id}: applies_until precedes applies_from"
            )
    logic = data.get("logic")
    if not isinstance(logic, dict) or not logic:
        raise RuleValidationError(f"rule {rule_id}: missing/empty logic tree")
    _validate_logic(logic, rule_id)
    verdict = data.get("verdict")
    if verdict not in VERDICTS:
        raise RuleValidationError(f"rule {rule_id}: verdict must be one of {VERDICTS}")
    rationale_key = _req_str(data.get("rationale_key"), rule_id, "rationale_key")
    return Rule(
        id=rule_id,
        legal_source=dict(source),
        applies_from=applies_from,
        applies_until=applies_until,
        logic=logic,
        verdict=verdict,
        rationale_key=rationale_key,
    )


def load_rules_file(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise RuleValidationError(
            f"{path}: unreadable rules file ({type(exc).__name__})"
        ) from exc
    if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
        raise RuleValidationError(f"{path}: expected a top-level 'rules' list")
    rules = [parse_rule(entry) for entry in data["rules"]]
    seen = set()
    for rule in rules:
        if rule.id in seen:
            raise RuleValidationError(f"{path}: duplicate rule id {rule.id!r}")
        seen.add(rule.id)
    return rules
