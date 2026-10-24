// Phase 1, build item 7: the boot pages share the app's tokens CSS (still plain HTML). The recovery
// page is the one with controls, so it is driven for real: the TEST database is deleted with a
// backup present, the page is checked in both themes, and the restore is done through the page.

import { mkdirSync } from "node:fs";
import { expect, test } from "@playwright/test";
import type { APIRequestContext } from "@playwright/test";
import { neededRatio, resetApp, saveProfile, textPairs, worstRatio } from "./helpers";

const HEADERS = { "X-Enderchest": "1" };

test.beforeAll(() => mkdirSync("/test-results/shots", { recursive: true }));

async function intoRecovery(request: APIRequestContext) {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata" });
  expect((await request.post("/api/v1/backups", { headers: HEADERS })).status()).toBe(201);
  expect((await request.post("/api/v1/test/delete-db", { headers: HEADERS })).ok()).toBe(true);
  const boot = await (await request.get("/api/v1/boot")).json();
  expect(boot.state).toBe("recovery");
}

// Whatever a spec did, leave the test app in a normal state for the next one.
test.afterEach(async ({ request }) => {
  const boot = await (await request.get("/api/v1/boot")).json();
  if (boot.state === "recovery" && boot.backups.length > 0) {
    await request.post("/api/v1/boot/restore", {
      headers: HEADERS,
      data: { name: boot.backups[0].name, confirm: "RESTORE" },
    });
  }
});

for (const scheme of ["dark", "light"] as const) {
  test(`the recovery page uses the shared tokens and passes contrast (${scheme})`, async ({
    page,
    request,
  }) => {
    await intoRecovery(request);
    await page.emulateMedia({ colorScheme: scheme, reducedMotion: "reduce" });
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "We found existing backups" })).toBeVisible();
    await expect(page.getByRole("img", { name: "Enderchest" })).toBeVisible();
    await expect(page.locator("html")).toHaveAttribute("data-theme", scheme);

    // The tokens file is really loaded: its variables resolve to the theme's colours.
    const base = await page.evaluate(() =>
      getComputedStyle(document.documentElement).getPropertyValue("--bg-base").trim(),
    );
    expect(base.toLowerCase()).toBe(scheme === "dark" ? "#16110d" : "#f4f1ea");

    const failing = (await textPairs(page))
      .filter((pair) => worstRatio(pair) < neededRatio(pair))
      .map((pair) => `${pair.where} "${pair.text.slice(0, 30)}" ${worstRatio(pair).toFixed(2)}`);
    expect(failing).toEqual([]);
    await page.screenshot({ path: `/test-results/shots/boot-recovery-${scheme}-1280x720.png` });
  });
}

test("a wrong confirmation is refused with a message and nothing changes", async ({
  page,
  request,
}) => {
  await intoRecovery(request);
  await page.goto("/");
  await page.getByPlaceholder("Type RESTORE to confirm").fill("restore");
  await page.getByRole("button", { name: "Restore this backup" }).click();
  await expect(page.locator(".error")).toBeVisible();
  const boot = await (await request.get("/api/v1/boot")).json();
  expect(boot.state).toBe("recovery");
});

test("restoring through the page brings the app and the owner's name back", async ({
  page,
  request,
}) => {
  await intoRecovery(request);
  await page.goto("/");
  await page.getByPlaceholder("Type RESTORE to confirm").fill("RESTORE");
  await page.getByRole("button", { name: "Restore this backup" }).click();
  await expect(page).toHaveURL(/:\d+\/$/, { timeout: 20_000 }); // the dashboard
  await expect(page.getByRole("button", { name: "Mohammed" })).toBeVisible();
});

test("every other address shows the same boot page while the app is not ready", async ({
  page,
  request,
}) => {
  await intoRecovery(request);
  for (const path of ["/", "/settings", "/welcome", "/anything"]) {
    await page.goto(path);
    await expect(page.getByRole("heading", { name: "We found existing backups" })).toBeVisible();
  }
});
