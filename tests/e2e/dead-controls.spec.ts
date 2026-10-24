// The dead-control crawler (ARCHITECTURE 10): on every route, every button, link, radio and
// switch is activated, and it must cause a navigation, a request to the app, an opened dialog, a
// file picker, or a visible change. A disabled control must show why. Zero dead controls.
// Phase 1 covered /welcome, /settings and the 404 page; Phase 2 adds every inventory route, each
// with real data made through the API first (gate 7); Phase 4 adds Tasks, Notifications and an
// item with a maintenance plan and a worn inspection (gate 9).
//
// Not clicked, by design: text boxes and selects (they are typed into, not activated), the
// already-chosen option of a radio group and the nav tab of the page you are on (choosing them
// again changes nothing, by nature), the skip
// link (tested on its own below), and the controls in SKIP, which empty the page under test and
// are exercised on purpose in inventory.spec.ts.
//
// Each control is found again BY ITS NAME after every reload (never by position: sections load
// at different speeds), and only once nothing on the page is still loading.

import { expect, test } from "@playwright/test";
import type { Locator, Page, Request } from "@playwright/test";
import {
  jpegBytes,
  labelBytes,
  makeDraft,
  makeItem,
  post,
  readingSettled,
  resetApp,
  saveProfile,
} from "./helpers";

const CONTROLS =
  'button:not(.skip-link), a[href]:not(.skip-link), [role="radio"], [role="switch"], [role="tab"], summary';
const SKIP = /\|(Delete|Discard|Discard draft|Hide photo|Move and delete|Delete permanently)(#\d+)?$/;

// The browser's print dialog is not part of the app (inventory.spec.ts tests Print and its
// question); a leave-page prompt is answered "leave" so a walk never stops on it.
test.use({ actionTimeout: 15_000, navigationTimeout: 30_000 });
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.print = () => undefined;
  });
  page.on("dialog", (dialog) => void dialog.accept());
});

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

/** The controls a person can reach: inside the top open dialog when one is open (it is modal). */
async function reachable(page: Page): Promise<Locator> {
  const dialogs = page.locator("dialog[open]");
  return (await dialogs.count()) > 0 ? dialogs.last().locator(CONTROLS) : page.locator(CONTROLS);
}

/** Every visible control, keyed by kind and name; repeats get #2, #3 … in page order. */
async function list(page: Page): Promise<Found[]> {
  const controls = await reachable(page);
  const count = await controls.count();
  const seen = new Map<string, number>();
  const found: Found[] = [];
  for (let index = 0; index < count; index++) {
    if (!(await controls.nth(index).isVisible())) continue;
    const base = await keyOf(controls.nth(index));
    const n = (seen.get(base) ?? 0) + 1;
    seen.set(base, n);
    found.push({ key: n > 1 ? `${base}#${n}` : base, index });
  }
  return found;
}

async function find(page: Page, key: string): Promise<Locator | null> {
  const match = (await list(page)).find((entry) => entry.key === key);
  return match ? (await reachable(page)).nth(match.index) : null;
}

