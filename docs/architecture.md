# Architecture (v1 triage slice)
Verdicts: COMPLIANT | NON_COMPLIANT | UNDETERMINED. Default:
UNDETERMINED (fail-closed, ADR-001/003). All sections carry an
`Impl:` line per ADR-005.

## L1 Corpus layer
`corpus/manifest.yaml`: each legal source = {id, instrument,
ELI/EUR-Lex ref, version_date, amending_acts[], sha256 of local
text}. Rules cite corpus ids, never raw URLs.
Impl: [corpus/manifest.yaml:L1-L141](corpus/manifest.yaml)

## L2 Rules layer
`rules/*.yaml`: rule = {id, legal_source{corpus_id, article,
paragraph}, applies_from, applies_until?, logic (typed predicate
tree over facts), verdict, rationale_key}. Loader REJECTS a rule
missing legal_source or applies_from (INV-2).
Impl: [engine/loader.py:L1-L262](engine/loader.py)

## L3 Facts schema
`schema/facts.yaml`: typed facts (bool/enum/date) with i18n keys
(it/en). The questionnaire is generated FROM this schema; no
free-text fact enters the engine (ADR-003).
Impl: [engine/facts.py:L1-L119](engine/facts.py)

## L4 Engine core
Pure function: (facts, as_of_date, corpus_version) -> verdicts +
explanation tree. Trivalent evaluation; UNKNOWN propagates
upward. No I/O, no clock reads inside the core (as_of_date is an
argument: testability + temporal queries).
Impl: [engine/core.py:L1-L194](engine/core.py)

## L5 Output paths
CLI first. Renderer contract: refuses to emit any user-facing
output lacking the NOT-LEGAL-ADVICE disclaimer block (INV-4).
Every verdict rendered with: citation, as_of stamp, corpus
version, explanation tree.
Impl: [engine/render.py:L1-L88](engine/render.py)

## L6 Oracle & tests
`oracle/golden/*.yaml`: frozen SME scenarios, each with expected
verdicts AND its own public-source citation (auditability for
future legal review). Property tests = invariants below. Golden
set is frozen BEFORE rules are authored (anti-confirmation-bias
gate).
Impl: TBD

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
