// Screenshots of the Phase 6 screens for review against the reference (D-097): the "Do I own
// this?" mode with results and the price sheet, Savings with entries and empty, and the
// dashboard road with its savings pill; 1280 px dark and light, 1024 px for the dense check
// page. Test data on the test stack; the owner approves the look (BLOCKED).

import { expect, test } from "@playwright/test";
import { jpegBytes, makeItem, post, resetApp, saveProfile } from "./helpers";

const SHOTS = "/test-results/shots-phase-6";
test.use({ reducedMotion: "reduce" });
test.setTimeout(180_000);

for (const theme of ["dark", "light"] as const) {
  test(`ownership screens (${theme})`, async ({ page, request }) => {
    await resetApp(request);
    await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata", theme });
    const tools = await post<{ id: number }>(request, "/api/v1/categories", { name: "Tools" });
    const garage = await post<{ id: number }>(request, "/api/v1/locations", { name: "Garage" });
    const shelf = await post<{ id: number }>(request, "/api/v1/locations", {
      name: "Shelf 2",
      parent_id: garage.id,
    });
    const spanner = await makeItem(request, {
      name: "13 mm spanner",
      category_id: tools.id,
      location_id: shelf.id,
      price_paise: 34900,
      attributes: { size: "13 mm", brand: "Taparia" },
    });
    await makeItem(request, {
      name: "13 mm ring spanner",
      category_id: tools.id,
      location_id: garage.id,
      attributes: { size: "13 mm" },
    });
    await makeItem(request, { name: "Spanner set", category_id: tools.id, quantity: 2 });
    await page.goto("/settings");
    const photo = await jpegBytes(page, "#7a6a58");
    await request.post(`/api/v1/items/${spanner}/photos`, {
      headers: { "X-Enderchest": "1" },
      multipart: { image: { name: "a.jpg", mimeType: "image/jpeg", buffer: photo } },
    });

    for (const width of [1280, 1024]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/camera?mode=own");
      await page.getByLabel("Or type what it is").fill("Taparia 13 mm spanner");
      await page.getByRole("button", { name: "Check", exact: true }).click();
      await expect(page.locator(".own-results .row-list__row").first()).toBeVisible();
      await page.screenshot({ path: `${SHOTS}/own-results-${theme}-${width}.png`, fullPage: true });
    }
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.getByRole("button", { name: "I didn't buy it" }).first().click();
    await expect(page.getByRole("dialog", { name: "I didn't buy it" })).toBeVisible();
    await page.screenshot({ path: `${SHOTS}/saving-sheet-${theme}-1280.png` });

    await page.goto("/savings");
    await expect(page.getByText(/Nothing saved yet/)).toBeVisible();
    await page.screenshot({ path: `${SHOTS}/savings-empty-${theme}-1280.png` });
    await post(request, "/api/v1/savings", { item_public_id: spanner, price_paise: 124000 });
    await post(request, "/api/v1/savings", {
      item_name: "Phone case",
      price_paise: 49900,
      note: "kept the old one",
    });
    await page.reload();
    await expect(page.locator(".savings-price")).toHaveCount(2);
    await page.screenshot({ path: `${SHOTS}/savings-${theme}-1280.png`, fullPage: true });

    await post(request, "/api/v1/tasks", {
      title: "Pantry Refill",
      first_due: new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(
        new Date(Date.now() + 5 * 86_400_000),
      ),
    });
    await page.goto("/");
    await expect(page.locator(".road__pill")).toBeVisible();
    await page.screenshot({ path: `${SHOTS}/dashboard-pill-${theme}-1280.png` });
  });
}
