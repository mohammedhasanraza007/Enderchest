// Phase 5 verification probe: the dashboard with the keyboard only. Tab reaches the rings, every
// card action and the road's days in reading order; Enter opens the ring sheet and Escape gives
// focus back to the rings. Storyboard frame 1 on the test stack.

import { expect, test } from "@playwright/test";
import { loadFixture, post, resetApp, saveProfile } from "./helpers";

const EVENING = "2026-10-16T19:30:00+05:30";

test.afterEach(async ({ request }) => {
  await post(request, "/api/v1/test/clock", { now: new Date().toISOString() });
});

test("Tab walks the rings, the card and the road; the sheet opens and closes by keys", async ({
  page,
  request,
}) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata", theme: "dark" });
  await post(request, "/api/v1/test/clock", { now: EVENING });
  await loadFixture(request, "storyboard-1");
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  await expect(page.locator('[aria-busy="true"]')).toHaveCount(0);

  const seen: string[] = [];
  for (let step = 0; step < 40; step += 1) {
    await page.keyboard.press("Tab");
    const name = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null;
      if (!el || el === document.body) return "";
      return (el.getAttribute("aria-label") ?? el.textContent ?? "").trim();
    });
    if (name === "" || name === seen[0]) break;
    seen.push(name);
  }
  const at = (pattern: RegExp) => seen.findIndex((name) => pattern.test(name));
  const rings = at(/^Inventory health/);
  const useIt = at(/^Use it$/);
  const road = at(/^18 Oct:/);
  expect(rings, seen.join(" | ")).toBeGreaterThan(-1);
  expect(useIt).toBeGreaterThan(rings);
  expect(road).toBeGreaterThan(useIt);
  expect(seen.filter((name) => /^(Use it|Snooze|Inspect now)$/.test(name)).length).toBe(5);

  const ringButton = page.getByRole("button", { name: /^Inventory health/ });
  await ringButton.focus();
  await page.keyboard.press("Enter");
  const sheet = page.getByRole("dialog", { name: "What counts" });
  await expect(sheet).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(sheet).toHaveCount(0);
  await expect(ringButton).toBeFocused();
});
