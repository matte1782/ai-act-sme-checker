# Architecture (v1 triage slice)
Verdicts: COMPLIANT | NON_COMPLIANT | UNDETERMINED | NOT_APPLICABLE.
Default: UNDETERMINED (fail-closed, ADR-001/003). NOT_APPLICABLE is the
material-scope answer (Art. 2, Gate-4 X1), distinct from the
temporal-INACTIVE shape (UNDETERMINED + applicability leaf). All sections
carry an `Impl:` line per ADR-005.

## L1 Corpus layer
`corpus/manifest.yaml`: each legal source = {id, instrument,
ELI/EUR-Lex ref, version_date, amending_acts[], sha256 of local
text}. Rules cite corpus ids, never raw URLs.
Impl: [corpus/manifest.yaml:L1-L141](corpus/manifest.yaml)

## L2 Rules layer
`rules/*.yaml`: rule = {id, legal_source{corpus_id, article,
paragraph}, applies_from, applies_until?, applicable_if?,
timeline_ref?, logic (typed predicate tree over facts), verdict,
rationale_key}. Loader REJECTS a rule missing legal_source or
applies_from (INV-2). Gate-4 grammar: `applicable_if` is a scope
predicate (same grammar as logic, X2); `applies_from` may be a
conditional branch list `[{when, date}..., {default}]` validated
per ADR-008 (X3); `timeline_ref` anchors dates to
corpus/timeline.yaml (ADR-011(4)). v1 rules: rules/*.yaml.
Impl: [engine/loader.py:L1-L342](engine/loader.py)

## L3 Facts schema
`schema/facts.yaml`: typed facts (bool/enum/date) with i18n keys
(it/en). Gate-4: canonical vocabulary = the union of fact names
used by the frozen golden set (ADR-009), Italian first-class. The
questionnaire is generated FROM this schema; no free-text fact
enters the engine (ADR-003). The synthetic schema moved to
tests/fixtures/facts_synthetic.yaml.
Impl: [engine/facts.py:L1-L121](engine/facts.py)

## L4 Engine core
Pure function: (facts, as_of_date, corpus_version) -> verdicts +
explanation tree. Trivalent evaluation; UNKNOWN propagates
upward. No I/O, no clock reads inside the core (as_of_date is an
argument: testability + temporal queries). Gate-4 precedence (X4)
per rule: (1) temporal window (X3 branch-date selection, fail
closed on an unknown 'when') -> INACTIVE; (2) applicable_if ->
NOT_APPLICABLE (FALSE, op=='scope' citation leaf) or UNDETERMINED
(UNKNOWN, named); (3) logic. NOT_APPLICABLE never rests on an
unknown scope fact (X5). Gate-5: the temporal-INACTIVE applicability
leaf also carries the resolved "applies_from" ISO date (C1).
Impl: [engine/core.py:L1-L288](engine/core.py)

## L5 Output paths
CLI first. Renderer contract: refuses to emit any user-facing
output lacking the NOT-LEGAL-ADVICE disclaimer block (INV-4).
Every verdict rendered with: citation, as_of stamp, corpus
version, explanation tree. Gate-4: a NOT_APPLICABLE verdict and
its op=='scope' leaf render with the leaf's citation (X1). Gate-5:
an optional i18n bundle localizes status labels + a rationale line
and appends a deadlines section built from the resolved applies_from
leaf field (never parsed from a reason string).
Impl: [engine/render.py:L1-L219](engine/render.py)

### L5 CLI (ADR-012 output-path contract)
`python -m engine.cli`, two modes: non-interactive (`--answers
<file.yaml> [--as-of YYYY-MM-DD] [--lang it|en]`) and interactive
(schema-ordered questionnaire on stdin; '?' = UNKNOWN; an EOF or
interrupt mid-questionnaire yields NO partial report and exits 2).
All verdict content goes through render_report (ADR-012(2)); i18n via
i18n/messages.yaml loaded strictly - a missing key is a load error,
never a silent fallback (ADR-012(4)); exit codes are exactly {0,2}
and carry no compliance semantics (ADR-012(5)); the banner and report
declare the AI-based interaction (ADR-012(6),
docs/self_classification.md).
Impl: [engine/cli.py:L1-L212](engine/cli.py)

### L5 i18n catalog
`i18n/messages.yaml`: status_labels, rationales, ui - each with it
AND en. Strict load + completeness (every rule rationale_key, all
four statuses, all required ui.* keys) or the catalog refuses to
load (ADR-012(4)).
Impl: [engine/i18n.py:L1-L88](engine/i18n.py)

### L5 Web (ADR-013 client-side static, Pyodide)
`web/`: a static SPA running the SAME engine in-browser via Pyodide
(no build step; deployed files are the source). The wizard is
generated from schema/facts.yaml and ALL verdict content comes from
render_structured through engine/webapi.py (single source of truth;
no rule/verdict logic in JS). Zero data leaves the device: enforced
by CSP (`connect-src 'self'`, no external origins) and verified by
the e2e network assertion (tests_e2e/test_web_e2e.py, CI-enforced). The report's
disclaimer is always visible (also in print); a PROVISIONAL corpus
shows a visible notice while preOJ. The engine bundle is deterministic
and sha256-frozen (web/assets/BUNDLE.sha256), rebuilt by
scripts/build_web.sh and verified in check.sh `== web`. WASM-absent
browsers get an explicit fail-closed message, never a blank page.
Impl: [web/app.js:L1-L231](web/app.js)
Impl: [engine/webapi.py:L1-L113](engine/webapi.py)
Impl: [scripts/build_web.sh:L1-L45](scripts/build_web.sh)

### L5 Transparency note + release engineering (ADR-013 + ADR-015)
`web/privacy.html`: bilingual transparency note (same CSP), linked from
the persistent footer + boot screen; explains the CSP guarantee, the
unsafe-eval honesty (Pyodide FFI; network rests on connect-src 'self'),
and the PROVISIONAL corpus. Release engineering (ADR-015): CI
(.github/workflows/ci.yml) runs check.sh + the Playwright e2e
(zero-exfiltration network assertion + mobile viewport) on every push/PR,
so the privacy guarantee is regression-protected, not point-in-time.
Playwright is installed in CI ONLY; locally it is an explicit
E2E_LOCAL_SKIP (CI=1 forbids the skip). Releases are prepared by
scripts/release.sh (fail-closed: clean tree + GATE_PASS + reproducible
bundle sha, then PRINTS the annotated-tag command; never tags/pushes).
CI is unverifiable offline (CI_UNVERIFIED_UNTIL_PUSH).
Impl: [web/privacy.html:L1-L91](web/privacy.html)
Impl: [.github/workflows/ci.yml:L1-L36](.github/workflows/ci.yml)
Impl: [tests_e2e/test_web_e2e.py:L1-L119](tests_e2e/test_web_e2e.py)
Impl: [scripts/release.sh:L1-L64](scripts/release.sh)

## L6 Oracle & tests
`oracle/golden/*.yaml`: frozen SME scenarios, each with expected
verdicts AND its own public-source citation (auditability for
future legal review). Property tests = invariants below. Golden
set is frozen BEFORE rules are authored (anti-confirmation-bias
gate). v1: S01-S14 frozen via oracle/FREEZE.sha256 (ADR-009,
verified by check.sh); self-arming checker scripts/oracle_check.py
(ORACLE_PENDING until Gate-4 rules land), its ADR-008 test
enumeration in tests/test_oracle_check.py.
Impl: [scripts/oracle_check.py:L1-L302](scripts/oracle_check.py)

## Invariants (each becomes a property test)
- INV-1 fail-closed: no COMPLIANT verdict may depend on any
  UNKNOWN fact. Impl: [tests/test_inv1_fail_closed.py:L1-L89](tests/test_inv1_fail_closed.py)
- INV-2 statute gate: loader rejects rules without citation or
  validity dates. Impl: [tests/test_inv2_statute_gate.py:L1-L102](tests/test_inv2_statute_gate.py)
- INV-3 temporal: identical facts, different as_of_date across an
  applicability boundary => verdicts change accordingly.
  Impl: [tests/test_inv3_temporal.py:L1-L94](tests/test_inv3_temporal.py)
- INV-4 disclaimer: rendering without disclaimer raises.
  Impl: [tests/test_inv4_disclaimer.py:L1-L67](tests/test_inv4_disclaimer.py)
- INV-5 explanation: every verdict carries a non-empty dependency
  tree whose leaves cite corpus ids. Impl: [tests/test_inv5_explanation.py:L1-L110](tests/test_inv5_explanation.py)
