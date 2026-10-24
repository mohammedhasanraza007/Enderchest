// Screenshots of the Phase 4 screens for review against the reference (D-097): Tasks,
// Notifications, the item page with its lifecycle actions and maintenance card, the inspection
// sheet, the snooze dialog and Settings -> Notifications; 1280 px dark and light, 1024 px dark for
// the dense item page. Test data on the test stack; the owner approves the look (BLOCKED).

import { expect, test } from "@playwright/test";
import { jpegBytes, makeItem, post, resetApp, saveProfile } from "./helpers";

const SHOTS = "/test-results/shots-phase-4";
test.use({ reducedMotion: "reduce" });
test.setTimeout(180_000);

function kolkataDay(offset = 0): string {
  const moment = new Date(Date.now() + offset * 86_400_000);
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(moment);
}

for (const theme of ["dark", "light"] as const) {
  test(`lifecycle screens (${theme})`, async ({ page, request }) => {
    await resetApp(request);
    await saveProfile(request, {
      name: "Mohammed",
      timezone: "Asia/Kolkata",
      theme,
    });
    const tools = await post<{ id: number }>(request, "/api/v1/categories", {
      name: "Tools",
      maintenance_default: true,
    });
    const food = await post<{ id: number }>(request, "/api/v1/categories", {
      name: "Food and drink",
      expires_default: true,
      label_default: false,
    });
    const fridge = await post<{ id: number }>(request, "/api/v1/locations", {
      name: "Fridge",
    });
    const garage = await post<{ id: number }>(request, "/api/v1/locations", {
      name: "Garage",
    });
    await makeItem(request, {
      name: "Oat milk",
      category_id: food.id,
      location_id: fridge.id,
      expiry_date: kolkataDay(0),
      no_label_needed: true,
    });
    await makeItem(request, {
      name: "Greek yogurt",
      category_id: food.id,
      location_id: fridge.id,
      expiry_date: kolkataDay(2),
      quantity: 2,
      no_label_needed: true,
    });
    const grinder = await makeItem(request, {
      name: "Angle grinder",
      category_id: tools.id,
      location_id: garage.id,
      price_paise: 349900,
      attributes: { model: "GWS 600" },
    });
    await page.goto("/settings");
    const photo = await jpegBytes(page, "#5b6b73");
    await request.post(`/api/v1/items/${grinder}/photos`, {
      headers: { "X-Enderchest": "1" },
      multipart: {
        image: { name: "a.jpg", mimeType: "image/jpeg", buffer: photo },
      },
    });
    await request.put(`/api/v1/items/${grinder}/maintenance`, {
      headers: { "X-Enderchest": "1" },
      data: {
        enabled: true,
        interval_days: 90,
        first_due: kolkataDay(-1),
        source: "gemini",
      },
    });
    const blade = await makeItem(request, {
      name: "Saw blade",
      category_id: tools.id,
    });
    await post(request, `/api/v1/items/${blade}/inspections`, {
      result: "worn",
      note: "Teeth dull",
    });
    await post(request, "/api/v1/tasks", {
      title: "Clean PC",
      interval_days: 14,
      first_due: kolkataDay(0),
    });
    await post(request, "/api/v1/tasks", {
      title: "Descale kettle",
      interval_days: 30,
      schedule_mode: "fixed",
      first_due: kolkataDay(5),
    });
    await post(request, "/api/v1/tasks", {
      title: "Renew bike insurance",
      first_due: kolkataDay(40),
    });

    const settle = async () => {
      await page.waitForLoadState("networkidle");
      await expect(page.locator('[aria-busy="true"]')).toHaveCount(0);
      await page.evaluate(() => document.fonts.ready);
    };
    const screens: Array<[string, string]> = [
      ["tasks", "/tasks"],
      ["notifications", "/notifications"],
      ["item-maintenance", `/items/${grinder}`],
      ["item-finding", `/items/${blade}`],
    ];
    for (const width of theme === "dark" ? [1280, 1024] : [1280]) {
      await page.setViewportSize({ width, height: 900 });
      for (const [name, path] of screens) {
        if (width === 1024 && !name.startsWith("item")) continue;
        await page.goto(path);
        await settle();
        await page.screenshot({
          path: `${SHOTS}/${name}-${theme}-${width}.png`,
          fullPage: true,
        });
      }
    }
    await page.setViewportSize({ width: 1280, height: 900 });

    await page.goto("/tasks");
    await settle();
    await page.getByRole("radio", { name: "All" }).click();
    await settle();
    await page.screenshot({
      path: `${SHOTS}/tasks-all-${theme}-1280.png`,
      fullPage: true,
    });
    await page.getByRole("button", { name: "New task" }).click();
    const sheet = page.getByRole("dialog", { name: "New task" });
    await sheet.getByLabel("Title").fill("Oil the hinges");
    await sheet.getByRole("radio", { name: "Every few days" }).click();
    await sheet.getByLabel("Every how many days").fill("90");
    await sheet.getByLabel("Item (optional)").fill("grind");
    await expect(sheet.getByRole("button", { name: /Angle grinder/ })).toBeVisible();
    await page.screenshot({ path: `${SHOTS}/task-sheet-${theme}-1280.png` });
    await sheet.getByRole("button", { name: "Cancel" }).click();
    await page.getByRole("button", { name: "Discard changes" }).click();

    await page.goto("/notifications");
    await settle();
    await page
      .locator(".reminder")
      .filter({ hasText: "Greek yogurt" })
      .getByRole("button", { name: "Snooze" })
      .click();
    await expect(page.getByRole("dialog", { name: "Snooze Greek yogurt" })).toBeVisible();
    await page.screenshot({ path: `${SHOTS}/snooze-${theme}-1280.png` });
    await page.keyboard.press("Escape");

    await page.goto(`/items/${grinder}`);
    await settle();
    await page.getByRole("button", { name: "Inspect now" }).click();
    const inspect = page.getByRole("dialog", { name: "Inspect Angle grinder" });
    await inspect.getByRole("radio", { name: "Good" }).click();
    await page.screenshot({
      path: `${SHOTS}/inspection-sheet-${theme}-1280.png`,
    });
    await page.keyboard.press("Escape");

    await page.goto("/settings");
    await settle();
    const section = page.locator(".glass-card").filter({ hasText: "Browser notifications" });
    await section.scrollIntoViewIfNeeded();
    await section.screenshot({
      path: `${SHOTS}/settings-notifications-${theme}-1280.png`,
    });
  });
}
