// SPDX-License-Identifier: EUPL-1.2
// SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
//
// Boot guard (ADR-013a). A CLASSIC (non-module) script, loaded before app.js,
// so it runs even when the module script cannot: .mjs served with a wrong MIME
// type, IIS 404 on unregistered extensions, a browser without ES modules. Two
// watchdogs, both fail-closed - the promise of ADR-013 is "an explicit message,
// never a blank page", and Pyodide swallows WebAssembly instantiation errors
// (console.warn, no rethrow), so without this the page sat at 10 % for ever.
// Text is hardcoded and bilingual: the i18n catalog lives inside the engine
// that failed to start. DOM via textContent only (E5).
(function () {
  "use strict";
  var MODULE_GRACE_MS = 15000;   // app.js sets the marker within milliseconds
  var STALL_MS = 120000;         // 2 min without progress while loading = dead
  var TICK_MS = 5000;

  function show(detail) {
    var box = document.getElementById("boot-error");
    var start = document.getElementById("boot-start");
    var status = document.getElementById("boot-status");
    if (!box || !box.hidden) return;          // app.js already reported
    if (start && !start.hidden) return;       // engine ready: nothing to do
    box.hidden = false;
    box.textContent =
      "Impossibile avviare lo strumento. Cause tipiche: browser senza " +
      "WebAssembly o senza moduli JavaScript, file serviti con tipo MIME " +
      "sbagliato (.mjs/.wasm), policy di sicurezza (CSP) del sito o " +
      "dell'azienda, connessione interrotta. Nessun risultato viene " +
      "mostrato (fail-closed).\n\n" +
      "The tool could not start. Typical causes: a browser without " +
      "WebAssembly or JavaScript modules, files served with a wrong MIME " +
      "type (.mjs/.wasm), a site or corporate security policy (CSP), a " +
      "broken connection. No result is shown (fail-closed).\n\n" +
      "[" + detail + "]";
    if (status) status.hidden = true;
    if (start) { start.hidden = true; start.disabled = true; }
  }

  // (1) the module never ran: app.js could not be loaded or parsed.
  window.setTimeout(function () {
    if (!window.__aiact_module_started) show("application script did not load within 15 s");
  }, MODULE_GRACE_MS);

  // (2) the module ran but the runtime never finished starting: the progress
  // bar has not moved for STALL_MS while Start is still hidden.
  var last = null, since = Date.now();
  window.setInterval(function () {
    var bar = document.getElementById("boot-bar");
    var start = document.getElementById("boot-start");
    if (!bar || (start && !start.hidden)) return;
    var w = bar.style.width;
    if (w !== last) { last = w; since = Date.now(); return; }
    if (Date.now() - since > STALL_MS) show("no progress for 120 s at " + (w || "0%"));
  }, TICK_MS);
})();
