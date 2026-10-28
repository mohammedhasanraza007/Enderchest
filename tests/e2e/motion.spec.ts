// Phase 8: the motion system (DESIGN.md 10, D-127 to D-130). The entrance plays once per tab
// session and any input ends it at the final state; nothing animates layout; input is never
// blocked; reduced motion shows final states with no animation; rows leave, the truck drives by
// transform, the save delivery runs and clears itself; the streak line shows from two days.

import { expect, test } from "@playwright/test";
import type { APIRequestContext, Page } from "@playwright/test";
import { loadFixture, makeItem, post, resetApp, saveProfile } from "./helpers";

const EVENING = "2026-10-16T19:30:00+05:30";
const ALLOWED = new Set(["transform", "opacity", "strokeDashoffset", "offset", "easing", "composite", "computedOffset"]);

async function story(request: APIRequestContext, stage: 1 | 2 | 3): Promise<void> {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata", theme: "dark" });
  await post(request, "/api/v1/test/clock", { now: EVENING });
  await loadFixture(request, `storyboard-${stage}`);
}

/** Every property any running animation on the page moves (CSS and Web Animations alike). */
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

/** The new-item form from the camera hub's "Enter manually" (P-06), saved with a name only. */
async function addByHand(page: Page, name: string): Promise<void> {
  await page.goto("/camera?mode=add");
  await page.getByRole("button", { name: "Enter manually" }).click();
  const sheet = page.getByRole("dialog", { name: "Add an item" });
  await sheet.getByLabel("Name", { exact: true }).fill(name);
  await sheet.getByRole("button", { name: "Save item" }).click();
}

test.afterEach(async ({ request }) => {
  await post(request, "/api/v1/test/clock", { now: new Date().toISOString() });
});

test("the entrance plays once, moves only transform, opacity and dash offset, and ends in time", async ({
  page,
  request,
}) => {
  await story(request, 1);
  await page.goto("/");
  await expect(page.locator(".dashboard--entrance")).toHaveCount(1);
  const moving = await animatedProperties(page);
  expect(moving.length).toBeGreaterThan(0);
  expect(moving.filter((name) => !ALLOWED.has(name))).toEqual([]);
  // Under 1.4 s from the data, the entrance is over and the numbers are the server's.
  await expect(page.locator(".dashboard--entrance")).toHaveCount(0, { timeout: 2_000 });
  await expect(page.locator(".rings__score")).toHaveText("82");
  // A second visit in the same tab plays no entrance.
  await page.getByRole("link", { name: "Tasks" }).click();
  await page.getByRole("link", { name: "Dashboard" }).click();
  await expect(page.locator(".rings__score")).toHaveText("82");
  await expect(page.locator(".dashboard--entrance")).toHaveCount(0);
});

test("any input ends the entrance at the final state and is not blocked", async ({ page, request }) => {
  await story(request, 1);
  await page.goto("/");
  await expect(page.locator(".dashboard--entrance")).toHaveCount(1);
  // The very first click works during the entrance: the ring sheet opens.
  await page.getByRole("button", { name: /^Inventory health/ }).click();
  await expect(page.locator(".dashboard--entrance")).toHaveCount(0);
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.locator(".rings__score")).toHaveText("82");
});

test.describe("reduced motion", () => {
  test.use({ reducedMotion: "reduce" });

  test("shows final states with nothing animating", async ({ page, request }) => {
    await story(request, 1);
    await page.goto("/");
    await expect(page.locator(".rings__score")).toHaveText("82");
    await expect(page.locator(".dashboard--entrance")).toHaveCount(0);
    expect(await page.evaluate(() => document.getAnimations().length)).toBe(0);
    // A save plays no delivery.
    await addByHand(page, "Torch");
    await expect(page.getByText("Item saved.")).toBeVisible();
    await expect(page.locator(".delivery")).toHaveCount(0);
  });
});

test("a used item's row slides out, the score glides up and its ring flares once", async ({
  page,
  request,
}) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata", theme: "dark" });
  await post(request, "/api/v1/test/clock", { now: EVENING });
  const built = await post<{ task_ids: Record<string, number> }>(
    request,
    "/api/v1/test/fixtures/storyboard-1",
  );
  await page.goto("/");
  await expect(page.locator(".rings__score")).toHaveText("82");
  await expect(page.locator(".dashboard--entrance")).toHaveCount(0, { timeout: 3_000 });
  // Two overdue chores done elsewhere: the refresh after "Use it" brings a higher On time ring.
  for (const title of ["Water the plants", "Change bedsheets"]) {
    await post(request, `/api/v1/tasks/${built.task_ids[title]}/done`);
  }
  const row = page.locator(".reminder", { hasText: "Oat Milk" });
  await row.getByRole("button", { name: "Use it" }).click();
  await expect(page.locator(".reminder--leaving")).toHaveCount(1);
  await expect(row).toHaveCount(0);
  await expect(page.locator(".rings__score")).toHaveText("86");
  await expect(page.locator('[data-ring="on_time"] .rings__flare')).toHaveCount(1);
  const moving = await animatedProperties(page);
  expect(moving.filter((name) => !ALLOWED.has(name))).toEqual([]);
});

