"""Gate-5 CLI (engine/cli.py, PROMPT 7 Phase D): TDD RED first.

Covers: INV-4 full-run both modes + both langs; answers-file ADR-008
classes; interactive stdin incl. '?', invalid-then-valid, EOF (no partial
report); deadlines section for an INACTIVE case; --as-of boundary dates;
exit codes exactly {0,2} incl. a NON_COMPLIANT-heavy run exiting 0;
R4 coherence (report as_of == evaluation as_of).
"""
import io

import pytest
import yaml

from engine import cli
from engine.facts import load_facts_schema
from engine.render import DISCLAIMER

# A fully-answered non-compliant chatbot (ART50_1 NON_COMPLIANT post-2026-08-02).
NONCOMPLIANT = {
    "is_ai_system": True, "in_eu_market": True,
    "personal_nonprofessional_use": False, "operator_role": "deployer",
    "interacts_with_persons": True, "interaction_disclosed": False,
}


def _answers_file(tmp_path, mapping):
    p = tmp_path / "answers.yaml"
    p.write_text(yaml.safe_dump(mapping), encoding="utf-8")
    return str(p)


def _schema_names():
    return [e["name"] for e in
            load_facts_schema("schema/facts.yaml").values() for _ in [0]]


# --- D1 non-interactive + INV-4 -------------------------------------------

@pytest.mark.parametrize("lang", ["it", "en"])
def test_answers_run_has_disclaimer_and_exits_0(tmp_path, capsys, lang):
    rc = cli.main(["--answers", _answers_file(tmp_path, NONCOMPLIANT),
                   "--as-of", "2026-09-01", "--lang", lang])
    out = capsys.readouterr().out
    assert rc == 0
    assert DISCLAIMER in out                       # INV-4 on the CLI path


def test_noncompliant_run_still_exits_0(tmp_path, capsys):
    rc = cli.main(["--answers", _answers_file(tmp_path, NONCOMPLIANT),
                   "--as-of", "2026-09-01"])
    out = capsys.readouterr().out
    assert rc == 0                                  # ADR-012(5): no verdict in exit code
    assert "NON CONFORME" in out or "NON-COMPLIANT" in out


def test_italian_status_label_localized(tmp_path, capsys):
    cli.main(["--answers", _answers_file(tmp_path, NONCOMPLIANT),
              "--as-of", "2026-09-01", "--lang", "it"])
    assert "[NON CONFORME]" in capsys.readouterr().out


# --- answers-file ADR-008 classes -> exit 2 -------------------------------

def test_undeclared_fact_exits_2(tmp_path, capsys):
    rc = cli.main(["--answers", _answers_file(tmp_path, {"ghost_fact": True}),
                   "--as-of", "2026-09-01"])
    assert rc == 2
    assert capsys.readouterr().out == ""            # no report on usage error


def test_wrong_type_exits_2(tmp_path, capsys):
    rc = cli.main(["--answers", _answers_file(tmp_path, {"is_ai_system": "yes"}),
                   "--as-of", "2026-09-01"])
    assert rc == 2


def test_malformed_as_of_exits_2(tmp_path):
    rc = cli.main(["--answers", _answers_file(tmp_path, NONCOMPLIANT),
                   "--as-of", "2026-13-40"])
    assert rc == 2


def test_non_iso_as_of_exits_2(tmp_path):
    rc = cli.main(["--answers", _answers_file(tmp_path, NONCOMPLIANT),
                   "--as-of", "01/09/2026"])
    assert rc == 2


# --- deadlines section (INACTIVE NCII before 2026-12-02) ------------------

def test_deadlines_section_shows_ncii_before_activation(tmp_path, capsys):
    facts = {"is_ai_system": True, "in_eu_market": True,
             "personal_nonprofessional_use": False, "operator_role": "provider",
             "ncii_generation_capability": True, "ncii_safeguards_state_of_art": False}
    cli.main(["--answers", _answers_file(tmp_path, facts),
              "--as-of", "2026-11-01", "--lang", "en"])
    out = capsys.readouterr().out
    assert "UPCOMING DEADLINES" in out
    assert "ART5_NCII" in out and "2026-12-02" in out


