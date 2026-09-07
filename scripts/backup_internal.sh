#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
#
# Encrypted off-machine backup of docs/internal (git-ignored per ADR-014;
# pre-mortem 2026-09-07 item B1: the only copies lived on one laptop).
#
# What it does: packs docs/internal into a 7-Zip archive with AES-256 and
# encrypted file names (-mhe=on), named by date, into a OneDrive-synced
# folder (the OneDrive client uploads it). Then it verifies the archive
# (7z t) and prints the sha256 so the handoff can record it.
#
# What it needs (one-time, by the author, NEVER in the repo):
#   - the passphrase in %USERPROFILE%\.ai_act_backup_pass (one line), also
#     stored in the author's password manager: without it the archives are
#     unrecoverable, by design;
#   - 7-Zip installed (default path below) and OneDrive running.
#
# Usage: bash scripts/backup_internal.sh [DEST_DIR]
set -euo pipefail
cd "$(dirname "$0")/.."

SEVENZ="${SEVENZ:-/c/Program Files/7-Zip/7z.exe}"
PASSFILE="${PASSFILE:-$HOME/.ai_act_backup_pass}"
DEST="${1:-/c/Users/matte/OneDrive/ai_act_internal_backups}"
STAMP="$(date +%Y-%m-%d_%H%M)"
OUT="$DEST/docs_internal_${STAMP}.7z"

[ -d docs/internal ] || { echo "BACKUP_REFUSE: docs/internal not found"; exit 2; }
[ -x "$SEVENZ" ] || { echo "BACKUP_REFUSE: 7-Zip not found at $SEVENZ"; exit 2; }
[ -s "$PASSFILE" ] || { echo "BACKUP_REFUSE: passphrase file $PASSFILE missing or empty (create it once, outside the repo)"; exit 2; }
PASS="$(head -1 "$PASSFILE" | tr -d '\r\n')"
[ "${#PASS}" -ge 16 ] || { echo "BACKUP_REFUSE: passphrase shorter than 16 characters"; exit 2; }
mkdir -p "$DEST"

# AES-256, encrypted headers (file names hidden), solid archive, max compression.
"$SEVENZ" a -t7z -mx=9 -mhe=on -p"$PASS" "$OUT" docs/internal >/dev/null
"$SEVENZ" t -p"$PASS" "$OUT" >/dev/null || { echo "BACKUP_FAIL: archive test failed"; exit 1; }
SHA="$(sha256sum "$OUT" | awk '{print $1}')"
echo "BACKUP_OK $OUT"
echo "sha256 $SHA"
echo "files $(find docs/internal -type f | wc -l)  size $(stat -c %s "$OUT") bytes"
# keep the last 12 archives in the cloud folder
ls -1t "$DEST"/docs_internal_*.7z 2>/dev/null | tail -n +13 | xargs -r rm -f --
