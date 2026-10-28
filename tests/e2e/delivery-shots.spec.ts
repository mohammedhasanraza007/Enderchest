// Final merge: frames of the save delivery on the dashboard (D-138), paused at each beat, for the
// comparison with the owner's delivery video. Storyboard data (test stack only); review material,
// never gate evidence for the owner's approval.

import { mkdirSync } from "node:fs";
import { expect, test } from "@playwright/test";
import { loadFixture, post, resetApp, saveProfile } from "./helpers";

const SHOTS = "/test-results/shots-delivery";
const BEATS = [0.15, 0.3, 0.38, 0.5, 0.66, 0.8, 0.93];

test("the save delivery, paused at each beat, dark and light", async ({ page, request }) => {
  mkdirSync(SHOTS, { recursive: true });
  for (const theme of ["dark", "light"] as const) {
    await resetApp(request);
    await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata", theme });
    await post(request, "/api/v1/test/clock", { now: "2026-10-16T19:30:00+05:30" });
    await loadFixture(request, "storyboard-1");
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto("/");
    await expect(page.locator(".road__truck")).toHaveCount(1);
    await page.waitForTimeout(2_500);
    await page.evaluate(() => window.dispatchEvent(new Event("enderchest:delivery")));
    await expect(page.locator(".delivery__vehicle")).toHaveCount(1);
    for (const beat of BEATS) {
      await page.evaluate((at) => {
        for (const one of document.querySelectorAll(".delivery *")) {
          for (const animation of one.getAnimations()) {
            animation.pause();
            animation.currentTime = at * 1150;
          }
        }
      }, beat);
      await page.screenshot({ path: `${SHOTS}/${theme}-${String(beat * 100).padStart(2, "0")}.png` });
    }
  }
});
