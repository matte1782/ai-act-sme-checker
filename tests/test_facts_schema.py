"""L3 facts schema: typed facts (bool/enum/date) with i18n keys; missing
answers resolve to UNKNOWN (fail-closed); undeclared/wrong-typed reject.
Synthetic facts only.
"""
import datetime as dt

import pytest

from engine.facts import (
    UNKNOWN,
    FactValidationError,
    load_facts_schema,
    validate_facts,
)

# Gate 4: the synthetic schema moved here so schema/facts.yaml holds the
# canonical vocabulary; only this path constant changed, assertions intact.
SCHEMA_PATH = "tests/fixtures/facts_synthetic.yaml"


@pytest.fixture()
def schema():
    return load_facts_schema(SCHEMA_PATH)


def test_schema_loads_with_i18n(schema):
    assert {"f_true", "f_false", "f_unknown", "a", "b"} <= set(schema)
    for entry in schema.values():
        assert entry["i18n"]["it"]
        assert entry["i18n"]["en"]


def test_bool_fact_validates(schema):
    facts = validate_facts(schema, {"f_true": True})
    assert facts["f_true"] is True


def test_missing_fact_resolves_unknown(schema):
    facts = validate_facts(schema, {})
    assert facts["f_true"] is UNKNOWN


def test_none_answer_resolves_unknown(schema):
    facts = validate_facts(schema, {"f_true": None})
    assert facts["f_true"] is UNKNOWN


def test_wrong_type_rejected(schema):
    with pytest.raises(FactValidationError):
        validate_facts(schema, {"f_true": "yes"})


def test_enum_value_rejected(schema):
    with pytest.raises(FactValidationError):
        validate_facts(schema, {"b": "nope"})


def test_enum_value_accepted(schema):
    assert validate_facts(schema, {"b": "x"})["b"] == "x"


def test_undeclared_fact_rejected(schema):
    with pytest.raises(FactValidationError):
        validate_facts(schema, {"ghost": True})


def test_date_fact_coerces_iso(schema):
    facts = validate_facts(schema, {"d_start": "2026-01-01"})
    assert facts["d_start"] == dt.date(2026, 1, 1)


def test_bad_date_rejected(schema):
    with pytest.raises(FactValidationError):
        validate_facts(schema, {"d_start": "not-a-date"})
