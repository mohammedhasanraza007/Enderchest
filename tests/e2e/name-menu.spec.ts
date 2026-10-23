// The name menu by keyboard alone (DESIGN.md 14, PAGES.md 1): Tab reaches the name pill, Enter
// opens the menu, Tab walks through it, Escape closes it and gives focus back to the pill.

import { expect, test, type Locator, type Page } from "@playwright/test";
import { resetApp, saveProfile } from "./helpers";

test.beforeEach(async ({ request }) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata", theme: "dark" });
});

const isFocused = (target: Locator) => target.evaluate((el) => el === document.activeElement);

/** Press Tab until `target` has focus; fail if it is not reached in 20 presses. */
async function tabTo(page: Page, target: Locator): Promise<void> {
  for (let i = 0; i < 20; i += 1) {
    await page.keyboard.press("Tab");
    if (await isFocused(target)) return;
  }
  throw new Error("Tab never reached the element");
}

test("the name menu works by keyboard alone", async ({ page }) => {
  await page.goto("/nothing-here"); // the not-found page, so following Settings is a real move
  const pill = page.getByRole("button", { name: "Mohammed" });
  const panel = page.locator(".name-menu__panel");

  await tabTo(page, pill);
  await page.keyboard.press("Enter");
  await expect(pill).toHaveAttribute("aria-expanded", "true");

  await page.keyboard.press("Tab");
  expect(await isFocused(panel.getByRole("link", { name: "Settings" }))).toBe(true);
  await tabTo(page, panel.getByRole("radio", { name: "Light" }));
  await page.keyboard.press("Space");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");

  await page.keyboard.press("Escape");
  await expect(pill).toHaveAttribute("aria-expanded", "false");
  await expect(panel).toHaveCount(0);
  expect(await isFocused(pill)).toBe(true);

  await page.keyboard.press("Enter");
  await page.keyboard.press("Tab");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/settings$/);
  await expect(panel).toHaveCount(0);
});
