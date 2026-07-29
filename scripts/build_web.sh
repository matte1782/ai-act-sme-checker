#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
#
# Deterministic web bundle (ADR-013). Assembles web/assets/engine_bundle.zip
# from the engine sources + rules + schema + i18n + corpus manifest/timeline
# (corpus/raw EXCLUDED). Deterministic: sorted entry order, fixed timestamps,
# STORED (no zlib dependency) -> stable sha256 across runs on any machine.
# Usage: build_web.sh [OUT_DIR]   (default web/assets). Prints WEB_BUNDLE_OK <sha>.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="${1:-web/assets}"
mkdir -p "$OUT"
PY=$(command -v python3 || command -v python)

"$PY" - "$OUT/engine_bundle.zip" <<'PY'
import pathlib, sys, zipfile

out = sys.argv[1]
files = []
for pattern in ("engine/*.py", "rules/*.yaml", "schema/*.yaml", "i18n/*.yaml"):
    files += [p.as_posix() for p in pathlib.Path(".").glob(pattern)]
files += ["corpus/manifest.yaml", "corpus/timeline.yaml"]
files = sorted(f for f in set(files) if "__pycache__" not in f)
missing = [f for f in files if not pathlib.Path(f).is_file()]
if missing:
    sys.exit(f"build_web: missing bundle inputs: {missing}")

with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as zf:
    for rel in files:                       # deterministic: sorted, fixed meta
        info = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
        info.external_attr = 0o644 << 16
        # ZipInfo.create_system defaults to 0 on Windows and 3 on Unix, which
        # would make the SAME inputs hash differently on Windows vs Linux/CI.
        # Pin it so the frozen sha is truly platform-independent.
        info.create_system = 3
        # normalize CRLF->LF so the sha is EOL-independent: a Windows (CRLF)
        # working tree and a Linux/CI (LF) checkout produce the SAME bundle.
        data = pathlib.Path(rel).read_bytes().replace(b"\r\n", b"\n")
        zf.writestr(info, data)
print(f"bundled {len(files)} files", file=sys.stderr)
PY

SHA=$(sha256sum "$OUT/engine_bundle.zip" | awk '{print $1}')
printf '%s  engine_bundle.zip\n' "$SHA" > "$OUT/BUNDLE.sha256"
GITSHA=$(git rev-parse --short HEAD 2>/dev/null || echo unknown)
CORPUS=$("$PY" -c "import yaml;print(yaml.safe_load(open('corpus/manifest.yaml'))['corpus_version'])")
# built_from_git_sha is HEAD **at build time**, i.e. the PARENT of the commit
# that ships this bundle (build, then commit). The artifact's authoritative
# identity is bundle_sha256, reproducible from source (see AUDIT.md §2).
printf 'built_from_git_sha %s\ncorpus_version %s\nbundle_sha256 %s\n' "$GITSHA" "$CORPUS" "$SHA" > "$OUT/VERSION"
echo "WEB_BUNDLE_OK $SHA"
