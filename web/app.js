// SPDX-License-Identifier: EUPL-1.2
// SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
//
// ADR-013 web controller. Loads the SAME engine via Pyodide, generates the
// wizard from schema/facts.yaml through the bridge (never duplicated here),
// and renders ALL verdict content from render_structured. No rule/verdict
// logic lives in JS. DOM is built with textContent only (E5, never innerHTML).
import { loadPyodide } from "./vendor/pyodide/pyodide.mjs";

const $ = (id) => document.getElementById(id);
const REPO = "https://github.com/"; // placeholder; institutions re-host verbatim

// --- DOM-safe element builder (E5) ---------------------------------------
function el(tag, opts = {}, children = []) {
  const node = document.createElement(tag);
  if (opts.text !== undefined) node.textContent = opts.text; // never innerHTML
  if (opts.cls) node.className = opts.cls;
  if (opts.attrs) for (const [k, v] of Object.entries(opts.attrs)) node.setAttribute(k, v);
  if (opts.on) for (const [ev, fn] of Object.entries(opts.on)) node.addEventListener(ev, fn);
  for (const c of children) node.appendChild(c);
  return node;
}
function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }

// Fail-closed message: bilingual, hardcoded because it may show before the
// engine (and its i18n catalog) is available. Never a blank page (E1).
function failClosed(detail) {
  const box = $("boot-error");
  box.hidden = false;
  box.textContent =
    "Impossibile avviare lo strumento in questo browser. " +
    "Serve un browser moderno con WebAssembly abilitato. " +
    "Nessun risultato viene mostrato (fail-closed).\n\n" +
    "This tool could not start in this browser. A modern browser with " +
    "WebAssembly enabled is required. No result is shown (fail-closed).\n\n" +
    (detail ? "[" + detail + "]" : "");
  $("boot-status").hidden = true;
}

// --- application state ----------------------------------------------------
const state = { lang: "it", facts: [], answers: {}, index: 0, boot: null,
                webapi: null, version: null };

function ui(key) { return state.boot.i18n[state.lang].ui[key]; }
function statusLabel(s) { return state.boot.i18n[state.lang].status_labels[s]; }
function rationale(key) { return state.boot.i18n[state.lang].rationales[key] || ""; }

// --- boot -----------------------------------------------------------------
async function boot() {
  if (typeof WebAssembly !== "object") { failClosed("no WebAssembly"); return; }
  try {
    setProgress(10, "Avvio del runtime… / Starting the runtime…");
    const pyodide = await loadPyodide({ indexURL: "./vendor/pyodide/" });
    setProgress(40, "Caricamento delle librerie… / Loading libraries…");
    await pyodide.loadPackage("pyyaml");
    setProgress(60, "Preparazione del motore… / Preparing the engine…");
    const buf = await (await fetch("./assets/engine_bundle.zip")).arrayBuffer();
    pyodide.unpackArchive(buf, "zip", { extractDir: "/bundle" });
    pyodide.runPython("import sys, os; sys.path.insert(0, '/bundle'); os.chdir('/bundle')");
    setProgress(80, "Inizializzazione… / Initializing…");
    state.webapi = pyodide.pyimport("engine.webapi");
    state.boot = JSON.parse(state.webapi.boot_data());
    state.facts = state.boot.facts;
    try { state.version = await (await fetch("./assets/VERSION")).text(); } catch (e) { state.version = ""; }
    setProgress(100, "Pronto / Ready");
    $("boot").hidden = true;
    renderWizard();
  } catch (err) {
    failClosed(String(err && err.message ? err.message : err));
  }
}
function setProgress(pct, msg) { $("boot-bar").style.width = pct + "%"; $("boot-status").textContent = msg; }

// --- shared toolbar (lang toggle) ----------------------------------------
function toolbar(onLang) {
  const mk = (code, label) => el("button", {
    text: label, attrs: { "aria-pressed": String(state.lang === code) },
    on: { click: () => { if (state.lang !== code) { state.lang = code; onLang(); } } },
  });
  return el("div", { cls: "toolbar" }, [
    el("span", { text: state.lang === "it" ? "Lingua" : "Language", cls: "cite" }),
    el("div", { cls: "lang-toggle" }, [mk("it", "Italiano"), mk("en", "English")]),
  ]);
}

