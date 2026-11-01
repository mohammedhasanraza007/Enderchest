// Final UX test, group 1 (D-144): first run, the shell and Settings, as a tester found them on a
// fresh release install. Test data on the test stack, never gate evidence for the owner.

import { expect, test } from "@playwright/test";
import { makeItem, post, resetApp, saveProfile } from "./helpers";

test.use({ reducedMotion: "reduce", timezoneId: "Asia/Kolkata" });

const LONG_NAME = "Mohammed Hasan Raza Khan";

test.beforeEach(async ({ request }) => {
  await resetApp(request);
});

test("the welcome error goes when the name is typed, and each step takes the focus", async ({ page }) => {
  await page.goto("/welcome");
  await page.getByRole("button", { name: "Continue" }).click();
  const name = page.getByLabel("Your name");
  await expect(name).toHaveAttribute("aria-invalid", "true");
  await name.fill("Ravi");
  await expect(name).not.toHaveAttribute("aria-invalid", "true");
  await page.getByRole("button", { name: "Continue" }).click();
  const title = page.getByRole("heading", { name: "Start with some categories?" });
  await expect(title).toBeFocused();

  // A chip gaining its check mark must not move the chips under the pointer.
  const chips = page.locator(".welcome-card .chip-row .chip");
  const before = await chips.first().boundingBox();
  const second = await chips.nth(1).boundingBox();
  await chips.first().click();
  expect((await chips.first().boundingBox())?.width).toBe(before?.width);
  expect((await chips.nth(1).boundingBox())?.x).toBe(second?.x);
});

test.describe("a long name", () => {
  test.beforeEach(async ({ request }) => {
    await saveProfile(request, { name: LONG_NAME, timezone: "Asia/Kolkata", theme: "dark" });
  });

  test("stays inside the nav capsule at 1024 px", async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 768 });
    await page.goto("/settings");
    const pill = await page.locator(".name-pill").boundingBox();
    const capsule = await page.locator(".nav__capsule").boundingBox();
    expect(pill!.x + pill!.width).toBeLessThanOrEqual(capsule!.x + capsule!.width);
  });

  test("wraps in the greeting instead of reaching the rings", async ({ page, request }) => {
    await saveProfile(request, { name: "M".repeat(40), timezone: "Asia/Kolkata", theme: "dark" });
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto("/");
    const fits = await page
      .locator(".greeting__title")
      .evaluate((title) => title.scrollWidth <= title.clientWidth);
    expect(fits).toBe(true);
  });
});

test.describe("Settings", () => {
  test.beforeEach(async ({ request }) => {
    await saveProfile(request, { name: "Ravi", timezone: "America/New_York", theme: "dark" });
  });

  test("the three theme chips share one row in both themes", async ({ page, request }) => {
    for (const theme of ["dark", "light"] as const) {
      await saveProfile(request, { name: "Ravi", timezone: "Asia/Kolkata", theme });
      await page.goto("/settings");
      await page.locator(".name-pill").click();
      const tops = await page
        .locator(".name-menu__panel .chip")
        .evaluateAll((chips) => chips.map((chip) => chip.getBoundingClientRect().top));
      expect(tops).toHaveLength(3);
      expect(new Set(tops).size).toBe(1);
    }
  });

  test("Use my time zone saves at once", async ({ page, request }) => {
    await page.goto("/settings");
    await page.getByRole("button", { name: "Use Asia/Kolkata" }).click();
    await expect(page.getByText("Profile saved.")).toBeVisible();
    const profile = await (await request.get("/api/v1/profile")).json();
    expect(profile.timezone).toBe("Asia/Kolkata");
  });

  test("the key error goes when the key field changes", async ({ page }) => {
    await page.goto("/settings");
    const key = page.getByLabel("Gemini API key");
    await key.fill("not a key");
    await key.press("Enter");
    await expect(page.getByText("space or line break")).toBeVisible();
    await key.fill("");
    await expect(page.getByText("space or line break")).toHaveCount(0);
  });

  test("Escape leaves a rename, and focus returns to Rename", async ({ page, request }) => {
    await post(request, "/api/v1/categories", { name: "Tools" });
    await page.goto("/settings");
    const row = page.locator(".row-list__row").filter({ hasText: "Tools" });
    await row.getByRole("button", { name: "Rename" }).click();
    // While renaming, the name is in the field, so the row no longer matches its text.
    const input = page.getByLabel("Name", { exact: true });
    await expect(input).toBeFocused();
    await input.press("Escape");
    await expect(input).toHaveCount(0);
    await expect(row.getByRole("button", { name: "Rename" })).toBeFocused();
    await expect(row.getByRole("switch", { name: "Maintenance by default" })).toBeVisible();
  });

  test("the reassign dialog gives the focus back when it goes", async ({ page, request }) => {
    const category = await post<{ id: number }>(request, "/api/v1/categories", { name: "Tools" });
    await makeItem(request, { name: "Drill", category_id: category.id });
    await page.goto("/settings");
    const row = page.locator(".row-list__row").filter({ hasText: "Tools" });
    const remove = row.getByRole("button", { name: "Delete" });
    await remove.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(remove).toBeFocused();
  });

  test("a row's old message goes when another action starts", async ({ page, request }) => {
    const parent = await post<{ id: number }>(request, "/api/v1/locations", { name: "Shed" });
    await post(request, "/api/v1/locations", { name: "Shelf", parent_id: parent.id });
    await page.goto("/settings");
    const row = page.locator(".row-list__row").filter({ hasText: "Shed" }).first();
    await row.getByRole("button", { name: "Delete" }).click();
    const message = row.getByRole("alert");
    await expect(message).toBeVisible();
    await row.getByRole("button", { name: "Rename" }).click();
    await expect(message).toHaveCount(0);
    await row.getByLabel("Name").press("Escape");
    await expect(row.getByRole("button", { name: "Rename" })).toBeFocused();
  });

  test("an off switch can be seen in the light theme", async ({ page, request }) => {
    await saveProfile(request, { name: "Ravi", timezone: "Asia/Kolkata", theme: "light" });
    await post(request, "/api/v1/categories", { name: "Tools" });
    await page.goto("/settings");
    const off = page.locator('.toggle[aria-checked="false"]').first();
    const colours = await off.evaluate((toggle) => {
      const thumb = toggle.querySelector(".toggle__thumb")!;
      return {
        thumb: getComputedStyle(thumb).backgroundColor,
        track: getComputedStyle(toggle).backgroundColor,
        edge: getComputedStyle(toggle).borderTopColor,
      };
    });
    expect(colours.thumb).not.toBe(colours.track);
    expect(colours.edge).toBe(colours.thumb);
  });
});

test("Enter in New location name adds the place and keeps the item form open", async ({ page, request }) => {
  await saveProfile(request, { name: "Ravi", timezone: "Asia/Kolkata", theme: "dark" });
  await page.goto("/camera?mode=add");
  await page.getByRole("button", { name: "Enter manually" }).click();
  const sheet = page.getByRole("dialog", { name: "Add an item" });
  await sheet.getByLabel("Name", { exact: true }).fill("Torch");
  await sheet.getByRole("button", { name: "New location" }).click();
  const place = sheet.getByLabel("New location name");
  await place.fill("Garage");
  await place.press("Enter");
  await expect(sheet).toBeVisible();
  await expect(place).toHaveCount(0);
  const items = await (await request.get("/api/v1/items")).json();
  expect(items.items).toHaveLength(0);
});
