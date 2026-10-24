// Screenshots of the Phase 3 screens for review against the reference (D-097): the confirm screen
// with read values, source tags and the expiry check, the "What was read" drawer, the queue and
// the Settings Gemini section; 1280 px dark and light, 1024 px dark for the dense confirm screen.
// Test data on the test stack; the owner approves the look (BLOCKED until they do).

import { expect, test } from "@playwright/test";
import { labelBytes, makeDraft, readingSettled, resetApp, saveProfile } from "./helpers";

const SHOTS = "/test-results/shots-phase-3";
test.use({ reducedMotion: "reduce" });
test.setTimeout(180_000);

for (const theme of ["dark", "light"] as const) {
  test(`smart capture screens (${theme})`, async ({ page, request }) => {
    await resetApp(request);
    await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata", theme });
    await request.post("/api/v1/categories", {
      headers: { "X-Enderchest": "1" },
      data: { name: "Food and drink", expires_default: true, label_default: false },
    });
    await page.goto("/add");
    const clear = await makeDraft(
      request,
      await labelBytes(page, [
        "OAT MILK BARISTA",
        "1 L  MODEL AB-1234X",
        "MFD 12/01/2026  EXP 14/03/2027",
        "BATCH L4471  Net Qty 500 ml",
      ]),
    );
    const ambiguous = await makeDraft(
      request,
      await labelBytes(page, ["SOAP BAR", "EXP 03/04/2027"]),
    );
    await readingSettled(request, clear);
    await readingSettled(request, ambiguous);

    const settle = async () => {
      await page.waitForLoadState("networkidle");
      await expect(page.locator('[aria-busy="true"]')).toHaveCount(0);
      await page.evaluate(() => document.fonts.ready);
    };
    const screens: Array<[string, string]> = [
      ["confirm-read", `/add/${clear}`],
      ["confirm-ambiguous", `/add/${ambiguous}`],
      ["queue-read", "/add"],
    ];
    for (const width of theme === "dark" ? [1280, 1024] : [1280]) {
      await page.setViewportSize({ width, height: 900 });
      for (const [name, path] of screens) {
        if (width === 1024 && name === "queue-read") continue;
        await page.goto(path);
        await settle();
        await page.screenshot({ path: `${SHOTS}/${name}-${theme}-${width}.png`, fullPage: true });
      }
    }
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(`/add/${clear}`);
    await settle();
    await page.getByRole("button", { name: "What was read" }).click();
    await expect(page.getByRole("dialog", { name: "What was read" })).toBeVisible();
    await page.screenshot({ path: `${SHOTS}/read-drawer-${theme}-1280.png` });

    await page.goto("/settings");
    await settle();
    const gemini = page.locator(".glass-card").filter({ hasText: "When to use Gemini" });
    await gemini.scrollIntoViewIfNeeded();
    await gemini.screenshot({ path: `${SHOTS}/settings-gemini-${theme}-1280.png` });
  });
}
