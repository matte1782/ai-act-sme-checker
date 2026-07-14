"""R1 (Gate-2 residual): PyYAML duplicate-key last-wins.

A rules file containing duplicate mapping keys must be REJECTED, not
silently resolved to whichever key comes last (a duplicated
'applies_from' would let an attacker shadow the temporal window).

ADR-008 classes enumerated here (the ones applicable to a YAML
duplicate-key surface):
- (7) duplicate identifiers: duplicate key at rule level, nested
  mapping level, and document top level;
- (4) wrong type: unhashable mapping key;
- control: a duplicate-free file still loads.
"""
import pytest

from engine.loader import RuleValidationError, load_rules_file

VALID = """\
rules:
  - id: r-ok
    legal_source:
      corpus_id: TEST-ACT-1
      article: Art. 5
      paragraph: "1"
    applies_from: 2026-01-01
    logic: {fact: f_x, op: eq, value: true}
    verdict: COMPLIANT
    rationale_key: test.r1
"""


def write(tmp_path, text):
    path = tmp_path / "rules.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_duplicate_applies_from_rejected(tmp_path):
    # ADR-008 (7): the prompt-mandated case - shadowed temporal window.
    text = VALID.replace(
        "    applies_from: 2026-01-01\n",
        "    applies_from: 2026-01-01\n    applies_from: 2099-01-01\n",
    )
    with pytest.raises(RuleValidationError, match="duplicate"):
        load_rules_file(write(tmp_path, text))


def test_duplicate_key_in_nested_mapping_rejected(tmp_path):
    # ADR-008 (7): duplicate inside legal_source (citation shadowing).
    text = VALID.replace(
        "      article: Art. 5\n",
        "      article: Art. 5\n      article: Art. 99\n",
    )
    with pytest.raises(RuleValidationError, match="duplicate"):
        load_rules_file(write(tmp_path, text))


def test_duplicate_top_level_key_rejected(tmp_path):
    # ADR-008 (7): a second 'rules:' document key must not win silently.
    text = VALID + "rules: []\n"
    with pytest.raises(RuleValidationError, match="duplicate"):
        load_rules_file(write(tmp_path, text))


def test_unhashable_mapping_key_rejected(tmp_path):
    # ADR-008 (4): wrong-type key must surface as a validation error,
    # not a raw TypeError.
    text = "rules:\n  - ? [a, b]\n    : 1\n"
    with pytest.raises(RuleValidationError):
        load_rules_file(write(tmp_path, text))


def test_duplicate_free_file_still_loads(tmp_path):
    rules = load_rules_file(write(tmp_path, VALID))
    assert [rule.id for rule in rules] == ["r-ok"]
