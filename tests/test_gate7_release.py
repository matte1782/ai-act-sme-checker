# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
"""Gate-7 release.sh refusal paths (PROMPT 9 Phase G).

release.sh is PREPARE-ONLY: it must fail-closed (RELEASE_REFUSE, exit 2) on a
missing/malformed version (ADR-008 on inputs) and on a dirty tree, and it must
never tag/push itself. The happy path (RELEASE_READY + printed tag command) is
a human step on a clean tree post-commit; here we pin the refusals + the
prepare-only structure.
"""
import pathlib
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
RELEASE = "scripts/release.sh"


def _run(*args):
    return subprocess.run(["bash", RELEASE, *args], cwd=ROOT,
                          capture_output=True, text=True)


def test_missing_version_refused():
    r = _run()
    assert r.returncode == 2
    assert "RELEASE_REFUSE" in r.stdout and "version required" in r.stdout


@pytest.mark.parametrize("bad", ["1.0.0", "v1.0", "v1", "v1.2.3.4", "vX.Y.Z", "1", " "])
def test_malformed_version_refused(bad):
    r = _run(bad)
    assert r.returncode == 2
    assert "RELEASE_REFUSE" in r.stdout


def test_dirty_tree_refused():
    # deterministic regardless of ambient state: a scratch untracked file makes
    # the tree dirty, so a well-formed version must still be refused.
    scratch = ROOT / ".release_dirty_probe"
    scratch.write_text("x", encoding="utf-8")
    try:
        r = _run("v1.0.0")
        assert r.returncode == 2
        assert "RELEASE_REFUSE" in r.stdout and "not clean" in r.stdout
    finally:
        scratch.unlink()


def test_script_is_prepare_only():
    text = (ROOT / RELEASE).read_text(encoding="utf-8")
    # tag/push commands exist ONLY inside the echoed heredoc, after RELEASE_READY
    assert "RELEASE_READY" in text
    assert "cat <<TAGCMD" in text
    assert text.index("cat <<TAGCMD") < text.index("git tag -a")
    assert "never tags" in text.lower() or "never tag" in text.lower()
    assert "bundle_sha256:" in text and "corpus_version:" in text
