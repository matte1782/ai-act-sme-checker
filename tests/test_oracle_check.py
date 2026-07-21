# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
"""L6 oracle checker tests (scripts/oracle_check.py).

ADR-008 classes enumerated on the golden-scenario validation surface:
- (1) missing: required scenario key absent; missing golden dir;
- (2) empty: empty title_it / facts map / expect list; empty dir;
- (3) whitespace: whitespace-only cite;
- (4) wrong type: quoted as_of string; null fact value; non-list expect;
- (5) unknown/misspelled key: top-level and expect-entry; stray .yml;
- (6) boundary: as_of as datetime (date/datetime edge); invalid
  calendar date; lowercase status outside the exact vocabulary;
- (7) duplicate identifiers: scenario id across files; duplicate
  mapping key in one file (R1 strict loader); duplicate rule_group.

Plus the self-arming state machine (ORACLE_ERR / ORACLE_PENDING /
ORACLE_FAIL / ORACLE_GREEN), the INACTIVE and NOT_APPLICABLE mappings
(ADR-009), the S09 named-unknowns contract, and the frozen-set anchor
(exactly S01-S14 load).
"""
import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location(
    "oracle_check", ROOT / "scripts" / "oracle_check.py"
)
oracle_check = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(oracle_check)

OracleError = oracle_check.OracleError

SCENARIO = """\
id: {sid}
title_it: "Scenario di prova"
facts: {{interaction_disclosed: {disclosed}}}
as_of: {as_of}
expect:
  - {{rule_group: G1, status: {status}, cite: "AIA Art. 50(1)"}}
"""

RULES_G1 = """\
rules:
  - id: G1-disclosure
    legal_source:
      corpus_id: test-corpus-src
      article: Art. 50
      paragraph: "1"
    applies_from: 2026-08-02
    logic: {fact: interaction_disclosed, op: eq, value: true}
    verdict: COMPLIANT
    rationale_key: test.g1
"""

MANIFEST = "corpus_version: test-corpus-v1\n"
TIMELINE = "entries:\n  - obligation: test\n    applies_from: '2026-08-02'\n"


def write_golden(tmp_path, *texts):
    golden = tmp_path / "golden"
    golden.mkdir(exist_ok=True)
    for index, text in enumerate(texts):
        (golden / f"S{index + 1:02d}.yaml").write_text(text, encoding="utf-8")
    return golden


def armed_env(tmp_path, *texts, rules=RULES_G1):
    golden = write_golden(tmp_path, *texts)
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir(exist_ok=True)
    (rules_dir / "g1.yaml").write_text(rules, encoding="utf-8")
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(MANIFEST, encoding="utf-8")
    timeline = tmp_path / "timeline.yaml"
    timeline.write_text(TIMELINE, encoding="utf-8")
    return dict(
        golden_dir=golden,
        rules_dir=rules_dir,
        manifest_path=manifest,
        timeline_path=timeline,
    )


def valid(sid="S01", disclosed="false", as_of="2026-09-01", status="NON_COMPLIANT"):
    return SCENARIO.format(sid=sid, disclosed=disclosed, as_of=as_of, status=status)


# --- directory surface -------------------------------------------------

def test_missing_directory_rejected(tmp_path):
    # ADR-008 (1)
    with pytest.raises(OracleError, match="not a directory"):
        oracle_check.load_golden(tmp_path / "no_such_dir")


def test_empty_directory_rejected_fail_closed(tmp_path):
    # ADR-008 (2): an empty oracle must never pass silently.
    (tmp_path / "golden").mkdir()
    with pytest.raises(OracleError, match="empty oracle"):
        oracle_check.load_golden(tmp_path / "golden")


def test_stray_yml_extension_rejected(tmp_path):
    # ADR-008 (5): a .yml scenario would silently escape the glob.
    golden = write_golden(tmp_path, valid())
    (golden / "S99.yml").write_text(valid(sid="S99"), encoding="utf-8")
    with pytest.raises(OracleError, match="\\.yml"):
        oracle_check.load_golden(golden)


# --- scenario mapping surface ------------------------------------------

def test_missing_required_key_rejected(tmp_path):
    # ADR-008 (1)
    text = valid().replace('title_it: "Scenario di prova"\n', "")
    golden = write_golden(tmp_path, text)
    with pytest.raises(OracleError, match="missing keys.*title_it"):
        oracle_check.load_golden(golden)


def test_empty_title_rejected(tmp_path):
    # ADR-008 (2)
    text = valid().replace('"Scenario di prova"', '""')
    golden = write_golden(tmp_path, text)
    with pytest.raises(OracleError, match="title_it"):
        oracle_check.load_golden(golden)


