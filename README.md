# Auto-verifica AI Act per PMI · AI Act self-check for SMEs

<!-- CI badge placeholder: sostituisci OWNER/REPO dopo il push -->
![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)

Strumento gratuito e open source (EUPL-1.2) di **auto-verifica** dell'AI
Act per piccole e medie imprese. Gira interamente nel browser: **le risposte
non lasciano mai il tuo dispositivo**. · Free and open-source (EUPL-1.2) AI
Act **self-check** for SMEs. It runs entirely in your browser: **your answers
never leave your device.**

> ⚠️ **NON è una consulenza legale / This is NOT legal advice.** È
> un'autovalutazione automatica e informativa. I verdetti possono essere
> incompleti o errati; rivolgiti a un professionista qualificato.

---

## Cosa fa · What it does

- Triage di conformità AI Act per PMI: rispondi a 19 domande, ottieni verdetti
  con la **citazione dell'articolo** e le **scadenze personalizzate**.
- **Fail-closed**: quando le informazioni non bastano, la risposta è
  *"non determinabile — serve revisione umana/legale"*, mai un falso "conforme".
  Cento onesti *non determinabile* valgono più di un falso *conforme*.
- Tre stati oltre a conforme/non conforme: *non determinabile* (mancano dati),
  *non applicabile* (fuori ambito, Art. 2), *inattivo* (obbligo non ancora in
  vigore — con la data di decorrenza).
- *English:* an AI Act triage self-check: 19 questions → verdicts with the
  **exact article citation** and **personalized deadlines**; fail-closed by
  design ("undetermined" is an honest answer, never a false "compliant").

## Cosa NON fa · What it does NOT do

- **NON è consulenza legale** (il disclaimer è riprodotto su ogni output).
- **Non copre ancora tutti gli obblighi high-risk** del Capo III: v1 è un
  triage (vedi `docs/decisions.md`, ADR-002); l'uso Allegato III è trattato in
  modo *verdict-safe* (non deriva mai un "non conforme" dal solo caso d'uso).
- I risultati si basano sul **corpus indicato in pagina**, che resta in stato
  **PROVISIONAL** finché il Digital Omnibus non è pubblicato in Gazzetta
  Ufficiale (l'app mostra un avviso finché è così).
- *English:* not legal advice; not full high-risk coverage yet (v1 triage);
  results depend on the corpus shown in-page (PROVISIONAL until the OJ text).

## Privacy

- **Le risposte non lasciano MAI il dispositivo.** Nessun server, nessun
  cookie, nessun analytics, nessun beacon.
- Garanzia **tecnica**, non solo dichiarata: la pagina impone una Content
  Security Policy con `connect-src 'self'` (nessuna connessione esterna
  possibile). Vedi la [nota di trasparenza](web/privacy.html).
- **Come verificarlo da solo:** apri gli strumenti sviluppatore del browser →
  scheda *Network* → completa il questionario: non parte alcuna richiesta verso
  origini esterne. In CI questo è verificato da un test e2e ad ogni push.
- *English:* your answers never leave the device — enforced by CSP
  `connect-src 'self'`, verified by an e2e network test in CI. Check it
  yourself in the browser's Network tab.

## Per le istituzioni · Re-hosting

Chiunque può ri-ospitare l'app verbatim (la EUPL-1.2 lo permette, incluso
l'adattamento). Non serve alcuna infrastruttura: nessun CDN, nessun server,
nessun trattamento di dati.

1. Copia la cartella `web/` su qualunque hosting statico (es. GitHub Pages).
2. Verifica l'integrità degli artefatti (vedi sotto).
3. La `BUNDLE.sha256` del sito pubblicato deve coincidere con quella del rilascio taggato.

## Verifica del bundle · Bundle verification

```sh
# runtime Pyodide vendorizzato (nessun CDN a runtime)
cd web/vendor/pyodide && sha256sum -c VENDOR.sha256
# motore + regole + schema + i18n + corpus (bundle deterministico e congelato)
cd web/assets && sha256sum -c BUNDLE.sha256
```

## Sviluppo · Development

- Gate deterministico completo: `bash scripts/check.sh` → `GATE_PASS`
  (test + trace + oracle + integrità del bundle web).
- **Oracle**: 14 scenari congelati (`oracle/golden/S01-S14`) sono l'arbitro
  anti-bias; le regole si scrivono per soddisfarli, mai il contrario (ADR-009).
- **Catena ADR**: le decisioni vivono in `docs/decisions.md` (append-only).
- **CI**: `.github/workflows/ci.yml` esegue `check.sh` + l'e2e Playwright
  (asserzione di rete + viewport mobile) ad ogni push/PR.
- Servire in locale: `python scripts/serve_web.py` → http://127.0.0.1:8000

## Licenza · Licence

**EUPL-1.2** (European Union Public Licence). Testo ufficiale in `LICENCE`
(valida in italiano e in tutte le lingue UE, vedi `LICENCE.NOTE`). Ogni file
sorgente porta l'header `SPDX-License-Identifier: EUPL-1.2`. Le dipendenze
vendorizzate mantengono la propria licenza (Pyodide MPL-2.0, PyYAML MIT).
