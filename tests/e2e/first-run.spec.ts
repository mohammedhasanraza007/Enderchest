// Gate 4 of Phase 1: first run. Closing the tab after the name step and reopening resumes
// correctly. (That the name survives stop.bat then run.bat is probe 17, which restarts the
// container; a browser test cannot.)

import { expect, test, type Page, type Route } from "@playwright/test";
import { resetApp, saveProfile } from "./helpers";

test.beforeEach(async ({ request }) => {
  await resetApp(request);
});

test("a new database sends the owner to the welcome screen from any address", async ({ page }) => {
  for (const path of ["/", "/settings", "/nothing-here"]) {
    await page.goto(path);
    await expect(page).toHaveURL(/\/welcome$/);
    await expect(page.getByRole("heading", { name: "Welcome to Enderchest" })).toBeVisible();
  }
});

test("an empty or too long name is refused with a message and nothing is saved", async ({
  page,
  request,
}) => {
  await page.goto("/welcome");
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByText("Enter a name of 1 to 40 characters.")).toBeVisible();
  await page.getByLabel("Your name").fill("x".repeat(41));
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByText("Enter a name of 1 to 40 characters.")).toBeVisible();
  const profile = await (await request.get("/api/v1/profile")).json();
  expect(profile.name).toBeNull();
});

test("name, then starter categories, then a greeting and the app", async ({ page, request }) => {
  await page.goto("/welcome");
  await page.getByLabel("Your name").fill("Mohammed");
  await page.getByLabel("Time zone").selectOption("Asia/Kolkata");
  await page.getByRole("button", { name: "Continue" }).click();

  // Step 2 (P-01): six optional starter categories.
  await expect(page.getByRole("heading", { name: "Start with some categories?" })).toBeVisible();
  await page.getByRole("button", { name: "Tools" }).click();
  await page.getByRole("button", { name: "Food and drink" }).click();
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(
    page.getByRole("heading", { name: /^Good (morning|afternoon|evening|night), Mohammed$/ }),
  ).toBeVisible();
  const profile = await (await request.get("/api/v1/profile")).json();
  expect(profile).toMatchObject({
    name: "Mohammed",
    timezone: "Asia/Kolkata",
    first_run_complete: true,
    first_run_step: "done",
  });
  const categories = await (await request.get("/api/v1/categories")).json();
  expect(categories.map((c: { name: string }) => c.name)).toEqual(["Food and drink", "Tools"]);
  expect(categories[0]).toMatchObject({ expires_default: true, label_default: false });

  await page.getByRole("link", { name: "Add your first item" }).click();
  await expect(page).toHaveURL(/\/camera\?mode=add$/);
  await expect(page.getByRole("button", { name: "Mohammed" })).toBeVisible();
});

test("Skip on step 2 makes no categories", async ({ page, request }) => {
  await page.goto("/welcome");
  await page.getByLabel("Your name").fill("Mohammed");
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Skip" }).click();
  await expect(page.getByRole("heading", { name: /Mohammed$/ })).toBeVisible();
  expect(await (await request.get("/api/v1/categories")).json()).toEqual([]);
});

test("closing the tab on step 2 and reopening resumes at step 2 with the name kept", async ({
  browser,
}) => {
  const first = await browser.newContext({ baseURL: "http://127.0.0.1:8470" });
  const tab = await first.newPage();
  await tab.goto("/welcome");
  await tab.getByLabel("Your name").fill("Mohammed");
  await tab.getByRole("button", { name: "Continue" }).click();
  await expect(tab.getByRole("heading", { name: "Start with some categories?" })).toBeVisible();
  await first.close(); // the tab is gone

  const second = await browser.newContext({ baseURL: "http://127.0.0.1:8470" });
  const reopened = await second.newPage();
  await reopened.goto("/inventory");
  await expect(reopened).toHaveURL(/\/welcome$/);
  await expect(
    reopened.getByRole("heading", { name: "Start with some categories?" }),
  ).toBeVisible();
  await reopened.getByRole("button", { name: "Skip" }).click();
  await expect(reopened.getByRole("heading", { name: /Mohammed$/ })).toBeVisible();
  await reopened.goto("/");
  await expect(reopened.getByRole("heading", { name: /Mohammed$/ })).toBeVisible(); // dashboard
  await reopened.goto("/welcome"); // first run cannot be repeated
  await expect(reopened).toHaveURL(/:\d+\/$/);
  await second.close();
});

test("the name can be changed later in Settings and shows in the capsule", async ({
  page,
  request,
}) => {
  await saveProfile(request, { name: "Mohammed", timezone: "UTC" });
  await page.goto("/settings");
  await page.getByLabel("Your name").fill("Mo");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByText("Profile saved.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Mo", exact: true })).toBeVisible();
});

/** Make only PUT /profile fail, the way `fail` says; every other request goes through. */
async function breakSaving(page: Page, fail: (route: Route) => Promise<void>): Promise<void> {
  await page.unrouteAll();
  await page.route("**/api/v1/profile", (route) =>
    route.request().method() === "PUT" ? fail(route) : route.continue(),
  );
}

test("a failed first-run save keeps the typed name, says why, and the button works again", async ({
  page,
  request,
}) => {
  await page.goto("/welcome");
  await page.getByLabel("Your name").fill("Mohammed");
  const button = page.getByRole("button", { name: "Continue" });

  await breakSaving(page, (route) => route.fulfill({ status: 500, body: "not json" }));
  await button.click();
  await expect(page.getByText("Something went wrong. Nothing was lost.")).toBeVisible();
  await expect(page.getByLabel("Your name")).toHaveValue("Mohammed");

  await breakSaving(page, (route) => route.abort("connectionrefused"));
  await button.click();
  await expect(page.getByText(/Enderchest is not answering/)).toBeVisible();
  await expect(page.getByLabel("Your name")).toHaveValue("Mohammed");
  expect((await (await request.get("/api/v1/profile")).json()).name).toBeNull();

  await page.unrouteAll();
  await button.click();
  await expect(page.getByRole("heading", { name: "Start with some categories?" })).toBeVisible();
});

test("a failed save in Settings keeps the change, says why, and changes nothing", async ({
  page,
  request,
}) => {
  await saveProfile(request, { name: "Mohammed", timezone: "UTC" });
  await page.goto("/settings");
  await page.getByLabel("Your name").fill("Mo");
  const error = { error: { code: "internal_error", message: "The disk is full.", details: {} } };
  await breakSaving(page, (route) => route.fulfill({ status: 500, json: error }));
  await page.getByRole("button", { name: "Save", exact: true }).click();

  await expect(page.getByText("The disk is full.")).toBeVisible();
  await expect(page.getByLabel("Your name")).toHaveValue("Mo");
  await expect(page.getByText("Profile saved.")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Mohammed", exact: true })).toBeVisible();
  expect((await (await request.get("/api/v1/profile")).json()).name).toBe("Mohammed");

  await page.unrouteAll();
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByText("Profile saved.")).toBeVisible();
  await expect(page.getByText("The disk is full.")).toHaveCount(0);
});
