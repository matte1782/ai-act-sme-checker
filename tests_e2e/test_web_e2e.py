# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
"""Gate-7 e2e regression gate (PROMPT 9 Phase C1), pytest-playwright style.

The zero-exfiltration guarantee and the disclaimer/i18n/print/mobile behaviour
become a REPEATABLE gate (not the point-in-time MCP run of Gate 6).

Local vs CI contract (ADR-015, dependency preflight):
- pytest-playwright ABSENT locally -> the whole module SKIPS with the explicit
  reason 'E2E_LOCAL_SKIP (playwright unavailable; CI will enforce)'. Never a
  silent pass.
- CI=1 -> the skip is FORBIDDEN: a missing plugin is an IMPORT ERROR (collection
  failure), so CI cannot go green without actually running these.

Run in CI: serve_web.py in background, then `CI=1 pytest tests_e2e/`.
"""
import os
import re

import pytest

CI = os.environ.get("CI") == "1"
BASE = os.environ.get("BASE_URL", "http://127.0.0.1:8000")

try:
    import pytest_playwright  # noqa: F401
    HAVE_PW = True
except ImportError:
    HAVE_PW = False
    if CI:
        # CI=1: Playwright MUST be installed; do not mask its absence as a skip.
        raise

pytestmark = pytest.mark.skipif(
    not HAVE_PW,
    reason="E2E_LOCAL_SKIP (playwright unavailable; CI will enforce)",
)

BOOT_TIMEOUT = 90_000  # Pyodide first load + WASM compile can be slow on CI


def _boot(page):
    page.goto(f"{BASE}/index.html")
    # UX pass 2026-08-27 (pilot F-P1): the boot screen no longer auto-advances;
    # the wizard appears only after the user clicks Start. The e2e drives the
    # same path a human takes.
    page.wait_for_selector("#boot-start:not([hidden])", timeout=BOOT_TIMEOUT)
    page.locator("#boot-start").click()
    page.wait_for_selector("#wizard .q-prompt", timeout=BOOT_TIMEOUT)


def _answer_all(page, unknown_at=5, yes_at=(0, 1, 4)):
    # Question indices follow schema/facts.yaml order: 0 is_ai_system,
    # 1 in_eu_market, 4 interacts_with_persons, 5 interaction_disclosed,
    # 11 practice_social_scoring (enum steps take the first option).
    for i in range(30):
        if not page.locator("#results").is_hidden():
            break
        btns = page.locator("#wizard .answers button")
        # EXACT match: Playwright has_text is substring + case-insensitive, so a
        # bare "No" would also match "Non so"/"none" (enum). Anchor it. For enum
        # steps there is no "No" button -> fall back to the first option.
        if i == unknown_at:
            label = r"^Non so$"
        elif i in yes_at:
            label = r"^Sì$"
        else:
            label = r"^No$"
        target = btns.filter(has_text=re.compile(label)).first
        (target if target.count() else btns.first).click()


def test_network_zero_exfiltration(page):
    origin = BASE
    external = []
    page.on("request", lambda r: external.append(r.url)
            if not r.url.startswith(origin) else None)
    _boot(page)
    after_load = []
    page.on("request", lambda r: after_load.append(r.url))
    _answer_all(page)
    page.wait_for_selector("#results .disclaimer")
    assert external == [], f"requests left the origin: {external}"
    assert after_load == [], f"requests after load (should be zero): {after_load}"


def test_disclaimer_computed_visible(page):
    _boot(page)
    _answer_all(page)
    # .first: the always-visible top disclaimer (a second copy lives inside the
    # print-only #print-meta; both share the class, so scope to the first).
    disc = page.locator("#results .disclaimer").first
    assert disc.is_visible()
    assert "NON COSTITUISCE CONSULENZA LEGALE" in disc.inner_text()


def test_lang_toggle_switches_question_text(page):
    _boot(page)
    it = page.locator("#wizard .q-prompt").inner_text()
    page.locator(".lang-toggle button", has_text="English").click()
    assert page.locator("#wizard .q-prompt").inner_text() != it


def test_print_contains_disclaimer(page):
    _boot(page)
    _answer_all(page)
    page.emulate_media(media="print")
    meta = page.locator("#print-meta")
    assert "NOT LEGAL ADVICE" in meta.inner_text()
    assert "corpus_version" in meta.inner_text()


def test_no_provisional_notice_after_oj_refresh(page):
    # ADR-016: corpus flipped PROVISIONAL -> FINAL on the OJ refresh, so the
    # provisional banner must retire by itself. (Before the refresh this test
    # asserted the notice WAS shown; the notice is driven by corpus_status.)
    _boot(page)
    _answer_all(page)
    assert page.locator("#results .provisional").count() == 0


