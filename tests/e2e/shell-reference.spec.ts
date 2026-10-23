// Gate 1 of Phase 1 (DESIGN.md 18.1, first pass of the shell): the parts of the reference that
// exist after this phase, measured at the 1376 x 768 reference frame, with the numbers recorded.
// The screenshots in /test-results/shots are what the owner approves.

import { mkdirSync, writeFileSync } from "node:fs";
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { resetApp, saveProfile } from "./helpers";

const SHOTS = "/test-results/shots";

async function box(page: Page, selector: string) {
  const rect = await page.locator(selector).first().boundingBox();
  if (!rect) throw new Error(`${selector} is not on the page`);
  return {
    x: Math.round(rect.x),
    y: Math.round(rect.y),
    width: Math.round(rect.width),
    height: Math.round(rect.height),
  };
}

test.beforeAll(() => mkdirSync(SHOTS, { recursive: true }));

test("the navigation capsule matches the reference frame within 12 px", async ({
  page,
  request,
}) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata", theme: "dark" });
  await page.setViewportSize({ width: 1376, height: 768 });
  await page.goto("/settings");
  await expect(page.getByRole("button", { name: "Mohammed" })).toBeVisible();
  await page.evaluate(() => document.fonts.ready);

  const nav = await box(page, ".nav__capsule");
  const logo = await box(page, ".nav__brand img");
  const wordmark = await page.locator(".nav__wordmark").evaluate((el) => {
    const style = getComputedStyle(el);
    return { fontSize: parseFloat(style.fontSize), family: style.fontFamily, colour: style.color };
  });
  const capsule = await page.locator(".nav__capsule").evaluate((el) => {
    const style = getComputedStyle(el);
    return {
      background: style.backgroundImage,
      border: style.borderTopColor,
      radius: style.borderTopLeftRadius,
      blur: style.backdropFilter,
    };
  });
  const logoStyle = await page.locator(".nav__brand img").evaluate((el) => {
    const style = getComputedStyle(el);
    return { filter: style.filter, transform: style.transform, src: el.getAttribute("src") };
  });
  const star = await page.locator("svg, img").evaluateAll(
    (nodes) => nodes.filter((n) => /star|sparkle/i.test(n.outerHTML)).length,
  );

  // Reference frame (DESIGN.md 4.7): capsule x 70 to 1305 (about 1235 wide), y 50 to 110 (60 tall).
  const reference = { x: 70, y: 50, width: 1235, height: 60 };
  const differences = {
    x: nav.x - reference.x,
    y: nav.y - reference.y,
    width: nav.width - reference.width,
    height: nav.height - reference.height,
  };
  writeFileSync(
    "/test-results/shell-reference.json",
    JSON.stringify({ frame: "1376x768 dark", nav, reference, differences, logo, wordmark, capsule, logoStyle }, null, 2),
  );

  for (const [name, difference] of Object.entries(differences)) {
    expect(Math.abs(difference), `capsule ${name}`).toBeLessThanOrEqual(12);
  }
  expect(logo).toMatchObject({ width: 32, height: 32 });
  expect(wordmark.fontSize).toBe(26);
  expect(wordmark.family).toContain("Newsreader");
  expect(capsule.radius).toMatch(/9999px|3.35544e\+07px/); // a full pill
  expect(capsule.background).toContain("rgb(82, 71, 63)"); // #52473F
  expect(capsule.background).toContain("rgb(99, 84, 72)"); // #635448
  expect(capsule.border).toBe("rgba(255, 243, 226, 0.38)");
  expect(capsule.blur).toContain("blur(18px)");
  // The logo is shown as supplied: no filter, no transform, the unmodified file.
  expect(logoStyle).toEqual({ filter: "none", transform: "none", src: "/enderchest-logo.svg" });
  // No star or sparkle anywhere (DESIGN.md 2.2).
  expect(star).toBe(0);
  // After Phase 2 the centre holds Inventory and Camera only (PAGES.md 1, D-034).
  await expect(page.locator(".nav__capsule a, .nav__capsule button")).toHaveCount(4); // + brand, name
  await expect(page.locator(".nav__item")).toHaveText(["Inventory", "Camera"]);
  await page.screenshot({ path: `${SHOTS}/settings-dark-1376x768.png` });
});

test("screenshots of the shell for the owner to approve", async ({ page, request }) => {
  await resetApp(request);
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/welcome");
  await expect(page.getByRole("heading", { name: "Welcome to Enderchest" })).toBeVisible();
  await page.screenshot({ path: `${SHOTS}/welcome-dark-1280x720.png` });

  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata", theme: "dark" });
  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: "Settings", exact: true })).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: `${SHOTS}/settings-dark-1280x720.png`, fullPage: true });

  await page.getByRole("button", { name: "Mohammed" }).click();
  await expect(page.getByRole("link", { name: "Settings" })).toBeVisible();
  await page.screenshot({ path: `${SHOTS}/name-menu-dark-1280x720.png` });

  await page.setViewportSize({ width: 1024, height: 768 });
  await page.goto("/settings");
  await page.screenshot({ path: `${SHOTS}/settings-dark-1024x768.png`, fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);

  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata", theme: "light" });
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.goto("/settings");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.screenshot({ path: `${SHOTS}/settings-light-1280x720.png`, fullPage: true });
  await page.goto("/not-a-page");
  await expect(page.getByRole("heading", { name: "That page doesn't exist" })).toBeVisible();
  await page.screenshot({ path: `${SHOTS}/not-found-light-1280x720.png` });

  await resetApp(request);
  await page.emulateMedia({ colorScheme: "light" });
  await page.goto("/welcome");
  await expect(page.getByRole("heading", { name: "Welcome to Enderchest" })).toBeVisible();
  await page.screenshot({ path: `${SHOTS}/welcome-light-1280x720.png` });
});
