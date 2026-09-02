# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
"""Gate-5 CLI-hunt pins (ADR-007, Phase F).

Finding 1 (confirmed, real): load_i18n enumerated status_labels and (via
check_completeness) rationale keys, but NOT the ui.* keys that cli.py /
render.py dereference by direct index. A catalog missing e.g.
ui.deadlines_header passed load, then raised an uncaught KeyError at use
time -> process exit 1, violating ADR-012(4) (load-time error) and
ADR-012(5) (exit codes {0,2}). Pinned: a missing required ui key must fail
at LOAD, and the CLI must exit 2 (never 1) on such a catalog.
"""
import re

import pytest
import yaml

from engine import cli
from engine.i18n import REQUIRED_UI as ENGINE_REQUIRED_UI
from engine.i18n import I18nError, load_i18n

REQUIRED_UI = ("web_help_label", "web_legend_title", "web_rule_help_label",
               "web_missing_info", "web_download", "web_back_results",  # web UX layer (review F5)
               "web_summary_title", "web_count_NON_COMPLIANT", "web_count_UNDETERMINED",
               "web_count_INACTIVE", "web_count_COMPLIANT", "web_count_NOT_APPLICABLE",
               "web_status_INACTIVE", "web_from", "web_deadlines_title", "web_deadlines_note",
               "web_prohibition_banner",  # Tier A/B (persona test)
               "web_yes", "web_no", "web_unknown", "web_back", "web_restart", "web_print",
               "web_question", "web_of", "web_explanation", "web_results_title",
               "provisional_notice",  # unguarded in app.js (verify 2026-09-02)
               "ai_disclosure", "intro", "hint_bool", "hint_enum",
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


# app.js keys read through a fallback (`if (x)` / `|| default`); everything
# else the web dereferences must be load-required (ADR-012(4)).
WEB_OPTIONAL_UI = {"web_next_steps", "web_print_hint"}


def test_f1_pins_track_every_unguarded_web_key():
    # drift guard (verify 2026-09-02): every literal ui("...") in web/app.js is
    # pinned above (hence load-required), unless it is in the optional set; and
    # the pinned list is a subset of the engine's own REQUIRED_UI, so a key
    # dropped from the engine fails here instead of rendering 'undefined'.
    with open("web/app.js", encoding="utf-8") as fh:
        literal = set(re.findall(r'ui\("([A-Za-z0-9_]+)"\)', fh.read()))
    unpinned = literal - WEB_OPTIONAL_UI - set(REQUIRED_UI)
    assert not unpinned, sorted(unpinned)
    assert set(REQUIRED_UI) <= set(ENGINE_REQUIRED_UI), \
        sorted(set(REQUIRED_UI) - set(ENGINE_REQUIRED_UI))


def test_f1_cli_incomplete_ui_exits_2_not_1(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(cli, "MESSAGES_PATH",
                        _catalog_missing_ui(tmp_path, "deadlines_header"))
    rc = cli.main(["--answers", _answers(tmp_path), "--as-of", "2026-09-01"])
    assert rc == 2                       # not 1 (ADR-012(5)); load-time catch
    assert capsys.readouterr().out == ""
