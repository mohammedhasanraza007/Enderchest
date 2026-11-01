// Final UX test, group 4 (D-150): the task item picker by keyboard, and a dialog's shadow. Test data
// on the test stack, never gate evidence for the owner.

import { expect, test } from "@playwright/test";
import { makeItem, resetApp, saveProfile } from "./helpers";

test.use({ reducedMotion: "reduce" });

test.beforeEach(async ({ request }) => {
  await resetApp(request);
  await saveProfile(request, { name: "Ravi", timezone: "Asia/Kolkata", theme: "dark" });
});

test("Enter in the task item picker never saves a half-typed item", async ({ page, request }) => {
  await makeItem(request, { name: "Oat milk" });
  await makeItem(request, { name: "Oat bran" });
  await page.goto("/tasks");
  await page.getByRole("button", { name: "New task" }).first().click();
  const sheet = page.getByRole("dialog", { name: "New task" });
  await sheet.getByLabel("Title").fill("Check the date");
  const picker = sheet.getByLabel("Item (optional)");
  await picker.fill("oat");
  await expect(sheet.getByRole("button", { name: "Oat bran" })).toBeVisible();

  await picker.press("Enter");
  await expect(sheet).toBeVisible();

  await picker.press("ArrowDown");
  await expect(sheet.getByRole("button", { name: "Oat bran" })).toBeFocused();
  await page.keyboard.press("ArrowDown");
  await expect(sheet.getByRole("button", { name: "Oat milk" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(sheet.getByRole("button", { name: "Remove item" })).toBeVisible();
  await expect(sheet.getByText("Oat milk")).toBeVisible();
});

test("Enter picks the only match", async ({ page, request }) => {
  await makeItem(request, { name: "Oat milk" });
  await page.goto("/tasks");
  await page.getByRole("button", { name: "New task" }).first().click();
  const sheet = page.getByRole("dialog", { name: "New task" });
  const picker = sheet.getByLabel("Item (optional)");
  await picker.fill("oat");
  await expect(sheet.getByRole("button", { name: "Oat milk" })).toBeVisible();
  await picker.press("Enter");
  await expect(sheet.getByRole("button", { name: "Remove item" })).toBeVisible();
});

test("a dialog does not clip its panel's shadow", async ({ page, request }) => {
  await saveProfile(request, { name: "Ravi", timezone: "Asia/Kolkata", theme: "light" });
  await page.goto("/settings");
  const overflow = await page.evaluate(() => {
    const dialog = document.createElement("dialog");
    dialog.className = "overlay overlay--dialog";
    document.body.append(dialog);
    const value = getComputedStyle(dialog).overflow;
    dialog.remove();
    return value;
  });
  expect(overflow).toBe("visible");
});
