"""Gate-5 CLI-hunt pins (ADR-007, Phase F).

Finding 1 (confirmed, real): load_i18n enumerated status_labels and (via
check_completeness) rationale keys, but NOT the ui.* keys that cli.py /
render.py dereference by direct index. A catalog missing e.g.
ui.deadlines_header passed load, then raised an uncaught KeyError at use
time -> process exit 1, violating ADR-012(4) (load-time error) and
ADR-012(5) (exit codes {0,2}). Pinned: a missing required ui key must fail
at LOAD, and the CLI must exit 2 (never 1) on such a catalog.
"""
import pytest
import yaml

from engine import cli
from engine.i18n import I18nError, load_i18n

REQUIRED_UI = ("ai_disclosure", "intro", "hint_bool", "hint_enum",
               "invalid_answer", "unknown_forced", "interrupted",
               "deadlines_header", "deadlines_none", "token_yes", "token_no")


def _catalog_missing_ui(tmp_path, key):
    with open("i18n/messages.yaml", encoding="utf-8") as fh:
        cat = yaml.safe_load(fh)
    del cat["ui"][key]
    p = tmp_path / "m.yaml"
    p.write_text(yaml.safe_dump(cat, allow_unicode=True), encoding="utf-8")
    return str(p)


def _answers(tmp_path):
    p = tmp_path / "a.yaml"
    p.write_text("is_ai_system: true\nin_eu_market: true\n"
                 "personal_nonprofessional_use: false\noperator_role: deployer\n",
                 encoding="utf-8")
    return str(p)


@pytest.mark.parametrize("key", REQUIRED_UI)
def test_f1_missing_ui_key_is_load_error(tmp_path, key):
    with pytest.raises(I18nError):
        load_i18n(_catalog_missing_ui(tmp_path, key))


def test_f1_shipped_catalog_still_loads(tmp_path):
    # the real catalog must remain complete (no regression the pin over-tightens)
    load_i18n("i18n/messages.yaml")


def test_f1_cli_incomplete_ui_exits_2_not_1(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(cli, "MESSAGES_PATH",
                        _catalog_missing_ui(tmp_path, "deadlines_header"))
    rc = cli.main(["--answers", _answers(tmp_path), "--as-of", "2026-09-01"])
    assert rc == 2                       # not 1 (ADR-012(5)); load-time catch
    assert capsys.readouterr().out == ""
