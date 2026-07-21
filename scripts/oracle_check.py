#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
"""L6 oracle checker: the frozen golden set as a self-arming gate.

The golden scenarios (oracle/golden/*.yaml) are the SPEC for Gate 4:
rules and the facts schema are written to satisfy them, never vice
versa - case authors != rule authors (ADR-009, anti-confirmation-bias).

States (surfaced in check.sh '== oracle'):
- ORACLE_ERR <detail>  exit 1: malformed golden set (ADR-008 classes);
- ORACLE_PENDING n=K   exit 0: rules/*.yaml absent or empty. Format
  validation still runs; this is the ONLY sanctioned non-evaluating
  pass (no masking);
- ORACLE_FAIL <list>   exit 1: any expect.status mismatch;
- ORACLE_GREEN n=K     exit 0: every scenario satisfied.

The expected-status vocabulary extends the engine's (Gate-4 work,
ADR-009):
- INACTIVE matches an UNDETERMINED verdict whose explanation carries
  an op=='applicability' leaf (the engine's temporal-inactive shape);
- NOT_APPLICABLE requires the Gate-4 status extension: until the
  engine exposes STATUS_NOT_APPLICABLE, an armed run lists it as a
  mismatch;
- UNDETERMINED (fail-closed) additionally requires the unknown facts
  to be NAMED in verdict.unknown_facts (S09 contract), which also
  keeps it disjoint from INACTIVE.
Group mapping (Gate-4 naming contract): a verdict belongs to
rule_group G iff its rule_id == G or rule_id starts with 'G-'.
Armed runs stamp corpus_version from corpus/manifest.yaml and require
a well-formed corpus/timeline.yaml (the temporal source of truth the
rules' applies_from dates encode).
"""
import datetime as dt
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from engine import core
from engine.loader import RuleValidationError, load_rules_dir, load_yaml_strict

SCENARIO_KEYS = {"id", "title_it", "facts", "as_of", "expect", "note"}
REQUIRED_KEYS = ("id", "title_it", "facts", "as_of", "expect")
EXPECT_KEYS = {"rule_group", "status", "cite"}
EXPECT_STATUSES = (
    "COMPLIANT",
    "NON_COMPLIANT",
    "UNDETERMINED",
    "INACTIVE",
    "NOT_APPLICABLE",
)


class OracleError(ValueError):
    """Malformed golden set: missing / empty / whitespace / wrong-type /
    unknown-key / duplicate-id (ADR-008)."""


def _req_str(value, where, field):
    if not isinstance(value, str) or not value.strip():
        raise OracleError(
            f"{where}: {field} must be a non-empty string, got {value!r}"
        )
    return value


def parse_scenario(data, where):
    if not isinstance(data, dict):
        raise OracleError(f"{where}: scenario must be a mapping")
    # key=repr: unknown keys may be non-comparable types (int + str);
    # the report must not die in sorted() (adversarial-hunt catch).
    extra = sorted(set(data) - SCENARIO_KEYS, key=repr)
    if extra:
        raise OracleError(
            f"{where}: unknown keys {extra} "
            f"(refusing to silently ignore; check spelling)"
        )
    missing = [key for key in REQUIRED_KEYS if key not in data]
    if missing:
        raise OracleError(f"{where}: missing keys {missing}")
    _req_str(data["id"], where, "id")
    _req_str(data["title_it"], where, "title_it")
    facts = data["facts"]
    if not isinstance(facts, dict) or not facts:
        raise OracleError(f"{where}: facts must be a non-empty mapping")
    for name, value in facts.items():
        _req_str(name, where, "facts key")
        if isinstance(value, bool):
            continue
        if isinstance(value, dt.date) and not isinstance(value, dt.datetime):
            continue
        if isinstance(value, str) and value.strip():
            continue
        raise OracleError(
            f"{where}: facts.{name} must be a bool, enum string or date, "
            f"got {value!r} (omitted facts are UNKNOWN by design; never null)"
        )
    as_of = data["as_of"]
    if isinstance(as_of, dt.datetime) or not isinstance(as_of, dt.date):
        raise OracleError(
            f"{where}: as_of must be an unquoted ISO date, got {as_of!r}"
        )
    expect = data["expect"]
    if not isinstance(expect, list) or not expect:
        raise OracleError(f"{where}: expect must be a non-empty list")
    seen_groups = set()
    for index, entry in enumerate(expect):
        at = f"{where}: expect[{index}]"
        if not isinstance(entry, dict):
            raise OracleError(f"{at} must be a mapping")
        if set(entry) != EXPECT_KEYS:
            raise OracleError(
                f"{at} keys must be exactly {sorted(EXPECT_KEYS)}, "
                f"got {sorted(entry, key=repr)}"
            )
        group = _req_str(entry["rule_group"], at, "rule_group")
        if entry["status"] not in EXPECT_STATUSES:
            raise OracleError(
                f"{at}: status must be one of {EXPECT_STATUSES}, "
                f"got {entry['status']!r}"
            )
        _req_str(entry["cite"], at, "cite")
        if group in seen_groups:
            raise OracleError(f"{at}: duplicate rule_group {group!r}")
        seen_groups.add(group)
    if "note" in data:
        _req_str(data["note"], where, "note")
    return data


