// Shared helpers for the browser tests: talking to the test app, and WCAG contrast arithmetic.
// Everything here is test code; nothing is shipped.

import type { APIRequestContext, Page } from "@playwright/test";

export const GALLERY = "http://127.0.0.1:4173/gallery.html";

/** Wipe the TEST database (POST /api/v1/test/reset): a brand-new first run. Test stack only. */
export async function resetApp(request: APIRequestContext): Promise<void> {
  const response = await request.post("/api/v1/test/reset", { headers: { "X-Enderchest": "1" } });
  if (!response.ok()) throw new Error(`reset failed: ${response.status()}`);
}

/** Complete first run through the API (name, then step 2 skipped), so a spec starts in the app. */
export async function saveProfile(
  request: APIRequestContext,
  body: { name: string; timezone: string; theme?: "system" | "light" | "dark" },
): Promise<void> {
  const response = await request.put("/api/v1/profile", {
    headers: { "X-Enderchest": "1" },
    data: body,
  });
  if (!response.ok()) throw new Error(`profile save failed: ${response.status()}`);
  const done = await request.patch("/api/v1/settings", {
    headers: { "X-Enderchest": "1" },
    data: { first_run_step: "done" },
  });
  if (!done.ok()) throw new Error(`first-run step failed: ${done.status()}`);
}

const WRITE = { "X-Enderchest": "1" };

/** POST JSON to the test app and return the body; throws on any refusal. */
export async function post<T>(request: APIRequestContext, path: string, data?: unknown): Promise<T> {
  const response = await request.post(path, { headers: WRITE, data });
  if (!response.ok()) {
    throw new Error(`${path} failed: ${response.status()} ${await response.text()}`);
  }
  return (await response.json()) as T;
}

/** Load the named test fixture (API 2.17), for example items-1000. Test stack only. */
export async function loadFixture(request: APIRequestContext, name: string): Promise<void> {
  await post(request, `/api/v1/test/fixtures/${name}`);
}

/** Make one item through the API and return its public id. */
export async function makeItem(
  request: APIRequestContext,
  fields: Record<string, unknown> = {},
): Promise<string> {
  const item = await post<{ public_id: string }>(request, "/api/v1/items", {
    name: "Torch",
    ...fields,
  });
  return item.public_id;
}

/** A small real JPEG drawn by the browser's own canvas (test data, never gate evidence). */
export async function jpegBytes(page: Page, colour = "#a0522d"): Promise<Buffer> {
  const base64 = await page.evaluate(async (fill) => {
    const canvas = document.createElement("canvas");
    canvas.width = 320;
    canvas.height = 240;
    const context = canvas.getContext("2d")!;
    context.fillStyle = fill;
    context.fillRect(0, 0, 320, 240);
    const blob = await new Promise<Blob>((resolve) =>
      canvas.toBlob((made) => resolve(made!), "image/jpeg"),
    );
    const bytes = new Uint8Array(await blob.arrayBuffer());
    let text = "";
    for (const byte of bytes) text += String.fromCharCode(byte);
    return btoa(text);
  }, colour);
  return Buffer.from(base64, "base64");
}

export async function setTheme(page: Page, theme: "light" | "dark"): Promise<void> {
  await page.evaluate((value) => {
    document.documentElement.setAttribute("data-theme-pref", value);
    document.documentElement.setAttribute("data-theme", value);
  }, theme);
}

// ---- WCAG 2.2 contrast ---------------------------------------------------------------------

export type Rgb = [number, number, number];

function channel(value: number): number {
  const v = value / 255;
  return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
}

