# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
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
import pathlib
import re
from typing import Optional

import yaml

VERDICTS = ("COMPLIANT", "NON_COMPLIANT")
CITATION_FIELDS = ("corpus_id", "article", "paragraph")
_RULE_KEYS = {
    "id",
    "legal_source",
    "applies_from",
    "applies_until",
    "applicable_if",
    "timeline_ref",
    "logic",
    "verdict",
    "rationale_key",
}
_LOGIC_KINDS = ("fact", "all", "any", "not")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class RuleValidationError(ValueError):
    """Raised when a rule is missing citation, validity dates, or logic."""


class _StrictYamlLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate mapping keys (R1, ADR-008 (7)).

    PyYAML's default lets the LAST duplicate win silently, so a second
    'applies_from' could shadow the temporal window without a trace.
    """

    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                duplicate = key in seen
            except TypeError as exc:
                raise RuleValidationError(
                    f"unhashable mapping key at {key_node.start_mark}"
                ) from exc
            if duplicate:
                raise RuleValidationError(
                    f"duplicate mapping key {key!r} at {key_node.start_mark}"
                )
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


@dataclasses.dataclass(frozen=True)
class Rule:
    id: str
    legal_source: dict
    # X3: a date, OR a branch list [{when: <tree>, date}, ..., {default: date}]
    applies_from: object
    applies_until: Optional[dt.date]
    logic: dict
    verdict: str
    rationale_key: str
    # X2 (optional) scope predicate; X3 anti-drift date anchors (ADR-011(4)).
    applicable_if: Optional[dict] = None
    timeline_ref: Optional[list] = None


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
        # R3: fromisoformat (>=3.11) accepts '20260101' and friends;
        # gate on the canonical form BEFORE parsing (ADR-008 (6)).
        if not _DATE_RE.match(value):
            raise RuleValidationError(
                f"rule {rule_id}: {field} {value!r} must match YYYY-MM-DD"
            )
        try:
            return dt.date.fromisoformat(value)
        except ValueError as exc:
            raise RuleValidationError(
                f"rule {rule_id}: {field} {value!r} is not an ISO date"
            ) from exc
    raise RuleValidationError(f"rule {rule_id}: {field} {value!r} is not a date")


def _parse_applies_from(value, rule_id):
    """X3: applies_from is either a scalar date or a conditional branch
    list. Validated per ADR-008 (missing/empty/wrong-type/unknown-key/
    boundary/duplicate) so date selection can never fail open at runtime."""
    if not isinstance(value, list):
        return _to_date(value, rule_id, "applies_from")
    if not value:
        raise RuleValidationError(
            f"rule {rule_id}: applies_from branch list is empty"
        )
    parsed = []
    default_seen = False
    last = len(value) - 1
    for index, branch in enumerate(value):
        at = f"applies_from[{index}]"
        if not isinstance(branch, dict) or not branch:
            raise RuleValidationError(
                f"rule {rule_id}: {at} must be a non-empty mapping"
            )
        keys = set(branch)
        if "default" in keys:
            if keys != {"default"}:
                raise RuleValidationError(
                    f"rule {rule_id}: {at} default branch takes only 'default', "
                    f"got {sorted(keys, key=repr)}"
                )
            if index != last:
                raise RuleValidationError(
                    f"rule {rule_id}: {at} 'default' branch must be last"
                )
            parsed.append({"default": _to_date(branch["default"], rule_id, f"{at}.default")})
            default_seen = True
        else:
            if keys != {"when", "date"}:
                raise RuleValidationError(
                    f"rule {rule_id}: {at} branch keys must be exactly "
                    f"'when','date', got {sorted(keys, key=repr)}"
                )
            _validate_logic(branch["when"], rule_id, f"{at}.when")
            parsed.append(
                {
                    "when": branch["when"],
                    "date": _to_date(branch["date"], rule_id, f"{at}.date"),
                }
            )
    if not default_seen:
        raise RuleValidationError(
            f"rule {rule_id}: applies_from branch list needs exactly one "
            f"'default' branch (last)"
        )
    return parsed


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
    applies_from = _parse_applies_from(data["applies_from"], rule_id)
    applies_until = None
    if data.get("applies_until") is not None:
        applies_until = _to_date(data["applies_until"], rule_id, "applies_until")
        if isinstance(applies_from, dt.date) and applies_until < applies_from:
            raise RuleValidationError(
                f"rule {rule_id}: applies_until precedes applies_from"
            )
    logic = data.get("logic")
    if not isinstance(logic, dict) or not logic:
        raise RuleValidationError(f"rule {rule_id}: missing/empty logic tree")
    _validate_logic(logic, rule_id)
    # X2: optional scope predicate, validated with the same grammar as logic.
    applicable_if = data.get("applicable_if")
    if applicable_if is not None:
        if not isinstance(applicable_if, dict) or not applicable_if:
            raise RuleValidationError(
                f"rule {rule_id}: applicable_if must be a non-empty predicate mapping"
            )
        _validate_logic(applicable_if, rule_id, "applicable_if")
    # ADR-011(4): timeline_ref anchors every date to corpus/timeline.yaml.
    timeline_ref = data.get("timeline_ref")
    if timeline_ref is not None:
        if not isinstance(timeline_ref, list) or not timeline_ref:
            raise RuleValidationError(
                f"rule {rule_id}: timeline_ref must be a non-empty list of strings"
            )
        for index, item in enumerate(timeline_ref):
            _req_str(item, rule_id, f"timeline_ref[{index}]")
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
        applicable_if=applicable_if,
        timeline_ref=list(timeline_ref) if timeline_ref is not None else None,
    )


def load_yaml_strict(path):
    """Parse a YAML file rejecting duplicate mapping keys (ADR-008 (7)).
    Corpus manifest/timeline and rules files share this gate."""
    try:
        with open(path, encoding="utf-8") as fh:
            # SafeLoader-derived (no arbitrary-type construction);
            # only adds duplicate-key rejection on top of safe_load.
            return yaml.load(fh, Loader=_StrictYamlLoader)
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise RuleValidationError(
            f"{path}: unreadable YAML ({type(exc).__name__})"
        ) from exc


def load_rules_file(path):
    data = load_yaml_strict(path)
    if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
        raise RuleValidationError(f"{path}: expected a top-level 'rules' list")
    rules = [parse_rule(entry) for entry in data["rules"]]
    seen = set()
    for rule in rules:
        if rule.id in seen:
            raise RuleValidationError(f"{path}: duplicate rule id {rule.id!r}")
        seen.add(rule.id)
    return rules


def load_rules_dir(path):
    """R2: load ALL *.yaml rules files in path (sorted) and reject
    cross-file duplicate rule ids. Fail-closed at the directory surface:
    a missing dir, an empty dir, or a stray .yml file (which the *.yaml
    glob would silently skip) is an error, never a silent empty engine.
    """
    root = pathlib.Path(path)
    if not root.is_dir():
        raise RuleValidationError(f"{path}: not a directory")
    stray = sorted(entry.name for entry in root.glob("*.yml"))
    if stray:
        raise RuleValidationError(
            f"{path}: .yml files would silently escape the *.yaml glob: "
            f"{stray} (rename to .yaml)"
        )
    files = sorted(root.glob("*.yaml"))
    if not files:
        raise RuleValidationError(
            f"{path}: no *.yaml rules files (refusing an empty engine)"
        )
    rules = []
    origin = {}
    for file in files:
        for rule in load_rules_file(file):
            if rule.id in origin:
                raise RuleValidationError(
                    f"duplicate rule id {rule.id!r} across files: "
                    f"{origin[rule.id]} and {file.name}"
                )
            origin[rule.id] = file.name
            rules.append(rule)
    return rules
