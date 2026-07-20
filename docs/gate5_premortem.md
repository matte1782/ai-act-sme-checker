# Gate 5 pre-mortem (ADR-011a)

It is 3 months out and the CLI shipped a defect. Why?
1. Interactive EOF/interrupt mid-questionnaire printed a PARTIAL report; an SME read a half-answered self-check as complete instead of exit-2 fail-closed.
2. A missing i18n key fell back silently to English (or blank); an Italian SME got mixed-language, untrustworthy output instead of a load-time error (ADR-012(4)).
3. The deadline line showed the wrong X3 branch (legacy 2026-12-02 vs new 2026-08-02) because it was parsed from a reason string instead of C1's resolved field.
4. A Windows cp1252 console mangled the accented Italian text (UnicodeEncodeError or garbling) because stdout was not reconfigured to UTF-8.
5. Verdict semantics leaked into the exit code, so a CI pipeline treated NON_COMPLIANT as a failing gate - the NOT-LEGAL-ADVICE misuse ADR-012(5) forbids.
6. A second print path emitted verdict text without the disclaimer block, bypassing INV-4.
