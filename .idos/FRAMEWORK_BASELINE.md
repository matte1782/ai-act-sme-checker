# Framework measurement baseline (pre-registration)

Installed: 2026-07-14 at HEAD `fe17b6e`.
Framework version: minimal-v1.

## Why this log exists
To judge, after 1-3 months, whether this minimal discipline layer
adds value - by accrued non-fabricatable data, not by feeling.
Schema v1 is IDENTICAL to the ACC repo install, deliberately: two
instrumented repos, one schema, so the retrospective can COMPARE
the layer's effect across projects (compliance engine vs ACC).

## session_log.jsonl schema v1 (Stop hook; deterministic)
ts, dur_s, sha0, sha1, files, ins, dels, adr, tests, stops.

## events.jsonl schema v1 (Claude appends only when notable)
{ts, kind: STOP|GATE|DEFECT|DEVIATION, note (<=30 words), ref}.
ref may be file:line, ADR-N, or Article/Annex + paragraph.

## Retrospective questions (answer at ~30/60/90 sessions)
1. Churn: files re-edited within 3 sessions trending down?
2. STOP yield: fraction of events that were REAL catches?
3. ADR density: decision trail keeping pace with code growth?
4. Cross-project: same layer, ACC vs this repo - where does it
   earn its keep, where is it noise?
5. Honest null: no signal => the layer is noise here; revise or
   remove, and say so openly.

## Analysis
A retro aggregation script is written LATER (not now). The schema
is fixed NOW so the accruing data stays analyzable. If the schema
must change, bump to v2 and never edit past rows; note the bump
in BOTH instrumented repos to preserve comparability.