def test_question_helper_and_results_legend(page):
    # UX rounds 2026-08-27: Q1 carries a plain-language helper (closed by
    # default, opens on click); results carry the legend and per-rule help.
    _boot(page)
    bar = page.locator("#wizard [role='progressbar']")
    assert bar.get_attribute("aria-valuemin") == "0" and bar.get_attribute("aria-label")
    helper = page.locator("#wizard details.q-help")
    assert helper.count() == 1
    helper.locator("summary").click()
    assert "art. 3" in helper.locator(".help-text").inner_text()
    _answer_all(page)
    assert page.locator("#results details.legend").count() == 1
    assert page.locator("#results .card details.q-help").count() >= 1
    # persona test (Tier A/B): summary block, INACTIVE badge for the rules not
    # yet in force, deadlines section AFTER the cards (never before).
    assert page.locator("#results .summary .summary-counts").count() == 1
    # date-bound pin: the last rule to enter into force is HR_ANNEX_III
    # (2027-12-02); until then at least one card is INACTIVE on this path.
    as_of = re.search(r"as_of: (\d{4}-\d{2}-\d{2})", page.locator("#print-meta").inner_text()).group(1)
    if as_of < "2027-12-02":
        assert page.locator("#results .badge.INACTIVE").count() >= 1
    order = page.evaluate(
        "() => { const h = [...document.querySelectorAll('#results h2')].map(e => e.textContent);"
        " const r = h.findIndex(t => /Risultati|Results/.test(t));"
        " const d = h.findIndex(t => /applicano|start to apply/.test(t));"
        " return r >= 0 && d > r; }"
    )
    assert order, "deadlines section must come after the verdict cards"
    # the missing-answer list shows QUESTIONS, never internal fact names
    unknowns = page.locator("#results .unknowns li")
    if unknowns.count():
        assert "_" not in unknowns.first.inner_text()


def test_prohibition_banner_on_article_5_violation(page):
    # Tier B2 (persona test): a NON_COMPLIANT Art. 5 rule carries the
    # "prohibited practice" banner; the kind comes from the engine (rule_kinds),
    # never from JS. Path: social scoring = Sì (question 11).
    _boot(page)
    _answer_all(page, yes_at=(0, 1, 4, 11))
    banner = page.locator("#results .card .prohibition")
    assert banner.count() == 1
    assert "VIETATA" in banner.inner_text()
    assert page.locator("#results .badge.NON_COMPLIANT").count() == 1


def test_jump_back_returns_to_results(page):
    # Review F7: answering a question reached from a results card returns to
    # the results directly, not to the next question.
    _boot(page)
    _answer_all(page)
    jump = page.locator("#results .unknowns button.jump").first
    if not jump.count():
        pytest.skip("no UNDETERMINED card with missing answers on this path")
    jump.click()
    page.wait_for_selector("#wizard .q-prompt")
    back = page.locator("#wizard .nav button")
    assert back.is_enabled() and "risultati" in back.inner_text()
    page.locator("#wizard .answers button", has_text=re.compile(r"^Sì$")).first.click()
    page.wait_for_selector("#results .card")
    assert not page.locator("#results").is_hidden()


def test_download_report_is_a_file_named_by_as_of(page):
    # Review: the downloaded report is a real file whose name carries the
    # report's as_of date (render time), delivered without leaving the page.
    _boot(page)
    _answer_all(page)
    as_of = re.search(r"as_of: (\d{4}-\d{2}-\d{2})", page.locator("#print-meta").inner_text()).group(1)
    with page.expect_download() as dl:
        page.locator("#results .actions button", has_text="Scarica").click()
    assert dl.value.suggested_filename == f"ai-act-self-check_{as_of}.txt"
    assert not page.locator("#results").is_hidden(), "download must not navigate away"


def test_mobile_flow_disclaimer_visible_no_hscroll(page):
    # NEW mobile scenario (viewport 375x812): full flow, disclaimer visible
    # without horizontal scroll, 'Non so' tappable.
    page.set_viewport_size({"width": 375, "height": 812})
    _boot(page)
    non_so = page.locator("#wizard .answers button", has_text=re.compile(r"^Non so$")).first
    assert non_so.is_visible()
    box = non_so.bounding_box()
    assert box and box["height"] >= 32 and box["width"] <= 375   # tap target, fits width
    _answer_all(page)
    disc = page.locator("#results .disclaimer").first
    assert disc.is_visible()
    overflow = page.evaluate(
        "() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1"
    )
    assert not overflow, "horizontal scroll on mobile (layout overflows viewport)"