export function luminance([r, g, b]: Rgb): number {
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

export function contrast(a: Rgb, b: Rgb): number {
  const [light, dark] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (light + 0.05) / (dark + 0.05);
}

export function parseRgb(css: string): Rgb {
  const parts = css.match(/-?\d+(\.\d+)?/g)?.map(Number);
  if (!parts || parts.length < 3) throw new Error(`cannot read colour ${css}`);
  return [parts[0]!, parts[1]!, parts[2]!];
}

/** The computed colour of a CSS variable, as the browser resolves it. */
export async function tokenColour(page: Page, token: string): Promise<Rgb> {
  const css = await page.evaluate((name) => {
    const probe = document.createElement("span");
    probe.style.color = `var(${name})`;
    document.body.append(probe);
    const value = getComputedStyle(probe).color;
    probe.remove();
    return value;
  }, token);
  return parseRgb(css);
}

export interface TextPair {
  where: string;
  text: string;
  fg: Rgb;
  backgrounds: Rgb[];
  fontSize: number;
  bold: boolean;
}

/**
 * Every piece of visible text on the page with its colour and the opaque colour(s) behind it
 * (the nearest ancestor with an opaque fill; a gradient contributes each of its stops, and the
 * worst one counts). Disabled controls are skipped: WCAG exempts inactive components.
 */
export async function textPairs(page: Page): Promise<TextPair[]> {
  return page.evaluate(() => {
    type Colour = [number, number, number];
    const read = (css: string): { c: Colour; a: number } | null => {
      const m = css.match(/rgba?\(([^)]+)\)/);
      if (!m || !m[1]) return null;
      const p = m[1].split(/[ ,/]+/).filter(Boolean).map(Number);
      return { c: [p[0] ?? 0, p[1] ?? 0, p[2] ?? 0], a: p.length > 3 ? (p[3] ?? 1) : 1 };
    };
    const behind = (start: Element): Colour[] => {
      for (let el: Element | null = start; el; el = el.parentElement) {
        const style = getComputedStyle(el);
        if (style.backgroundImage.includes("gradient")) {
          const stops = [...style.backgroundImage.matchAll(/rgba?\([^)]+\)/g)]
            .map((m) => read(m[0]))
            .filter((s): s is { c: Colour; a: number } => s !== null && s.a >= 0.99);
          if (stops.length) return stops.map((s) => s.c);
        }
        const fill = read(style.backgroundColor);
        if (fill && fill.a >= 0.99) return [fill.c];
      }
      return [[255, 255, 255]];
    };
    const label = (el: Element): string => {
      const id = el.id ? `#${el.id}` : "";
      const cls = typeof el.className === "string" && el.className ? `.${el.className.split(" ")[0]}` : "";
      return `${el.tagName.toLowerCase()}${id}${cls}`;
    };

    const found: Array<{
      where: string;
      text: string;
      fg: Colour;
      backgrounds: Colour[];
      fontSize: number;
      bold: boolean;
    }> = [];
    for (const el of document.querySelectorAll("body *")) {
      const own = [...el.childNodes]
        .filter((n) => n.nodeType === Node.TEXT_NODE)
        .map((n) => n.textContent?.trim() ?? "")
        .join(" ")
        .trim();
      const isField = el.matches("input, select");
      if (!own && !isField) continue;
      if (el.getClientRects().length === 0) continue;
      const style = getComputedStyle(el);
      if (style.visibility === "hidden" || style.display === "none") continue;
      if (el.closest(":disabled, [disabled]")) continue;
      if (el.closest("[aria-hidden='true']") && !own) continue;
      const fg = read(style.color);
      if (!fg) continue;
      found.push({
        where: label(el),
        text: own || (el as HTMLInputElement).value || "",
        fg: fg.c,
        backgrounds: behind(el),
        fontSize: parseFloat(style.fontSize),
        bold: parseInt(style.fontWeight, 10) >= 700,
      });
    }
    return found;
  });
}

/** WCAG large text: 24 px, or 18.66 px and bold. Large text needs 3:1, other text 4.5:1. */
export function neededRatio(pair: TextPair): number {
  return pair.fontSize >= 24 || (pair.fontSize >= 18.66 && pair.bold) ? 3 : 4.5;
}

export function worstRatio(pair: TextPair): number {
  return Math.min(...pair.backgrounds.map((bg) => contrast(pair.fg, bg)));
}

// ---- smart capture (Phase 3) ---------------------------------------------------------------

/**
 * A product label drawn by the browser's canvas: black text on white, the first line twice as
 * big. It reads far more cleanly than a real pack, so it is a regression tool for the reading
 * flow and never accuracy evidence (D-056).
 */
export async function labelBytes(page: Page, lines: string[]): Promise<Buffer> {
  const base64 = await page.evaluate(async (rows) => {
    const canvas = document.createElement("canvas");
    canvas.width = 1200;
    canvas.height = 120 + rows.length * 90;
    const context = canvas.getContext("2d")!;
    context.fillStyle = "#ffffff";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.fillStyle = "#000000";
    context.textBaseline = "top";
    let top = 50;
    rows.forEach((row, index) => {
      const size = index === 0 ? 80 : 40;
      context.font = `${size}px sans-serif`;
      context.fillText(row, 50, top);
      top += size + 36;
    });
    const blob = await new Promise<Blob>((resolve) =>
      canvas.toBlob((made) => resolve(made!), "image/jpeg", 0.92),
    );
    const bytes = new Uint8Array(await blob.arrayBuffer());
    let text = "";
    for (const byte of bytes) text += String.fromCharCode(byte);
    return btoa(text);
  }, lines);
  return Buffer.from(base64, "base64");
}

/** Upload one photo as a new draft and return its id; the app starts reading it at once. */
export async function makeDraft(request: APIRequestContext, image: Buffer): Promise<string> {
  const response = await request.post("/api/v1/drafts", {
    headers: WRITE,
    multipart: { "images[]": { name: "label.jpg", mimeType: "image/jpeg", buffer: image } },
  });
  if (!response.ok()) throw new Error(`draft failed: ${response.status()} ${await response.text()}`);
  return ((await response.json()) as { drafts: Array<{ id: string }> }).drafts[0]!.id;
}

/** Wait until no reading of the draft is pending (the app reads in the background). */
export async function readingSettled(request: APIRequestContext, draftId: string): Promise<void> {
  for (let tries = 0; tries < 120; tries += 1) {
    const draft = (await (await request.get(`/api/v1/drafts/${draftId}`)).json()) as {
      ocr_status: string;
      gemini_status: string;
    };
    if (draft.ocr_status !== "pending" && draft.gemini_status !== "pending") return;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error("the reading never finished");
}
