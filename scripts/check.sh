#!/usr/bin/env bash
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
