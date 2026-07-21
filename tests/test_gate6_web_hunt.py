# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
"""Gate-6 web adversarial hunt (ADR-007, Phase G): deterministic checks on the
web sources that pin the security surfaces the e2e also exercised live.

Attack surfaces: XSS (innerHTML with data), disclaimer-hide, URL/state
exfiltration, external network at runtime, CSP integrity, WASM-off fail-closed,
bundle staleness/tamper.
"""
import pathlib
import re
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
INDEX = (WEB / "index.html").read_text(encoding="utf-8")
APP = (WEB / "app.js").read_text(encoding="utf-8")


def _csp():
    m = re.search(r'Content-Security-Policy"\s+content="([^"]+)"', INDEX)
    assert m, "no CSP meta tag"
    return m.group(1)


# --- CSP integrity: zero-exfiltration is technically enforced --------------

def test_csp_locks_network_to_self():
    csp = _csp()
    assert "default-src 'self'" in csp
    assert "connect-src 'self'" in csp        # blocks all external fetch/XHR/WS/beacon
    # connect-src must have NO external origin
    connect = re.search(r"connect-src ([^;]+)", csp).group(1)
    assert "http://" not in connect and "https://" not in connect and "*" not in connect


def test_csp_has_no_inline_script():
    # script is external (app.js); no inline <script> body, no on*= handlers
    assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>\s*\S", INDEX)
    assert not re.search(r"\son\w+\s*=", INDEX)


# --- XSS: DOM built with textContent, never innerHTML with data -----------

def test_app_never_assigns_innerhtml():
    assert not re.search(r"\.innerHTML\s*=", APP)
    assert not re.search(r"\.outerHTML\s*=", APP)
    assert not re.search(r"insertAdjacentHTML", APP)


def test_app_has_no_eval_or_function_ctor():
    assert not re.search(r"\beval\s*\(", APP)
    assert not re.search(r"\bnew\s+Function\b", APP)


def test_app_no_inline_style_attribute():
    # Hunt G finding: style="" attributes are blocked by style-src 'self'; the
    # app must use CSSOM (element.style.prop) and CSS classes instead.
    assert 'setAttribute("style"' not in APP and "setAttribute('style'" not in APP
    assert not re.search(r"attrs:\s*\{[^}]*\bstyle\b\s*:", APP)


# --- no URL/state exfiltration channel (web analogue of ADR-012(5)) -------

def test_app_no_shareable_state_exfiltration():
    for bad in ("history.pushState", "history.replaceState", "location.hash =",
                "location.search", "document.cookie", "localStorage", "sessionStorage"):
        assert bad not in APP, f"potential state channel: {bad}"


# --- no external network at runtime (only self-relative fetches) ----------

def test_app_only_fetches_relative():
    for m in re.finditer(r"fetch\(\s*([\"'])(.*?)\1", APP):
        url = m.group(2)
        assert url.startswith("./") or url.startswith("/"), f"non-relative fetch: {url}"


# --- WASM-off fail-closed, never a blank page (E1) ------------------------

def test_app_feature_checks_wasm_and_fails_closed():
    assert "typeof WebAssembly" in APP
    assert "failClosed" in APP
    # the fail-closed message is bilingual and mentions no result is shown
    assert "fail-closed" in APP and "No result is shown" in APP


# --- disclaimer parity: boot screen carries the exact engine block ---------

def test_boot_disclaimer_matches_engine():
    from engine.render import DISCLAIMER
    # the distinctive lines must be present verbatim (no drift from the source)
    assert "=== NOT LEGAL ADVICE / NON COSTITUISCE CONSULENZA LEGALE ===" in INDEX
    assert "seek human/legal review." in INDEX
    for line in DISCLAIMER.splitlines():
        assert line in INDEX, f"boot disclaimer drifted from engine: {line!r}"


# --- bundle freeze: rebuild must match the committed sha (stale/tamper) ----

def test_bundle_matches_fresh_rebuild(tmp_path):
    out = tmp_path / "b"
    subprocess.run(["bash", "scripts/build_web.sh", str(out)], cwd=ROOT, check=True,
                   capture_output=True)
    import hashlib
    fresh = hashlib.sha256((out / "engine_bundle.zip").read_bytes()).hexdigest()
    committed = (WEB / "assets" / "BUNDLE.sha256").read_text(encoding="utf-8").split()[0]
    assert fresh == committed, "committed bundle is stale or tampered vs source"
