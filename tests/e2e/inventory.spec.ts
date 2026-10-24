// Phase 2 in the browser: add, find, edit, photos, delete and undo, Trash, labels, settings
// rules, and the general message for a problem on a field a form does not show (F-024). Test
// data only (D-056): these are regression tests, never the owner's acceptance.

import { writeFileSync } from "node:fs";
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { jpegBytes, loadFixture, makeItem, post, resetApp, saveProfile } from "./helpers";

const WRITE = { "X-Enderchest": "1" };

test.beforeEach(async ({ request }) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata" });
});

async function item(page: Page, publicId: string) {
  return (await (await page.request.get(`/api/v1/items/${publicId}`)).json()) as {
    deleted_at: string | null;
    photos: Array<{ id: string; is_primary: boolean }>;
    label: { printed_at: string | null };
    category: { name: string } | null;
  };
}

test("an item added by hand shows in Inventory with its category, location and details", async ({
  page,
}) => {
  await page.goto("/inventory");
  await expect(page.getByText("No items yet.")).toBeVisible();
  await page.getByRole("link", { name: "＋ Add item" }).click();
  await expect(page).toHaveURL(/\/camera\?mode=add$/);
  await page.getByRole("button", { name: "Enter manually" }).click();

  const sheet = page.getByRole("dialog", { name: "Add an item" });
  await sheet.getByLabel("Name", { exact: true }).fill("Spirit level");
  await sheet.getByRole("button", { name: "New category" }).click();
  await sheet.getByLabel("New category name").fill("Tools");
  await sheet.getByRole("button", { name: "Add", exact: true }).click();
  await expect(sheet.getByLabel("Category", { exact: true })).not.toHaveValue("");
  await sheet.getByRole("button", { name: "New location" }).click();
  await sheet.getByLabel("New location name").fill("Garage");
  await sheet.getByRole("button", { name: "Add", exact: true }).click();
  await expect(sheet.getByLabel("Location", { exact: true })).not.toHaveValue("");
  await sheet.getByRole("radio", { name: "Has date" }).click();
  await sheet.getByLabel("Expiry date").fill("2030-01-31");
  await sheet.getByLabel("Price of one (₹, optional)").fill("1240.50");
  await sheet.getByRole("button", { name: "+ size" }).click();
  await sheet.getByLabel("Value").fill("8, 10, 12");
  await sheet.getByRole("button", { name: "Save item" }).click();
  await expect(page.getByText("Item saved.")).toBeVisible();

  await page.goto("/inventory");
  const tile = page.getByRole("link", { name: /Spirit level/ });
  await expect(tile).toContainText("Tools · Garage");
  await tile.click();
  await expect(page.getByRole("heading", { name: "Spirit level" })).toBeVisible();
  await expect(page.getByText("₹1,240.50")).toBeVisible();
  await expect(page.getByText("8, 10, 12")).toBeVisible();
  await expect(page.getByText("31 Jan 2030")).toBeVisible();
});

test("Save stays disabled with the reason while the form is wrong; closing with edits asks", async ({
  page,
}) => {
  await page.goto("/camera?mode=add");
  await page.getByRole("button", { name: "Enter manually" }).click();
  const sheet = page.getByRole("dialog", { name: "Add an item" });
  await expect(sheet.getByRole("button", { name: "Save item" })).toBeDisabled();
  await expect(sheet.getByText("Enter a name of 1 to 120 characters.").first()).toBeVisible();
  await sheet.getByLabel("Name", { exact: true }).fill("Tape");
  await sheet.getByLabel("Quantity").fill("-2");
  await expect(sheet.getByText("Enter a whole number, 0 or more.").first()).toBeVisible();
  await sheet.getByRole("button", { name: "Cancel" }).click();
  const ask = page.getByRole("dialog", { name: "Discard your changes?" });
  await expect(ask).toBeVisible();
  await ask.getByRole("button", { name: "Keep editing" }).click();
  await expect(sheet.getByLabel("Name", { exact: true })).toHaveValue("Tape");
});

