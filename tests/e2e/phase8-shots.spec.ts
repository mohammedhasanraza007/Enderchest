// Phase 8: every screen in both themes at 1280 and 1024 px for the light-theme pass and the
// reviewer's look (DESIGN.md 8, 18.2; D-097). Data is the storyboard's (test stack only); these
// pictures are regression and review material, never gate evidence for the owner's approval.

import { mkdirSync } from "node:fs";
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { makeItem, post, resetApp, saveProfile } from "./helpers";

test.use({ reducedMotion: "reduce" });
test.setTimeout(240_000);

const SHOTS = "/test-results/shots-phase-8";
const EVENING = "2026-10-16T19:30:00+05:30";

async function settle(page: Page): Promise<void> {
  await page.waitForLoadState("networkidle");
  await expect(page.locator('[aria-busy="true"]')).toHaveCount(0);
}

test("every screen, both themes, 1280 and 1024 px", async ({ page, request }) => {
  mkdirSync(SHOTS, { recursive: true });
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata", theme: "dark" });
  await post(request, "/api/v1/test/clock", { now: EVENING });
  const built = await post<{ public_ids: Record<string, string> }>(
    request,
    "/api/v1/test/fixtures/storyboard-1",
  );
  await makeItem(request, { name: "Spare torch bulbs" });
  await post(request, "/api/v1/savings", { item_name: "Phone case", price_paise: 49900 });
  const item = built.public_ids["Oat Milk"];
  const screens: [string, string][] = [
    ["dashboard", "/"],
    ["inventory", "/inventory"],
    ["item", `/items/${item}`],
    ["camera-add", "/camera?mode=add"],
    ["camera-scan", "/camera?mode=scan"],
    ["camera-own", "/camera?mode=own"],
    ["add-queue", "/add"],
    ["labels", "/labels"],
    ["trash", "/trash"],
    ["tasks", "/tasks"],
    ["notifications", "/notifications"],
    ["savings", "/savings"],
    ["settings", "/settings"],
    ["not-found", "/nowhere"],
  ];
  for (const theme of ["dark", "light"] as const) {
    await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata", theme });
    for (const width of [1280, 1024]) {
      await page.setViewportSize({ width, height: 800 });
      for (const [name, path] of screens) {
        await page.goto(path);
        await settle(page);
        await page.screenshot({ path: `${SHOTS}/${name}-${theme}-${width}.png`, fullPage: true });
      }
    }
  }
  await post(request, "/api/v1/test/clock", { now: new Date().toISOString() });
});
