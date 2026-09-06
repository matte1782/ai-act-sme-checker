# Self-classification of the engine under the AI Act

Closes CLAUDE.md non-negotiable #4. The engine classifies ITSELF as an AI
system: per Art. 3(1) (a machine-based system that infers outputs from
input) and Commission Guidelines C(2025) 5053 (logic- and knowledge-based
approaches are expressly included), a deterministic rule engine that infers
compliance verdicts is an AI system. Below is its own self-check, produced
by dogfooding the CLI on `examples/self_check.yaml` (as of 2026-09-07, IT; corpus FINAL, first run 2026-07-15 pre-OJ);
genuinely-uncertain facts were left UNKNOWN (a fail-closed self-assessment,
not a clean bill).

```
=== NON COSTITUISCE CONSULENZA LEGALE / NOT LEGAL ADVICE ===
Questa è un'autovalutazione automatica e informativa. NON è
una consulenza legale e non crea alcun rapporto professionale.
I verdetti possono essere incompleti o errati; gli obblighi
dipendono da circostanze che solo un professionista
qualificato può valutare. NON DETERMINABILE significa: è
necessaria una revisione umana/legale.

This is an automated, informational self-check. It is NOT legal
advice and creates no professional-client relationship. Verdicts
may be incomplete or wrong; obligations depend on circumstances
only a qualified professional can assess. UNDETERMINED means:
seek human/legal review.
============================================================

Stai interagendo con un sistema basato su IA: questa è un'autovalutazione automatica, NON una consulenza legale.

as_of: 2026-09-07
corpus_version: aia-omnibus-oj-2026-1744

[NON DETERMINABILE] HR_ANNEX_III (aia-2024-1689-en Chapter III (Art. 6(2), Annex III))
  -> Per un uso ad alto rischio (allegato III) vanno soddisfatti gli obblighi del capo III entro la scadenza.
  - rule -> UNKNOWN (not yet applicable (applies_from 2027-12-02))
    - applicability -> UNKNOWN (not yet applicable (applies_from 2027-12-02))

[CONFORME] ART50_1 (aia-2024-1689-en Art. 50(1))
  -> Un sistema che interagisce con le persone deve dichiarare di essere un'IA (Art. 50(1)).
  - rule -> FALSE
    - all -> FALSE
      - interacts_with_persons = True -> TRUE [aia-2024-1689-en Art. 50(1)]
      - interaction_disclosed = False -> FALSE [aia-2024-1689-en Art. 50(1)]

[NON DETERMINABILE] ART50_2 (aia-2024-1689-en Art. 50(2))
  -> I contenuti generati dall'IA vanno marcati come artificiali in formato leggibile meccanicamente (Art. 50(2)).
  unknown facts: content_marked_machine_readable, generates_synthetic_content
  - rule -> UNKNOWN (unknown facts: content_marked_machine_readable, generates_synthetic_content)
    - all -> UNKNOWN
      - generates_synthetic_content = True -> UNKNOWN [aia-2024-1689-en Art. 50(2)]
      - content_marked_machine_readable = False -> UNKNOWN [aia-2024-1689-en Art. 50(2)]

[CONFORME] ART50_4 (aia-2024-1689-en Art. 50(4))
  -> I deep fake vanno dichiarati come contenuti generati o manipolati artificialmente (Art. 50(4)).
  - rule -> FALSE
    - all -> FALSE
      - deepfake_published = True -> FALSE [aia-2024-1689-en Art. 50(4)]
      - deepfake_disclosed = False -> TRUE [aia-2024-1689-en Art. 50(4)]

[CONFORME] ART5_SOCIAL_SCORING (aia-2024-1689-en Art. 5(1)(c))
  -> Il punteggio sociale delle persone è una pratica vietata (Art. 5(1)(c)).
  - rule -> FALSE
    - practice_social_scoring = True -> FALSE [aia-2024-1689-en Art. 5(1)(c)]

[CONFORME] ART5_EMOTION_WORKPLACE (aia-2024-1689-en Art. 5(1)(f))
  -> Inferire le emozioni sul lavoro o a scuola è vietato, salvo motivi medici o di sicurezza (Art. 5(1)(f)).
  - rule -> FALSE
    - all -> FALSE
      - emotion_recognition_workplace = True -> FALSE [aia-2024-1689-en Art. 5(1)(f)]
      - emotion_medical_safety_exception = False -> TRUE [aia-2024-1689-en Art. 5(1)(f)]

[NON DETERMINABILE] ART5_NCII (oj-2026-1744-en Art. 5(1)(ba) as amended (Reg. (EU) 2026/1744))
  -> Generare o manipolare materiale intimo non consensuale (immagini, video o audio) è vietato, sia quando è lo scopo del sistema sia quando il sistema ne ha la capacità senza adeguate salvaguardie (Art. 5(1)(ba), Omnibus).
  - rule -> UNKNOWN (not yet applicable (applies_from 2026-12-02))
    - applicability -> UNKNOWN (not yet applicable (applies_from 2026-12-02))


PROSSIME SCADENZE:
  - HR_ANNEX_III: 2027-12-02 [aia-2024-1689-en Chapter III (Art. 6(2), Annex III)]
  - ART5_NCII: 2026-12-02 [oj-2026-1744-en Art. 5(1)(ba) as amended (Reg. (EU) 2026/1744)]
```

## AI-based interaction disclosure (ADR-012(6))

The CLI declares to every user that they are interacting with an AI-based
system (the "Stai interagendo con un sistema basato su IA ..." line above,
and its EN counterpart) - the engine's own Art. 50(1)-style transparency.
As of 2026-09-07 its Art. 50 duties apply (since 2026-08-02): ART50_1 is
CONFORME because the disclosure is structural on every output path. The
genuinely-uncertain Art. 50(2) question - is a deterministic compliance
report "synthetic content"? - is still recorded UNKNOWN, so ART50_2 is
NON DETERMINABILE by design; the Commission Guidelines C(2026) 5054
(section 4, Art. 50(2) scope and exceptions) are the reference for
resolving it - an owner decision, not a silent default.
