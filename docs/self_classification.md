# Self-classification of the engine under the AI Act

Closes CLAUDE.md non-negotiable #4. The engine classifies ITSELF as an AI
system: per Art. 3(1) (a machine-based system that infers outputs from
input) and Commission Guidelines C(2025) 5053 (logic- and knowledge-based
approaches are expressly included), a deterministic rule engine that infers
compliance verdicts is an AI system. Below is its own self-check, produced
by dogfooding the CLI on `examples/self_check.yaml` (as of 2026-07-15, IT);
genuinely-uncertain facts were left UNKNOWN (a fail-closed self-assessment,
not a clean bill).

```
=== NOT LEGAL ADVICE / NON COSTITUISCE CONSULENZA LEGALE ===
This is an automated, informational self-check. It is NOT legal
advice and creates no professional-client relationship. Verdicts
may be incomplete or wrong; obligations depend on circumstances
only a qualified professional can assess. UNDETERMINED means:
seek human/legal review.
============================================================

Stai interagendo con un sistema basato su IA: questa e un'autovalutazione automatica, NON una consulenza legale.

as_of: 2026-07-15
corpus_version: aia-omnibus-preOJ-9247-26

[NON DETERMINABILE] HR_ANNEX_III (aia-2024-1689-en Chapter III (Art. 6(2), Annex III)(6(2)))
  -> Per un uso ad alto rischio (Allegato III) vanno soddisfatti gli obblighi del Capo III entro la scadenza.
  - rule -> UNKNOWN (not yet applicable (applies_from 2027-12-02))
    - applicability -> UNKNOWN (not yet applicable (applies_from 2027-12-02))

[NON DETERMINABILE] ART50_1 (aia-2024-1689-en Art. 50(1)(1))
  -> Un sistema che interagisce con le persone deve dichiarare di essere un'IA (Art. 50(1)).
  - rule -> UNKNOWN (not yet applicable (applies_from 2026-08-02))
    - applicability -> UNKNOWN (not yet applicable (applies_from 2026-08-02))

[NON DETERMINABILE] ART50_2 (aia-2024-1689-en Art. 50(2)(2))
  -> I contenuti generati dall'IA vanno marcati come artificiali in formato leggibile dalla macchina (Art. 50(2)).
  - rule -> UNKNOWN (not yet applicable (applies_from 2026-08-02))
    - applicability -> UNKNOWN (not yet applicable (applies_from 2026-08-02))

[NON DETERMINABILE] ART50_4 (aia-2024-1689-en Art. 50(4)(4))
  -> I deepfake vanno dichiarati come contenuti generati o manipolati artificialmente (Art. 50(4)).
  - rule -> UNKNOWN (not yet applicable (applies_from 2026-08-02))
    - applicability -> UNKNOWN (not yet applicable (applies_from 2026-08-02))

[CONFORME] ART5_SOCIAL_SCORING (aia-2024-1689-en Art. 5(1)(c)(1))
  -> Il punteggio sociale delle persone e una pratica vietata (Art. 5(1)(c)).
  - rule -> FALSE
    - fact practice_social_scoring -> FALSE [aia-2024-1689-en Art. 5(1)(c)]

[CONFORME] ART5_EMOTION_WORKPLACE (aia-2024-1689-en Art. 5(1)(f)(1))
  -> Dedurre le emozioni sul lavoro o a scuola e vietato, salvo motivi medici o di sicurezza (Art. 5(1)(f)).
  - rule -> FALSE
    - all -> FALSE
      - fact emotion_recognition_workplace -> FALSE [aia-2024-1689-en Art. 5(1)(f)]
      - fact emotion_medical_safety_exception -> TRUE [aia-2024-1689-en Art. 5(1)(f)]

[NON DETERMINABILE] ART5_NCII (omnibus-st-9247-26-en Art. 5(1)(ba) as amended (Omnibus)(1))
  -> Generare immagini intime non consensuali (per scopo, o per capacita senza salvaguardie) e vietato (Art. 5, Omnibus).
  - rule -> UNKNOWN (not yet applicable (applies_from 2026-12-02))
    - applicability -> UNKNOWN (not yet applicable (applies_from 2026-12-02))


PROSSIME SCADENZE:
  - HR_ANNEX_III: 2027-12-02 [aia-2024-1689-en Chapter III (Art. 6(2), Annex III)]
  - ART50_1: 2026-08-02 [aia-2024-1689-en Art. 50(1)]
  - ART50_2: 2026-08-02 [aia-2024-1689-en Art. 50(2)]
  - ART50_4: 2026-08-02 [aia-2024-1689-en Art. 50(4)]
  - ART5_NCII: 2026-12-02 [omnibus-st-9247-26-en Art. 5(1)(ba) as amended (Omnibus)]

```

## AI-based interaction disclosure (ADR-012(6))

The CLI declares to every user that they are interacting with an AI-based
system (the "Stai interagendo con un sistema basato su IA ..." line above,
and its EN counterpart) - the engine's own Art. 50(1)-style transparency.
As of 2026-07-15 its Art. 50 duties are not yet applicable (they begin
2026-08-02; see the deadlines in the report); the genuinely-uncertain
Art. 50(2) question - is a deterministic compliance report "synthetic
content"? - is recorded UNKNOWN and will surface once that duty is active.
