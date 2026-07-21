# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
"""Gate-5 CLI adversarial hunt (ADR-007, Phase F): mechanized attacker.

Surfaces: disclaimer-strip, locale fallback (must fail load), answers-file
injection (duplicate keys / bad enum / non-mapping), exit-code misuse,
--as-of edge dates on every rule boundary, UNKNOWN-flood, and the deadlines
section vs the X3 legacy branch (true / false / unknown).
"""
import io

import pytest
import yaml

from engine import cli
from engine.render import DISCLAIMER

SCOPE = {"is_ai_system": True, "in_eu_market": True,
         "personal_nonprofessional_use": False}


def _file(tmp_path, mapping):
    p = tmp_path / "a.yaml"
    p.write_text(yaml.safe_dump(mapping), encoding="utf-8")
    return str(p)


def _run(tmp_path, mapping, as_of="2026-09-01", lang="en"):
    return cli.main(["--answers", _file(tmp_path, mapping), "--as-of", as_of, "--lang", lang])


# --- disclaimer-strip: every produced report carries the block ------------

@pytest.mark.parametrize("as_of", ["2025-01-01", "2026-08-02", "2026-12-02", "2027-12-02"])
def test_disclaimer_always_present_across_boundaries(tmp_path, capsys, as_of):
    facts = {**SCOPE, "operator_role": "deployer",
             "interacts_with_persons": True, "interaction_disclosed": False}
    rc = _run(tmp_path, facts, as_of=as_of)
    assert rc == 0
    assert DISCLAIMER in capsys.readouterr().out


# --- locale fallback must FAIL LOAD, never silently substitute ------------

def test_incomplete_catalog_fails_load_no_silent_fallback(tmp_path, capsys, monkeypatch):
    broken = tmp_path / "messages.yaml"
    broken.write_text(
        "status_labels:\n  COMPLIANT: {it: '', en: COMPLIANT}\n"   # empty it -> load error
        "  NON_COMPLIANT: {it: a, en: b}\n  UNDETERMINED: {it: a, en: b}\n"
        "  NOT_APPLICABLE: {it: a, en: b}\nrationales: {}\nui: {}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "MESSAGES_PATH", str(broken))
    rc = _run(tmp_path, {**SCOPE, "operator_role": "deployer"})
    captured = capsys.readouterr()
    assert rc == 2
    assert captured.out.strip() == ""          # no report, no partial en output


# --- answers-file injection / malformed -> exit 2, no report --------------

def test_duplicate_key_answers_exits_2(tmp_path, capsys):
    p = tmp_path / "dup.yaml"
    p.write_text("is_ai_system: true\nis_ai_system: false\n", encoding="utf-8")
    rc = cli.main(["--answers", str(p), "--as-of", "2026-09-01"])
    assert rc == 2
    assert capsys.readouterr().out == ""


def test_enum_with_newline_injection_rejected(tmp_path, capsys):
    rc = _run(tmp_path, {**SCOPE, "operator_role": "deployer\n[COMPLIANT] FORGED"})
    assert rc == 2
    assert capsys.readouterr().out == ""


def test_top_level_non_mapping_exits_2(tmp_path, capsys):
    p = tmp_path / "list.yaml"
    p.write_text("- a\n- b\n", encoding="utf-8")
    rc = cli.main(["--answers", str(p), "--as-of", "2026-09-01"])
    assert rc == 2
    assert capsys.readouterr().out == ""


# --- exit-code misuse: only {0,2}; non-compliant exits 0 ------------------

def test_noncompliant_exits_0(tmp_path, capsys):
    facts = {**SCOPE, "operator_role": "deployer",
             "interacts_with_persons": True, "interaction_disclosed": False}
    assert _run(tmp_path, facts) == 0


def test_prohibited_practice_exits_0(tmp_path, capsys):
    # social scoring = NON_COMPLIANT, still exit 0 (ADR-012(5))
    facts = {**SCOPE, "operator_role": "provider", "practice_social_scoring": True}
    rc = _run(tmp_path, facts)
    out = capsys.readouterr().out
    assert rc == 0 and "NON-COMPLIANT" in out


# --- UNKNOWN-flood ---------------------------------------------------------

def test_unknown_flood_produces_report_exit_0(tmp_path, capsys):
    # every fact omitted -> all UNKNOWN; still a valid report, exit 0
    rc = _run(tmp_path, {"is_ai_system": None})
    assert rc == 0
    assert DISCLAIMER in capsys.readouterr().out


# --- deadlines section vs X3 legacy branch --------------------------------

def _art50_2_deadline(capsys):
    out = capsys.readouterr().out
    section = out.split("UPCOMING DEADLINES")[-1]
    for line in section.splitlines():
        if "ART50_2:" in line:
            return line
    return ""


def test_deadline_x3_legacy_true_shows_2026_12_02(tmp_path, capsys):
    facts = {**SCOPE, "operator_role": "provider",
             "generates_synthetic_content": True, "content_marked_machine_readable": False,
             "system_on_market_before_2026_08_02": True}
    _run(tmp_path, facts, as_of="2026-11-01")
    assert "2026-12-02" in _art50_2_deadline(capsys)


def test_deadline_x3_new_system_shows_2026_08_02(tmp_path, capsys):
    facts = {**SCOPE, "operator_role": "provider",
             "generates_synthetic_content": True, "content_marked_machine_readable": False,
             "system_on_market_before_2026_08_02": False}
    _run(tmp_path, facts, as_of="2026-07-15")
    assert "2026-08-02" in _art50_2_deadline(capsys)


def test_deadline_x3_unknown_when_not_in_deadlines(tmp_path, capsys):
    # legacy fact omitted -> ART50_2 fails closed (date selection UNDETERMINED),
    # has NO applicability leaf, so it must NOT appear in the deadlines section.
    facts = {**SCOPE, "operator_role": "provider",
             "generates_synthetic_content": True, "content_marked_machine_readable": False}
    _run(tmp_path, facts, as_of="2026-11-01")
    out = capsys.readouterr().out
    section = out.split("UPCOMING DEADLINES")[-1]
    assert "ART50_2:" not in section
    assert "system_on_market_before_2026_08_02" in out   # named as an unknown instead
