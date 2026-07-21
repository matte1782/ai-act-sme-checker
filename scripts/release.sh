#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
#
# Release PREPARE (ADR-015). Fail-closed: it verifies a clean tree + GATE_PASS +
# a reproducible frozen bundle, then PRINTS the exact annotated-tag command. It
# NEVER tags and NEVER pushes - tagging and pushing are human steps (and require
# CI green on GitHub, which is unverifiable here). Usage: release.sh vX.Y.Z
set -euo pipefail
cd "$(dirname "$0")/.."
PY=$(command -v python3 || command -v python)

VERSION="${1:-}"
# ADR-008 on the version input: missing / empty / wrong format.
if [ -z "${VERSION// }" ]; then
  echo "RELEASE_REFUSE: version required, e.g. release.sh v1.0.0"; exit 2
fi
if ! printf '%s' "$VERSION" | grep -qE '^v[0-9]+\.[0-9]+\.[0-9]+$'; then
  echo "RELEASE_REFUSE: version must match v<major>.<minor>.<patch>, got '$VERSION'"; exit 2
fi

# Refuse on a dirty tree (release only from a committed state).
if [ -n "$(git status --porcelain)" ]; then
  echo "RELEASE_REFUSE: working tree not clean - commit Gate work first"; exit 2
fi

# Full deterministic gate must pass.
gate_out="$(bash scripts/check.sh 2>&1 || true)"
if ! printf '%s' "$gate_out" | grep -q 'GATE_PASS'; then
  echo "RELEASE_REFUSE: check.sh did not reach GATE_PASS"; exit 2
fi
TESTS="$(printf '%s' "$gate_out" | grep -oE '[0-9]+ passed' | head -1)"

# The frozen bundle must reproduce byte-for-byte.
tmp="$(mktemp -d)"
bash scripts/build_web.sh "$tmp" >/dev/null 2>&1 || { echo "RELEASE_REFUSE: bundle build failed"; rm -rf "$tmp"; exit 2; }
FRESH="$(sha256sum "$tmp/engine_bundle.zip" | awk '{print $1}')"
rm -rf "$tmp"
FROZEN="$(awk '{print $1}' web/assets/BUNDLE.sha256)"
if [ "$FRESH" != "$FROZEN" ]; then
  echo "RELEASE_REFUSE: rebuilt bundle sha ($FRESH) != frozen ($FROZEN)"; exit 2
fi

CORPUS="$("$PY" -c "import yaml;print(yaml.safe_load(open('corpus/manifest.yaml'))['corpus_version'])")"
STATUS="$("$PY" -c "import sys;sys.path.insert(0,'.');from engine.render import _corpus_status;print(_corpus_status('$CORPUS'))")"
PYODIDE="$(head -1 web/vendor/pyodide/VERSION)"

echo "RELEASE_READY $VERSION"
echo
echo "# Human step - release.sh never tags or pushes. Verify CI is GREEN on"
echo "# GitHub first, then run:"
echo
cat <<TAGCMD
git tag -a $VERSION -m "$VERSION

bundle_sha256: $FROZEN
corpus_version: $CORPUS ($STATUS)
$PYODIDE
tests: $TESTS

Deploy: GitHub Pages serving web/ verbatim; the live site's
web/assets/BUNDLE.sha256 must equal the value above."
git push origin $VERSION
TAGCMD
