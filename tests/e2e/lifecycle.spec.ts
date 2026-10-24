// Phase 4 in the browser: Tasks, Notifications, the item's lifecycle and maintenance, Settings ->
// Notifications, the bell and the tab title (gates 4 to 6 and 8 in the UI; the browser
// notification itself is in browser-notifications.spec.ts). Test data on the test stack, never
// gate evidence for the owner's acceptance run.

import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { makeItem, resetApp, saveProfile } from "./helpers";

test.use({ reducedMotion: "reduce" });

const WRITE = { "X-Enderchest": "1" };

/** YYYY-MM-DD in Asia/Kolkata (the profile's zone), moved by whole days. */
function kolkataDay(offset = 0): string {
  const moment = new Date(Date.now() + offset * 86_400_000);
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(moment);
}

async function ready(page: Page): Promise<void> {
  await page.waitForLoadState("networkidle");
  await expect(page.locator('[aria-busy="true"]')).toHaveCount(0);
}

test.beforeEach(async ({ request }) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata" });
});

test("a task made on the Tasks page is due today, done, and undone", async ({ page }) => {
  await page.goto("/tasks");
  await ready(page);
  await expect(page.getByText("No tasks yet.")).toBeVisible();
  await page.getByRole("button", { name: "New task" }).first().click();
  const sheet = page.getByRole("dialog", { name: "New task" });
  await expect(sheet.getByRole("button", { name: "Save task" })).toBeDisabled();
  await sheet.getByLabel("Title").fill("Clean PC");
  await sheet.getByRole("radio", { name: "Every few days" }).click();
  await sheet.getByLabel("Every how many days").fill("14");
  await sheet.getByRole("button", { name: "Save task" }).click();
  await expect(sheet).toBeHidden();
  const row = page.locator(".task-row").filter({ hasText: "Clean PC" });
  await expect(row).toContainText("every 14 days");
  await expect(row).toContainText("due today");
  await expect(page.getByRole("link", { name: "Notifications, 1 open" })).toBeVisible();
  await expect(page).toHaveTitle("(1) Tasks · Enderchest");

  await row.getByRole("button", { name: "Mark done" }).click();
  await expect(page.getByText(/^Done\. Next due/)).toBeVisible();
  await expect(page.getByText("Nothing is due in the next 7 days.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Notifications", exact: true })).toBeVisible();
  await expect(page).toHaveTitle("Tasks · Enderchest");
  await page.getByRole("button", { name: "Undo" }).click();
  await expect(row).toContainText("due today");
  await expect(page.getByRole("link", { name: "Notifications, 1 open" })).toBeVisible();
});

test("a reminder is snoozed, and Use it with Undo restores the quantity", async ({
  page,
  request,
}) => {
  const milk = await makeItem(request, {
    name: "Oat milk",
    expiry_date: kolkataDay(2),
    quantity: 3,
  });
  await page.goto("/notifications");
  await ready(page);
  const row = page.locator(".reminder").filter({ hasText: "Oat milk" });
  await expect(row).toContainText("Oat milk (2 days left)");
  await row.getByRole("button", { name: "Use it" }).click();
  await expect(page.getByText("Oat milk used one, 2 left.")).toBeVisible();
  await expect(row).toBeVisible(); // two are left, so it still needs the owner
  await page.getByRole("button", { name: "Undo" }).click();
  await expect
    .poll(async () => (await (await request.get(`/api/v1/items/${milk}`)).json()).quantity)
    .toBe(3);

  await row.getByRole("button", { name: "Snooze" }).click();
  const dialog = page.getByRole("dialog", { name: "Snooze Oat milk" });
  await expect(dialog).toContainText("never hides an item past its date");
  await dialog.getByRole("button", { name: "Next week" }).click();
  await expect(page.getByText(/^Snoozed until/)).toBeVisible();
  await expect(page.getByText("Nothing needs you right now.")).toBeVisible();
  await page.getByRole("radio", { name: "Snoozed" }).click();
  await expect(page.locator(".reminder")).toContainText("Oat milk");
  await expect(page.locator(".reminder")).toContainText("Snoozed until");
});

test("the item page: use, mark expired, reactivate, plan and inspect", async ({
  page,
  request,
}) => {
  const grinder = await makeItem(request, {
    name: "Angle grinder",
    quantity: 1,
  });
  await page.goto(`/items/${grinder}`);
  await ready(page);
  await page.getByRole("button", { name: "Mark expired" }).click();
  await expect(page.getByText("Marked expired.").first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Reactivate" })).toBeVisible();
  await page.getByRole("button", { name: "Reactivate" }).click();
  await expect(page.getByRole("button", { name: "Use it" })).toBeVisible();

  const card = page.locator(".maintenance-card");
  await card.getByRole("button", { name: "Plan inspections" }).click();
  await card.getByLabel("Inspect every how many days").fill("30");
  await card.getByRole("button", { name: "Save plan" }).click();
  await expect(card).toContainText("Every 30 days · next due");
  await expect(card.getByRole("switch", { name: "Inspection reminders" })).toBeChecked();

  await card.getByRole("button", { name: "Inspect now" }).click();
  const sheet = page.getByRole("dialog", { name: "Inspect Angle grinder" });
  await expect(sheet.getByRole("button", { name: "Save inspection" })).toBeDisabled();
  await sheet.getByRole("radio", { name: "Worn" }).click();
  await sheet.getByLabel("Note (optional)").fill("Brushes low");
  await sheet.getByRole("button", { name: "Save inspection" }).click();
  await expect(card).toContainText("Inspection suggested: worn.");
  await expect(card).toContainText("Worn · Brushes low");
  await expect(card.getByRole("button", { name: "Mark discarded" })).toBeVisible();
  await expect(page.locator("body")).not.toContainText(/replacement required/i);

  await page.goto("/notifications");
  const finding = page.locator(".reminder").filter({ hasText: "Angle grinder" });
  await expect(finding).toContainText("(inspection suggested: worn)");
  await finding.getByRole("button", { name: "Mark discarded" }).click();
  await expect(page.getByText("Angle grinder discarded.")).toBeVisible();
  await expect(page.getByText("Nothing needs you right now.")).toBeVisible();
});

test("Settings -> Notifications saves the lead days and says the honest limit", async ({
  page,
  request,
}) => {
  await makeItem(request, { name: "Rice", expiry_date: kolkataDay(6) });
  await page.goto("/settings");
  await ready(page);
  const section = page.locator(".glass-card").filter({ hasText: "Browser notifications" });
  await expect(section).toContainText(
    "Reminders appear here and as browser notifications while an Enderchest tab is open.",
  );
  await expect(section.getByRole("button", { name: "Save days" })).toBeDisabled();
  await section.getByLabel("Warn me this many days before expiry").fill("20");
  await expect(section).toContainText("Choose 1 to 14 days.");
  await section.getByLabel("Warn me this many days before expiry").fill("7");
  await section.getByRole("button", { name: "Save days" }).click();
  await expect(page.getByText("You will be warned 7 days before.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Notifications, 1 open" })).toBeVisible();
  const settings = await (await request.get("/api/v1/settings")).json();
  expect(settings.lead_days).toBe(7);
});

test("a write without the safety header is refused for the new endpoints", async ({ request }) => {
  const refused = await request.post("/api/v1/tasks", {
    data: { title: "x", first_due: kolkataDay(0) },
  });
  expect(refused.status()).toBe(403);
  const ok = await request.post("/api/v1/tasks", {
    headers: WRITE,
    data: { title: "x", first_due: kolkataDay(0) },
  });
  expect(ok.status()).toBe(201);
});
