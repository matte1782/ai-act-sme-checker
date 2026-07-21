// SPDX-License-Identifier: EUPL-1.2
// SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
//
// Gate-6 e2e (PROMPT 8 Phase F2). ADR-013 zero-exfiltration + disclaimer +
// i18n + print, driven against the locally-served web/.
//
// EXECUTION NOTE (owner-authorized 2026-07-20): pytest-playwright is not
// installed and installing it is network outside the Phase-A acquisition
// whitelist (Constraint 1) - a gate about network discipline. So the assertions
// below were RUN this session via the already-connected Playwright MCP browser
// against `python scripts/serve_web.py` (results recorded in the Gate-6 summary
// + GATE event). This file is the CI-runnable artifact: `npx playwright test`
// with @playwright/test + a local server reproduces every assertion.
import { test, expect } from "@playwright/test";

const BASE = process.env.BASE_URL || "http://127.0.0.1:8000";

async function boot(page) {
  await page.goto(BASE + "/index.html");
  await expect(page.getByText("Domanda 1 di 19")).toBeVisible({ timeout: 30000 });
}

async function answerAll(page, unknownAt = 5) {
  for (let i = 0; i < 30; i++) {
    if (!(await page.locator("#results").isHidden())) break;
    const btns = page.locator("#wizard .answers button");
    let label;
    if (i === unknownAt) label = "Non so";
    else if ([0, 1, 4].includes(i)) label = "Sì";
    else label = "No";
    const target = btns.filter({ hasText: new RegExp("^" + label + "$") }).first();
    if (await target.count()) await target.click();
    else await btns.first().click(); // enum step: first option
  }
}

test("zero data leaves the device (network assertion)", async ({ page }) => {
  const external = [];
  page.on("request", (r) => {
    const u = new URL(r.url());
    if (u.origin !== new URL(BASE).origin) external.push(r.url());
  });
  await boot(page);
  const afterLoad = [];
  page.on("request", (r) => afterLoad.push(r.url())); // must stay empty during the flow
  await answerAll(page);
  await expect(page.locator("#results .disclaimer")).toBeVisible();
  expect(external, "no request to any non-self origin").toEqual([]);
  expect(afterLoad, "zero requests after load (all computation is client-side)").toEqual([]);
});

test("disclaimer is computed-visible on results and in print", async ({ page }) => {
  await boot(page);
  await answerAll(page);
  await expect(page.locator("#results .disclaimer")).toBeVisible();
  await page.emulateMedia({ media: "print" });
  const printMeta = page.locator("#print-meta");
  await expect(printMeta).toContainText("NOT LEGAL ADVICE");
  await expect(printMeta).toContainText("corpus_version");
});

test("language toggle switches question text", async ({ page }) => {
  await boot(page);
  const it = await page.locator("#wizard .q-prompt").textContent();
  await page.locator("#wizard .lang-toggle button", { hasText: "English" }).click();
  const en = await page.locator("#wizard .q-prompt").textContent();
  expect(en).not.toEqual(it);
});

test("provisional corpus shows the notice", async ({ page }) => {
  await boot(page);
  await answerAll(page);
  await expect(page.locator("#results .provisional")).toContainText("testo provvisorio del Consiglio");
});
