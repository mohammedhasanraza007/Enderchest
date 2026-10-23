// The dead-control crawler (ARCHITECTURE 10): on every route, every button, link, radio and
// switch is activated, and it must cause a navigation, a request to the app, an opened dialog, a
// file picker, or a visible change. A disabled control must show why. Zero dead controls.
// Phase 1 covered /welcome, /settings and the 404 page; Phase 2 adds every inventory route, each
// with real data made through the API first (gate 7).
//
// Not clicked, by design: text boxes and the time zone select (they are typed into, not
// activated), the already-chosen option of a radio group (choosing it again changes nothing, by
// nature), and the skip link (tested on its own below).

import { expect, test } from "@playwright/test";
import type { Locator, Page, Request } from "@playwright/test";
import { jpegBytes, makeItem, post, resetApp, saveProfile } from "./helpers";

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
  let pickers = 0;
  const count = (request: Request) => {
    const url = request.url();
    if (url.includes("/api/") || url.includes("/health")) requests += 1;
  };
  const picked = () => {
    pickers += 1;
  };
  page.on("request", count);
  page.on("filechooser", picked);
  await control.click();
  await page.waitForTimeout(500);
  page.off("request", count);
  page.off("filechooser", picked);
  const after = await snapshot(page);
  if (after.url !== before.url) return "navigated";
  if (requests > 0) return "sent a request";
  if (pickers > 0) return "opened a file picker";
  if (after.dialogs > before.dialogs) return "opened a dialog";
  if (after.html !== before.html) return "changed the page";
  return null;
}

// Controls that empty the page under test; inventory.spec.ts covers them on purpose.
const SKIP = /\|(Delete|Discard|Discard draft|Hide photo|Move and delete|Delete permanently)$/;

async function crawl(page: Page, path: string): Promise<{ dead: string[]; tested: number }> {
  await page.goto(path);
  await page.waitForLoadState("networkidle");
  const first = await list(page);
  const known = new Set(first.map((f) => f.key));
  const dead: string[] = [];
  let tested = 0;

  for (const control of first) {
    if (SKIP.test(control.key)) continue;
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
      if (known.has(extra.key) || SKIP.test(extra.key)) continue;
      known.add(extra.key);
      if (extra.index >= (await page.locator(CONTROLS).count())) continue; // gone after a click
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
  // Each control is tried from a fresh page load, so a page with many controls takes minutes.
  test.setTimeout(600_000);

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

  test("every inventory route has no dead controls", async ({ page, request }) => {
    await resetApp(request);
    await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata" });
    const tools = await post<{ id: number }>(request, "/api/v1/categories", { name: "Tools" });
    const garage = await post<{ id: number }>(request, "/api/v1/locations", { name: "Garage" });
    await post(request, "/api/v1/locations", { name: "Shelf", parent_id: garage.id });
    const first = await makeItem(request, {
      name: "Drill",
      category_id: tools.id,
      location_id: garage.id,
      expiry_mode: "date",
      expiry_date: "2026-01-01",
      attributes: { size: [8, 10] },
    });
    const second = await makeItem(request, { name: "Glue" });
    const trashed = await makeItem(request, { name: "Old tape" });
    await request.delete(`/api/v1/items/${trashed}`, { headers: { "X-Enderchest": "1" } });
    await page.goto("/settings");
    const photo = await jpegBytes(page);
    for (const id of [first, first]) {
      await request.post(`/api/v1/items/${id}/photos`, {
        headers: { "X-Enderchest": "1" },
        multipart: { image: { name: "a.jpg", mimeType: "image/jpeg", buffer: photo } },
      });
    }
    const drafts = await request.post("/api/v1/drafts", {
      headers: { "X-Enderchest": "1" },
      multipart: { "images[]": { name: "b.jpg", mimeType: "image/jpeg", buffer: photo } },
    });
    const draft = ((await drafts.json()) as { drafts: Array<{ id: string }> }).drafts[0]!.id;

    // Delete and discard are left out of these walks: they would empty the very page under test.
    // They are exercised on purpose in inventory.spec.ts.
    const routes = [
      "/inventory",
      `/items/${first}`,
      "/camera?mode=add",
      "/camera?mode=scan",
      "/add",
      `/add/${draft}`,
      `/labels?ids=${first},${second}`,
      "/trash",
      `/items/${trashed}`, // after /trash: Restore on either page takes it out of Trash
      "/settings",
    ];
    const report: Record<string, { tested: number; dead: string[] }> = {};
    for (const route of routes) {
      report[route] = await crawl(page, route);
    }
    for (const [route, result] of Object.entries(report)) {
      expect(result.tested, `${route} tested`).toBeGreaterThan(0);
      expect(result.dead, route).toEqual([]);
    }
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