test("a server problem on a field the form does not show becomes a general message (F-024)", async ({
  page,
}) => {
  const refusal = {
    error: {
      code: "validation_error",
      message: "Some values are not valid.",
      details: { problems: [{ field: "mystery_field", problem: "The server found a hidden problem." }] },
    },
  };
  await page.route("**/api/v1/items", (route) =>
    route.request().method() === "POST" ? route.fulfill({ status: 422, json: refusal }) : route.continue(),
  );
  await page.route("**/api/v1/categories", (route) =>
    route.request().method() === "POST" ? route.fulfill({ status: 422, json: refusal }) : route.continue(),
  );
  await page.goto("/camera?mode=add");
  await page.getByRole("button", { name: "Enter manually" }).click();
  const sheet = page.getByRole("dialog", { name: "Add an item" });
  await sheet.getByLabel("Name", { exact: true }).fill("Glue");
  await sheet.getByRole("button", { name: "Save item" }).click();
  await expect(sheet.getByRole("alert")).toHaveText("The server found a hidden problem.");

  await page.goto("/settings");
  await page.getByLabel("New category").fill("Paint");
  await page.getByRole("button", { name: "Add", exact: true }).first().click();
  await expect(page.getByText("The server found a hidden problem.")).toBeVisible();
});

test("search and filters live in the URL, Back restores them, and 1,000 items stay light", async ({
  page,
  request,
}) => {
  await loadFixture(request, "items-1000");
  const total = ((await (await request.get("/api/v1/items")).json()) as { total: number }).total;
  await page.goto("/inventory");
  await expect(page.getByText(`${total} items`)).toBeVisible();
  // Virtualised: only the rows near the screen exist in the page.
  expect(await page.locator(".item-tile").count()).toBeLessThan(80);

  // Scroll to the end: every page loads, and frames keep coming (smoothness, recorded).
  const frames = await page.evaluate(async () => {
    const gaps: number[] = [];
    let last = performance.now();
    for (let step = 0; step < 240; step++) {
      window.scrollBy(0, 400);
      await new Promise((resolve) => requestAnimationFrame(resolve));
      const now = performance.now();
      gaps.push(now - last);
      last = now;
    }
    window.scrollTo(0, document.body.scrollHeight);
    return { worst: Math.max(...gaps), average: gaps.reduce((a, b) => a + b, 0) / gaps.length };
  });
  writeFileSync("/test-results/inventory-scroll.json", JSON.stringify({ total, frames }, null, 2));
  expect(frames.worst).toBeLessThan(250);
  await expect(page.locator(".item-tile").last()).toBeVisible();

  const search = page.getByRole("searchbox", { name: "Search items" });
  await search.fill("spare");
  await expect(page).toHaveURL(/q=spare/);
  const spare = ((await (await request.get("/api/v1/items?q=spare")).json()) as { total: number })
    .total;
  await expect(page.getByText(`${spare} items`)).toBeVisible();
  await page.getByLabel("Category").selectOption({ label: "Tools" });
  await expect(page).toHaveURL(/category=\d+/);
  const query = new URL(page.url()).search;
  const narrowed = (
    (await (
      await request.get(`/api/v1/items?q=spare&category_id=${new URLSearchParams(query).get("category")}`)
    ).json()) as { total: number }
  ).total;
  await expect(page.getByText(narrowed === 1 ? "1 item" : `${narrowed} items`)).toBeVisible();

  await page.goto("/settings");
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`${query.replace("?", "\\?")}$`));
  await expect(search).toHaveValue("spare");

  await search.fill("no such thing at all");
  await expect(page.getByText("Nothing matches these filters.")).toBeVisible();
  await page.getByRole("button", { name: "Clear filters" }).click();
  await expect(page.getByText(`${total} items`)).toBeVisible();
  await expect(search).toHaveValue("");
});

test("photos on the item page: add, make main, hide; the file stays on disk", async ({
  page,
  request,
}) => {
  const id = await makeItem(request, { name: "Drill" });
  await page.goto(`/items/${id}`);
  const picker = page.locator('input[type="file"]');
  await picker.setInputFiles({ name: "a.jpg", mimeType: "image/jpeg", buffer: await jpegBytes(page) });
  await expect(page.getByText("Photo added.")).toBeVisible();
  await picker.setInputFiles({
    name: "b.jpg",
    mimeType: "image/jpeg",
    buffer: await jpegBytes(page, "#2f6b4f"),
  });
  await expect(page.getByRole("button", { name: /^Photo 2/ })).toBeVisible();
  await page.getByRole("button", { name: /^Photo 2/ }).click();
  await page.getByRole("button", { name: "Make main photo" }).click();
  await expect(page.locator(".photo-frame__main-label")).toHaveText("Main photo");
  const before = await item(page, id);
  const main = before.photos.find((photo) => photo.is_primary)!;
  expect(before.photos[1]!.id).toBe(main.id);

  await page.getByRole("button", { name: "Hide photo" }).click();
  await expect(page.getByText("Photo hidden. The file is kept.")).toBeVisible();
  const after = await item(page, id);
  expect(after.photos.map((photo) => photo.id)).toEqual([before.photos[0]!.id]);
  // The hidden photo's file is still served: hiding never deletes a file (gate 3).
  expect((await request.get(`/api/v1/photos/${main.id}/file`)).status()).toBe(200);
});

