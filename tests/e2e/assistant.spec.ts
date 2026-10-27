// The Assistant page (P-15, Phase 9). The unavailable states and the offline error run on the
// real test backend (its Gemini address is a closed port). The conversation itself is drawn from
// `page.route` stubs: test code only, a regression check of the rendering, never gate evidence
// (the real answers are the owner's tests/live run).

import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { resetApp, saveProfile } from "./helpers";

const WRITE = { "X-Enderchest": "1" };
const KEY = "AIzaTestKeyThatIsNotReal_0123456789";

async function switchOn(page: Page) {
  await page.request.put("/api/v1/gemini/key", {
    headers: WRITE,
    data: { key: KEY },
  });
  await page.request.patch("/api/v1/settings", {
    headers: WRITE,
    data: { assistant_share_item_text: true },
  });
}

function stubReply(page: Page, replies: object[], seen: unknown[] = []) {
  return page.route("**/api/v1/assistant/chat", async (route) => {
    seen.push(route.request().postDataJSON());
    const body = replies.shift();
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });
}

const EXPIRING = {
  reply: "Oat Milk — expires today\nGreek Yogurt — 2 days left",
  segments: [
    { text: "Oat Milk", public_id: "ENDR-7K2M9QXA" },
    { text: " — expires today\n", public_id: null },
    { text: "Greek Yogurt", public_id: "ENDR-4H8P2RTW" },
    { text: " — 2 days left", public_id: null },
  ],
  cited: [],
  tools_used: ["items_expiring"],
  rows_checked: 2,
};
const MISS = {
  reply: "I couldn't find that in your inventory.",
  segments: [{ text: "I couldn't find that in your inventory.", public_id: null }],
  cited: [],
  tools_used: ["search_items"],
  rows_checked: 0,
};

test.beforeEach(async ({ request }) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata" });
});

test("the nav has an Assistant tab after Savings", async ({ page }) => {
  await page.goto("/assistant");
  const tabs = page.getByRole("navigation", { name: "Main" }).getByRole("listitem");
  await expect(tabs.last()).toHaveText("Assistant");
  await expect(page.getByRole("link", { name: "Assistant" })).toHaveAttribute(
    "aria-current",
    "page",
  );
});

test("with no key it explains and links to the switch, with no input", async ({ page }) => {
  await page.goto("/assistant");
  await expect(page.getByText(/needs a Gemini key/)).toBeVisible();
  await expect(page.getByPlaceholder("Ask about your things…")).toHaveCount(0);
  await page.getByRole("link", { name: "Open Gemini settings" }).click();
  await expect(page).toHaveURL(/\/settings#assistant-switch$/);
  await expect(page.getByRole("switch", { name: "Use the assistant" })).toBeInViewport();
});

test("with a key but the switch off it says so; the switch turns it on", async ({ page }) => {
  await page.request.put("/api/v1/gemini/key", {
    headers: WRITE,
    data: { key: KEY },
  });
  await page.goto("/assistant");
  await expect(page.getByText(/assistant is switched off/)).toBeVisible();
  await page.goto("/settings#assistant-switch");
  const toggle = page.getByRole("switch", { name: "Use the assistant" });
  await expect(toggle).toHaveAttribute("aria-checked", "false");
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-checked", "true");
  await expect(page.getByText(/matching item rows .* are sent to Gemini/)).toBeVisible();
  await page.goto("/assistant");
  await expect(page.getByPlaceholder("Ask about your things…")).toBeVisible();
});

test("offline: the real backend's error is shown with Retry", async ({ page }) => {
  await switchOn(page);
  await page.goto("/assistant");
  await expect(page.getByText(/Ask about your things: what expires/)).toBeVisible();
  await page.getByPlaceholder("Ask about your things…").fill("What expires this week?");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByRole("alert")).toContainText("could not be reached", {
    timeout: 60_000,
  });
  await expect(page.getByRole("button", { name: "Retry" })).toBeVisible();
  await expect(page.locator(".assistant__question")).toHaveText("What expires this week?");
});

test("an answer links its items, shows the foot line, and survives a visit", async ({ page }) => {
  await switchOn(page);
  const seen: unknown[] = [];
  await stubReply(page, [EXPIRING, MISS], seen);
  await page.goto("/assistant");
  const input = page.getByPlaceholder("Ask about your things…");
  await input.fill("What expires this week?");
  await input.press("Enter"); // the keyboard sends too
  await expect(page.getByRole("link", { name: "Oat Milk" })).toHaveAttribute(
    "href",
    "/items/ENDR-7K2M9QXA",
  );
  await expect(page.getByText("From your inventory · 2 items checked")).toBeVisible();
  await expect(input).toHaveValue("");

  await input.fill("Do I have a drill?");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText("I couldn't find that in your inventory.")).toBeVisible();
  await expect(page.getByText(/items checked/)).toHaveCount(1); // no foot line on the miss
  expect(seen[1]).toEqual({
    messages: [
      { role: "user", content: "What expires this week?" },
      { role: "assistant", content: EXPIRING.reply },
      { role: "user", content: "Do I have a drill?" },
    ],
  });

  await page.goto("/savings");
  await page.goBack();
  await expect(page.locator(".assistant__question")).toHaveCount(2);
  await page.getByRole("button", { name: "Start over" }).click();
  await expect(page.locator(".assistant__question")).toHaveCount(0);
  await page.reload();
  await expect(page.getByText(/Ask about your things: what expires/)).toBeVisible();
});

test("an empty send asks for a question; sending disables the input", async ({ page }) => {
  await switchOn(page);
  await page.route("**/api/v1/assistant/chat", async (route) => {
    await new Promise((done) => setTimeout(done, 800));
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MISS),
    });
  });
  await page.goto("/assistant");
  const send = page.getByRole("button", { name: "Send" });
  await send.click();
  await expect(page.getByText("Type a question first.")).toBeVisible();
  await page.getByPlaceholder("Ask about your things…").fill("Spanner?");
  await send.click();
  await expect(page.getByPlaceholder("Ask about your things…")).toBeDisabled();
  await expect(send).toBeDisabled();
  await expect(
    page.getByRole("status").filter({ hasText: "Checking your inventory" }),
  ).toBeVisible();
  await expect(page.getByText("I couldn't find that in your inventory.")).toBeVisible();
});

test("at 1024 px the six tabs and the name pill fit inside the capsule", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 800 });
  await page.goto("/assistant");
  const capsule = await page.locator(".nav__capsule").boundingBox();
  const pill = await page.getByRole("button", { name: "Mohammed" }).boundingBox();
  expect(capsule && pill).toBeTruthy();
  expect(pill!.x + pill!.width).toBeLessThanOrEqual(capsule!.x + capsule!.width);
  const scroll = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(scroll).toBeLessThanOrEqual(1024);
});
