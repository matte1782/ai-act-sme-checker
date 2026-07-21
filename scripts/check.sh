#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
# Single deterministic gate runner. Exit 0 <=> GATE_PASS.
PY=$(command -v python3 || command -v python)
status=0
echo "== tests"
"$PY" -m pytest -q
rc=$?
# Sanctioned exception (ADR-005a): pytest exit 5 = zero tests collected,
# allowed only so the runner works before the first test lands.
if [ "$rc" -ne 0 ] && [ "$rc" -ne 5 ]; then status=1; fi
echo "== trace"
"$PY" scripts/trace_check.py || status=1
echo "== oracle"
# ADR-009: the golden set is FROZEN; any byte drift fails the gate.
( cd oracle && sha256sum -c FREEZE.sha256 --quiet ) \
  || { echo "ORACLE_FROZEN_VIOLATION"; status=1; }
# Self-arming: ORACLE_PENDING (exit 0) is the ONLY sanctioned
# non-evaluating pass; once rules/*.yaml exist it evaluates for real.
"$PY" scripts/oracle_check.py || status=1
echo "== web"
# ADR-013: the web bundle is deterministic + sha256-frozen. If it exists,
# rebuild it into a temp dir and compare to the frozen BUNDLE.sha256; a
# mismatch means stale (source changed, not rebuilt) or tampered. No masking:
# absent bundle => WEB_SKIP, never a silent pass with a broken deploy.
if [ -f web/assets/engine_bundle.zip ]; then
  tmp=$(mktemp -d)
  bash scripts/build_web.sh "$tmp" >/dev/null 2>&1 || { echo "WEB_BUILD_FAIL"; status=1; }
  new=$(sha256sum "$tmp/engine_bundle.zip" 2>/dev/null | awk '{print $1}')
  old=$(awk '{print $1}' web/assets/BUNDLE.sha256 2>/dev/null)
  rm -rf "$tmp"
  if [ -n "$new" ] && [ "$new" = "$old" ]; then
    echo "WEB_OK $old"
  else
    echo "WEB_BUNDLE_MISMATCH (rebuild != frozen BUNDLE.sha256; stale or tampered)"
    status=1
  fi
else
  echo "WEB_SKIP"
fi
echo "== session log"
if [ -f .idos/session_log.jsonl ]; then
  tail -1 .idos/session_log.jsonl | "$PY" -c \
"import sys,json;json.loads(sys.stdin.read());print('LOG_OK')" \
  || status=1
else
  echo "LOG_SKIP (no session log yet)"
fi
if [ "$status" -eq 0 ]; then echo "GATE_PASS"; else
  echo "GATE_FAIL see checks above"; fi
exit $status
