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

## ADR-009: oracle golden set v1 FROZEN
Date: 2026-07-14. Status: ACCEPTED. HEAD: 5d65927.
14 scenarios (S01-S14) authored in chat 2026-07-14, installed
verbatim, frozen: sha256 in oracle/FREEZE.sha256, verified by
check.sh on every run. Modification protocol: any change to a
frozen scenario requires an ADR-009x amendment stating the legal
reason + citation, then re-freeze; silent edits are DEFECTs.
Golden set = Gate-4 spec: rules and facts schema are written to
satisfy these cases; engine extensions required: INACTIVE
matching (applicability leaf) and NOT_APPLICABLE status
(Art. 2 scope). Known dependency: dates reflect the Omnibus
final agreement; if the Gate-3a preOJ branch was taken and the
OJ text diverges on a date, that is an ADR-009a amendment, not
a silent fix.
FREEZE hashes:
fb29f9376b95440b24f6962af75a18c3477abade66dd1d8040361860eabc5844 *golden/S01.yaml
b299589388cd6654b5ae713ab73873669f5bbcdc4899a7103b1cfdcc99369336 *golden/S02.yaml
4ac8658f10aa1c6956326f4bec2c6c6f91f72e0d8667e00bc20a8d3a7af2bbe7 *golden/S03.yaml
dfddee7e5f383c85867e3db6417f6cb0f9f9237fb909439fbd8fbc4f88883114 *golden/S04.yaml
6a3e1eee8e3c1cfbaff62960032a8795ecfef8f59f583e80ceb263cb6f31d8e6 *golden/S05.yaml
836dcd80b1955f0b13f17c319c0d5b278575c334e5b1ed75024b3fd991c1fb62 *golden/S06.yaml
281e6a79b7ea6a7772eb6002d4e33051add8e22ef71cbaefd77d34e150639ede *golden/S07.yaml
8ed66f339c8b659dd90ea22a13106709c77ab8b59ded93ef348f831cb0737123 *golden/S08.yaml
aec90aa12d002893e24908e2cacd0bb0ead6e568ef22f5fda38f051c779e6e26 *golden/S09.yaml
b73fa03c550787a9327035b2bdd6a619862bce696d009303c0a092cb25e29cb4 *golden/S10.yaml
a89429c49bfe1cc65104abfaf88c6957873a540be25e52641d8c3b4baa2b1be6 *golden/S11.yaml
82ae4ddfb9f7b44849bc86a6e6a5a6ba9621f338a6eb65dcb3731951c085d060 *golden/S12.yaml
963d35b40f010ced54d54c0c171d7e7fc6ac74804f7c8c80415c5d311ceccc21 *golden/S13.yaml
41f9ee853c929ec5d5dd5dcc9536240f9f2f71cd9a6ce92527b816887b3e2fb8 *golden/S14.yaml

## ADR-010: session entry protocol; precedents live in ADRs only
Date: 2026-07-15. Status: ACCEPTED. HEAD: 694556b.
Gates 3a/3b entered on dirty trees; the agent applied a
'standing owner ruling' (commit-first) recalled from a prior
session. Disclosed and correct in outcome, but precedent held in
agent memory is drift by construction. Codified: at session
entry, if every dirty path belongs to the previous gate's
deliverables AND check.sh ends GATE_PASS, exactly one
baseline-restoring commit is authorized; any other dirty state
is a STOP. No other cross-session ruling may be applied unless
written in an ADR. Commit messages are not ADRs.

## ADR-011: rule authoring protocol (anti-confirmation-bias)
Date: 2026-07-15. Status: ACCEPTED. HEAD: 694556b.
The rule author can see the 14 frozen cases: teaching-to-the-test
is the structural temptation of Gate 4. Protocol, binding:
(1) STATUTE-FIRST: before authoring a rule, read the cited
article in corpus/raw (the manifest names the files); the rule
encodes the article, the oracle only judges the outcome. Logic
reverse-engineered from a golden scenario is a DEFECT.
(2) PRE-MORTEM (prospective hindsight, Klein): before any code,
write docs/gate4_premortem.md - 'this gate failed in 3 months:
why?' - >=3 concrete causes, <=15 lines total.
(3) CONSIDER-THE-OPPOSITE (Lord/Lepper/Preston): every rule
carries a '# opposite: [<RULE_ID>] <one line: why the contrary
verdict would violate the cited provision>' comment; enforced by
test (comment ids must equal loaded rule ids, both directions).
(4) NO HAND-TYPED DATES: every rule declares timeline_ref
(list of corpus/timeline.yaml obligation strings); a test
asserts every date in the rule is covered by its referenced
entries. Dates are anchored, never re-typed from memory.
(5) EXPRESSIVENESS STOP: where the rule grammar cannot express
the cited provision faithfully (an exception, a scope nuance),
STOP with the article text quoted - never approximate silently.
Deterministic gates: (3) and (4) sandbox-verified 2026-07-14.

