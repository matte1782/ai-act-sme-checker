# AI Act SME Compliance Engine - Decisions (ADR chain)

(seeded by the install; ADR-001 appended in Phase C with the
live SHA)

## ADR-001: Minimal framework installed (repo birth)
Date: `2026-07-14`. Status: `ACCEPTED`. HEAD: `fe17b6e`.
Installed the minimal discipline + measurement layer at the
birth of the AI Act SME compliance engine: CLAUDE.md contract
(incl. the four project non-negotiables: fail-closed verdicts,
statute-gated rules, not-legal-advice disclaimer in every
output path, self-classification of the engine under the Act),
this ADR chain, three Claude Code hooks (start-SHA capture,
destructive-bash guard, deterministic Stop logger), and the
.idos measurement log. claude-mem excluded; decorative toolkit
scripts excluded; heavy pre-commit gates deferred. Log schema
minimal-v1, IDENTICAL to the ACC repo install, so the 1-3 month
retrospective compares the layer across projects.

## ADR-001a (amends ADR-001): Stop logger hardened after adversarial install verification (schema v1 unchanged, cross-repo)
Date: `2026-07-14`. Status: `ACCEPTED`. HEAD: `fe17b6e` (patch in the working tree with the install, uncommitted).
Two latent corner cases in FILE-6 `session_log.sh`, found by the 4-agent adversarial
verification at install and recorded as DEFECTs in `.idos/events.jsonl`: (1) in a
zero-commit repo `git rev-parse HEAD` leaks `HEAD`+newline into `sha1`, splitting the
appended JSON row into two unparseable lines (session_log.sh:6); (2) a non-numeric
`.idos/.session_start_ts` breaks the `dur` arithmetic and emits `"dur_s":,`
(session_log.sh:9). Both were unreachable in this repo's installed state; fixed anyway
because the logger's pre-registered promise is always-parseable rows. Fix (2 lines):
`git rev-parse --verify` (fails clean, empty stdout) and a digit-only guard
`case "$ts0" in ''|*[!0-9]*) ts0=0;; esac`. Row shape unchanged -> log schema stays v1,
no bump. The SAME two-line change landed the same day in the OTHER instrumented repo
(ACC, its ADR-020) to preserve cross-project comparability. Verified by an 8-run corner
matrix (normal / zero-commit / corrupted-ts / no-git x both repos' scripts): every run
exits 0 and appends exactly one parseable schema-v1 row (zero-commit -> single line with
sha1 "unknown"; corrupted-ts -> integer dur_s). Pre-existing drift noted, NOT reconciled
here: ACC's FILE 6 logs `ts` as epoch (collapsed printf, June install) while this repo
logs ISO-8601 Z; the key set and row validity are identical, so the retrospective is
unaffected.

## ADR-002: v1 scope = triage slice; temporal validity mandatory
Date: 2026-07-14. Status: ACCEPTED. HEAD: fe17b6e.
V1 answers what an SME faces in the next 12 months: (a) in-scope
check (AI system definition, operator role, territorial scope);
(b) Art. 5 prohibited practices incl. the Omnibus NCII/CSAM
addition (applies 2026-12-02); (c) Art. 50 transparency (applies
2026-08-02; Art. 50(2) legacy 2026-12-02); (d) Art. 4 literacy
(softened by Omnibus: support, not guarantee); (e) risk-class
triage + personalized deadline calculator per the post-Omnibus
timeline (Annex III 2027-12-02; Annex I 2028-08-02). High-risk
Chapter III obligations are informational output in v1 (deadline
+ checklist pointer), NOT verdict-bearing rules. Consequence of
the Omnibus: every rule MUST carry temporal validity
(applies_from, optional applies_until, amending act); every
verdict is stamped "as of DATE, corpus version V". A rule
without validity dates does not load.

## ADR-003: deterministic verdict core; no LLM in verdict path
Date: 2026-07-14. Status: ACCEPTED. HEAD: fe17b6e.
Evidence: legal hallucination 69-88% for general LLMs on specific
legal queries, with reinforcement of users' incorrect assumptions
(Dahl et al. 2024, Stanford RegLab); purpose-built legal RAG
tools still 17-33% (Stanford 2025), sycophancy a major error
type. A probabilistic component in the verdict path is
incompatible with fail-closed. Decision: v1 verdicts are computed
by a deterministic rule engine over typed facts from a structured
questionnaire. Trivalent logic: TRUE/FALSE/UNKNOWN; UNKNOWN
propagates; default verdict UNDETERMINED. LLM intake assistant
DEFERRED to v2+ under a constraint pre-registered NOW: the LLM
may only PROPOSE structured facts; each proposed fact requires
explicit user confirmation before entering the engine; any
unconfirmed fact resolves to UNKNOWN. OpenFisca is a design
reference (date-based parameters, unknown propagation,
explanation trees), NOT a dependency (AGPL; numeric-calculation
bias per its own docs).

## ADR-004: stack = Python 3.12, rules as YAML, pytest
Date: 2026-07-14. Status: ACCEPTED. HEAD: fe17b6e.
Python 3.12 (rules-as-code ecosystem standard; contributor pool).
Rules and facts schema as YAML data files validated at load time
(pydantic permitted for schema validation). Tests: pytest,
including property tests for the invariants in
docs/architecture.md. Stdlib-first; no web framework, no DB in
v1 (CLI first). Licensing of THIS repo: to be decided ADR-006
before first release (AGPL contamination from OpenFisca avoided
by ADR-003).

## ADR-005: documentation contract (traceability, minimal prose)
Date: 2026-07-14. Status: ACCEPTED. HEAD: fe17b6e.
All docs are minimal: no decorative prose. Every architecture or
algorithm section in docs/ carries a trailing line:
`Impl: TBD` or `Impl: [<path>:L<a>-L<b>](<relative-link>)`.
Sections with Impl: TBD are unimplemented checklist items. When
code implementing a section lands, its Impl: line is updated IN
THE SAME change; divergence between doc and code is a DEFECT
(log to .idos/events.jsonl). A deterministic trace-checker
script (verifies links resolve and cited line ranges exist) is
pre-registered here and built at Gate 3; format above is fixed
now to stay machine-checkable.

## ADR-005a: amends ADR-005 - trace-checker anticipated to Gate 2
Date: 2026-07-14. Status: ACCEPTED. HEAD: 9525b96.
ADR-005 scheduled the trace-checker for Gate 3. Anticipated to
Gate 2 at owner request: day-0 deterministic verification.
`scripts/check.sh` is the single gate entry point (tests +
trace-check + log-parse). Every gate session ends with its
verbatim output: `GATE_PASS`, or `GATE_FAIL <reason>` reported
as PARTIAL. `PARTIAL: N` from the trace-checker flags
unimplemented sections deterministically. Gate rule hardened
project-wide: numeric gates count DISTINCTIVE markers only
(e.g. 'Impl: TBD', never 'Impl:'); expected counts derivable
from repo state are captured live in Phase 0, never hardcoded.

## ADR-007: sub-agents - adversarial verification ONLY
Date: 2026-07-14. Status: ACCEPTED. HEAD: edacd2d.
Amends the CLAUDE.md exclusion ("no sub-agents yet"), which the
Gate-2 bypass hunt de facto violated (disclosed, high yield:
17 findings incl. 1 CRITICAL). Regularized: sub-agents are
PERMITTED exclusively for post-GREEN adversarial verification
(bypass hunts, property fuzzing, spec attacks) and PROHIBITED
for implementation, tests-as-spec authoring, or doc writing.
Rationale: builder/attacker separation is structural
anti-confirmation-bias. Every hunt logs one GATE event with
findings count; confirmed findings become pinning tests before
fixes (TDD preserved).

## ADR-008: validation test contract - malformed-class enumeration
Date: 2026-07-14. Status: ACCEPTED. HEAD: edacd2d.
Root cause of the Gate-2 CRITICAL (whitespace citations loading):
the spec said "missing/empty" without enumerating adverse
classes. Contract, binding for every validation surface (loader,
manifest, oracle, CLI input): tests MUST enumerate at minimum:
(1) missing field; (2) empty value; (3) whitespace-only string;
(4) wrong type; (5) unknown/misspelled key; (6) boundary values
(dates at applies_from/until edges, zero/negative counts);
(7) duplicate identifiers. A validation feature without this
enumeration is INCOMPLETE regardless of GREEN status.
