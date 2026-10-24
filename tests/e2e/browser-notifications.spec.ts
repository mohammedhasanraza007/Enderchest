// Gate 8: a browser notification fires once per row, across reloads and two tabs, and the tab
// title shows the open count. Real Chromium in its new headless mode (the headless shell always
// answers "denied" for notifications); the Notification constructor is wrapped only to count
// calls, the real one still runs. Test data on the test stack.

import { expect, test } from "@playwright/test";
import type { BrowserContext } from "@playwright/test";
import { makeItem, post, resetApp, saveProfile } from "./helpers";

test.use({ channel: "chromium", reducedMotion: "reduce" });

function kolkataDay(offset = 0): string {
  const moment = new Date(Date.now() + offset * 86_400_000);
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(moment);
}

test.beforeEach(async ({ request }) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata" });
});

/** Count every Notification made in this context, by tag; the real constructor still runs. */
async function countAlerts(context: BrowserContext): Promise<Map<string, number>> {
  const counts = new Map<string, number>();
  await context.exposeBinding("__enderchestAlert", (_source, tag: string) => {
    counts.set(tag, (counts.get(tag) ?? 0) + 1);
  });
  await context.addInitScript(() => {
    const Original = window.Notification;
    const record = (window as unknown as { __enderchestAlert: (tag: string) => void })
      .__enderchestAlert;
    class Counted extends Original {
      constructor(title: string, options?: NotificationOptions) {
        record(options?.tag ?? title);
        super(title, options);
      }
    }
    Object.defineProperty(Counted, "permission", {
      get: () => Original.permission,
    });
    Object.defineProperty(Counted, "requestPermission", {
      value: Original.requestPermission.bind(Original),
    });
    window.Notification = Counted as unknown as typeof Notification;
  });
  return counts;
}

test("a browser notification fires once per row across reloads and two tabs", async ({
  browser,
  request,
  baseURL,
}) => {
  const context = await browser.newContext({ baseURL });
  await context.grantPermissions(["notifications"]);
  const counts = await countAlerts(context);
  await makeItem(request, {
    name: "Greek yogurt",
    expiry_date: kolkataDay(1),
  });
  await post(request, "/api/v1/tasks", {
    title: "Clean PC",
    first_due: kolkataDay(0),
  });
  const rows = (await (await request.get("/api/v1/notifications")).json()).items as Array<{
    id: number;
  }>;
  expect(rows).toHaveLength(2);

  const first = await context.newPage();
  const second = await context.newPage();
  await Promise.all([first.goto("/inventory"), second.goto("/inventory")]);
  for (const id of rows.map((row) => row.id)) {
    await expect.poll(() => counts.get(`enderchest-${id}`) ?? 0).toBe(1);
  }
  await expect(first).toHaveTitle("(2) Inventory · Enderchest");
  await Promise.all([first.reload(), second.reload()]);
  await first.bringToFront();
  await first.evaluate(() => window.dispatchEvent(new Event("focus")));
  await first.waitForTimeout(2_000);
  for (const id of rows.map((row) => row.id)) {
    expect(counts.get(`enderchest-${id}`)).toBe(1);
  }

  // A new row later in the session gets its own single alert.
  await makeItem(request, {
    name: "Baby spinach",
    expiry_date: kolkataDay(0),
  });
  await first.reload();
  await expect.poll(() => [...counts.values()].reduce((a, b) => a + b, 0)).toBe(3);
  await second.reload();
  await second.waitForTimeout(1_500);
  expect([...counts.values()].every((n) => n === 1)).toBe(true);

  // Settings sends a real test notification once permission is granted.
  await first.goto("/settings");
  const section = first.locator(".glass-card").filter({ hasText: "Browser notifications" });
  await expect(section).toContainText("Allowed");
  await section.getByRole("button", { name: "Send a test notification" }).click();
  await expect.poll(() => counts.get("enderchest-test") ?? 0).toBe(1);
  await context.close();
});
