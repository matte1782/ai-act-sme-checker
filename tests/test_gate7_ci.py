# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
"""Gate-7 CI workflow lint (PROMPT 9 Phase C2).

Local validation is limited to HONESTY: the workflow yaml parses and contains
the required steps (string level). It does NOT claim CI is green - CI is
unverifiable offline (CI_UNVERIFIED_UNTIL_PUSH). Also pins the e2e module's
local-skip / CI-forbidden-skip contract so it cannot silently regress.
"""
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
CI = ROOT / ".github" / "workflows" / "ci.yml"
E2E = ROOT / "tests_e2e" / "test_web_e2e.py"


def test_ci_yaml_parses():
    data = yaml.safe_load(CI.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    # PyYAML parses the bare `on:` key as boolean True; accept either form.
    trig = data.get("on", data.get(True))
    assert isinstance(trig, dict) and {"push", "pull_request"} <= set(trig)


def test_ci_runs_check_sh_and_e2e():
    text = CI.read_text(encoding="utf-8")
    assert "runs-on: ubuntu-latest" in text
    assert 'python-version: "3.12"' in text
    assert "actions/checkout@v4" in text and "actions/setup-python@v5" in text  # pinned
    assert "bash scripts/check.sh" in text                       # step 1
    assert "pytest-playwright==0.5.2" in text                    # pinned, CI-only
    assert "playwright install --with-deps chromium" in text
    assert "serve_web.py" in text                                # server for e2e
    assert "CI=1" in text and "pytest -q tests_e2e/" in text     # step 2, enforced


def test_e2e_module_has_local_skip_and_ci_forbidden():
    text = E2E.read_text(encoding="utf-8")
    assert "E2E_LOCAL_SKIP" in text                              # explicit local skip
    assert 'os.environ.get("CI") == "1"' in text
    assert "if CI:" in text and "raise" in text                 # CI=1 => import error, no mask
    # the mobile scenario exists
    assert '"width": 375, "height": 812' in text
    assert "scrollWidth" in text                                 # no-horizontal-scroll assertion
