// Screenshots of every Phase 2 screen for review against the reference (D-097): 1280 px in dark
// and light, and 1024 px for the dense screens. Test data on the test stack; the owner approves
// the look on their own laptop (gate: owner screenshot approval, BLOCKED until they do).

import { expect, test } from "@playwright/test";
import { jpegBytes, makeItem, post, resetApp, saveProfile } from "./helpers";

const SHOTS = "/test-results/shots-phase-2";
test.use({ reducedMotion: "reduce" });
test.setTimeout(180_000);

for (const theme of ["dark", "light"] as const) {
  test(`every inventory screen at 1280 px (${theme})`, async ({ page, request }) => {
    await resetApp(request);
    await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata", theme });
    const food = await post<{ id: number }>(request, "/api/v1/categories", {
      name: "Food and drink",
      expires_default: true,
      label_default: false,
    });
    const tools = await post<{ id: number }>(request, "/api/v1/categories", { name: "Tools" });
    const kitchen = await post<{ id: number }>(request, "/api/v1/locations", { name: "Kitchen" });
    const pantry = await post<{ id: number }>(request, "/api/v1/locations", {
      name: "Pantry",
      parent_id: kitchen.id,
    });
    const garage = await post<{ id: number }>(request, "/api/v1/locations", { name: "Garage" });
    const day = (offset: number) => new Date(Date.now() + offset * 86_400_000).toISOString().slice(0, 10);
    await page.goto("/settings");
    const colours = ["#8a5a3c", "#3c6a8a", "#5a8a3c", "#8a3c5a", "#6a6a3c", "#3c8a7a"];
    const ids: string[] = [];
    const specs = [
      { name: "Oat milk", category_id: food.id, location_id: pantry.id, expiry_date: day(1), quantity: 2 },
      { name: "Greek yogurt", category_id: food.id, location_id: pantry.id, expiry_date: day(0) },
      { name: "Baby spinach", category_id: food.id, location_id: kitchen.id, expiry_date: day(-2) },
      { name: "Cordless drill", category_id: tools.id, location_id: garage.id, expiry_mode: "none", price_paise: 649900, attributes: { model: "GSR 120-LI", voltage: "12 V" } },
      { name: "Spanner set", category_id: tools.id, location_id: garage.id, expiry_mode: "none", attributes: { sizes: [8, 10, 12, 13] } },
      { name: "AA batteries", location_id: garage.id, quantity: 8 },
    ];
    for (const [index, fields] of specs.entries()) {
      const id = await makeItem(request, fields);
      ids.push(id);
      if (index < 4) {
        await request.post(`/api/v1/items/${id}/photos`, {
          headers: { "X-Enderchest": "1" },
          multipart: {
            image: { name: "p.jpg", mimeType: "image/jpeg", buffer: await jpegBytes(page, colours[index]) },
          },
        });
      }
    }
    await request.delete(`/api/v1/items/${ids[5]}`, { headers: { "X-Enderchest": "1" } });
    const drafts = await request.post("/api/v1/drafts", {
      headers: { "X-Enderchest": "1" },
      multipart: {
        "images[]": { name: "d.jpg", mimeType: "image/jpeg", buffer: await jpegBytes(page, colours[4]) },
      },
    });
    const draft = ((await drafts.json()) as { drafts: Array<{ id: string }> }).drafts[0]!.id;

    const screens: Array<[string, string]> = [
      ["inventory", "/inventory"],
      ["item", `/items/${ids[3]}`],
      ["item-food", `/items/${ids[0]}`],
      ["camera-add", "/camera?mode=add"],
      ["camera-scan", "/camera?mode=scan"],
      ["queue", "/add"],
      ["confirm", `/add/${draft}`],
      ["labels", `/labels?ids=${ids.slice(0, 4).join(",")}`],
      ["trash", "/trash"],
      ["settings", "/settings"],
    ];
    for (const width of theme === "dark" ? [1280, 1024] : [1280]) {
      await page.setViewportSize({ width, height: 800 });
      for (const [name, path] of screens) {
        if (width === 1024 && !["inventory", "item", "confirm"].includes(name)) continue;
        await page.goto(path);
        await page.waitForLoadState("networkidle");
        await expect(page.locator('[aria-busy="true"]')).toHaveCount(0);
        await page.evaluate(() => document.fonts.ready);
        await page.screenshot({ path: `${SHOTS}/${name}-${theme}-${width}.png`, fullPage: true });
      }
    }
    // The item form sheet, open.
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(`/items/${ids[3]}`);
    await page.getByRole("button", { name: "Edit" }).click();
    await page.screenshot({ path: `${SHOTS}/item-form-${theme}-1280.png` });
  });
}