def test_empty_facts_rejected(tmp_path):
    # ADR-008 (2): a scenario with no facts asserts nothing.
    text = valid().replace("facts: {interaction_disclosed: false}", "facts: {}")
    golden = write_golden(tmp_path, text)
    with pytest.raises(OracleError, match="facts must be a non-empty mapping"):
        oracle_check.load_golden(golden)


def test_empty_expect_rejected(tmp_path):
    # ADR-008 (2): an expectation-free scenario cannot gate anything.
    text = valid().split("expect:")[0] + "expect: []\n"
    golden = write_golden(tmp_path, text)
    with pytest.raises(OracleError, match="expect must be a non-empty list"):
        oracle_check.load_golden(golden)


def test_whitespace_cite_rejected(tmp_path):
    # ADR-008 (3): the Gate-2 CRITICAL class - blank strings load.
    text = valid().replace('"AIA Art. 50(1)"', '"   "')
    golden = write_golden(tmp_path, text)
    with pytest.raises(OracleError, match="cite"):
        oracle_check.load_golden(golden)


def test_quoted_as_of_string_rejected(tmp_path):
    # ADR-008 (4): as_of must parse to a real date object.
    text = valid().replace("as_of: 2026-09-01", 'as_of: "2026-09-01"')
    golden = write_golden(tmp_path, text)
    with pytest.raises(OracleError, match="as_of"):
        oracle_check.load_golden(golden)


def test_null_fact_value_rejected(tmp_path):
    # ADR-008 (4): omitted facts are UNKNOWN by design; null is a typo.
    text = valid().replace(
        "facts: {interaction_disclosed: false}",
        "facts: {interaction_disclosed: null}",
    )
    golden = write_golden(tmp_path, text)
    with pytest.raises(OracleError, match="never null"):
        oracle_check.load_golden(golden)


def test_expect_not_a_list_rejected(tmp_path):
    # ADR-008 (4)
    text = valid().split("expect:")[0] + "expect: {rule_group: G1}\n"
    golden = write_golden(tmp_path, text)
    with pytest.raises(OracleError, match="expect must be a non-empty list"):
        oracle_check.load_golden(golden)


def test_unknown_top_level_key_rejected(tmp_path):
    # ADR-008 (5)
    text = valid() + "extra_key: 1\n"
    golden = write_golden(tmp_path, text)
    with pytest.raises(OracleError, match="unknown keys.*extra_key"):
        oracle_check.load_golden(golden)


def test_unknown_expect_key_rejected(tmp_path):
    # ADR-008 (5): e.g. a misspelled 'cited' must never silently drop.
    text = valid().replace("cite:", "cited:")
    golden = write_golden(tmp_path, text)
    with pytest.raises(OracleError, match="keys must be exactly"):
        oracle_check.load_golden(golden)


def test_datetime_as_of_rejected(tmp_path):
    # ADR-008 (6): date/datetime boundary (mirrors the core's gate).
    text = valid().replace("as_of: 2026-09-01", "as_of: 2026-09-01T00:00:00")
    golden = write_golden(tmp_path, text)
    with pytest.raises(OracleError, match="as_of"):
        oracle_check.load_golden(golden)


def test_invalid_calendar_date_rejected(tmp_path):
    # ADR-008 (6): 2026-02-30 must not load as anything.
    text = valid().replace("as_of: 2026-09-01", "as_of: 2026-02-30")
    golden = write_golden(tmp_path, text)
    with pytest.raises(OracleError, match="invalid scalar"):
        oracle_check.load_golden(golden)


def test_status_outside_vocabulary_rejected(tmp_path):
    # ADR-008 (6): exact vocabulary, no case drift.
    text = valid(status="non_compliant")
    golden = write_golden(tmp_path, text)
    with pytest.raises(OracleError, match="status must be one of"):
        oracle_check.load_golden(golden)


def test_duplicate_scenario_id_across_files_rejected(tmp_path):
    # ADR-008 (7)
    golden = write_golden(tmp_path, valid(sid="S-dup"), valid(sid="S-dup"))
    with pytest.raises(OracleError, match="duplicate scenario id"):
        oracle_check.load_golden(golden)


def test_duplicate_mapping_key_rejected(tmp_path):
    # ADR-008 (7) at the YAML layer (R1 strict loader shared with L2).
    text = valid() + "as_of: 2026-10-01\n"
    golden = write_golden(tmp_path, text)
    with pytest.raises(Exception, match="duplicate mapping key"):
        oracle_check.load_golden(golden)