# --- --as-of boundary (2026-08-01 INACTIVE vs 2026-08-02 active) ----------

def test_as_of_boundary_before_is_inactive(tmp_path, capsys):
    cli.main(["--answers", _answers_file(tmp_path, NONCOMPLIANT),
              "--as-of", "2026-08-01", "--lang", "en"])
    out = capsys.readouterr().out
    assert "UPCOMING DEADLINES" in out and "2026-08-02" in out   # not yet applicable


def test_as_of_boundary_on_date_is_active(tmp_path, capsys):
    cli.main(["--answers", _answers_file(tmp_path, NONCOMPLIANT),
              "--as-of", "2026-08-02", "--lang", "en"])
    out = capsys.readouterr().out
    assert "[NON-COMPLIANT] ART50_1" in out


# --- R4 coherence ----------------------------------------------------------

def test_report_stamp_matches_as_of(tmp_path, capsys):
    cli.main(["--answers", _answers_file(tmp_path, NONCOMPLIANT),
              "--as-of", "2026-09-01"])
    assert "as_of: 2026-09-01" in capsys.readouterr().out


# --- D2 interactive --------------------------------------------------------

def _feed(monkeypatch, text):
    monkeypatch.setattr("sys.stdin", io.StringIO(text))


def _n_questions():
    return len(load_facts_schema("schema/facts.yaml"))


@pytest.mark.parametrize("lang", ["it", "en"])
def test_interactive_all_unknown_produces_report(monkeypatch, capsys, lang):
    _feed(monkeypatch, "\n".join(["?"] * _n_questions()) + "\n")
    rc = cli.main(["--as-of", "2026-09-01", "--lang", lang])
    out = capsys.readouterr().out
    assert rc == 0
    assert DISCLAIMER in out                        # INV-4, interactive path


def test_interactive_ai_disclosure_shown(monkeypatch, capsys):
    _feed(monkeypatch, "\n".join(["?"] * _n_questions()) + "\n")
    cli.main(["--as-of", "2026-09-01", "--lang", "en"])
    err = capsys.readouterr().err
    assert "AI-based system" in err                 # ADR-012(6)


def test_interactive_invalid_then_valid(monkeypatch, capsys):
    # first question is_ai_system: an invalid token, then a valid 's' (it),
    # then '?' for the rest.
    lines = ["xx", "s"] + ["?"] * (_n_questions() - 1)
    _feed(monkeypatch, "\n".join(lines) + "\n")
    rc = cli.main(["--as-of", "2026-09-01", "--lang", "it"])
    err = capsys.readouterr().err
    assert rc == 0
    assert "non valida" in err.lower()              # invalid-answer notice shown


def test_interactive_eof_midway_no_partial_report(monkeypatch, capsys):
    # only 3 answers then EOF -> fail closed, exit 2, NO report on stdout
    _feed(monkeypatch, "?\n?\n?\n")
    rc = cli.main(["--as-of", "2026-09-01", "--lang", "en"])
    captured = capsys.readouterr()
    assert rc == 2
    assert DISCLAIMER not in captured.out
    assert captured.out.strip() == ""


def test_interactive_answered_noncompliant(monkeypatch, capsys):
    # drive a real NON_COMPLIANT: is_ai=y, in_eu=y, personal=n, role=deployer(1),
    # interacts=y, disclosed=n, then '?' for the remaining facts.
    schema = load_facts_schema("schema/facts.yaml")
    order = list(schema)
    answers = {"is_ai_system": "y", "in_eu_market": "y",
               "personal_nonprofessional_use": "n", "operator_role": "1",
               "interacts_with_persons": "y", "interaction_disclosed": "n"}
    feed = [answers.get(name, "?") for name in order]
    _feed(monkeypatch, "\n".join(feed) + "\n")
    rc = cli.main(["--as-of", "2026-09-01", "--lang", "en"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "[NON-COMPLIANT] ART50_1" in out
