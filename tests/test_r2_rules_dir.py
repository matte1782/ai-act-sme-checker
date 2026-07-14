"""R2 (Gate-2 residual): rule-id uniqueness was only per-file.

load_rules_dir(path) loads ALL rules/*.yaml and rejects cross-file
duplicate ids. Fail-closed at the directory surface too: a missing or
empty rules directory is an error, never a silent empty engine.

ADR-008 classes enumerated here (directory-level validation surface):
- (1) missing: path does not exist / is a file;
- (2) empty: directory with no *.yaml files;
- (5) unknown/misspelled: a stray .yml file would be silently skipped
  by the *.yaml glob - rejected instead;
- (7) duplicate identifiers: same rule id across two files;
- propagation: a malformed file anywhere in the dir fails the load;
- control: distinct files/ids load, deterministic (sorted) order.
"""
import pytest

from engine.loader import RuleValidationError, load_rules_dir

RULE = """\
rules:
  - id: {rid}
    legal_source:
      corpus_id: TEST-ACT-1
      article: Art. 5
      paragraph: "1"
    applies_from: 2026-01-01
    logic: {{fact: f_x, op: eq, value: true}}
    verdict: COMPLIANT
    rationale_key: test.{rid}
"""


def test_missing_directory_rejected(tmp_path):
    # ADR-008 (1)
    with pytest.raises(RuleValidationError, match="not a directory"):
        load_rules_dir(tmp_path / "no_such_dir")


def test_path_that_is_a_file_rejected(tmp_path):
    # ADR-008 (1)/(4): wrong node type for the surface.
    file_path = tmp_path / "rules.yaml"
    file_path.write_text(RULE.format(rid="r-a"), encoding="utf-8")
    with pytest.raises(RuleValidationError, match="not a directory"):
        load_rules_dir(file_path)


def test_empty_directory_rejected_fail_closed(tmp_path):
    # ADR-008 (2): zero rules must never load silently (INV-1 spirit).
    with pytest.raises(RuleValidationError, match="no .*\\.yaml"):
        load_rules_dir(tmp_path)


def test_stray_yml_extension_rejected(tmp_path):
    # ADR-008 (5): a .yml file would silently escape the *.yaml glob.
    (tmp_path / "a.yaml").write_text(RULE.format(rid="r-a"), encoding="utf-8")
    (tmp_path / "b.yml").write_text(RULE.format(rid="r-b"), encoding="utf-8")
    with pytest.raises(RuleValidationError, match="\\.yml"):
        load_rules_dir(tmp_path)


def test_cross_file_duplicate_id_rejected(tmp_path):
    # ADR-008 (7): the residual itself.
    (tmp_path / "a.yaml").write_text(RULE.format(rid="r-dup"), encoding="utf-8")
    (tmp_path / "b.yaml").write_text(RULE.format(rid="r-dup"), encoding="utf-8")
    with pytest.raises(RuleValidationError, match="r-dup"):
        load_rules_dir(tmp_path)


def test_malformed_file_in_dir_fails_load(tmp_path):
    (tmp_path / "a.yaml").write_text(RULE.format(rid="r-a"), encoding="utf-8")
    (tmp_path / "b.yaml").write_text("rules: [{id: broken}]\n", encoding="utf-8")
    with pytest.raises(RuleValidationError):
        load_rules_dir(tmp_path)


def test_distinct_files_load_in_sorted_order(tmp_path):
    (tmp_path / "b.yaml").write_text(RULE.format(rid="r-b"), encoding="utf-8")
    (tmp_path / "a.yaml").write_text(RULE.format(rid="r-a"), encoding="utf-8")
    rules = load_rules_dir(tmp_path)
    assert [rule.id for rule in rules] == ["r-a", "r-b"]
