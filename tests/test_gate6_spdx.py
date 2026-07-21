# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
"""Gate-6 SPDX coverage (PROMPT 8 Phase H, ADR-006).

Every first-party .py/.js/.sh source file carries the EUPL-1.2 SPDX header.
Vendored third-party code (web/vendor/**, MPL-2.0 Pyodide + MIT PyYAML) is
excluded - it keeps its own upstream licence. Deterministic: files vs headers.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXCLUDE = ("web/vendor", "__pycache__", "/.git/", ".benchmarks", ".pytest_cache",
           ".playwright-mcp")
MARK = "SPDX-License-Identifier: EUPL-1.2"


def _sources():
    out = []
    for ext in ("*.py", "*.sh", "*.js"):
        for p in ROOT.rglob(ext):
            s = "/" + str(p.relative_to(ROOT)).replace("\\", "/") + "/"
            if any(e in s for e in EXCLUDE):
                continue
            out.append(p)
    return out


def test_every_source_file_has_spdx_header():
    files = _sources()
    assert files, "no source files discovered (glob broke)"
    missing = [str(p.relative_to(ROOT)) for p in files
               if MARK not in p.read_text(encoding="utf-8")]
    assert not missing, f"{len(missing)} source files missing SPDX header: {missing}"


def test_vendored_code_is_not_relicensed():
    # sanity: we did NOT stamp our SPDX onto vendored third-party files
    vendor = ROOT / "web" / "vendor" / "pyodide" / "pyodide.mjs"
    if vendor.exists():
        assert MARK not in vendor.read_text(encoding="utf-8", errors="ignore")