def load_golden(golden_dir):
    root = pathlib.Path(golden_dir)
    if not root.is_dir():
        raise OracleError(f"{golden_dir}: not a directory")
    stray = sorted(entry.name for entry in root.glob("*.yml"))
    if stray:
        raise OracleError(
            f"{golden_dir}: .yml files would silently escape the *.yaml "
            f"glob: {stray} (rename to .yaml)"
        )
    files = sorted(root.glob("*.yaml"))
    if not files:
        raise OracleError(
            f"{golden_dir}: no *.yaml scenarios (refusing an empty oracle)"
        )
    scenarios = []
    origin = {}
    for file in files:
        try:
            data = load_yaml_strict(file)  # rejects duplicate keys (R1)
        except RuleValidationError:
            raise
        except ValueError as exc:
            # PyYAML raises bare ValueError on e.g. 2026-02-30: an
            # invalid calendar date must surface as ORACLE_ERR, not a
            # traceback (ADR-008 (6)).
            raise OracleError(f"{file.name}: invalid scalar ({exc})") from exc
        scenario = parse_scenario(data, file.name)
        sid = scenario["id"]
        if sid in origin:
            raise OracleError(
                f"duplicate scenario id {sid!r} across files: "
                f"{origin[sid]} and {file.name}"
            )
        origin[sid] = file.name
        scenarios.append(scenario)
    return scenarios


def rules_present(rules_dir):
    """Arming probe. False only while Gate 4 has not landed: no rules
    path at all, an empty dir, or whitespace-only *.yaml files.
    Anything else - a regular FILE named rules, stray .yml files, an
    unreadable file - counts as present so the strict loader surfaces
    the error: the probe must never mask a BROKEN rules dir as
    'pending' (adversarial-hunt catch, 2026-07-14)."""
    root = pathlib.Path(rules_dir)
    if not root.exists():
        return False
    if not root.is_dir():
        return True
    if any(root.glob("*.yml")):
        return True
    for file in sorted(root.glob("*.yaml")):
        try:
            if file.read_text(encoding="utf-8").strip():
                return True
        except (OSError, UnicodeDecodeError):
            return True
    return False


def _load_timeline(timeline_path):
    data = load_yaml_strict(timeline_path)
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, list) or not entries:
        raise OracleError(f"{timeline_path}: missing/empty entries")
    return entries


def _in_group(rule_id, group):
    return rule_id == group or rule_id.startswith(group + "-")


def _has_applicability_leaf(node):
    if not isinstance(node, dict):
        return False
    if node.get("op") == "applicability":
        return True
    return any(
        _has_applicability_leaf(child) for child in node.get("children", [])
    )


def _status_matches(expected, verdict):
    if expected == "INACTIVE":
        return verdict.status == core.STATUS_UNDETERMINED and (
            _has_applicability_leaf(verdict.explanation)
        )
    if expected == "NOT_APPLICABLE":
        supported = getattr(core, "STATUS_NOT_APPLICABLE", None)
        return supported is not None and verdict.status == supported
    if expected == "UNDETERMINED":
        # S09 contract: a fail-closed UNDETERMINED names its unknowns.
        return verdict.status == core.STATUS_UNDETERMINED and bool(
            verdict.unknown_facts
        )
    return verdict.status == expected


def evaluate_scenarios(scenarios, rules, corpus_version):
    mismatches = []
    for scenario in scenarios:
        verdicts = core.evaluate(
            rules, scenario["facts"], scenario["as_of"], corpus_version
        )
        for entry in scenario["expect"]:
            group = entry["rule_group"]
            expected = entry["status"]
            in_group = [v for v in verdicts if _in_group(v.rule_id, group)]
            if not in_group:
                mismatches.append(f"{scenario['id']}/{group}: no rule in group")
                continue
            bad = [v for v in in_group if not _status_matches(expected, v)]
            if bad:
                got = ",".join(sorted({v.status for v in bad}))
                detail = f"{scenario['id']}/{group}: expected {expected}, got {got}"
                if expected == "NOT_APPLICABLE" and not hasattr(
                    core, "STATUS_NOT_APPLICABLE"
                ):
                    detail += (
                        " (engine cannot express NOT_APPLICABLE yet;"
                        " Gate-4 extension, ADR-009)"
                    )
                mismatches.append(detail)
    return mismatches


def main(
    golden_dir="oracle/golden",
    rules_dir="rules",
    manifest_path="corpus/manifest.yaml",
    timeline_path="corpus/timeline.yaml",
):
    try:
        scenarios = load_golden(golden_dir)
    except (OracleError, RuleValidationError) as exc:
        print(f"ORACLE_ERR {exc}")
        return 1
    if not rules_present(rules_dir):
        print(f"ORACLE_PENDING n={len(scenarios)} (no rules yet; arms at Gate 4)")
        return 0
    try:
        rules = load_rules_dir(rules_dir)
        manifest = load_yaml_strict(manifest_path)
        version = (
            manifest.get("corpus_version") if isinstance(manifest, dict) else None
        )
        if not isinstance(version, str) or not version.strip():
            raise OracleError(f"{manifest_path}: missing corpus_version")
        _load_timeline(timeline_path)
        mismatches = evaluate_scenarios(scenarios, rules, version)
    except (OracleError, RuleValidationError, core.EvaluationError) as exc:
        print(f"ORACLE_ERR {exc}")
        return 1
    except ValueError as exc:
        # Bare ValueError out of PyYAML scalar construction (e.g. an
        # unquoted 2026-02-30 in rules/manifest/timeline): the same
        # ADR-008 (6) class the golden path guards - never a traceback
        # (adversarial-hunt catch, 2026-07-14).
        print(f"ORACLE_ERR invalid scalar in rules/corpus input ({exc})")
        return 1
    if mismatches:
        print("ORACLE_FAIL " + "; ".join(mismatches))
        return 1
    print(f"ORACLE_GREEN n={len(scenarios)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