async function open(page: Page, path: string): Promise<void> {
  await page.goto(path);
  await page.waitForLoadState("networkidle");
  await expect(page.locator('[aria-busy="true"]')).toHaveCount(0);
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

/** The chosen radio, or the link to the page already open (`aria-current="page"`). */
async function alreadyChosen(control: Locator): Promise<boolean> {
  return control.evaluate(
    (el) => el.getAttribute("aria-checked") === "true" || el.getAttribute("aria-current") === "page",
  );
}

async function disabledReason(control: Locator): Promise<string> {
  return control.evaluate((el) => {
    const id = el.getAttribute("aria-describedby");
    return id ? (document.getElementById(id)?.textContent?.trim() ?? "") : "";
  });
}

async function crawl(page: Page, path: string): Promise<{ dead: string[]; tested: number }> {
  await open(page, path);
  const first = await list(page);
  const known = new Set(first.map((f) => f.key));
  const dead: string[] = [];
  let tested = 0;

  for (const control of first) {
    if (SKIP.test(control.key)) continue;
    await open(page, path);
    const target = await find(page, control.key);
    if (target === null) continue; // gone after an earlier click changed the data
    if (!(await target.isEnabled())) {
      // A disabled control has to say why: it is described by visible text.
      tested += 1;
      if (!(await disabledReason(target))) dead.push(`${control.key} is disabled and does not say why`);
      continue;
    }
    if (await alreadyChosen(target)) continue;
    tested += 1;
    const did = await activate(page, target);
    if (did === null) {
      dead.push(`${control.key} did nothing`);
      continue;
    }
    if (did === "navigated") continue;

    // It revealed more (a menu, for example): try each control that was not there before, from a
    // fresh page with the same control opened again first.
    const extras = (await list(page)).filter((e) => !known.has(e.key) && !SKIP.test(e.key));
    for (const extra of extras) {
      known.add(extra.key);
      await open(page, path);
      const parent = await find(page, control.key);
      if (parent === null || !(await parent.isEnabled())) continue; // the data changed
      await parent.click();
      await page.waitForTimeout(300);
      const revealed = await find(page, extra.key);
      if (revealed === null) continue;
      if (!(await revealed.isEnabled())) {
        tested += 1;
        if (!(await disabledReason(revealed))) {
          dead.push(`${extra.key} (inside ${control.key}) is disabled and does not say why`);
        }
        continue;
      }
      if (await alreadyChosen(revealed)) continue;
      tested += 1;
      const result = await activate(page, revealed);
      if (result === null) dead.push(`${extra.key} (inside ${control.key}) did nothing`);
    }
  }
  return { dead, tested };
}

/** Real data for the inventory routes: categories, a location tree, items, photos, a draft. */
async function seed(page: Page): Promise<Record<string, string>> {
  const request = page.request;
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
  for (let n = 0; n < 2; n++) {
    await request.post(`/api/v1/items/${first}/photos`, {
      headers: { "X-Enderchest": "1" },
      multipart: { image: { name: "a.jpg", mimeType: "image/jpeg", buffer: photo } },
    });
  }
  // Phase 4: a task due today, a repeating one, a maintenance plan and a worn inspection, so
  // Tasks, Notifications and the item's maintenance card have real rows and actions.
  const today = new Date().toISOString().slice(0, 10);
  await post(request, "/api/v1/tasks", { title: "Clean PC", first_due: today });
  await post(request, "/api/v1/tasks", { title: "Water plants", interval_days: 7, first_due: today });
  await request.put(`/api/v1/items/${first}/maintenance`, {
    headers: { "X-Enderchest": "1" },
    data: { enabled: true, interval_days: 30, first_due: today },
  });
  const blade = await makeItem(request, { name: "Saw blade" });
  await post(request, `/api/v1/items/${blade}/inspections`, { result: "worn" });
  // A read label (Phase 3), so the confirm screen has its tags, date pills and drawer.
  const draft = await makeDraft(
    request,
    await labelBytes(page, ["OAT MILK BARISTA", "MODEL AB-1234X", "EXP 03/04/2027"]),
  );
  // Phase 6: a confirmed saving, so Savings has a row with Remove and the road its pill.
  await post(request, "/api/v1/savings", { item_public_id: second, price_paise: 24000 });
  await readingSettled(request, draft);
  return { first, second, trashed, draft, blade };
}

test.describe("dead-control crawler", () => {
  // Each control is tried from a fresh page load, so a page with many controls takes minutes.
  test.setTimeout(300_000);

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

  test("the empty dashboard has no dead controls", async ({ page, request }) => {
    await resetApp(request);
    await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata" });
    const result = await crawl(page, "/");
    expect(result.tested).toBeGreaterThan(1);
    expect(result.dead).toEqual([]);
  });

  const ROUTES: Array<[string, (ids: Record<string, string>) => string]> = [
    ["the dashboard", () => "/"],
    ["Inventory", () => "/inventory"],
    ["an item", (ids) => `/items/${ids["first"]}`],
    ["an item in Trash", (ids) => `/items/${ids["trashed"]}`],
    ["Camera, add", () => "/camera?mode=add"],
    ["Camera, scan", () => "/camera?mode=scan"],
    ["Camera, do I own this", () => "/camera?mode=own"],
    ["the review queue", () => "/add"],
    ["a draft", (ids) => `/add/${ids["draft"]}`],
    ["Labels", (ids) => `/labels?ids=${ids["first"]},${ids["second"]}`],
    ["Trash", () => "/trash"],
    ["Tasks", () => "/tasks"],
    ["Notifications", () => "/notifications"],
    ["Savings", () => "/savings"],
    ["an item with a worn inspection", (ids) => `/items/${ids["blade"]}`],
    ["Settings with data", () => "/settings"],
  ];
  for (const [name, route] of ROUTES) {
    test(`${name} has no dead controls`, async ({ page }) => {
      const path = route(await seed(page));
      const result = await crawl(page, path);
      expect(result.tested, `${path} tested`).toBeGreaterThan(0);
      expect(result.dead, path).toEqual([]);
    });
  }

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
