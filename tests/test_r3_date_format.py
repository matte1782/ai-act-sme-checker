"""R3 (Gate-2 residual): fromisoformat laxity.

Python >= 3.11 date.fromisoformat() accepts non-canonical forms like
'20260101'. String dates must match ^\\d{4}-\\d{2}-\\d{2}$ BEFORE any
parsing; both applies_from and applies_until are gated.

ADR-008 classes enumerated here (date-string validation surface):
- (1) missing applies_from;
- (2) empty string;
- (3) whitespace-only and whitespace-padded strings;
- (4) wrong type (int that "looks like" a date);
- (6) boundary: canonical form accepted; regex-passing but
  calendar-invalid month rejected; compact and non-padded forms
  rejected;
- control: canonical string and YAML-native date both load.
"""
import datetime as dt

import pytest

from engine.loader import RuleValidationError, parse_rule


def rule_data(**overrides):
    data = {
        "id": "r-r3",
        "legal_source": {
            "corpus_id": "TEST-ACT-1",
            "article": "Art. 5",
            "paragraph": "1",
        },
        "applies_from": "2026-01-01",
        "logic": {"fact": "f_x", "op": "eq", "value": True},
        "verdict": "COMPLIANT",
        "rationale_key": "test.r3",
    }
    data.update(overrides)
    return data


@pytest.mark.parametrize(
    "bad",
    [
        "20260101",       # ADR-008 (6): compact ISO accepted by fromisoformat
        "2026-1-1",       # ADR-008 (6): non-padded
        "",               # ADR-008 (2)
        "   ",            # ADR-008 (3)
        " 2026-01-01",    # ADR-008 (3): leading whitespace
        "2026-01-01 ",    # ADR-008 (3): trailing whitespace
        "2026-13-01",     # ADR-008 (6): regex-passing, calendar-invalid
        "2026-01-01T00",  # ADR-008 (6): datetime-ish tail
        20260101,         # ADR-008 (4): wrong type
    ],
)
def test_bad_applies_from_rejected(bad):
    with pytest.raises(RuleValidationError):
        parse_rule(rule_data(applies_from=bad))


@pytest.mark.parametrize("bad", ["20270101", "2027-1-1", "2027-01-01 "])
def test_bad_applies_until_rejected(bad):
    # Same gate on the second date field (no single-field blind spot).
    with pytest.raises(RuleValidationError):
        parse_rule(rule_data(applies_until=bad))


def test_missing_applies_from_rejected():
    # ADR-008 (1)
    data = rule_data()
    del data["applies_from"]
    with pytest.raises(RuleValidationError):
        parse_rule(data)


def test_canonical_string_accepted():
    rule = parse_rule(rule_data(applies_from="2026-01-01"))
    assert rule.applies_from == dt.date(2026, 1, 1)


def test_yaml_native_date_accepted():
    # YAML parses unquoted dates to datetime.date before the regex gate.
    rule = parse_rule(rule_data(applies_from=dt.date(2026, 1, 1)))
    assert rule.applies_from == dt.date(2026, 1, 1)
