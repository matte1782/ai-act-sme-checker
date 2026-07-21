# Gate 7 pre-mortem (ADR-011a)

It is 3 months out and the release shipped a defect. Why?
1. The CI yaml parsed locally but failed on GitHub - a wrong action version, a missing `playwright install --with-deps`, or serve_web.py not backgrounded - so the "regression gate" was red from the first push and got ignored.
2. The e2e was flaky in CI: Pyodide's ~5s load raced a short fixed timeout, giving intermittent red, so people learned to re-run until green - the gate stopped meaning anything.
3. The README overclaimed ("garantisce la conformita"): legally dangerous and false - the tool is a fail-closed triage, not a compliance guarantee - and no test backed the sentence.
4. The privacy note drifted from the real CSP (claimed no unsafe-eval while the meta tag has it); a security-savvy user caught the contradiction and distrusted the whole zero-exfiltration promise.
5. The mobile layout pushed the NOT-LEGAL-ADVICE disclaimer below the fold or behind a horizontal scroll, so an SME on a phone never saw it.
6. The release tag's BUNDLE.sha256 diverged from the deployed site's (rebuilt with different line endings), so the "auditable artifact" claim failed the first time someone checked.