def test_duplicate_rule_group_in_expect_rejected(tmp_path):
    # ADR-008 (7): one verdict slot per rule_group per scenario.
    text = valid().split("expect:")[0] + (
        "expect:\n"
        '  - {rule_group: G1, status: COMPLIANT, cite: "AIA Art. 50(1)"}\n'
        '  - {rule_group: G1, status: NON_COMPLIANT, cite: "AIA Art. 50(1)"}\n'
    )
    golden = write_golden(tmp_path, text)
    with pytest.raises(OracleError, match="duplicate rule_group"):
        oracle_check.load_golden(golden)


# --- self-arming state machine ------------------------------------------

def test_pending_when_rules_dir_absent(tmp_path, capsys):
    golden = write_golden(tmp_path, valid())
    rc = oracle_check.main(
        golden_dir=golden,
        rules_dir=tmp_path / "rules",
        manifest_path=tmp_path / "manifest.yaml",
        timeline_path=tmp_path / "timeline.yaml",
    )
    assert rc == 0
    out = capsys.readouterr().out.strip()
    assert out == "ORACLE_PENDING n=1 (no rules yet; arms at Gate 4)"


def test_pending_when_rules_files_blank(tmp_path, capsys):
    golden = write_golden(tmp_path, valid())
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "empty.yaml").write_text("  \n", encoding="utf-8")
    rc = oracle_check.main(
        golden_dir=golden,
        rules_dir=rules_dir,
        manifest_path=tmp_path / "manifest.yaml",
        timeline_path=tmp_path / "timeline.yaml",
    )
    assert rc == 0
    assert "ORACLE_PENDING n=1" in capsys.readouterr().out


def test_err_on_malformed_golden_even_without_rules(tmp_path, capsys):
    # Format validation is never skipped: PENDING only after it passes.
    golden = write_golden(tmp_path, valid().replace('"Scenario di prova"', '""'))
    rc = oracle_check.main(golden_dir=golden, rules_dir=tmp_path / "rules")
    assert rc == 1
    assert capsys.readouterr().out.startswith("ORACLE_ERR ")


def test_stray_yml_rules_dir_is_err_not_pending(tmp_path, capsys):
    # Hunt catch (2026-07-14): rules landed as .yml would otherwise
    # park the gate at PENDING forever with zero scenarios evaluated.
    golden = write_golden(tmp_path, valid())
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "g1.yml").write_text(RULES_G1, encoding="utf-8")
    rc = oracle_check.main(
        golden_dir=golden,
        rules_dir=rules_dir,
        manifest_path=tmp_path / "manifest.yaml",
        timeline_path=tmp_path / "timeline.yaml",
    )
    assert rc == 1
    out = capsys.readouterr().out
    assert out.startswith("ORACLE_ERR ")
    assert ".yml" in out


def test_rules_path_as_regular_file_is_err_not_pending(tmp_path, capsys):
    # Hunt catch (2026-07-14): a FILE named 'rules' is broken, not
    # absent - the probe must arm and let the loader surface it.
    golden = write_golden(tmp_path, valid())
    rules_path = tmp_path / "rules"
    rules_path.write_text(RULES_G1, encoding="utf-8")
    rc = oracle_check.main(
        golden_dir=golden,
        rules_dir=rules_path,
        manifest_path=tmp_path / "manifest.yaml",
        timeline_path=tmp_path / "timeline.yaml",
    )
    assert rc == 1
    assert "not a directory" in capsys.readouterr().out


def test_armed_invalid_calendar_date_is_err_not_traceback(tmp_path, capsys):
    # Hunt catch (2026-07-14): unquoted 2026-02-30 in rules/*.yaml
    # must print ORACLE_ERR like the golden path does (ADR-008 (6)),
    # never a raw PyYAML ValueError traceback.
    env = armed_env(tmp_path, valid())
    (env["rules_dir"] / "g1.yaml").write_text(
        RULES_G1.replace("2026-08-02", "2026-02-30"), encoding="utf-8"
    )
    rc = oracle_check.main(**env)
    assert rc == 1
    assert capsys.readouterr().out.startswith("ORACLE_ERR ")


def test_mixed_type_unknown_keys_err_not_typeerror(tmp_path, capsys):
    # Hunt catch (2026-07-14): unknown keys of non-comparable types
    # (int + str) must yield ORACLE_ERR, not a sorted() TypeError.
    text = valid() + "7: stray-int-key\nzzz: stray-str-key\n"
    golden = write_golden(tmp_path, text)
    rc = oracle_check.main(golden_dir=golden, rules_dir=tmp_path / "rules")
    assert rc == 1
    assert capsys.readouterr().out.startswith("ORACLE_ERR ")


