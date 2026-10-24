// Phase 6 verification (written by the verifying session): paste and drop on "Do I own this?",
// the own mode and Savings by keyboard only, and the Savings loading and error states. Test data
// on the test stack: regression checks, never gate evidence (D-056).

import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { makeItem, post, resetApp, saveProfile } from "./helpers";

test.use({ reducedMotion: "reduce" });

async function start(request: Parameters<typeof resetApp>[0]) {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata" });
  return makeItem(request, { name: "13 mm spanner", price_paise: 34900, attributes: { size: "13 mm" } });
}

/** Hands the page an image file the way the browser does for a paste or a drop. */
async function giveImage(page: Page, how: "paste" | "drop") {
  await page.evaluate(async (kind) => {
    const canvas = document.createElement("canvas");
    canvas.width = 160;
    canvas.height = 120;
    canvas.getContext("2d")!.fillRect(0, 0, 160, 120);
    const blob = await new Promise<Blob>((resolve) => canvas.toBlob((b) => resolve(b!), "image/png"));
    const data = new DataTransfer();
    data.items.add(new File([blob], "screenshot.png", { type: "image/png" }));
    if (kind === "paste") {
      window.dispatchEvent(new ClipboardEvent("paste", { clipboardData: data }));
    } else {
      document
        .querySelector(".camera-controls")!
        .dispatchEvent(new DragEvent("drop", { dataTransfer: data, bubbles: true, cancelable: true }));
    }
  }, how);
}

/** Presses Tab until the focused control's name matches, or fails after `max` presses. */
async function tabTo(page: Page, name: RegExp, max = 80) {
  for (let i = 0; i < max; i += 1) {
    await page.keyboard.press("Tab");
    const label = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null;
      if (!el || el === document.body) return ""; // the body's text holds every label
      if (el instanceof HTMLInputElement) return el.labels?.[0]?.textContent?.trim() ?? "";
      return el.getAttribute("aria-label") ?? el.textContent?.trim() ?? "";
    });
    if (name.test(label)) return;
  }
  throw new Error(`Tab never reached ${name}`);
}

test("a pasted image becomes the photo to check", async ({ page, request }) => {
  await start(request);
  await page.goto("/camera?mode=own");
  await giveImage(page, "paste");
  await expect(page.getByRole("img", { name: "The photo to check" })).toBeVisible();
  await page.getByRole("button", { name: "Check", exact: true }).click();
  await expect(page.locator(".own-results")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByRole("button", { name: "None of these" })).toBeVisible();
});

test("a dropped image becomes the photo to check", async ({ page, request }) => {
  await start(request);
  await page.goto("/camera?mode=own");
  await giveImage(page, "drop");
  await expect(page.getByRole("img", { name: "The photo to check" })).toBeVisible();
});

test("own mode by keyboard only: type, check, record a saving, Escape returns focus", async ({
  page,
  request,
}) => {
  await start(request);
  await page.goto("/camera?mode=own");
  await tabTo(page, /Or type what it is/);
  await page.keyboard.type("13 mm spanner");
  await page.keyboard.press("Enter");
  await expect(page.locator(".own-results")).toBeVisible();
  await tabTo(page, /^I didn't buy it$/);
  await page.keyboard.press("Enter");
  const sheet = page.getByRole("dialog", { name: "I didn't buy it" });
  await expect(sheet).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(sheet).toHaveCount(0);
  await expect(page.getByRole("button", { name: "I didn't buy it" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(sheet).toBeVisible();
  await tabTo(page, /^Price saved/, 6);
  await page.keyboard.press("Control+A");
  await page.keyboard.type("500");
  await page.keyboard.press("Enter");
  await expect(page.getByText("₹500 saved on 13 mm spanner.")).toBeVisible();
  expect((await (await request.get("/api/v1/savings")).json()).total_paise).toBe(50000);
  for (const name of [/^Open item$/, /^Not the same$/, /^None of these$/]) await tabTo(page, name);
});

test("Savings by keyboard only: period, Remove with confirm, Undo", async ({ page, request }) => {
  await start(request);
  await post(request, "/api/v1/savings", { item_name: "Phone case", price_paise: 49900 });
  await page.goto("/savings");
  await expect(page.locator(".savings-total__amount")).toHaveText("₹499");
  await tabTo(page, /^All time$/);
  await page.keyboard.press("Enter");
  await expect(page.getByRole("radio", { name: "All time" })).toHaveAttribute("aria-checked", "true");
  await tabTo(page, /^Remove$/);
  await page.keyboard.press("Enter");
  const dialog = page.getByRole("dialog", { name: "Remove this saving?" });
  await expect(dialog).toBeVisible();
  await tabTo(page, /^Remove$/, 6);
  await page.keyboard.press("Enter");
  await expect(page.locator(".savings-total__amount")).toHaveText("₹0");
  await expect(page.getByText(/Nothing saved yet/)).toBeVisible();
});

test("Savings shows its shape while loading and a Retry when the read fails", async ({
  page,
  request,
}) => {
  await start(request);
  let fail = true;
  await page.route("**/api/v1/savings?**", async (route) => {
    if (!fail) return route.continue();
    await new Promise((resolve) => setTimeout(resolve, 800));
    await route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ error: { code: "internal_error", message: "Something went wrong." } }),
    });
  });
  await page.goto("/savings");
  await expect(page.locator(".savings-list [aria-busy='true']")).toBeVisible();
  await expect(page.getByText("Something went wrong.")).toBeVisible();
  fail = false;
  await page.getByRole("button", { name: "Retry" }).click();
  await expect(page.getByText(/Nothing saved yet/)).toBeVisible();
  await expect(page.locator(".savings-total__amount")).toHaveText("₹0");
});

test("the savings pill and the truck on today do not overlap each other or the title", async ({
  page,
  request,
}) => {
  await start(request);
  const board = await (await request.get("/api/v1/dashboard")).json();
  await post(request, "/api/v1/tasks", { title: "Clean PC", kind: "chore", first_due: board.road.start });
  await post(request, "/api/v1/savings", { item_name: "Phone case", price_paise: 49900 });
  for (const width of [1024, 1280]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    const pill = page.locator(".road__pill");
    await expect(pill).toHaveText("₹499 saved");
    const truck = page.locator(".road__truck");
    const title = page.getByText("Next 14 days", { exact: true });
    const [p, t, h] = [await pill.boundingBox(), await truck.boundingBox(), await title.boundingBox()];
    for (const other of [t, h]) {
      const apart =
        p!.x + p!.width <= other!.x ||
        other!.x + other!.width <= p!.x ||
        p!.y + p!.height <= other!.y ||
        other!.y + other!.height <= p!.y;
      expect(apart, `pill ${JSON.stringify(p)} vs ${JSON.stringify(other)} at ${width}px`).toBe(true);
    }
    await page.screenshot({ path: `/test-results/shots-phase-6v/pill-and-truck-${width}.png` });
  }
});