// --- E3 wizard ------------------------------------------------------------
function renderWizard() {
  const root = $("wizard"); root.hidden = false; $("results").hidden = true; clear(root);
  root.appendChild(toolbar(renderWizard));
  const fact = state.facts[state.index];
  const total = state.facts.length;
  root.appendChild(el("p", {
    text: ui("web_question") + " " + (state.index + 1) + " " + ui("web_of") + " " + total, cls: "cite",
  }));
  const prog = el("div", { cls: "progress" });
  const bar = el("div", { cls: "progress-bar" });
  bar.style.width = `${((state.index + 1) / total) * 100}%`;   // CSSOM, not a style attr (CSP)
  prog.appendChild(bar);
  root.appendChild(prog);
  root.appendChild(el("p", { text: fact.prompt[state.lang], cls: "q-prompt" }));

  const answers = el("div", { cls: "answers" });
  const choose = (value) => { state.answers[fact.name] = value; advance(); };
  const cur = state.answers[fact.name];
  const sel = (on) => (on ? " selected" : "");
  if (fact.type === "bool") {
    answers.appendChild(el("button", { text: ui("web_yes"), cls: "ans" + sel(cur === true), on: { click: () => choose(true) } }));
    answers.appendChild(el("button", { text: ui("web_no"), cls: "ans" + sel(cur === false), on: { click: () => choose(false) } }));
    answers.appendChild(el("button", { text: ui("web_unknown"), cls: "unknown" + sel(cur === null), on: { click: () => choose(null) } }));
  } else if (fact.type === "enum") {
    for (const v of fact.values) {
      answers.appendChild(el("button", { text: v, cls: "ans" + sel(cur === v), on: { click: () => choose(v) } }));
    }
    answers.appendChild(el("button", { text: ui("web_unknown"), cls: "unknown" + sel(cur === null), on: { click: () => choose(null) } }));
  } else {
    const input = el("input", { attrs: { type: "text", placeholder: "YYYY-MM-DD", value: (cur == null ? "" : cur) } });
    answers.appendChild(input);
    answers.appendChild(el("button", { text: "OK", on: { click: () => choose(input.value.trim() || null) } }));
    answers.appendChild(el("button", { text: ui("web_unknown"), cls: "unknown", on: { click: () => choose(null) } }));
  }
  root.appendChild(answers);

  const nav = el("div", { cls: "nav" });
  nav.appendChild(el("button", { text: ui("web_back"), attrs: state.index === 0 ? { disabled: "" } : {}, on: { click: back } }));
  root.appendChild(nav);
}
function advance() {
  if (state.index < state.facts.length - 1) { state.index++; renderWizard(); }
  else { renderResults(); }
}
function back() { if (state.index > 0) { state.index--; renderWizard(); } }