test("delete from the item page, then Undo brings it back", async ({ page, request }) => {
  const id = await makeItem(request, { name: "Torch" });
  await page.goto(`/items/${id}`);
  await page.getByRole("button", { name: "More item actions" }).click();
  await page.getByRole("button", { name: "Delete" }).click();
  await expect(page).toHaveURL(/\/inventory$/);
  await expect(page.getByText("No items yet.")).toBeVisible();
  await page.getByRole("button", { name: "Undo" }).click();
  await expect(page.getByRole("link", { name: /Torch/ })).toBeVisible();
  expect((await item(page, id)).deleted_at).toBeNull();
});

test("select mode deletes several items with one Undo, and moves them", async ({
  page,
  request,
}) => {
  const garage = await post<{ id: number }>(request, "/api/v1/locations", { name: "Garage" });
  const ids = [await makeItem(request, { name: "Alpha" }), await makeItem(request, { name: "Beta" })];
  await page.goto("/inventory");
  await page.getByRole("button", { name: "Print labels" }).click();
  await page.locator("label.item-tile", { hasText: "Alpha" }).click();
  await page.locator("label.item-tile", { hasText: "Beta" }).click();
  await page.getByRole("button", { name: "Move to location" }).click();
  const dialog = page.getByRole("dialog", { name: "Move to location" });
  await dialog.getByLabel("Location").selectOption({ label: "Garage" });
  await dialog.getByRole("button", { name: "Move 2 items" }).click();
  await expect(page.getByText("2 items moved.")).toBeVisible();
  for (const id of ids) {
    const body = (await (await request.get(`/api/v1/items/${id}`)).json()) as {
      location: { id: number };
    };
    expect(body.location.id).toBe(garage.id);
  }
  await page.locator("label.item-tile", { hasText: "Alpha" }).click();
  await page.locator("label.item-tile", { hasText: "Beta" }).click();
  await page.locator(".selection-bar").getByRole("button", { name: "Delete" }).click();
  await expect(page.getByText("2 items moved to Trash.")).toBeVisible();
  await page.getByRole("button", { name: "Undo" }).click();
  await expect(page.getByText("2 items", { exact: true })).toBeVisible();
});

test("Trash: restore, then permanent delete after a fresh backup", async ({ page, request }) => {
  const keep = await makeItem(request, { name: "Keeper" });
  const gone = await makeItem(request, { name: "Leaver" });
  for (const id of [keep, gone]) await request.delete(`/api/v1/items/${id}`, { headers: WRITE });

  await page.goto("/trash");
  const keeper = page.locator(".row-list__row", { hasText: "Keeper" });
  await keeper.getByRole("button", { name: "Restore" }).click();
  await expect(page.getByText("Keeper restored.")).toBeVisible();

  const leaver = page.locator(".row-list__row", { hasText: "Leaver" });
  await leaver.getByRole("button", { name: "Delete permanently" }).click();
  const dialog = page.getByRole("dialog", { name: "Delete permanently?" });
  await expect(dialog.getByText(/Older backups still/)).toBeVisible();
  await dialog.getByLabel("Type DELETE to confirm").fill("DELETE");
  await expect(dialog.getByRole("button", { name: "Delete permanently" })).toBeDisabled();
  await dialog.getByRole("button", { name: "Back up now" }).click();
  await expect(dialog.getByRole("button", { name: "Delete permanently" })).toBeEnabled();
  await dialog.getByRole("button", { name: "Delete permanently" }).click();
  await expect(page.getByText("Leaver was deleted permanently.")).toBeVisible();
  await expect(page.getByText("Trash is empty.")).toBeVisible();
  expect((await request.get(`/api/v1/items/${gone}`)).status()).toBe(404);
  expect((await item(page, keep)).deleted_at).toBeNull();
});

