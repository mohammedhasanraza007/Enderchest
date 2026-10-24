// Smart capture in the browser (PAGES.md P-07, P-02 Gemini; Phase 3 gates 3 and 6): a photo is
// read on the test app, its values fill the form with tags, a read expiry must be tapped before
// saving, and Gemini without a network says so plainly. The label is drawn by the canvas and the
// test app's Gemini address is a closed port: regression only, never accuracy or Gemini evidence.

import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { labelBytes, makeDraft, readingSettled, resetApp, saveProfile } from "./helpers";

const WRITE = { "X-Enderchest": "1" };
const LABEL = [
  "OAT MILK BARISTA",
  "1 L  MODEL AB-1234X",
  "MFD 12/01/2026  EXP 14/03/2027",
  "BATCH L4471  Net Qty 500 ml",
];
const KEY = "AIzaTestKeyThatIsNotReal_0123456789";

test.setTimeout(120_000);

test.beforeEach(async ({ request }) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata" });
});

const nameBox = (page: Page) => page.getByRole("textbox", { name: "Name", exact: true }).first();
const readStatus = (page: Page) => page.getByText(/^Filled \d+ fields? from the photo/);

async function openRead(page: Page, lines: string[]): Promise<string> {
  await page.goto("/add");
  const draft = await makeDraft(page.request, await labelBytes(page, lines));
  await page.goto(`/add/${draft}`);
  await expect(readStatus(page)).toBeVisible({ timeout: 60_000 });
  return draft;
}

test("a read photo fills the form with tags, and the expiry needs a tap", async ({ page }) => {
  await openRead(page, LABEL);
  await expect(nameBox(page)).toHaveValue("Oat Milk Barista");
  const nameRow = page.locator(".field__label-row").filter({ hasText: /^Name/ }).first();
  await expect(nameRow).toContainText("Read from photo");
  await expect(page.getByRole("textbox", { name: "Value" }).first()).toHaveValue("AB-1234X");
  await expect(page.getByLabel("Expiry date")).toHaveValue("2027-03-14");
  await expect(page.getByText("Not confirmed")).toBeVisible();
  await expect(page.getByText("To save: Confirm the expiry date.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Save item" })).toBeDisabled();

  await page.getByRole("button", { name: "Confirm 14 Mar 2027" }).click();
  await expect(page.getByText("Confirmed", { exact: true })).toBeVisible();
  await nameBox(page).fill("Oat milk, barista");
  await expect(nameRow).toContainText("You");
  await page.getByRole("button", { name: "Save item" }).click();
  await expect(page).toHaveURL(/\/items\/ENDR-/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Oat milk, barista");
  await expect(page.getByText("AB-1234X")).toBeVisible();
});

test("an ambiguous date offers both readings and saves the one picked", async ({ page }) => {
  await openRead(page, ["SOAP BAR", "EXP 03/04/2027"]);
  const choices = page.getByRole("radiogroup", { name: "Which date is printed?" });
  await expect(choices.getByRole("radio")).toHaveText(["3 Apr 2027", "4 Mar 2027"]);
  await expect(page.getByRole("button", { name: "Save item" })).toBeDisabled();
  await choices.getByRole("radio", { name: "4 Mar 2027" }).click();
  await expect(page.getByLabel("Expiry date")).toHaveValue("2027-03-04");
  await page.getByRole("button", { name: "Save item" }).click();
  await expect(page).toHaveURL(/\/items\/ENDR-/);
  const publicId = page.url().split("/items/")[1]!;
  const item = (await (await page.request.get(`/api/v1/items/${publicId}`)).json()) as {
    expiry: { date: string };
  };
  expect(item.expiry.date).toBe("2027-03-04");
});

