// Phase 9 verification probes (docs/reviews/phase-9-verification.md): the nav at the three review
// widths, the conversation kept in sessionStorage (reload, item link, Start over, corrupt data),
// a switch turned off mid-conversation, one request per send, and the Settings switch. Answers are
// `page.route` stubs: test code only, a regression check of the page, never gate evidence.

import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { resetApp, saveProfile } from "./helpers";

const WRITE = { "X-Enderchest": "1" };
const KEY = "AIzaTestKeyThatIsNotReal_0123456789";
const STORAGE_KEY = "enderchest.assistant";
const TABS = ["Dashboard", "Inventory", "Camera", "Tasks", "Savings", "Assistant"];

const OAT_REPLY = {
  reply: "Oat Milk — expires today",
  segments: [
    { text: "Oat Milk", public_id: "ENDR-7K2M9QXA" },
    { text: " — expires today", public_id: null },
  ],
  cited: [{ public_id: "ENDR-7K2M9QXA", name: "Oat Milk" }],
  tools_used: ["items_expiring"],
  rows_checked: 1,
};

async function switchOn(page: Page) {
  await page.request.put("/api/v1/gemini/key", { headers: WRITE, data: { key: KEY } });
  await page.request.patch("/api/v1/settings", {
    headers: WRITE,
    data: { assistant_share_item_text: true },
  });
}

async function answerWith(page: Page, status: number, body: object, seen: unknown[] = []) {
  await page.route("**/api/v1/assistant/chat", async (route) => {
    seen.push(route.request().postDataJSON());
    await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
  });
}

async function askOnce(page: Page, question: string) {
  const input = page.getByPlaceholder("Ask about your things…");
  await input.fill(question);
  await input.press("Enter");
}

test.beforeEach(async ({ request }) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata" });
});

for (const width of [1024, 1280, 1536]) {
  test(`V1 at ${width} px the six tabs sit on one line in order and the page never widens`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 800 });
    await page.goto("/assistant");
    const items = page.getByRole("navigation", { name: "Main" }).getByRole("listitem");
    await expect(items).toHaveText(TABS);
    const tops = await items.evaluateAll((nodes) =>
      nodes.map((node) => Math.round(node.getBoundingClientRect().top)),
    );
    expect(new Set(tops).size).toBe(1);
    for (const tab of await items.all()) await expect(tab).toBeInViewport({ ratio: 1 });
    const scroll = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(scroll).toBeLessThanOrEqual(width);
  });
}

test("V2 the conversation survives a reload and an item link, and Start over forgets it", async ({
  page,
}) => {
  await switchOn(page);
  await answerWith(page, 200, OAT_REPLY);
  await page.goto("/assistant");
  await askOnce(page, "What expires today?");
  await expect(page.getByRole("link", { name: "Oat Milk" })).toBeVisible();
  await page.reload();
  await expect(page.locator(".assistant__question")).toHaveText("What expires today?");
  await page.getByRole("link", { name: "Oat Milk" }).click();
  await expect(page).toHaveURL(/\/items\/ENDR-7K2M9QXA$/);
  await page.goBack();
  await expect(page.getByRole("link", { name: "Oat Milk" })).toBeVisible();
  await page.getByRole("button", { name: "Start over" }).click();
  const stored = await page.evaluate((key) => window.sessionStorage.getItem(key), STORAGE_KEY);
  expect(stored).toBeNull();
});

for (const [label, value] of [
  ["not JSON", "{not json"],
  ["an object", '{"question":"x"}'],
  ["a null reply", '[{"question":"x","reply":null}]'],
  ["a null segment", '[{"question":"x","reply":{"text":"x","segments":[null],"rowsChecked":0}}]'],
]) {
  test(`V3 a stored conversation that is ${label} never breaks the page`, async ({ page }) => {
    await switchOn(page);
    await page.addInitScript(
      ([key, stored]) => window.sessionStorage.setItem(key, stored),
      [STORAGE_KEY, value],
    );
    await page.goto("/assistant");
    await expect(page.getByPlaceholder("Ask about your things…")).toBeVisible();
    await expect(page.getByText("Something went wrong")).toHaveCount(0);
  });
}

test("V4 a switch turned off mid-conversation says so and links to it", async ({ page }) => {
  await switchOn(page);
  await answerWith(page, 409, {
    error: {
      code: "gemini_disabled",
      message: 'The assistant is off. Turn on "Use the assistant" in Settings → Gemini.',
      details: { reason: "assistant_off" },
    },
  });
  await page.goto("/assistant");
  await askOnce(page, "What expires today?");
  const alert = page.getByRole("alert");
  await expect(alert).toContainText("The assistant is off.");
  await expect(alert.getByRole("link", { name: "Open Gemini settings" })).toHaveAttribute(
    "href",
    "/settings#assistant-switch",
  );
});

test("V5 pressing Enter twice sends one request", async ({ page }) => {
  await switchOn(page);
  const seen: unknown[] = [];
  await page.route("**/api/v1/assistant/chat", async (route) => {
    seen.push(route.request().postDataJSON());
    await new Promise((done) => setTimeout(done, 500));
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(OAT_REPLY),
    });
  });
  await page.goto("/assistant");
  const input = page.getByPlaceholder("Ask about your things…");
  await input.fill("What expires today?");
  await input.press("Enter");
  await input.press("Enter");
  await expect(page.getByRole("link", { name: "Oat Milk" })).toBeVisible();
  expect(seen).toHaveLength(1);
  await expect(page.locator(".assistant__question")).toHaveCount(1);
});

test("V6 the switch is reached by its link, is off by default and stays on", async ({ page }) => {
  await page.request.put("/api/v1/gemini/key", { headers: WRITE, data: { key: KEY } });
  await page.goto("/settings#assistant-switch");
  const toggle = page.getByRole("switch", { name: "Use the assistant" });
  await expect(toggle).toBeInViewport();
  await expect(toggle).toHaveAttribute("aria-checked", "false");
  await expect(page.getByLabel("New Gemini API key")).toBeVisible();
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-checked", "true");
  await page.reload();
  await expect(page.getByRole("switch", { name: "Use the assistant" })).toHaveAttribute(
    "aria-checked",
    "true",
  );
});
