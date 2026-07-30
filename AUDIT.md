<!-- SPDX-License-Identifier: EUPL-1.2 -->
<!-- SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors -->

# Verify this tool yourself · Verifica indipendente

🇮🇹 *Versione italiana: [AUDIT.it.md](AUDIT.it.md)*

This project asks you to trust nothing. Every public claim below can be
checked by you, from scratch, with commands that are known to work. Five
independent auditors (a lawyer, a security auditor, a DPO, an institutional
re-hoster and a sceptical engineer) ran this exercise cold: it took them
32–85 minutes because this page did not exist. With it, most checks take
minutes. Where they found something that does **not** hold, it is written
down in [What this does not prove](#5-what-this-does-not-prove).

Live tool: <https://matte1782.github.io/ai-act-sme-checker/> ·
Repo: <https://github.com/matte1782/ai-act-sme-checker>

---

## 1. Sixty seconds, in your browser (no clone, no tools)

**Anyone.** Open the tool, press F12 → **Network** tab, then complete the
questionnaire.

* No request appears while you answer, and none after the page finished
  loading. Everything is computed on your device.
* On the results page every verdict shows the article it rests on, and
  "PROSSIME SCADENZE" shows the date each obligation starts applying.
* Answer "Non so" to anything: the verdict becomes **NON DETERMINABILE**,
  never a guessed "conforme".

⚠️ Do not test the network claim with `navigator.sendBeacon()` in the
console: it returns `true` even when the browser blocks the request. Read the
**Console** tab instead — a blocked attempt logs a CSP violation.

## 2. Prove the live site is the source you audited

**Auditors, DPOs, institutional IT.** Needs `git`, `bash`, `curl`, `sha256sum`.

```sh
git clone https://github.com/matte1782/ai-act-sme-checker.git
cd ai-act-sme-checker

# (a) rebuild the engine bundle from source and compare with the live site.
#     This is the check that matters: a checksum file shipped next to a zip
#     proves nothing against tampering - rebuilding does.
bash scripts/build_web.sh /tmp/verify
sha256sum /tmp/verify/engine_bundle.zip
curl -s https://matte1782.github.io/ai-act-sme-checker/assets/engine_bundle.zip | sha256sum
# the two hashes must be identical, and equal to web/assets/BUNDLE.sha256

# (b) the vendored Python runtime is unmodified upstream Pyodide 0.26.4
cd web/vendor/pyodide && sha256sum -c VENDOR.sha256 && cd ../../..
```

The bundle is byte-reproducible on Windows, macOS and Linux (line endings are
normalised at build time). `web/assets/VERSION` records
`built_from_git_sha`, which is HEAD **at build time** — i.e. the parent of the
commit that ships the bundle. The artifact's real identity is its
`bundle_sha256`.

## 3. Check the law: rule → article → date

**Lawyers and compliance officers. No code reading required.**

Each rule is a small YAML file naming its own legal basis:

```sh
cat rules/art50_transparency.yaml   # Art. 50 transparency
cat rules/art5_prohibited.yaml      # Art. 5 prohibitions (incl. the new NCII/CSAM one)
cat rules/annex_iii.yaml            # Annex III high-risk (deadline only - see §5)
cat corpus/timeline.yaml            # every applicability date + the source it came from
```

Every date in `corpus/timeline.yaml` is quoted from the published act,
Regulation (EU) 2026/1744 (OJ L, 24.7.2026), a copy of which is in
`corpus/raw/oj_32026R1744_en.pdf` with its sha256 recorded in
`corpus/manifest.yaml`. The operative passages are the amended Article 113,
third paragraph, points (a), (c) and (d), and the new Article 111(4).

Reproduce any verdict offline, without the browser:

```sh
python -m engine.cli --answers examples/self_check.yaml --as-of 2026-08-02 --lang en
```

Write your own client's facts into a YAML file (same shape) and re-run it with
any `--as-of` date to see when an obligation starts to bite.

> EUR-Lex blocks scripted downloads (it answers `HTTP 202` with an empty body
> to `curl`), so authenticate the PDF by opening the CELEX page in a **browser**:
> <https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32026R1744>

## 4. The frozen oracle: run it, then read what it proves

**Sceptical reviewers.**

```sh
cd oracle && sha256sum -c FREEZE.sha256 && cd ..   # must be run from oracle/
python scripts/oracle_check.py                     # -> ORACLE_GREEN n=14
bash scripts/check.sh                              # full gate: tests + oracle + bundle
```

`oracle/golden/S01–S14` are 14 legal scenarios with their expected outcome.
They were committed (and hash-frozen) **before** the rules existed, and have
never been edited since — one commit in the repository's whole history touches
that directory:

```sh
git log --diff-filter=A --format='%h %ad %s' --date=iso -- oracle/golden
git log --format='%h %ad %s' --date=iso -- rules/ | tail -1
git log --oneline -- oracle/golden          # exactly one commit, ever
```

What this proves and what it does not is in §5.

## 5. What this does not prove

Read this before quoting the tool to a client or a board.

1. **"Frozen before the rules" is weaker than it sounds.** The freeze
   provably stops the *scenarios* being edited to fit the rules. It does not
   stop the *rules* being written to fit the scenarios — the author saw them
   while writing. `docs/decisions.md` (ADR-011) states this openly and lists
   the counter-measures (statute-first authoring, opposite-comments,
   timeline-anchored dates). Commit timestamps are author-controlled: GitHub's
   server-side record begins only at the first push (2026-07-22).
2. **No external legal review has taken place.** Nobody outside the project
   has validated that the rules correctly encode the law. That is the single
   thing most needed — see below.
3. **Chapter III (high-risk) is not substantively assessed.** The tool tells
   you the deadline and asks whether the obligations are met; it does not check
   them. The Italian national law L. 132/2025 is out of scope entirely.
4. **`operator_role` (provider/deployer) is collected but no rule branches on
   it yet**, so provider- and deployer-specific duties are not distinguished.
5. **CSP protects the data path, not navigation.** It blocks fetch, XHR,
   WebSocket and beacon — what carries data out. No CSP can stop a top-level
   navigation, and on GitHub Pages the policy is `<meta>`-only, so header-only
   directives (`frame-ancestors`, `report-to`) do not apply.
6. **The site is hosted.** GitHub Pages (via Fastly) logs visitor IPs like any
   host; those logs belong to GitHub. Your questionnaire answers are not in
   them. See `web/privacy.html`.
7. **Verification here is English-only** for the OJ text, and the timeline rows
   that drive no rule (Art. 4 literacy, GPAI Art. 51–55, Art. 57 sandboxes)
   were checked less closely than the ones that do.

## 6. Re-host it yourself (institutions)

**EUPL-1.2 permits re-hosting and adaptation, verbatim or modified.**

```sh
git clone https://github.com/matte1782/ai-act-sme-checker.git
cd ai-act-sme-checker
python scripts/serve_web.py 8000      # then open http://127.0.0.1:8000
```

Copy `web/` to any static host, with **one hard requirement**: the host must
serve `.mjs` as `text/javascript` and `.wasm` as `application/wasm`. If it does
not — or if you open the files via `file://` — the page stops at "Caricamento
del motore…" with no error message. `scripts/serve_web.py` sets these
correctly and works from a sub-path as well as a domain root.

Keep `LICENCE` alongside the copy, and after deploying compare your site's
`assets/BUNDLE.sha256` with the value you rebuilt in §2.

## Found something wrong?

That is the point of this page. Open an issue:
<https://github.com/matte1782/ai-act-sme-checker/issues> — findings about the
legal rules are more valuable than findings about the code.