test("What was read shows the raw text, and Re-read reads again", async ({ page }) => {
  const draft = await openRead(page, LABEL);
  await page.getByRole("button", { name: "What was read" }).click();
  const drawer = page.getByRole("dialog", { name: "What was read" });
  await expect(drawer).toContainText("EXP 14/03/2027");
  await expect(drawer).toContainText("RapidOCR");
  await page.keyboard.press("Escape");
  await expect(drawer).toBeHidden();
  await page.getByRole("button", { name: "Re-read" }).click();
  await readingSettled(page.request, draft);
  await expect(readStatus(page)).toBeVisible();
  await expect(nameBox(page)).toHaveValue("Oat Milk Barista");
});

test("the queue shows the name read from the photo", async ({ page }) => {
  await page.goto("/add");
  const draft = await makeDraft(page.request, await labelBytes(page, LABEL));
  await readingSettled(page.request, draft);
  await page.goto("/add");
  await expect(page.getByRole("link", { name: "Oat Milk Barista" })).toBeVisible();
  await expect(page.getByText(/· read$/)).toBeVisible();
});

test("Gemini with no network says so and leaves the photo reading alone", async ({ page }) => {
  await page.request.put("/api/v1/gemini/key", { headers: WRITE, data: { key: KEY } });
  await page.request.patch("/api/v1/settings", { headers: WRITE, data: { gemini_mode: "ask" } });
  await openRead(page, LABEL);
  await expect(page.getByText(/sends the text read from this photo/)).toBeVisible();
  await page.getByRole("button", { name: "Improve with Gemini" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "could not be reached" })).toBeVisible({
    timeout: 30_000,
  });
  await expect(nameBox(page)).toHaveValue("Oat Milk Barista");
});

test("Improve with Gemini is not on screen while Gemini is off", async ({ page }) => {
  await openRead(page, LABEL);
  await expect(page.getByRole("button", { name: "Re-read" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Improve with Gemini" })).toHaveCount(0);
});

test("Settings: set a key, choose a mode, test without network, remove the key", async ({
  page,
}) => {
  await page.goto("/settings");
  const section = page.locator(".glass-card").filter({ hasText: "When to use Gemini" });
  await expect(section.getByText("No key")).toBeVisible();
  await expect(section.getByRole("button", { name: "Test connection" })).toBeDisabled();
  await section.getByLabel("Gemini API key").fill(KEY);
  await section.getByRole("button", { name: "Save key" }).click();
  await expect(section.getByText("Key set")).toBeVisible();
  await expect(section.getByLabel("New Gemini API key")).toHaveValue("");
  expect(await page.content()).not.toContain(KEY);

  await section.getByRole("radio", { name: "Ask each time" }).click();
  await expect(section.getByRole("radio", { name: "Ask each time" })).toBeChecked();
  await section.getByRole("switch", { name: "Send photos to Gemini" }).click();
  await expect(section.getByText(/On: the photo is sent too/)).toBeVisible();
  const settings = (await (await page.request.get("/api/v1/settings")).json()) as {
    gemini_mode: string;
    share_images_with_gemini: boolean;
  };
  expect([settings.gemini_mode, settings.share_images_with_gemini]).toEqual(["ask", true]);

  await section.getByRole("button", { name: "Test connection" }).click();
  await expect(section.getByRole("alert")).toContainText("could not be reached");
  await section.getByRole("button", { name: "Remove key" }).click();
  await expect(section.getByText("No key")).toBeVisible();
});

test("a key the server refuses for an unseen reason still shows a message (F-024)", async ({
  page,
}) => {
  await page.route("**/api/v1/gemini/key", (route) =>
    route.fulfill({
      status: 422,
      contentType: "application/json",
      body: JSON.stringify({
        error: {
          code: "validation_error",
          message: "Some values are not valid.",
          details: { problems: [{ field: "other", problem: "Something else is wrong." }] },
        },
      }),
    }),
  );
  await page.goto("/settings");
  const section = page.locator(".glass-card").filter({ hasText: "When to use Gemini" });
  await section.getByLabel("Gemini API key").fill(KEY);
  await section.getByRole("button", { name: "Save key" }).click();
  await expect(section.getByText("Some values are not valid.")).toBeVisible();
});
