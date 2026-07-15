"""Gate-4 canonical facts schema (schema/facts.yaml, ADR-009).

The frozen golden set DEFINES the vocabulary: every fact name a scenario
uses must be a declared fact, and every enum value a scenario uses must be
in that fact's declared values. Plus ADR-008 malformed-class enumeration
on the schema loader itself.
"""
import datetime as dt
import pathlib

import pytest
import yaml

from engine.facts import FactValidationError, load_facts_schema

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schema" / "facts.yaml"
GOLDEN_DIR = ROOT / "oracle" / "golden"


@pytest.fixture(scope="module")
def schema():
    return load_facts_schema(str(SCHEMA_PATH))


def _golden_facts():
    """(names, enum_values_by_name) actually used across S01-S14."""
    names = set()
    used_values = {}
    for file in sorted(GOLDEN_DIR.glob("*.yaml")):
        data = yaml.safe_load(file.read_text(encoding="utf-8"))
        for name, value in data["facts"].items():
            names.add(name)
            if isinstance(value, str):
                used_values.setdefault(name, set()).add(value)
    return names, used_values


# --- vocabulary coverage --------------------------------------------------

def test_schema_loads(schema):
    assert schema
    assert "is_ai_system" in schema


def test_every_golden_fact_name_is_declared(schema):
    names, _ = _golden_facts()
    missing = sorted(names - set(schema))
    assert not missing, f"golden facts not declared in schema: {missing}"


def test_every_enum_value_used_by_a_scenario_is_declared(schema):
    _, used_values = _golden_facts()
    for name, values in used_values.items():
        assert schema[name]["type"] == "enum", f"{name} used a string but is not enum"
        declared = set(schema[name]["values"])
        missing = sorted(values - declared)
        assert not missing, f"{name}: golden uses undeclared enum values {missing}"


def test_operator_role_and_annex_enums_present(schema):
    assert set(schema["operator_role"]["values"]) == {"provider", "deployer"}
    assert {"none", "employment_recruitment", "law_enforcement"} <= set(
        schema["annex_iii_use_case"]["values"]
    )


def test_every_fact_has_it_and_en(schema):
    for name, entry in schema.items():
        assert entry["i18n"]["it"], f"{name}: missing Italian label"
        assert entry["i18n"]["en"], f"{name}: missing English label"


def test_types_are_valid(schema):
    for name, entry in schema.items():
        assert entry["type"] in ("bool", "enum", "date"), name


# --- ADR-008 malformed classes on the schema loader ----------------------

def _write(tmp_path, body):
    p = tmp_path / "facts.yaml"
    p.write_text(body, encoding="utf-8")
    return str(p)


def test_missing_name_rejected(tmp_path):                 # ADR-008 (1)
    with pytest.raises(FactValidationError):
        load_facts_schema(_write(tmp_path, "facts:\n  - type: bool\n    i18n: {it: a, en: b}\n"))


def test_unknown_type_rejected(tmp_path):                 # ADR-008 (4)
    with pytest.raises(FactValidationError):
        load_facts_schema(_write(
            tmp_path, "facts:\n  - name: q\n    type: str\n    i18n: {it: a, en: b}\n"
        ))


def test_enum_without_values_rejected(tmp_path):          # ADR-008 (1)
    with pytest.raises(FactValidationError):
        load_facts_schema(_write(
            tmp_path, "facts:\n  - name: q\n    type: enum\n    i18n: {it: a, en: b}\n"
        ))


def test_missing_it_label_rejected(tmp_path):             # ADR-008 (1)
    with pytest.raises(FactValidationError):
        load_facts_schema(_write(
            tmp_path, "facts:\n  - name: q\n    type: bool\n    i18n: {en: b}\n"
        ))


def test_missing_en_label_rejected(tmp_path):             # ADR-008 (1)
    with pytest.raises(FactValidationError):
        load_facts_schema(_write(
            tmp_path, "facts:\n  - name: q\n    type: bool\n    i18n: {it: a}\n"
        ))


def test_not_a_facts_list_rejected(tmp_path):             # ADR-008 (4)
    with pytest.raises(FactValidationError):
        load_facts_schema(_write(tmp_path, "facts: {q: bool}\n"))