## ADR-011a: amends ADR-011 - pre-mortem generalized per gate
Date: 2026-07-15. Status: ACCEPTED. HEAD: 2d46af3.
ADR-011(2) named docs/gate4_premortem.md. Generalized: every
gate session writes docs/gate<N>_premortem.md (>=3 causes,
<=15 lines, no Impl: lines) BEFORE any code, and uses it as the
review lens for the gate's build and hunt phases.

## ADR-012: output-path contract (CLI first)
Date: 2026-07-15. Status: ACCEPTED. HEAD: 2d46af3.
Every user-facing output path MUST: (1) be registered in
docs/architecture.md L5; (2) route verdict content EXCLUSIVELY
through render_report (or a successor with the same structural
disclaimer refusal) - no second print path for verdicts; (3)
carry its own INV-4 test (full-run output contains the exact
disclaimer block); (4) i18n via i18n/messages.yaml - a missing
catalog key is a LOAD-TIME error, never a silent fallback to
another language; (5) process exit codes carry NO compliance
semantics: 0 = report produced (whatever the verdicts), 2 =
input/usage error. Encoding verdicts in exit codes would let a
CI pipeline treat this tool as a legal gate - the misuse the
NOT-LEGAL-ADVICE constraint exists to prevent. (6) The CLI
declares to the user that they are interacting with an AI-based
system (the engine's own Art. 50(1)-style disclosure; see
docs/self_classification.md). (7) The corpus refresh (OJ
publication) is NEVER performed inside an output-path gate: it
is a re-run of PROMPT 4 Phase C (manifest refresh_task).

## ADR-006: licence = EUPL-1.2
Date: 2026-07-20. Status: ACCEPTED. HEAD: 555a603. EUPL-1.2, owner
decision 2026-07-15. Rationale: the European Commission's own
licence; legally binding in Italian and all EU languages; copyleft
strong enough to prevent closed proprietary forks while remaining
institution-friendly (public bodies can re-host and adapt). LICENCE
file = official EN text (joinup.ec.europa.eu EUPL-1.2 EN, acquired
2026-07-20), sha256
6fc9e709ccbfe0d77fbffa2427a983282be2eb88e47b1cdb49f21a83b4d1e665.
Every source file gains a 2-line SPDX header
(SPDX-License-Identifier: EUPL-1.2) - header-only edits to existing
files are AUTHORIZED by this ADR (no logic changes). Dependency
check: Pyodide (MPL-2.0) and PyYAML (MIT) are compatible as
dependencies of an EUPL-1.2 work.

## ADR-013: web platform = client-side static (Pyodide); scope
Date: 2026-07-20. Status: ACCEPTED. HEAD: 555a603. Options weighed
(owner-arbitrated 2026-07-15, market analysis on record in chat):
(A) ACCEPTED - static SPA, real engine in-browser via Pyodide.
Single source of truth (same engine/rules/schema/renderer, same
tests); user answers NEVER leave the device (decisive for
professionals handling client data - the questionnaire includes
facts about potentially unlawful practices); zero server, free
static hosting, re-hostable verbatim by institutions (EUPL); release
bundle sha256-frozen (deploy = auditable artifact). Accepted cost:
first load ~6-15MB / 4-5s init (mitigated: loading screen doubles as
the ADR-012(6) AI disclosure + disclaimer; assets cached after),
WASM required (unsupported browsers get an explicit fail-closed
message, never a blank page). (B) REJECTED - JS re-implementation of
rule evaluation: dual source of truth, drift by construction, oracle
would need to arbitrate two engines. Violates the project's core
discipline. (C) DEFERRED - hosted Python API: makes us a data
processor for sensitive answers, adds ops/uptime/attack surface and
costs that scale with adoption. Revisit trigger: integrator demand
for a server API (Gate 7+, its own ADR). UI is framework-free vanilla
JS with NO build/bundling step: deployed files are the readable
source (institutional auditability). Languages v1: it + en (already
first-class); additional EU languages require a native-review gate;
market focus: Italy. Zero-exfiltration is enforced by CSP (no
external connect-src) and verified by e2e test, not merely promised.

## ADR-014: internal planning docs, git-ignored; protocol pre-registration
Date: 2026-07-20. Status: ACCEPTED. HEAD: 555a603.
docs/internal/ holds owner-facing planning material (launch
sequencing, user-research protocol, institutional outreach):
git-ignored, local-only, never in public history. The user-test
protocol is pre-registered - metrics and thresholds frozen
before the first participant, append-only amendments - the same
anti-confirmation-bias mechanism as the frozen oracle (ADR-009)
applied to product research.
