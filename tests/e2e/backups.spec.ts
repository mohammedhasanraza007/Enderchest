// Gate 5 of Phase 1, first half: "Back up now" creates a real file. (The banner when the folder is
// not connected is nobackups.spec.ts, against an app that really has no /backups mount.)
// /backups here is the test stack's backup folder, mounted read-only into the test container.

import { readdirSync, statSync } from "node:fs";
import { expect, test } from "@playwright/test";
import { resetApp, saveProfile } from "./helpers";

function manualBackups(): string[] {
  return readdirSync("/backups")
    .filter((name) => /^manual-.*\.sqlite3$/.test(name))
    .sort();
}

test("Back up now makes a real file in the backup folder and lists it", async ({
  page,
  request,
}) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata" });
  const before = manualBackups();

  await page.goto("/settings");
  await expect(page.getByText(/^Folder: /)).toBeVisible();
  await page.getByRole("button", { name: "Back up now" }).click();
  await expect(page.getByText(/^Backup saved \(\d+(\.\d)? (KB|MB)\)\.$/)).toBeVisible();

  const after = manualBackups();
  expect(after).toHaveLength(before.length + 1);
  const made = after.find((name) => !before.includes(name));
  expect(made).toBeDefined();
  const bytes = statSync(`/backups/${made}`).size;
  expect(bytes).toBeGreaterThan(0);

  const view = await (await request.get("/api/v1/backups")).json();
  const item = view.items.find((entry: { name: string }) => `${entry.name}.sqlite3` === made);
  expect(item).toMatchObject({ kind: "manual", bytes, ok: true });
  expect(view.last_good.name).toBe(item.name);

  await expect(page.getByRole("list", { name: "Recent backups" })).toContainText("manual");
  await expect(page.getByText(/^Last backup /)).toBeVisible();
});

test("a double click makes one backup, not two", async ({ page, request }) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata" });
  const before = manualBackups().length;
  await page.goto("/settings");
  const button = page.getByRole("button", { name: "Back up now" });
  await button.dblclick();
  await expect(page.getByText(/^Backup saved/)).toBeVisible();
  await page.waitForTimeout(1500);
  expect(manualBackups().length).toBe(before + 1);
});

test("no backup banner shows while backups are healthy", async ({ page, request }) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata" });
  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: "Backup" })).toBeVisible();
  await expect(page.locator(".banner")).toHaveCount(0);
});
