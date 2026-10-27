// Phase 8 verification probes (docs/reviews/phase-8-verification.md): motion on every screen, not
// only the dashboard; reduced motion on every screen; the save delivery never stacks and never
// blocks a click; the truck lane never widens the page at the three review widths.

import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { loadFixture, makeItem, post, resetApp, saveProfile } from "./helpers";

const EVENING = "2026-10-16T19:30:00+05:30";
const ALLOWED = new Set(["transform", "opacity", "strokeDashoffset", "offset", "easing", "composite", "computedOffset"]);
const ROUTES = ["/inventory", "/camera", "/tasks", "/notifications", "/savings", "/settings", "/labels", "/trash"];

async function animatedProperties(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const names = new Set<string>();
    for (const animation of document.getAnimations()) {
      const effect = animation.effect as KeyframeEffect | null;
      if (animation instanceof CSSTransition) names.add(animation.transitionProperty);
      for (const frame of effect?.getKeyframes() ?? []) Object.keys(frame).forEach((k) => names.add(k));
    }
    return [...names].map((name) => name.replace(/-([a-z])/g, (_m, c: string) => c.toUpperCase()));
  });
}

async function saveByHand(page: Page, name: string): Promise<void> {
  await page.getByRole("button", { name: "Enter manually" }).click();
  const sheet = page.getByRole("dialog", { name: "Add an item" });
  await sheet.getByLabel("Name", { exact: true }).fill(name);
  await sheet.getByRole("button", { name: "Save item" }).click();
  await expect(sheet).toHaveCount(0);
}

test.afterEach(async ({ request }) => {
  await post(request, "/api/v1/test/clock", { now: new Date().toISOString() });
});

test("V1 every screen's page arrival moves only transform and opacity", async ({ page, request }) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata", theme: "dark" });
  const item = await makeItem(request, { name: "Torch" });
  await page.goto("/");
  for (const path of [...ROUTES, `/items/${item}`]) {
    await page.evaluate((to) => {
      window.history.pushState({}, "", to);
      window.dispatchEvent(new PopStateEvent("popstate"));
    }, path);
    const moving = await animatedProperties(page);
    expect(moving.filter((name) => !ALLOWED.has(name)), path).toEqual([]);
  }
});

test.describe("V2 reduced motion on every screen", () => {
  test.use({ reducedMotion: "reduce" });

  test("nothing animates after arriving on any screen", async ({ page, request }) => {
    await resetApp(request);
    await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata", theme: "dark" });
    const item = await makeItem(request, { name: "Torch" });
    await page.goto("/");
    for (const path of [...ROUTES, `/items/${item}`, "/"]) {
      await page.evaluate((to) => {
        window.history.pushState({}, "", to);
        window.dispatchEvent(new PopStateEvent("popstate"));
      }, path);
      await page.waitForTimeout(50);
      expect(await page.evaluate(() => document.getAnimations().length), path).toBe(0);
    }
  });
});

test("V3 two quick saves never stack a second delivery, and it clears", async ({ page, request }) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata", theme: "dark" });
  await page.goto("/camera?mode=add");
  await saveByHand(page, "Torch");
  await saveByHand(page, "Batteries");
  expect(await page.locator(".delivery").count()).toBeLessThanOrEqual(1);
  expect(await page.locator(".delivery__vehicle").count()).toBeLessThanOrEqual(1);
  await expect(page.locator(".delivery")).toHaveCount(0, { timeout: 1_500 });
  await expect(page.locator("body.delivering")).toHaveCount(0);
});

test("V4 a click during the delivery lands and finishes it", async ({ page, request }) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata", theme: "dark" });
  await page.goto("/camera?mode=add");
  await saveByHand(page, "Torch");
  await expect(page.locator(".delivery")).toHaveCount(1);
  await page.getByRole("link", { name: "Tasks" }).click();
  await expect(page).toHaveURL(/\/tasks$/);
  await expect(page.locator(".delivery")).toHaveCount(0);
});

for (const width of [1024, 1280, 1536]) {
  test(`V5 the road never widens the dashboard at ${width} px`, async ({ page, request }) => {
    await resetApp(request);
    await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata", theme: "dark" });
    await post(request, "/api/v1/test/clock", { now: EVENING });
    await loadFixture(request, "storyboard-1");
    await page.setViewportSize({ width, height: 800 });
    for (const path of ["/", "/tasks"]) {
      await page.goto(path);
      await expect(page.locator(".road__lane").first()).toBeVisible();
      await page.waitForTimeout(1_500);
      const [scroll, inner] = await page.evaluate(() => [
        document.documentElement.scrollWidth,
        window.innerWidth,
      ]);
      expect(scroll, path).toBeLessThanOrEqual(inner);
    }
  });
}
