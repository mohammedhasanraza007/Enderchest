// Shared helpers for the browser tests: talking to the test app, and WCAG contrast arithmetic.
// Everything here is test code; nothing is shipped.

import type { APIRequestContext, Page } from "@playwright/test";

export const GALLERY = "http://127.0.0.1:4173/gallery.html";

/** Wipe the TEST database (POST /api/v1/test/reset): a brand-new first run. Test stack only. */
export async function resetApp(request: APIRequestContext): Promise<void> {
  const response = await request.post("/api/v1/test/reset", { headers: { "X-Enderchest": "1" } });
  if (!response.ok()) throw new Error(`reset failed: ${response.status()}`);
}

/** Complete first run through the API, so a spec can start on a normal page. */
export async function saveProfile(
  request: APIRequestContext,
  body: { name: string; timezone: string; theme?: "system" | "light" | "dark" },
): Promise<void> {
  const response = await request.put("/api/v1/profile", {
    headers: { "X-Enderchest": "1" },
    data: body,
  });
  if (!response.ok()) throw new Error(`profile save failed: ${response.status()}`);
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
