// Gate 5 of Phase 1, second half: the banner appears when the backup folder is unavailable.
// This runs against a second test app that really has no /backups mount (compose.test.yaml,
// service app-nobackups), not against a faked response.

import { expect, test } from "@playwright/test";
import { resetApp, saveProfile } from "./helpers";

test("the banner says the folder is not connected, on every page", async ({ page, request }) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata" });

  const view = await (await request.get("/api/v1/backups")).json();
  expect(view.status).toBe("unavailable");

  for (const path of ["/settings", "/not-a-page"]) {
    await page.goto(path);
    const banner = page.locator(".banner");
    await expect(banner).toBeVisible();
    await expect(banner).toContainText("Not backed up");
    await expect(banner).toContainText("The backup folder is not connected");
    // It says what to do, and offers no button that could not work.
    await expect(banner).toContainText("run.bat");
    await expect(banner.getByRole("button")).toHaveCount(0);
  }
});

test("Settings shows the same truth and a Back up now that says why it is off", async ({
  page,
  request,
}) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata" });
  await page.goto("/settings");
  await expect(page.getByText("Backup folder not connected")).toBeVisible();
  const button = page.getByRole("button", { name: "Back up now" });
  await expect(button).toBeDisabled();
  await expect(page.getByText("The backup folder is not connected.", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Mohammed" }).click();
  await expect(page.locator(".name-menu__status")).toHaveText("Backup folder not connected");
});

test("no backup is attempted, so no request for one is sent", async ({ page, request }) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata" });
  const posts: string[] = [];
  page.on("request", (r) => {
    if (r.method() === "POST" && r.url().includes("/api/v1/backups")) posts.push(r.url());
  });
  await page.goto("/settings");
  await page.getByRole("button", { name: "Back up now" }).click({ force: true }).catch(() => undefined);
  await page.waitForTimeout(500);
  expect(posts).toEqual([]);
});
