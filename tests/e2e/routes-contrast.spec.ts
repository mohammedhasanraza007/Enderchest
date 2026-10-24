// Gate 7 of Phase 2: every piece of text on every inventory route passes WCAG AA in both themes,
// measured on the real pages with real data made through the API (the gallery spec covers the
// primitives on their own).

import { writeFileSync } from "node:fs";
import { expect, test } from "@playwright/test";
import {
  jpegBytes,
  labelBytes,
  makeDraft,
  makeItem,
  neededRatio,
  post,
  readingSettled,
  resetApp,
  saveProfile,
  textPairs,
  worstRatio,
} from "./helpers";

test.use({ reducedMotion: "reduce" });

for (const theme of ["dark", "light"] as const) {
  test(`text on every inventory route passes WCAG AA (${theme})`, async ({ page, request }) => {
    await resetApp(request);
    await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata", theme });
    const food = await post<{ id: number }>(request, "/api/v1/categories", {
      name: "Food and drink",
      expires_default: true,
    });
    const shelf = await post<{ id: number }>(request, "/api/v1/locations", { name: "Pantry" });
    const soon = new Date(Date.now() + 86_400_000).toISOString().slice(0, 10);
    const milk = await makeItem(request, {
      name: "Oat milk",
      category_id: food.id,
      location_id: shelf.id,
      quantity: 2,
      expiry_date: soon,
      price_paise: 12500,
      attributes: { brand: "Oatly" },
      notes: "Second shelf",
    });
    const expired = await makeItem(request, { name: "Old yogurt", expiry_date: "2020-01-01" });
    const trashed = await makeItem(request, { name: "Broken lamp" });
    await request.delete(`/api/v1/items/${trashed}`, { headers: { "X-Enderchest": "1" } });
    await page.goto("/settings");
    const photo = await jpegBytes(page);
    await request.post(`/api/v1/items/${milk}/photos`, {
      headers: { "X-Enderchest": "1" },
      multipart: { image: { name: "a.jpg", mimeType: "image/jpeg", buffer: photo } },
    });
    // A read label (Phase 3): source tags, an ambiguous date to pick, and Gemini switched on
    // so its button and disclosure are measured too (its address is a closed port here).
    const draft = await makeDraft(
      request,
      await labelBytes(page, ["OAT MILK BARISTA", "MODEL AB-1234X  500 ml", "EXP 03/04/2027"]),
    );
    await request.put("/api/v1/gemini/key", {
      headers: { "X-Enderchest": "1" },
      data: { key: "AIzaTestKeyThatIsNotReal_0123456789" },
    });
    await request.patch("/api/v1/settings", {
      headers: { "X-Enderchest": "1" },
      data: { gemini_mode: "ask" },
    });
    await readingSettled(request, draft);
    // Phase 4: a task due today, a maintenance plan with a Gemini source and a worn inspection,
    // so Tasks, Notifications and the maintenance card are measured with real rows.
    const today = new Date().toISOString().slice(0, 10);
    await post(request, "/api/v1/tasks", { title: "Clean PC", first_due: today });
    await request.put(`/api/v1/items/${milk}/maintenance`, {
      headers: { "X-Enderchest": "1" },
      data: { enabled: true, interval_days: 30, first_due: today, source: "gemini" },
    });
    await post(request, `/api/v1/items/${expired}/inspections`, { result: "worn" });

    const routes = [
      "/inventory",
      `/items/${milk}`,
      `/items/${expired}`,
      `/items/${trashed}`,
      "/camera?mode=add",
      "/camera?mode=scan",
      "/add",
      `/add/${draft}`,
      `/labels?ids=${milk},${expired}`,
      "/trash",
      "/settings",
      "/tasks",
      "/notifications",
    ];
    const failures: string[] = [];
    let checked = 0;
    for (const route of routes) {
      await page.goto(route);
      await page.waitForLoadState("networkidle");
      await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
      for (const pair of await textPairs(page)) {
        checked += 1;
        const ratio = worstRatio(pair);
        if (ratio < neededRatio(pair)) {
          failures.push(`${route} ${pair.where} "${pair.text.slice(0, 30)}" ${ratio.toFixed(2)}`);
        }
      }
    }
    writeFileSync(
      `/test-results/routes-contrast-${theme}.json`,
      JSON.stringify({ routes, checked, failures }, null, 2),
    );
    expect(checked).toBeGreaterThan(100);
    expect(failures).toEqual([]);
  });
}
