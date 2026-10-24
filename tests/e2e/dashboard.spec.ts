// Phase 5: the dashboard (PAGES.md P-12, DESIGN.md 6.7 to 6.11) on the storyboard fixtures and on
// an empty inventory; its loading and error states; the ring sheet, the road's day and the card's
// actions; the Tasks page's 30-day road (D-103). The test clock is put back after each test.

import { expect, test } from "@playwright/test";
import type { APIRequestContext, Page } from "@playwright/test";
import { loadFixture, post, resetApp, saveProfile } from "./helpers";

// The storyboard's evening: 16 Oct 2026, 19:30 in Kolkata (DESIGN.md 20).
const EVENING = "2026-10-16T19:30:00+05:30";

async function story(request: APIRequestContext, stage: 1 | 2 | 3): Promise<void> {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata", theme: "dark" });
  await post(request, "/api/v1/test/clock", { now: EVENING });
  await loadFixture(request, `storyboard-${stage}`);
}

async function settled(page: Page): Promise<void> {
  await page.waitForLoadState("networkidle");
  await expect(page.locator('[aria-busy="true"]')).toHaveCount(0);
}

test.afterEach(async ({ request }) => {
  await post(request, "/api/v1/test/clock", { now: new Date().toISOString() });
});

test("frame 1: greeting, score, count, card rows and the truck on the 18th", async ({
  page,
  request,
}) => {
  await story(request, 1);
  await page.goto("/");
  await settled(page);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Good evening,Mohammed");
  await expect(page.getByText("3 things need you today")).toBeVisible();
  await expect(page.locator(".rings__score")).toHaveText("82");
  await expect(page.locator(".rings__count")).toHaveText("• 142 items");
  await expect(
    page.getByRole("button", { name: /^Inventory health 82 out of 100/ }),
  ).toHaveAccessibleName(
    "Inventory health 82 out of 100. Documented 79, Located 87, Fresh 96, On time 56. Show what counts",
  );
  const card = page.locator(".attention-card");
  await expect(card.locator(".reminder__text")).toHaveText([
    "Oat Milk (expires today)",
    "Baby Spinach (inspect)",
    "Greek Yogurt (2 days left)",
  ]);
  await expect(card.getByRole("link", { name: /View all/ })).toHaveCount(0);
  // The truck parks at the next job; its day says what is there (D-110).
  await expect(page.locator(".road__label")).toHaveText("Pantry Refill +1");
  const truck = await page.locator(".road__truck").boundingBox();
  const tick = await page.locator(".road__tick").nth(2).boundingBox();
  expect(Math.abs(truck!.x + truck!.width * 0.2 - (tick!.x + tick!.width / 2))).toBeLessThan(2);
  await expect(page.locator(".road__tick--today .road__day")).toHaveText("16 Oct");
  await expect(page.locator(".road__day")).toHaveCount(14);
});

test("frames 2 and 3 move the score, the card and the truck", async ({ page, request }) => {
  await story(request, 2);
  await page.goto("/");
  await settled(page);
  await expect(page.locator(".rings__score")).toHaveText("86");
  await expect(page.locator(".road__label")).toHaveText("Clean PC");
  await story(request, 3);
  await page.reload();
  await settled(page);
  await expect(page.locator(".rings__score")).toHaveText("91");
  await expect(page.locator(".rings__count")).toHaveText("• 141 items");
  await expect(page.locator(".attention-card .reminder__text")).toHaveText([
    "Baby Spinach (inspect)",
  ]);
  await expect(page.locator(".road__label")).toHaveText("Blade check");
});

test("using an item from the card takes its row out, and Undo brings it back", async ({
  page,
  request,
}) => {
  await story(request, 1);
  await page.goto("/");
  await settled(page);
  const card = page.locator(".attention-card");
  await card
    .locator(".reminder")
    .filter({ hasText: "Oat Milk" })
    .getByRole("button", { name: "Use it" })
    .click();
  await expect(card.locator(".reminder").filter({ hasText: "Oat Milk" })).toHaveCount(0);
  await expect(page.locator(".rings__count")).toHaveText("• 141 items");
  await expect(page.getByText("2 things need you today")).toBeVisible();
  await page.locator(".toast").getByRole("button", { name: "Undo" }).click();
  await expect(card.locator(".reminder").filter({ hasText: "Oat Milk" })).toHaveCount(1);
  await expect(page.locator(".rings__count")).toHaveText("• 142 items");
});