def test_broken_rules_dir_is_err_not_pending(tmp_path, capsys):
    # No masking: a present-but-invalid rules dir must surface.
    env = armed_env(tmp_path, valid(), rules="rules: [{id: broken}]\n")
    rc = oracle_check.main(**env)
    assert rc == 1
    assert capsys.readouterr().out.startswith("ORACLE_ERR ")


def test_armed_green_on_satisfied_expectation(tmp_path, capsys):
    # G1-disclosure + interaction_disclosed=false => NON_COMPLIANT.
    env = armed_env(tmp_path, valid(status="NON_COMPLIANT"))
    rc = oracle_check.main(**env)
    assert rc == 0
    assert capsys.readouterr().out.strip() == "ORACLE_GREEN n=1"


def test_armed_fail_on_status_mismatch(tmp_path, capsys):
    env = armed_env(tmp_path, valid(status="COMPLIANT"))
    rc = oracle_check.main(**env)
    assert rc == 1
    out = capsys.readouterr().out
    assert out.startswith("ORACLE_FAIL ")
    assert "S01/G1: expected COMPLIANT, got NON_COMPLIANT" in out


def test_armed_fail_on_missing_rule_group(tmp_path, capsys):
    text = valid().replace("rule_group: G1", "rule_group: G_ABSENT")
    env = armed_env(tmp_path, text)
    rc = oracle_check.main(**env)
    assert rc == 1
    assert "S01/G_ABSENT: no rule in group" in capsys.readouterr().out


def test_inactive_matches_applicability_leaf(tmp_path, capsys):
    # ADR-009 mapping: before applies_from the engine says UNDETERMINED
    # with an op=='applicability' leaf - the oracle reads INACTIVE.
    env = armed_env(tmp_path, valid(as_of="2026-07-15", status="INACTIVE"))
    rc = oracle_check.main(**env)
    assert rc == 0
    assert capsys.readouterr().out.strip() == "ORACLE_GREEN n=1"


def test_inactive_does_not_match_active_verdict(tmp_path, capsys):
    env = armed_env(tmp_path, valid(as_of="2026-09-01", status="INACTIVE"))
    rc = oracle_check.main(**env)
    assert rc == 1
    assert "S01/G1: expected INACTIVE" in capsys.readouterr().out


def test_undetermined_requires_named_unknowns(tmp_path, capsys):
    # S09 contract: unknown fact omitted => UNDETERMINED naming it.
    text = valid(status="UNDETERMINED").replace(
        "facts: {interaction_disclosed: false}", "facts: {is_ai_system: true}"
    )
    env = armed_env(tmp_path, text)
    rc = oracle_check.main(**env)
    assert rc == 0
    assert capsys.readouterr().out.strip() == "ORACLE_GREEN n=1"


def test_undetermined_disjoint_from_temporal_inactive(tmp_path, capsys):
    # A temporal-inactive verdict names no unknown facts, so it must
    # NOT satisfy an expected fail-closed UNDETERMINED.
    env = armed_env(tmp_path, valid(as_of="2026-07-15", status="UNDETERMINED"))
    rc = oracle_check.main(**env)
    assert rc == 1
    assert "S01/G1: expected UNDETERMINED" in capsys.readouterr().out


def test_not_applicable_pending_engine_extension(tmp_path, capsys):
    # Post-Gate-4 (owner-authorized 2026-07-15, events.jsonl): the engine
    # now exposes core.STATUS_NOT_APPLICABLE, so oracle_check's transitional
    # "Gate-4 extension" hint (guarded by `not hasattr`) is unreachable.
    # Substance preserved: RULES_G1 has no applicable_if scope gate, so it
    # can NEVER produce NOT_APPLICABLE - an S10-class expectation on it is
    # reported as a mismatch, never a silent pass.
    env = armed_env(tmp_path, valid(status="NOT_APPLICABLE"))
    rc = oracle_check.main(**env)
    assert rc == 1
    out = capsys.readouterr().out
    assert out.startswith("ORACLE_FAIL")
    assert "S01/G1: expected NOT_APPLICABLE, got NON_COMPLIANT" in out


# --- frozen-set anchor ---------------------------------------------------

def test_frozen_golden_set_loads_s01_to_s14():
    scenarios = oracle_check.load_golden(ROOT / "oracle" / "golden")
    assert [s["id"] for s in scenarios] == [f"S{i:02d}" for i in range(1, 15)]
    statuses = {e["status"] for s in scenarios for e in s["expect"]}
    # The two Gate-4 vocabulary extensions are present in the spec.
    assert "INACTIVE" in statuses and "NOT_APPLICABLE" in statuses
