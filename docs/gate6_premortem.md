# Gate 6 pre-mortem (ADR-011a)

It is 3 months out and the web app shipped a defect. Why?
1. The disclaimer scrolled off-screen or was dropped from the printed page; an SME shared a verdict with no NOT-LEGAL-ADVICE block and it read as authoritative.
2. XSS: an answer string (or citation) reached the DOM via innerHTML and executed / broke layout, because dynamic text was not forced through textContent.
3. A stale cached Pyodide bundle survived a corpus refresh; the UI showed old law under a new VERSION label, and the user acted on superseded rules.
4. A WASM-blocked or old browser rendered a blank page instead of an explicit fail-closed message, so the user assumed "no issues found".
5. The preOJ corpus was presented as final law; the user treated the provisional Council text (9247/26) as the published Gazzetta Ufficiale.
6. A shareable URL encoded answers/verdicts, leaking sensitive answers by link and breaking the CSP zero-exfiltration promise.