test("the rings open a sheet whose lists match the ring's numbers", async ({ page, request }) => {
  await story(request, 1);
  await page.goto("/");
  await settled(page);
  await page.getByRole("button", { name: /^Inventory health/ }).click();
  const sheet = page.getByRole("dialog", { name: "What counts" });
  await expect(sheet.getByText("112 of 142 count: 79")).toBeVisible();
  await expect(sheet.getByRole("heading", { name: "Not counted (30)" })).toBeVisible();
  await expect(sheet.locator(".ring-sheet__group").first().locator("li")).toHaveCount(30);
  await sheet.getByRole("radio", { name: "On time 56" }).click();
  await expect(sheet.getByText("5 of 9 count: 56")).toBeVisible();
  await expect(sheet.locator(".ring-sheet__group").first().locator(".ring-sheet__note")).toHaveText(
    ["4 days overdue", "3 days overdue", "2 days overdue", "1 day overdue"],
  );
  await sheet.getByRole("link", { name: "Clean the fridge" }).click();
  await expect(page).toHaveURL(/\/tasks$/);
});

test("a day on the road opens what is on it", async ({ page, request }) => {
  await story(request, 1);
  await page.goto("/");
  await settled(page);
  const day = page.getByRole("button", {
    name: "18 Oct: Pantry Refill is due, Greek Yogurt expires. Open the day",
  });
  await day.focus();
  await expect(day.locator(".road__tip")).toHaveCSS("opacity", "1");
  await day.click();
  const dialog = page.getByRole("dialog", { name: "18 Oct" });
  await expect(dialog.getByRole("link")).toHaveText([
    "Pantry Refill is due",
    "Greek Yogurt expires",
  ]);
  await dialog.getByRole("link", { name: "Greek Yogurt expires" }).click();
  await expect(page).toHaveURL(/\/items\/ENDR-/);
});

test("an empty inventory shows the real empty dashboard", async ({ page, request }) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata" });
  await page.goto("/");
  await settled(page);
  await expect(page.locator(".rings__score")).toHaveText("—");
  await expect(page.locator(".rings__arc")).toHaveCount(0);
  await expect(page.getByText("Add items to see your overview")).toBeVisible();
  await expect(page.getByText("Nothing needs attention.")).toBeVisible();
  await expect(page.getByText("No tasks or expiries in the next 14 days.")).toBeVisible();
  await page.getByRole("link", { name: "Add your first item" }).click();
  await expect(page).toHaveURL(/\/camera\?mode=add$/);
});

test("more than three reminders: two rows and View all", async ({ page, request }) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata" });
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(new Date());
  for (const title of ["Water plants", "Clean PC", "Descale kettle", "Oil hinges", "Sweep"]) {
    await post(request, "/api/v1/tasks", { title, first_due: today });
  }
  await page.goto("/");
  await settled(page);
  await expect(page.locator(".attention-card .reminder")).toHaveCount(2);
  await page.getByRole("link", { name: "View all 5" }).click();
  await expect(page).toHaveURL(/\/notifications$/);
  // No items but tasks: the score is left empty, the On time ring still counts the tasks.
  await page.goto("/");
  await expect(page.locator(".rings__score")).toHaveText("—");
});

test("loading shows the page's shape; a failed load says so and retries", async ({
  page,
  request,
}) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata" });
  let release: () => void = () => {};
  const held = new Promise<void>((resolve) => (release = resolve));
  await page.route("**/api/v1/dashboard", async (route) => {
    await held;
    await route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ error: { code: "internal", message: "Something went wrong." } }),
    });
  });
  await page.goto("/");
  await expect(page.locator('.dashboard[aria-busy="true"] .skeleton').first()).toBeVisible();
  release();
  await expect(page.getByRole("heading", { name: "The dashboard did not load" })).toBeVisible({
    timeout: 20_000,
  });
  await page.unroute("**/api/v1/dashboard");
  await page.getByRole("button", { name: "Retry" }).click();
  await expect(page.locator(".rings__score")).toHaveText("—");
});

test("the Tasks page has the same road over 30 days", async ({ page, request }) => {
  await story(request, 1);
  await page.goto("/tasks");
  await settled(page);
  await expect(page.getByRole("heading", { name: "Next 30 days" })).toBeVisible();
  await expect(page.locator(".road__tick")).toHaveCount(30);
  await expect(page.locator(".road__day").nth(1)).toHaveText(""); // every other day on 30 days
  await expect(page.locator(".road__label")).toHaveText("Pantry Refill +1");
  await expect(page.getByRole("button", { name: /^26 Oct: Blade check is due/ })).toHaveCount(1);
});
