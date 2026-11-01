// Final UX test, group 3 (D-149): the camera hub, drafts and the ownership check, as a tester found
// them with the camera blocked. Test data on the test stack, never gate evidence for the owner.

import { expect, test } from "@playwright/test";
import { makeItem, resetApp, saveProfile } from "./helpers";

test.use({ reducedMotion: "reduce" });

test.beforeEach(async ({ request }) => {
  await resetApp(request);
  await saveProfile(request, { name: "Ravi", timezone: "Asia/Kolkata", theme: "dark" });
});

test("an unknown typed ID says so with the camera off", async ({ page }) => {
  await page.goto("/camera?mode=scan");
  const id = page.getByLabel("Type the ID");
  await id.fill("ENDR-00000000");
  await id.press("Enter");
  await expect(page.getByText("No item with that ID.")).toBeVisible();
});

test("a missing draft offers the way back, not a useless Retry", async ({ page }) => {
  await page.goto("/add/does-not-exist");
  await expect(page.getByRole("link", { name: "Back to the review list" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Retry" })).toHaveCount(0);
});

test("the ownership check: a new item is not a duplicate, and a saving shows on its row", async ({
  page,
  request,
}) => {
  await makeItem(request, { name: "Bosch cordless drill" });
  await page.goto("/camera?mode=own");
  await page.getByLabel("Or type what it is").fill("Bosch cordless drill");
  await page.getByRole("button", { name: "Check", exact: true }).click();
  await page.getByRole("button", { name: "I didn't buy it" }).click();
  const sheet = page.getByRole("dialog", { name: "I didn't buy it" });
  await sheet.getByLabel(/price/i).fill("1500");
  await sheet.getByRole("button", { name: "Save" }).click();
  await expect(page.getByText("Saving recorded")).toBeVisible();
  await expect(page.getByRole("button", { name: "I didn't buy it" })).toHaveCount(0);

  await page.getByRole("button", { name: "Undo" }).click();
  await expect(page.getByRole("button", { name: "I didn't buy it" })).toBeVisible();

  await page.getByRole("button", { name: /None of these/ }).click();
  await page.getByRole("button", { name: /Add it to my inventory/ }).click();
  await expect(page.getByRole("dialog", { name: "Add an item" })).toBeVisible();
});