// --- E4 results -----------------------------------------------------------
function renderResults() {
  let out;
  try {
    const asOf = localISODate();
    out = JSON.parse(state.webapi.evaluate_answers(JSON.stringify(state.answers), asOf, state.lang));
  } catch (err) { failClosed(String(err)); $("wizard").hidden = true; $("boot").hidden = false; return; }
  const s = out.structured;
  const root = $("results"); root.hidden = false; $("wizard").hidden = true; clear(root);
  root.appendChild(toolbar(renderResults));

  // (1) disclaimer ALWAYS visible at top, not collapsible. Shown in the
  // selected language (bilingual header + that language's body): a display
  // SELECTION of the structural INV-4 block, never a rewrite - the full
  // canonical block stays in the payload and in the print view (#print-meta),
  // and any parsing surprise falls back to the full block (fail-safe).
  root.appendChild(el("pre", { text: localizedDisclaimer(s.disclaimer, state.lang), cls: "disclaimer" }));

  // (4) provisional-corpus notice
  if (s.corpus_status === "PROVISIONAL") {
    root.appendChild(el("div", { text: "⚠ " + ui("provisional_notice"), cls: "provisional" }));
  }

  // (2) Prossime scadenze FIRST
  root.appendChild(el("h2", { text: ui("deadlines_header") }));
  if (s.deadlines.length === 0) {
    root.appendChild(el("p", { text: ui("deadlines_none"), cls: "cite" }));
  } else {
    const ul = el("ul", { cls: "deadlines" });
    for (const d of s.deadlines) {
      ul.appendChild(el("li", { text: `${d.rule_id}: ${d.applies_from} [${d.citation.corpus_id} ${d.citation.article}]` }));
    }
    root.appendChild(ul);
  }

  // (3) verdict cards
  root.appendChild(el("h2", { text: ui("web_results_title") }));
  for (const v of s.verdicts) {
    const card = el("div", { cls: "card" });
    const head = el("div", { cls: "card-head" }, [
      el("span", { text: statusLabel(v.status), cls: "badge " + v.status }),
      el("strong", { text: v.rule_id }),
      el("span", { text: `${v.citation.corpus_id} ${v.citation.article}(${v.citation.paragraph})`, cls: "cite" }),
    ]);
    card.appendChild(head);
    const r = rationale(v.rationale_key);
    if (r) card.appendChild(el("p", { text: r, cls: "rationale" }));
    if (v.unknown_facts.length) {
      card.appendChild(el("p", { text: "? " + v.unknown_facts.join(", "), cls: "unknowns" }));
    }
    const det = el("details", { cls: "explain" });
    det.appendChild(el("summary", { text: ui("web_explanation") }));
    det.appendChild(el("pre", { text: treeText(v.explanation, 0).join("\n") }));
    card.appendChild(det);
    root.appendChild(card);
  }

  // (5) print meta + (6) footer
  const meta = el("div", { attrs: { id: "print-meta" } }, [
    el("div", { text: `as_of: ${s.as_of}` }),
    el("div", { text: `corpus_version: ${s.corpus_version} (${s.corpus_status})` }),
    el("div", { text: (state.version || "").replace(/\n/g, " ") }),
    el("pre", { text: s.disclaimer, cls: "disclaimer" }),
  ]);
  root.appendChild(meta);

  const actions = el("div", { cls: "actions" }, [
    el("button", { text: ui("web_print"), on: { click: () => window.print() } }),
    el("button", { text: ui("web_restart"), cls: "secondary", on: { click: restart } }),
  ]);
  root.appendChild(actions);

  const footer = el("footer", { cls: "meta" });
  footer.appendChild(el("div", { text: (state.version || "").replace(/\n/g, "  ·  ") }));
  footer.appendChild(el("div", { text: `as_of ${s.as_of} · ${s.corpus_version} · licence EUPL-1.2` }));
  footer.appendChild(el("a", { text: "source repository", attrs: { href: REPO, rel: "noopener" } }));
  root.appendChild(footer);
  window.scrollTo(0, 0);
}

// explanation tree -> indented plain text (presentation only, DOM-safe)
function treeText(node, depth) {
  const pad = "  ".repeat(depth);
  let head;
  if (node.op === "fact") {
    head = `${pad}- fact ${node.fact} -> ${node.value} [${node.citation.corpus_id} ${node.citation.article}]`;
  } else if (node.op === "scope" || node.op === "applicability") {
    head = `${pad}- ${node.op} -> ${node.value}${node.reason ? " (" + node.reason + ")" : ""}`;
  } else {
    head = `${pad}- ${node.op || "?"} -> ${node.value || "?"}${node.reason ? " (" + node.reason + ")" : ""}`;
  }
  const lines = [head];
  for (const c of node.children || []) lines.push(...treeText(c, depth + 1));
  return lines;
}

// The canonical block is: bilingual header line, Italian body, blank line,
// English body, footer line. Return header + selected-language body + footer;
// on any unexpected shape return the FULL block (fail-safe, never less).
function localizedDisclaimer(full, lang) {
  const lines = full.split("\n");
  const blank = lines.indexOf("");
  if (lines.length < 5 || blank <= 1 || blank >= lines.length - 2) return full;
  const header = lines[0], footer = lines[lines.length - 1];
  const body = lang === "en" ? lines.slice(blank + 1, lines.length - 1) : lines.slice(1, blank);
  return [header, ...body, footer].join("\n");
}

function restart() { state.answers = {}; state.index = 0; renderWizard(); }
function localISODate() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

boot();
