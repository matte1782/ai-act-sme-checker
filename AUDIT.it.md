<!-- SPDX-License-Identifier: EUPL-1.2 -->
<!-- SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors -->

# Verifica indipendente · Come controllare questo strumento

🇬🇧 *English version: [AUDIT.md](AUDIT.md)*

Questo progetto non ti chiede di fidarti. Ogni affermazione pubblica qui sotto
puoi controllarla tu, da zero, con comandi che funzionano davvero. Cinque
revisori indipendenti (un avvocato, un auditor di sicurezza, un DPO, un
tecnico che doveva ri-ospitarlo e un ingegnere scettico) hanno fatto questo
esercizio senza alcun contesto: ci hanno messo dai 32 agli 85 minuti, perché
questa pagina non esisteva. Con questa pagina, quasi tutti i controlli
richiedono minuti. Dove hanno trovato qualcosa che **non** regge, è scritto
in [Cosa questo non dimostra](#5-cosa-questo-non-dimostra).

Strumento: <https://matte1782.github.io/ai-act-sme-checker/> ·
Codice: <https://github.com/matte1782/ai-act-sme-checker>

---

## 1. Sessanta secondi, dal browser (niente clone, niente strumenti)

**Per chiunque.** Apri lo strumento, premi F12 e vai alla scheda **Rete**
(*Network*), poi completa il questionario.

* Mentre rispondi non parte alcuna richiesta, e nemmeno dopo il caricamento
  della pagina. Tutto viene calcolato sul tuo dispositivo.
* Nella pagina dei risultati ogni verdetto mostra l'articolo su cui si basa, e
  «PROSSIME SCADENZE» indica da quando ciascun obbligo si applica.
* Rispondi «Non so» a qualunque domanda: il verdetto diventa **NON
  DETERMINABILE**, mai un «conforme» indovinato.

⚠️ Non testare la promessa sulla rete con `navigator.sendBeacon()` dalla
console: restituisce `true` anche quando il browser blocca la richiesta.
Guarda invece la scheda **Console**: un tentativo bloccato registra una
violazione della CSP.

## 2. Dimostrare che il sito live è il codice che hai controllato

**Auditor, DPO, IT istituzionale.** Servono `git`, `bash`, `curl`, `sha256sum`.

```sh
git clone https://github.com/matte1782/ai-act-sme-checker.git
cd ai-act-sme-checker

# (a) ricostruisci il motore dai sorgenti e confrontalo con il sito live.
#     È il controllo che conta: un file di checksum spedito accanto allo zip
#     non prova nulla contro una manomissione. Ricostruire sì.
bash scripts/build_web.sh /tmp/verify
sha256sum /tmp/verify/engine_bundle.zip
curl -s https://matte1782.github.io/ai-act-sme-checker/assets/engine_bundle.zip | sha256sum
# i due hash devono essere identici, e uguali a web/assets/BUNDLE.sha256

# (b) il runtime Python vendorizzato è Pyodide 0.26.4 non modificato
cd web/vendor/pyodide && sha256sum -c VENDOR.sha256 && cd ../../..
```

Il pacchetto è riproducibile byte per byte su Windows, macOS e Linux (i fine
riga sono normalizzati in fase di build). `web/assets/VERSION` registra
`built_from_git_sha`, che è HEAD **al momento della build**, cioè il commit
precedente a quello che pubblica il pacchetto. L'identità vera dell'artefatto
è il suo `bundle_sha256`.

## 3. Controllare il diritto: regola → articolo → data

**Avvocati e professionisti della compliance. Non serve leggere codice.**

Ogni regola è un piccolo file YAML che dichiara la propria base legale:

```sh
cat rules/art50_transparency.yaml   # Art. 50, obblighi di trasparenza
cat rules/art5_prohibited.yaml      # Art. 5, pratiche vietate (incl. il nuovo divieto NCII/CSAM)
cat rules/annex_iii.yaml            # Allegato III, alto rischio (solo scadenza: vedi §5)
cat corpus/timeline.yaml            # tutte le date di applicabilità + la fonte di ciascuna
```

Ogni data in `corpus/timeline.yaml` è ripresa dall'atto pubblicato,
il Regolamento (UE) 2026/1744 (GU UE L, 24.7.2026), di cui una copia sta in
`corpus/raw/oj_32026R1744_en.pdf` con lo sha256 registrato in
`corpus/manifest.yaml`. Le disposizioni operative sono l'art. 113, terzo
comma, lettere (a), (c) e (d) come modificato, e il nuovo art. 111(4).

Puoi riprodurre qualunque verdetto **fuori dal browser**:

```sh
python -m engine.cli --answers examples/self_check.yaml --as-of 2026-08-02 --lang it
```

Scrivi i fatti di un tuo cliente in un file YAML con la stessa struttura e
rilancia il comando con qualsiasi data in `--as-of`, per vedere da quando un
obbligo inizia a mordere.

> EUR-Lex blocca gli scaricamenti automatici (risponde `HTTP 202` con corpo
> vuoto a `curl`), quindi autentica il PDF aprendo la pagina CELEX in un
> **browser**:
> <https://eur-lex.europa.eu/legal-content/IT/TXT/?uri=CELEX:32026R1744>

## 4. L'oracle congelato: eseguilo, poi leggi cosa dimostra

**Per i revisori scettici.**

```sh
cd oracle && sha256sum -c FREEZE.sha256 && cd ..   # va eseguito DA dentro oracle/
python scripts/oracle_check.py                     # -> ORACLE_GREEN n=14
bash scripts/check.sh                              # gate completo: test + oracle + integrità
```

`oracle/golden/S01–S14` sono 14 scenari giuridici con il verdetto atteso.
Sono stati committati (e congelati con hash) **prima** che le regole
esistessero, e non sono mai stati modificati: un solo commit in tutta la
storia del repository tocca quella cartella.

```sh
git log --diff-filter=A --format='%h %ad %s' --date=iso -- oracle/golden
git log --format='%h %ad %s' --date=iso -- rules/ | tail -1
git log --oneline -- oracle/golden          # esattamente un commit, in tutto
```

Cosa dimostri e cosa no è scritto nel §5.

## 5. Cosa questo NON dimostra

Da leggere prima di citare lo strumento a un cliente o a un consiglio.

1. **«Congelato prima delle regole» è più debole di come suona.** Il freeze
   impedisce in modo verificabile che gli *scenari* siano stati piegati sulle
   regole. Non impedisce che le *regole* siano state scritte per far passare
   gli scenari: l'autore li aveva davanti mentre scriveva.
   `docs/decisions.md` (ADR-011) lo dichiara apertamente ed elenca le
   contromisure (scrivere la regola partendo dal testo dell'articolo,
   motivare per iscritto perché il verdetto opposto violerebbe la norma
   citata, ancorare ogni data a una tabella invece di riscriverla). Le date
   dei commit sono controllate dall'autore: la registrazione lato server
   inizia solo al primo push (22 luglio 2026). L'ordine è un indizio, non
   una prova.
2. **Nessuna revisione legale esterna.** Nessuno fuori dal progetto ha
   validato che le regole codifichino correttamente la norma. È la cosa che
   manca di più.
3. **Il Capo III (alto rischio) non è valutato nel merito.** Lo strumento
   indica la scadenza e chiede se gli obblighi sono stati soddisfatti; non
   li verifica. La legge italiana 132/2025 è del tutto fuori perimetro.
4. **`operator_role` (fornitore/deployer) viene raccolto ma nessuna regola
   ci si dirama ancora**, quindi gli obblighi specifici dei due ruoli non
   sono distinti.
5. **La CSP protegge il percorso dei dati, non la navigazione.** Blocca
   fetch, XHR, WebSocket e beacon, cioè ciò che porta i dati fuori. Nessuna
   CSP può fermare una navigazione di primo livello, e su GitHub Pages la
   policy viaggia solo nel tag `<meta>`: le direttive che funzionano solo
   come header HTTP (`frame-ancestors`, `report-to`) non hanno effetto.
6. **Il sito è ospitato.** GitHub Pages (tramite Fastly) registra gli IP dei
   visitatori come qualunque host, e quei log sono di GitHub. Le tue risposte
   al questionario non ci finiscono. Vedi `web/privacy.html`.
7. **La verifica del testo UE qui è fatta sulla versione inglese**, e le
   righe della timeline che non guidano alcuna regola (art. 4 alfabetizzazione,
   GPAI artt. 51-55, art. 57 sandbox) sono state controllate meno a fondo di
   quelle che le guidano.

## 6. Ri-ospitalo tu (istituzioni)

**La licenza EUPL-1.2 permette di ri-ospitare e adattare, verbatim o modificato.**

```sh
git clone https://github.com/matte1782/ai-act-sme-checker.git
cd ai-act-sme-checker
python scripts/serve_web.py 8000      # poi apri http://127.0.0.1:8000
```

Copia `web/` su qualunque hosting statico, con **un requisito obbligatorio**:
l'host deve servire `.mjs` come `text/javascript` e `.wasm` come
`application/wasm`. Se sbaglia i MIME (o se apri i file via `file://`) la
pagina resta ferma su «Caricamento del motore…» senza alcun messaggio
d'errore. `scripts/serve_web.py` imposta i MIME corretti e funziona sia da
sottocartella sia da radice del dominio.

Tieni il file `LICENCE` accanto alla copia e, dopo la pubblicazione,
confronta il `BUNDLE.sha256` del tuo sito con quello che hai ricostruito al §2.

## Hai trovato un errore?

È esattamente lo scopo di questa pagina. Apri una segnalazione:
<https://github.com/matte1782/ai-act-sme-checker/issues> — le osservazioni
sulle **regole giuridiche** valgono più di quelle sul codice.
