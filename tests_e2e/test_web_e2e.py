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
    page.wait_for_selector("#wizard .q-prompt", timeout=BOOT_TIMEOUT)


def _answer_all(page, unknown_at=5):
    for i in range(30):
        if not page.locator("#results").is_hidden():
            break
        btns = page.locator("#wizard .answers button")
        # EXACT match: Playwright has_text is substring + case-insensitive, so a
        # bare "No" would also match "Non so"/"none" (enum). Anchor it. For enum
        # steps there is no "No" button -> fall back to the first option.
        if i == unknown_at:
            label = r"^Non so$"
        elif i in (0, 1, 4):
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
    disc = page.locator("#results .disclaimer")
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


def test_provisional_notice_shown(page):
    _boot(page)
    _answer_all(page)
    assert "testo provvisorio del Consiglio" in page.locator("#results .provisional").inner_text()


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
    disc = page.locator("#results .disclaimer")
    assert disc.is_visible()
    overflow = page.evaluate(
        "() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1"
    )
    assert not overflow, "horizontal scroll on mobile (layout overflows viewport)"
