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
Impl: [engine/loader.py:L1-L340](engine/loader.py)

## L3 Facts schema
`schema/facts.yaml`: typed facts (bool/enum/date) with i18n keys
(it/en). Gate-4: canonical vocabulary = the union of fact names
used by the frozen golden set (ADR-009), Italian first-class. The
questionnaire is generated FROM this schema; no free-text fact
enters the engine (ADR-003). The synthetic schema moved to
tests/fixtures/facts_synthetic.yaml.
Impl: [engine/facts.py:L1-L119](engine/facts.py)

## L4 Engine core
Pure function: (facts, as_of_date, corpus_version) -> verdicts +
explanation tree. Trivalent evaluation; UNKNOWN propagates
upward. No I/O, no clock reads inside the core (as_of_date is an
argument: testability + temporal queries). Gate-4 precedence (X4)
per rule: (1) temporal window (X3 branch-date selection, fail
closed on an unknown 'when') -> INACTIVE; (2) applicable_if ->
NOT_APPLICABLE (FALSE, op=='scope' citation leaf) or UNDETERMINED
(UNKNOWN, named); (3) logic. NOT_APPLICABLE never rests on an
unknown scope fact (X5).
Impl: [engine/core.py:L1-L282](engine/core.py)

## L5 Output paths
CLI first. Renderer contract: refuses to emit any user-facing
output lacking the NOT-LEGAL-ADVICE disclaimer block (INV-4).
Every verdict rendered with: citation, as_of stamp, corpus
version, explanation tree. Gate-4: a NOT_APPLICABLE verdict and
its op=='scope' leaf render with the leaf's citation (X1).
Impl: [engine/render.py:L1-L102](engine/render.py)

## L6 Oracle & tests
`oracle/golden/*.yaml`: frozen SME scenarios, each with expected
verdicts AND its own public-source citation (auditability for
future legal review). Property tests = invariants below. Golden
set is frozen BEFORE rules are authored (anti-confirmation-bias
gate). v1: S01-S14 frozen via oracle/FREEZE.sha256 (ADR-009,
verified by check.sh); self-arming checker scripts/oracle_check.py
(ORACLE_PENDING until Gate-4 rules land), its ADR-008 test
enumeration in tests/test_oracle_check.py.
Impl: [scripts/oracle_check.py:L1-L300](scripts/oracle_check.py)

## Invariants (each becomes a property test)
- INV-1 fail-closed: no COMPLIANT verdict may depend on any
  UNKNOWN fact. Impl: [tests/test_inv1_fail_closed.py:L1-L87](tests/test_inv1_fail_closed.py)
- INV-2 statute gate: loader rejects rules without citation or
  validity dates. Impl: [tests/test_inv2_statute_gate.py:L1-L100](tests/test_inv2_statute_gate.py)
- INV-3 temporal: identical facts, different as_of_date across an
  applicability boundary => verdicts change accordingly.
  Impl: [tests/test_inv3_temporal.py:L1-L92](tests/test_inv3_temporal.py)
- INV-4 disclaimer: rendering without disclaimer raises.
  Impl: [tests/test_inv4_disclaimer.py:L1-L65](tests/test_inv4_disclaimer.py)
- INV-5 explanation: every verdict carries a non-empty dependency
  tree whose leaves cite corpus ids. Impl: [tests/test_inv5_explanation.py:L1-L108](tests/test_inv5_explanation.py)