test("labels render at their physical sizes, print, and are marked printed only on Yes", async ({
  page,
  request,
}) => {
  const ids = [await makeItem(request, { name: "Drill" }), await makeItem(request, { name: "Saw" })];
  const skipped = await makeItem(request, { name: "Milk", no_label_needed: true });
  await page.goto(`/labels?ids=${[...ids, skipped].join(",")}`);
  await expect(page.getByText('Milk: marked "I don\'t need a printed label".')).toBeVisible();

  const mm = 96 / 25.4; // CSS pixels per millimetre
  const sheet = await page.locator(".print-sheet--a4").boundingBox();
  const label = await page.locator(".print-label").first().boundingBox();
  const qr = await page.locator(".print-label__qr").first().boundingBox();
  expect(Math.abs(sheet!.width - 210 * mm)).toBeLessThan(2);
  expect(Math.abs(sheet!.height - 297 * mm)).toBeLessThan(2);
  expect(Math.abs(label!.width - 63.5 * mm)).toBeLessThan(2);
  expect(Math.abs(label!.height - 38.1 * mm)).toBeLessThan(2);
  expect(qr!.width).toBeGreaterThanOrEqual(25 * mm - 0.5);

  await page.getByRole("radio", { name: "Single label (50 × 30 mm)" }).click();
  const single = await page.locator(".print-sheet--single").first().boundingBox();
  const singleQr = await page.locator(".print-label__qr").first().boundingBox();
  expect(Math.abs(single!.width - 50 * mm)).toBeLessThan(2);
  expect(Math.abs(single!.height - 30 * mm)).toBeLessThan(2);
  expect(singleQr!.width).toBeGreaterThanOrEqual(25 * mm - 0.5);

  await page.emulateMedia({ media: "print" });
  await expect(page.locator(".nav")).toBeHidden();
  await expect(page.locator(".print-sheet").first()).toBeVisible();
  await page.screenshot({ path: "/test-results/labels-print-preview.png", fullPage: true });
  await page.emulateMedia({ media: "screen" });

  await page.getByRole("button", { name: "Print" }).click();
  await page.getByRole("button", { name: "No" }).click();
  expect((await item(page, ids[0]!)).label.printed_at).toBeNull();
  await page.getByRole("button", { name: "Print" }).click();
  await page.getByRole("button", { name: "Yes, mark as printed" }).click();
  await expect(page.getByText("2 labels marked as printed.")).toBeVisible();
  expect((await item(page, ids[0]!)).label.printed_at).not.toBeNull();
  expect((await item(page, skipped)).label.printed_at).toBeNull();
});

test("categories: a delete in use asks where the items go; locations refuse a cycle", async ({
  page,
  request,
}) => {
  const tools = await post<{ id: number }>(request, "/api/v1/categories", { name: "Tools" });
  await post(request, "/api/v1/categories", { name: "Other" });
  const id = await makeItem(request, { name: "Hammer", category_id: tools.id });
  const garage = await post<{ id: number }>(request, "/api/v1/locations", { name: "Garage" });
  await post(request, "/api/v1/locations", { name: "Shelf", parent_id: garage.id });

  await page.goto("/settings");
  await page.locator(".row-list__row", { hasText: "Tools" }).getByRole("button", { name: "Delete" }).click();
  const dialog = page.getByRole("dialog", { name: "Delete Tools" });
  await expect(dialog.getByText("1 item uses this category.")).toBeVisible();
  await dialog.getByLabel("Move them to").selectOption({ label: "Other" });
  await dialog.getByRole("button", { name: "Move and delete" }).click();
  await expect(page.locator(".row-list__row", { hasText: "Tools" })).toHaveCount(0);
  expect((await item(page, id)).category?.name).toBe("Other");

  await page.getByLabel("New category").fill("other");
  await page.getByRole("button", { name: "Add", exact: true }).first().click();
  await expect(page.getByText("A category with that name already exists.")).toBeVisible();

  const garageRow = page.locator(".row-list__row", { hasText: "Garage" }).first();
  await garageRow.getByRole("button", { name: "Move" }).click();
  const move = page.getByRole("dialog", { name: "Move Garage" });
  await move.getByLabel("Put it inside").selectOption({ label: "Garage › Shelf" });
  await move.getByRole("button", { name: "Move", exact: true }).click();
  await expect(move.getByText("A place cannot go inside itself or a place inside it.")).toBeVisible();
});
