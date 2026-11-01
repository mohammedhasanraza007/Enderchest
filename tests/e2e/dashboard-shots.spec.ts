// Screenshots of the dashboard and the Tasks road for review against the reference (D-097,
// DESIGN.md 18.1): the reference frame (1376 x 768, dark) on the three storyboard fixtures with
// measured positions; 1024, 1280 and 1536 px in both themes; the empty dashboard, the ring sheet
// and the Tasks page. Test data on the test stack; the owner approves the look (BLOCKED).

import { writeFileSync } from "node:fs";
import { expect, test } from "@playwright/test";
import type { APIRequestContext, Page } from "@playwright/test";
import { loadFixture, post, resetApp, saveProfile } from "./helpers";

const SHOTS = "/test-results/shots-phase-5";
const EVENING = "2026-10-16T19:30:00+05:30";
test.use({ reducedMotion: "reduce" });
test.setTimeout(240_000);

async function story(
  request: APIRequestContext,
  stage: number,
  theme: "dark" | "light",
): Promise<void> {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata", theme });
  await post(request, "/api/v1/test/clock", { now: EVENING });
  if (stage > 0) await loadFixture(request, `storyboard-${stage}`);
}

async function settle(page: Page): Promise<void> {
  await page.waitForLoadState("networkidle");
  await expect(page.locator('[aria-busy="true"]')).toHaveCount(0);
  await page.evaluate(() => document.fonts.ready);
}

/** Boxes of the reference's landmarks (DESIGN.md 4.7), in CSS pixels. */
async function measure(page: Page) {
  return page.evaluate(() => {
    const box = (selector: string) => {
      const rect = document.querySelector(selector)?.getBoundingClientRect();
      return rect
        ? [rect.left, rect.top, rect.right, rect.bottom].map((value) => Math.round(value))
        : null;
    };
    const ticks = [...document.querySelectorAll(".road__day")].map((tick) => {
      const rect = tick.getBoundingClientRect();
      return Math.round(rect.left + rect.width / 2);
    });
    return {
      nav: box(".nav__capsule"),
      rings: box(".rings"),
      card: box(".attention-card"),
      innerPanel: box(".attention-card .inner-panel"),
      greeting: box(".greeting__title"),
      roadBar: box(".road__bar"),
      truck: box(".road__truck"),
      firstTick: ticks[0],
      lastTick: ticks[ticks.length - 1],
      scroll: [document.documentElement.scrollWidth, document.documentElement.scrollHeight],
    };
  });
}

test.afterEach(async ({ request }) => {
  await post(request, "/api/v1/test/clock", { now: new Date().toISOString() });
});

test("the reference frame on the three storyboard fixtures", async ({ page, request }) => {
  await page.setViewportSize({ width: 1376, height: 768 });
  const measured: Record<string, unknown> = {};
  for (const stage of [1, 2, 3]) {
    await story(request, stage, "dark");
    await page.goto("/");
    await settle(page);
    await page.screenshot({ path: `${SHOTS}/storyboard-${stage}-dark-1376x768.png` });
    measured[`storyboard-${stage}`] = await measure(page);
  }
  writeFileSync(`${SHOTS}/reference-measurements.json`, JSON.stringify(measured, null, 2));
  // The frame fits one 768 px screen with no scrolling either way.
  const first = measured["storyboard-1"] as { scroll: number[] };
  expect(first.scroll).toEqual([1376, 768]);
});

for (const theme of ["dark", "light"] as const) {
  test(`dashboard and Tasks road at three widths (${theme})`, async ({ page, request }) => {
    await story(request, 1, theme);
    for (const [width, height] of [
      [1024, 768],
      [1280, 800],
      [1536, 864],
    ] as const) {
      await page.setViewportSize({ width, height });
      await page.goto("/");
      await settle(page);
      await page.screenshot({ path: `${SHOTS}/dashboard-${theme}-${width}.png`, fullPage: true });
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth),
      ).toBeLessThanOrEqual(0);
      await page.goto("/tasks");
      await settle(page);
      await page.screenshot({ path: `${SHOTS}/tasks-road-${theme}-${width}.png`, fullPage: true });
    }
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto("/");
    await settle(page);
    await page.getByRole("button", { name: /^Inventory health/ }).click();
    await page
      .getByRole("dialog", { name: "What counts" })
      .getByRole("radio", { name: /On time/ })
      .click();
    await expect(page.getByText("5 of 9 tasks, 56%")).toBeVisible();
    await page.screenshot({ path: `${SHOTS}/ring-sheet-${theme}-1280.png` });
    await page.keyboard.press("Escape");
    await page.getByRole("button", { name: /^18 Oct:/ }).focus();
    await page.screenshot({ path: `${SHOTS}/road-tooltip-${theme}-1280.png` });

    await story(request, 0, theme);
    await page.goto("/");
    await settle(page);
    await page.screenshot({ path: `${SHOTS}/dashboard-empty-${theme}-1280.png`, fullPage: true });
  });
}