test("the truck drives by transform when its day changes, never by left", async ({
  page,
  request,
}) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata", theme: "dark" });
  await post(request, "/api/v1/test/clock", { now: EVENING });
  const built = await post<{ task_ids: Record<string, number> }>(
    request,
    "/api/v1/test/fixtures/storyboard-1",
  );
  await page.goto("/");
  await expect(page.locator(".rings__score")).toHaveText("82");
  await expect(page.locator(".dashboard--entrance")).toHaveCount(0, { timeout: 3_000 });
  const lane = page.locator(".road__lane");
  const before = await lane.evaluate((el) => (el as HTMLElement).style.transform);
  expect(before).toMatch(/^translateX\([\d.]+%\)$/);
  expect(await page.locator(".road__truck").evaluate((el) => (el as SVGElement).style.left)).toBe("");
  await post(request, `/api/v1/tasks/${built.task_ids["Pantry Refill"]}/done`);
  await page.reload();
  await expect(page.locator(".road__label")).toContainText("Clean PC");
  const after = await lane.evaluate((el) => (el as HTMLElement).style.transform);
  expect(after).toMatch(/^translateX\([\d.]+%\)$/);
  expect(after).not.toBe(before);
  // The shifted lane never widens the page (it is clipped inside the road).
  for (const path of ["/", "/tasks"]) {
    await page.goto(path);
    await expect(page.locator(".road__lane").first()).toBeVisible();
    const [scroll, inner] = await page.evaluate(() => [
      document.documentElement.scrollWidth,
      window.innerWidth,
    ]);
    expect(scroll).toBeLessThanOrEqual(inner);
  }
});

test("saving a new item sends the box to the brand mark and clears itself", async ({
  page,
  request,
}) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata", theme: "dark" });
  await addByHand(page, "Torch");
  const layer = page.locator(".delivery");
  await expect(layer).toHaveCount(1);
  expect(await layer.evaluate((el) => getComputedStyle(el).pointerEvents)).toBe("none");
  await expect(layer).toHaveCount(0, { timeout: 1_500 });
});

test("the delivery drops the box from under the nav, draws a trail and shrinks into the mark (D-138)", async ({
  page,
  request,
}) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata", theme: "dark" });
  await addByHand(page, "Lamp");
  await expect(page.locator(".delivery")).toHaveCount(1);
  await expect(page.locator(".delivery__trail")).toHaveCount(1);
  await expect(page.locator(".delivery__star")).toHaveCount(1);
  const beats = await page.evaluate(() => {
    const frames = (selector: string) =>
      (document.querySelector(selector)?.getAnimations()[0]?.effect as KeyframeEffect).getKeyframes();
    const drive = frames(".delivery__vehicle");
    const fall = Number(/translateY\(-(\d+(?:\.\d+)?)px\)/.exec(String(frames(".delivery__parcel")[0].transform))![1]);
    const props = [...document.querySelectorAll(".delivery *")]
      .flatMap((el) => el.getAnimations())
      .flatMap((a) => (a.effect as KeyframeEffect).getKeyframes())
      .flatMap((k) => Object.keys(k))
      .filter((key) => !["offset", "easing", "composite", "computedOffset"].includes(key));
    return {
      fall,
      turns: drive.some((k) => String(k.transform).includes("scaleX(0.15)")),
      last: String(drive[drive.length - 1].transform),
      props: [...new Set(props)],
    };
  });
  // Off the dashboard the trip starts at the bottom centre, never on its own copy at the top left.
  expect(beats.fall).toBeGreaterThan(200);
  expect(beats.turns).toBe(true);
  expect(beats.last).toContain("scale(0.05)");
  for (const prop of beats.props) expect(["transform", "opacity", "strokeDashoffset"]).toContain(prop);
  await expect(page.locator(".delivery")).toHaveCount(0, { timeout: 1_500 });
});

test("the streak line shows from two days and never speaks of a break", async ({ page, request }) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata", theme: "dark" });
  await post(request, "/api/v1/test/clock", { local_date: "2026-10-15" });
  const first = await makeItem(request, { name: "Bread", expiry_mode: "date", expiry_date: "2026-10-16" });
  await post(request, `/api/v1/items/${first}/use`);
  await post(request, "/api/v1/test/clock", { local_date: "2026-10-16" });
  await page.goto("/");
  await expect(page.locator(".rings__score")).not.toHaveText("");
  await expect(page.locator(".greeting__streak")).toHaveCount(0);
  const second = await makeItem(request, { name: "Milk", expiry_mode: "date", expiry_date: "2026-10-17" });
  await post(request, `/api/v1/items/${second}/use`);
  await page.reload();
  await expect(page.locator(".greeting__streak")).toHaveText("2 days in a row");
  await expect(page.getByText(/broke|lost|missed/i)).toHaveCount(0);
});
