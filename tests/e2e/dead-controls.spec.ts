// Gate 3 of Phase 1 (ARCHITECTURE 10, the dead-control crawler, first version): on /welcome,
// /settings and the 404 page, every button, link, radio and switch is activated, and it must
// cause a navigation, a request to the app, an opened dialog, or a visible change. A disabled
// control must show why. Zero dead controls.
//
// Not clicked, by design: text boxes and the time zone select (they are typed into, not
// activated), the already-chosen option of a radio group (choosing it again changes nothing, by
// nature), and the skip link (tested on its own below).

import { expect, test } from "@playwright/test";
import type { Locator, Page, Request } from "@playwright/test";
import { resetApp, saveProfile } from "./helpers";

const CONTROLS =
  'button:not(.skip-link), a[href]:not(.skip-link), [role="radio"], [role="switch"], [role="tab"], summary';

interface Found {
  key: string;
  index: number;
}

async function keyOf(control: Locator): Promise<string> {
  return control.evaluate((el) => {
    const name =
      el.getAttribute("aria-label") ?? el.textContent?.trim() ?? el.getAttribute("href") ?? "";
    return `${el.tagName.toLowerCase()}|${el.getAttribute("role") ?? ""}|${name.slice(0, 40)}`;
  });
}

async function list(page: Page): Promise<Found[]> {
  const controls = page.locator(CONTROLS);
  const count = await controls.count();
  const found: Found[] = [];
  for (let index = 0; index < count; index++) {
    if (await controls.nth(index).isVisible()) {
      found.push({ key: await keyOf(controls.nth(index)), index });
    }
  }
  return found;
}

async function snapshot(page: Page) {
  return page.evaluate(() => ({
    url: location.href,
    html: document.body.innerHTML,
    dialogs: document.querySelectorAll("dialog[open]").length,
  }));
}

/** Click one control and say what, if anything, it did. */
async function activate(page: Page, control: Locator): Promise<string | null> {
  const before = await snapshot(page);
  let requests = 0;
  const count = (request: Request) => {
    const url = request.url();
    if (url.includes("/api/") || url.includes("/health")) requests += 1;
  };
  page.on("request", count);
  await control.click();
  await page.waitForTimeout(500);
  page.off("request", count);
  const after = await snapshot(page);
  if (after.url !== before.url) return "navigated";
  if (requests > 0) return "sent a request";
  if (after.dialogs > before.dialogs) return "opened a dialog";
  if (after.html !== before.html) return "changed the page";
  return null;
}

async function crawl(page: Page, path: string): Promise<{ dead: string[]; tested: number }> {
  await page.goto(path);
  await page.waitForLoadState("networkidle");
  const first = await list(page);
  const known = new Set(first.map((f) => f.key));
  const dead: string[] = [];
  let tested = 0;

  for (const control of first) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    const target = page.locator(CONTROLS).nth(control.index);
    if (!(await target.isEnabled())) {
      // A disabled control has to say why: it is described by visible text.
      const reason = await target.evaluate((el) => {
        const id = el.getAttribute("aria-describedby");
        return id ? (document.getElementById(id)?.textContent?.trim() ?? "") : "";
      });
      tested += 1;
      if (!reason) dead.push(`${control.key} is disabled and does not say why`);
      continue;
    }
    if ((await target.getAttribute("aria-checked")) === "true") continue; // already chosen
    tested += 1;
    const did = await activate(page, target);
    if (did === null) {
      dead.push(`${control.key} did nothing`);
      continue;
    }
    if (did === "navigated") continue;

    // It revealed more (a menu, for example): try the controls that were not there before.
    for (const extra of await list(page)) {
      if (known.has(extra.key)) continue;
      known.add(extra.key);
      const revealed = page.locator(CONTROLS).nth(extra.index);
      if ((await revealed.getAttribute("aria-checked")) === "true") continue;
      tested += 1;
      const result = await activate(page, revealed);
      if (result === null) dead.push(`${extra.key} (inside ${control.key}) did nothing`);
      if (result === "navigated") break; // left the page; the next control starts fresh
    }
  }
  return { dead, tested };
}

test.describe("dead-control crawler", () => {
  test("/welcome has no dead controls", async ({ page, request }) => {
    await resetApp(request);
    const result = await crawl(page, "/welcome");
    expect(result.tested).toBeGreaterThan(0);
    expect(result.dead).toEqual([]);
  });

  test("/settings has no dead controls", async ({ page, request }) => {
    await resetApp(request);
    await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata" });
    const result = await crawl(page, "/settings");
    expect(result.tested).toBeGreaterThan(5);
    expect(result.dead).toEqual([]);
  });

  test("the not-found page has no dead controls", async ({ page, request }) => {
    await resetApp(request);
    await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata" });
    const result = await crawl(page, "/this-page-does-not-exist");
    expect(result.tested).toBeGreaterThan(1);
    expect(result.dead).toEqual([]);
  });

  test("the skip link moves to the main content", async ({ page, request }) => {
    await resetApp(request);
    await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata" });
    await page.goto("/settings");
    await expect(page.getByRole("button", { name: "Mohammed" })).toBeVisible(); // the page is drawn
    await page.keyboard.press("Tab");
    await expect(page.getByRole("link", { name: "Skip to content" })).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/#main$/);
  });
});
