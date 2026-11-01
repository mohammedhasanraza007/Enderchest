// Final UX test, group 2 (D-146): nothing cut off at 1024 px in the Inventory filters or in the item
// form's attribute rows. Test data on the test stack, never gate evidence for the owner.

import { expect, test } from "@playwright/test";
import { resetApp, saveProfile } from "./helpers";

test.use({ reducedMotion: "reduce", viewport: { width: 1024, height: 768 } });

test.beforeEach(async ({ request }) => {
  await resetApp(request);
  await saveProfile(request, { name: "Ravi", timezone: "Asia/Kolkata", theme: "dark" });
});

test("the Sort select shows its whole label", async ({ page }) => {
  await page.goto("/inventory");
  const fits = await page.getByLabel("Sort").evaluate((element) => {
    const select = element as HTMLSelectElement;
    const style = getComputedStyle(select);
    const canvas = document.createElement("canvas").getContext("2d")!;
    canvas.font = `${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
    const room = select.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
    return canvas.measureText("Newest first").width <= room;
  });
  expect(fits).toBe(true);
});

test("an attribute's name and a long value both fit their boxes", async ({ page }) => {
  await page.goto("/camera?mode=add");
  await page.getByRole("button", { name: "Enter manually" }).click();
  const sheet = page.getByRole("dialog", { name: "Add an item" });
  await sheet.getByRole("button", { name: /Other/ }).click();
  const row = sheet.locator(".attribute-row").last();
  const name = row.getByLabel("Name");
  const value = row.getByLabel("Value");
  await name.fill("Capacity");
  await value.fill("GSR 12V-15, GSR 12V-35");
  for (const input of [name, value]) {
    const fits = await input.evaluate((box) => box.scrollWidth <= box.clientWidth);
    expect(fits).toBe(true);
  }
});
