#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
mkdir -p .idos
git rev-parse HEAD > .idos/.session_start_sha 2>/dev/null \
  || printf 'no-git' > .idos/.session_start_sha
date -u +%s > .idos/.session_start_ts
echo '[framework] Read docs/decisions.md first. Plan-first.'
echo '[framework] STOP on discrepancy/ambiguity/scope-creep.'
echo '[framework] Verdicts are FAIL-CLOSED; rules cite the law.'
exit 0
