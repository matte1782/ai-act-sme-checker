"""L3 typed facts + Kleene K3 primitives (ADR-003).

UNKNOWN is the third truth value AND the value of any unanswered fact.
It deliberately has no boolean coercion: code that tries `if fact:` on
an UNKNOWN crashes instead of silently guessing.
"""
import datetime as dt

import yaml


class _Unknown:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self):
        return "UNKNOWN"

    def __bool__(self):
        raise TypeError("UNKNOWN has no boolean value; use the K3 operators")


UNKNOWN = _Unknown()


def k3_not(value):
    if value is UNKNOWN:
        return UNKNOWN
    return not value


def k3_all(values):
    result = True
    for value in values:
        if value is False:
            return False
        if value is UNKNOWN:
            result = UNKNOWN
    return result


def k3_any(values):
    result = False
    for value in values:
        if value is True:
            return True
        if value is UNKNOWN:
            result = UNKNOWN
    return result


class FactValidationError(ValueError):
    """A malformed schema or a non-conforming answer never enters the engine."""


_TYPES = ("bool", "enum", "date")


def load_facts_schema(path):
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict) or not isinstance(data.get("facts"), list):
        raise FactValidationError(f"{path}: expected a top-level 'facts' list")
    schema = {}
    for entry in data["facts"]:
        name = entry.get("name") if isinstance(entry, dict) else None
        if not name:
            raise FactValidationError(f"{path}: fact entry without name: {entry!r}")
        if entry.get("type") not in _TYPES:
            raise FactValidationError(f"fact {name}: type must be one of {_TYPES}")
        i18n = entry.get("i18n") or {}
        if not (i18n.get("it") and i18n.get("en")):
            raise FactValidationError(f"fact {name}: i18n keys it/en are required")
        if entry["type"] == "enum" and not entry.get("values"):
            raise FactValidationError(f"fact {name}: enum requires non-empty values")
        schema[name] = entry
    return schema


def validate_facts(schema, raw):
    """Type-check raw answers against the schema.

    Missing or None answers resolve to UNKNOWN (fail-closed); undeclared
    fact names and type mismatches raise - they never enter the engine.
    """
    facts = {}
    for name, value in raw.items():
        if name not in schema:
            raise FactValidationError(f"undeclared fact: {name}")
        if value is UNKNOWN or value is None:
            facts[name] = UNKNOWN
            continue
        ftype = schema[name]["type"]
        if ftype == "bool":
            if not isinstance(value, bool):
                raise FactValidationError(f"fact {name}: expected bool, got {value!r}")
        elif ftype == "enum":
            if value not in schema[name]["values"]:
                raise FactValidationError(
                    f"fact {name}: {value!r} not in {schema[name]['values']}"
                )
        elif ftype == "date":
            if isinstance(value, str):
                try:
                    value = dt.date.fromisoformat(value)
                except ValueError as exc:
                    raise FactValidationError(
                        f"fact {name}: {value!r} is not an ISO date"
                    ) from exc
            if isinstance(value, dt.datetime) or not isinstance(value, dt.date):
                raise FactValidationError(f"fact {name}: expected date, got {value!r}")
        facts[name] = value
    for name in schema:
        facts.setdefault(name, UNKNOWN)
    return facts
