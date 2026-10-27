// Screenshots of the Assistant page (P-15) for review against the owner's reference (D-097,
// docs/design/reference-assistant.md): unavailable, empty, and a conversation with links, the
// foot line and the honest miss; 1280 px dark and light, 1024 px. The answers come from
// `page.route` stubs (test code only); the owner approves the look (BLOCKED). The conversation
// state's text contrast is measured here too, since routes-contrast sees only the off state.

import { expect, test } from "@playwright/test";
import { neededRatio, resetApp, saveProfile, textPairs, worstRatio } from "./helpers";

const SHOTS = "/test-results/shots-phase-9";
const WRITE = { "X-Enderchest": "1" };
test.use({ reducedMotion: "reduce" });
test.setTimeout(180_000);

const ANSWER = {
  reply: "Oat Milk — expires today\nGreek Yogurt — 2 days left\nBaby Spinach — 5 days left",
  segments: [
    { text: "Oat Milk", public_id: "ENDR-7K2M9QXA" },
    { text: " — expires today\n", public_id: null },
    { text: "Greek Yogurt", public_id: "ENDR-4H8P2RTW" },
    { text: " — 2 days left\n", public_id: null },
    { text: "Baby Spinach", public_id: "ENDR-9C3D5FGH" },
    { text: " — 5 days left", public_id: null },
  ],
  cited: [],
  tools_used: ["items_expiring"],
  rows_checked: 3,
};
const MISS = {
  reply: "I couldn't find that in your inventory.",
  segments: [{ text: "I couldn't find that in your inventory.", public_id: null }],
  cited: [],
  tools_used: ["search_items"],
  rows_checked: 0,
};

for (const theme of ["dark", "light"] as const) {
  test(`assistant screens (${theme})`, async ({ page, request }) => {
    await resetApp(request);
    await saveProfile(request, {
      name: "Mohammed",
      timezone: "Asia/Kolkata",
      theme,
    });
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/assistant");
    await expect(page.getByText(/needs a Gemini key/)).toBeVisible();
    await page.screenshot({
      path: `${SHOTS}/assistant-nokey-${theme}-1280.png`,
    });

    await request.put("/api/v1/gemini/key", {
      headers: WRITE,
      data: { key: "AIzaTestKeyThatIsNotReal_0123456789" },
    });
    await request.patch("/api/v1/settings", {
      headers: WRITE,
      data: { assistant_share_item_text: true },
    });
    await page.goto("/assistant");
    await expect(page.getByPlaceholder("Ask about your things…")).toBeVisible();
    await page.screenshot({
      path: `${SHOTS}/assistant-empty-${theme}-1280.png`,
    });

    const replies = [ANSWER, MISS];
    await page.route("**/api/v1/assistant/chat", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(replies.shift()),
      }),
    );
    const input = page.getByPlaceholder("Ask about your things…");
    await input.fill("What's expiring this week?");
    await input.press("Enter");
    await expect(page.getByText("From your inventory · 3 items checked")).toBeVisible();
    await input.fill("Do I have a drill?");
    await input.press("Enter");
    await expect(page.getByText("I couldn't find that in your inventory.")).toBeVisible();
    await page.mouse.move(0, 0);

    const failures: string[] = [];
    for (const pair of await textPairs(page)) {
      if (worstRatio(pair) < neededRatio(pair))
        failures.push(`${pair.where} "${pair.text.slice(0, 30)}"`);
    }
    expect(failures).toEqual([]);

    for (const width of [1280, 1024]) {
      await page.setViewportSize({ width, height: 900 });
      await page.screenshot({
        path: `${SHOTS}/assistant-chat-${theme}-${width}.png`,
        fullPage: true,
      });
    }
  });
}
