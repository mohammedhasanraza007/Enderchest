// Phase 6: "Do I own this?" (P-13) and Savings (P-14). Items and photos are test data on the test
// stack: regression checks, never the gate-1 measurement on the owner's photos (D-056).

import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { jpegBytes, makeItem, post, resetApp, saveProfile } from "./helpers";

test.use({ reducedMotion: "reduce" });

async function start(page: Page, request: Parameters<typeof resetApp>[0]) {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata" });
  const garage = await post<{ id: number }>(request, "/api/v1/locations", { name: "Garage" });
  const spanner = await makeItem(request, {
    name: "13 mm spanner",
    location_id: garage.id,
    price_paise: 34900,
    attributes: { size: "13 mm" },
  });
  await makeItem(request, { name: "14 mm spanner", attributes: { size: "14 mm" } });
  return spanner;
}

async function checkWords(page: Page, words: string) {
  await page.goto("/camera?mode=own");
  await page.getByLabel("Or type what it is").fill(words);
  await page.getByRole("button", { name: "Check", exact: true }).click();
}

test("words find the right size, never say certain, and Not the same hides it", async ({
  page,
  request,
}) => {
  const spanner = await start(page, request);
  await page.goto("/camera?mode=own");
  await expect(page.getByRole("radio", { name: "Do I own this?" })).toHaveAttribute(
    "aria-checked",
    "true",
  );
  await expect(page.getByText(/Check before you order/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Check", exact: true })).toBeDisabled();
  await checkWords(page, "13 mm spanner");
  const results = page.locator(".own-results");
  await expect(results.getByRole("heading")).toHaveText("One item may be the same");
  await expect(results.getByRole("link", { name: "13 mm spanner" })).toHaveAttribute(
    "href",
    `/items/${spanner}`,
  );
  await expect(results.getByText("Medium")).toBeVisible();
  await expect(results.getByText("Same size · Same name")).toBeVisible();
  await expect(results.getByText("Garage · quantity 1")).toBeVisible();
  const body = (await page.locator("body").innerText()).toLowerCase();
  for (const word of ["certain", "you own this", "100%"]) expect(body).not.toContain(word);
  await results.getByRole("button", { name: "Not the same" }).click();
  await expect(results.getByRole("heading")).toHaveText("Nothing in your inventory looks like this");
});

test("I didn't buy it needs a typed price, records it, and Undo takes it back", async ({
  page,
  request,
}) => {
  await start(page, request);
  await checkWords(page, "13 mm spanner");
  await page.getByRole("button", { name: "I didn't buy it" }).click();
  const sheet = page.getByRole("dialog", { name: "I didn't buy it" });
  const price = sheet.getByLabel("Price saved (₹)");
  await expect(price).toHaveValue("349"); // pre-filled from the item's price
  await price.fill("");
  await expect(sheet.getByRole("button", { name: "Save" })).toBeDisabled();
  const before = await (await request.get("/api/v1/savings")).json();
  expect(before.total_paise).toBe(0); // nothing is counted before the tap
  await price.fill("1,240");
  await sheet.getByRole("button", { name: "Save" }).click();
  await expect(page.getByText("₹1,240 saved on 13 mm spanner.")).toBeVisible();
  expect((await (await request.get("/api/v1/savings")).json()).total_paise).toBe(124000);
  await page.getByRole("button", { name: "Undo" }).click();
  await expect.poll(async () => (await (await request.get("/api/v1/savings")).json()).total_paise).toBe(0);
});

test("None of these: words open the new-item form, a photo makes a draft", async ({
  page,
  request,
}) => {
  await start(page, request);
  await checkWords(page, "cordless drill");
  await page.getByRole("button", { name: "None of these" }).click();
  await page.getByRole("button", { name: "Add it to my inventory" }).click();
  const form = page.getByRole("dialog");
  await expect(form.getByLabel("Name")).toHaveValue("cordless drill");
  await form.getByRole("button", { name: "Close" }).click();
  expect((await (await request.get("/api/v1/items")).json()).total).toBe(2); // nothing saved

  await page.goto("/camera?mode=own");
  await page.locator('input[type="file"]').setInputFiles({
    name: "drill.jpg",
    mimeType: "image/jpeg",
    buffer: await jpegBytes(page, "#2f6f4f"),
  });
  await expect(page.getByRole("img", { name: "The photo to check" })).toBeVisible();
  await page.getByRole("button", { name: "Check", exact: true }).click();
  await page.getByRole("button", { name: "None of these" }).click({ timeout: 60_000 });
  await page.getByRole("button", { name: "I'll buy it" }).click();
  await expect(page.locator(".own-results")).toHaveCount(0);
  await expect(page.getByRole("img", { name: "The photo to check" })).toHaveCount(0);
});

test("Savings: totals equal the list, Remove asks, and Undo brings it back", async ({
  page,
  request,
}) => {
  const spanner = await start(page, request);
  await page.goto("/savings");
  await expect(page.getByText(/Nothing saved yet/)).toBeVisible();
  await expect(page.locator(".savings-total__amount")).toHaveText("₹0");
  await post(request, "/api/v1/savings", { item_public_id: spanner, price_paise: 124000 });
  await post(request, "/api/v1/savings", { item_name: "Phone case", price_paise: 49950 });
  await page.reload();
  await expect(page.locator(".savings-total__amount")).toHaveText("₹1,739.50");
  await page.getByRole("radio", { name: "All time" }).click();
  await expect(page.locator(".savings-total__amount")).toHaveText("₹1,739.50");
  await expect(page.locator(".savings-price")).toHaveText(["₹499.50", "₹1,240"]);
  await expect(page.getByRole("link", { name: "13 mm spanner" })).toHaveAttribute(
    "href",
    `/items/${spanner}`,
  );
  await page.getByRole("button", { name: "Remove" }).first().click();
  const dialog = page.getByRole("dialog", { name: "Remove this saving?" });
  await dialog.getByRole("button", { name: "Keep it" }).click();
  await expect(page.locator(".savings-price")).toHaveCount(2);
  await page.getByRole("button", { name: "Remove" }).first().click();
  await dialog.getByRole("button", { name: "Remove" }).click();
  await expect(page.locator(".savings-total__amount")).toHaveText("₹1,240");
  await page.getByRole("button", { name: "Undo" }).click();
  await expect(page.locator(".savings-total__amount")).toHaveText("₹1,739.50");
});

test("the dashboard road shows the savings pill only on the day of a saving", async ({
  page,
  request,
}) => {
  await start(page, request);
  await page.goto("/");
  await expect(page.locator(".road__pill")).toHaveCount(0);
  await post(request, "/api/v1/savings", { item_name: "Torch", price_paise: 124000 });
  await page.reload();
  const pill = page.locator(".road__pill");
  await expect(pill).toHaveText("₹1,240 saved");
  await pill.click();
  await expect(page).toHaveURL(/\/savings$/);
  await expect(page.getByRole("link", { name: "Savings" })).toHaveAttribute("aria-current", "page");
});
