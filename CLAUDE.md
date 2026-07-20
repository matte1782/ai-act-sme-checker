# AI Act SME Compliance Engine - Operating Contract

This repo runs under a minimal deterministic discipline layer.
No claude-mem.

## Session start (recall)
1. Read `docs/decisions.md` (the ADR chain) before any work. It
   is the memory.
2. State a numbered plan before editing code on a non-trivial
   task; wait for confirmation.

## Discipline (every session)
- STOP on a numeric/factual discrepancy, ambiguity, or scope
  creep beyond the prompt. Surface it; do not push through.
- Every factual claim about code/data cites `file:line`; every
  claim about the LAW cites Article/Annex + paragraph.
- Fix the code, not the harness. Never weaken a check or disable
  a hook to make something pass.
- Observation separate from interpretation.
- Sub-agents: adversarial verification only, never
  implementation (ADR-007).
- Validation tests enumerate malformed classes: missing, empty,
  whitespace, wrong-type, unknown-key, boundary, duplicate
  (ADR-008).
- Entry: dirty tree only per ADR-010; precedents live in ADRs,
  never in agent memory.
- Rules: statute-first, opposite-comment, timeline-anchored
  dates, expressiveness STOPs (ADR-011).
- Output paths per ADR-012: registered, disclaimer-structural,
  no verdicts in exit codes, i18n load-strict.

## Project non-negotiables (the engine's ethics)
- FAIL-CLOSED: when the rules do not decide, the verdict is
  'non determinabile - requires human/legal review'. Never guess
  'compliant'. A hundred honest UNDETERMINED beat one false
  COMPLIANT.
- RULES AS DATA, STATUTE-GATED: every rule carries its legal
  source (Article/Annex + paragraph). A rule without a citation
  does not ship.
- NOT LEGAL ADVICE: every user-facing output path (CLI, API, UI,
  report) carries the disclaimer. It is a design constraint of
  each output path, not a README footer.
- SELF-CLASSIFICATION: the engine itself falls under the Act's
  definition of an AI system (logic/knowledge-based approaches
  are included); its own classification is documented in docs.

## Memory backbone
- `docs/decisions.md`: append-only ADR chain, one decision per
  ADR. Never edit a past ADR; add an amendment `ADR-Na`.

## Measurement (do not skip - this is why the layer exists)
- `.idos/session_log.jsonl` is written automatically by the Stop
  hook (deterministic, zero-token). Do NOT write it by hand.
- When a STOP fires, a gate catches a real issue, or you find a
  defect: append ONE line to `.idos/events.jsonl` in the fixed
  schema (see `.idos/FRAMEWORK_BASELINE.md`), <=30 words.

## Excluded by design
- No claude-mem. No decorative prompt scripts. No heavy
  pre-commit gates at birth. No sub-agents yet.

## Documentation contract (ADR-005)
- Docs minimal, no excess prose.
- Every architecture/algorithm section ends with an `Impl:` line:
  `Impl: TBD` until implemented, then
  `Impl: [<path>:L<a>-L<b>](<relative-link>)` updated in the
  same change as the code. Divergence = DEFECT (events.jsonl).
