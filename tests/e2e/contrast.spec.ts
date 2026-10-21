// Gate 2 of Phase 1: contrast passes in both themes against the opaque tokens and the status
// chips, and the recorded ratios match the tables in DESIGN.md 4.3 and 4.5.

import { writeFileSync } from "node:fs";
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import {
  GALLERY,
  contrast,
  neededRatio,
  setTheme,
  textPairs,
  tokenColour,
  worstRatio,
} from "./helpers";

// Colours are measured at rest: with reduced motion the theme switch has no crossfade, so no
// element is caught half way between the two themes.
test.use({ reducedMotion: "reduce" });

// DESIGN.md 4.3 (text contrast on each glass surface), 4.1 (cream and clay) and 4.5 (status chip).
// [text token, surface token, ratio in the table, tolerance]
const DARK_TABLE: Array<[string, string, number, number]> = [
  ["--text", "--surface-nav", 8.7, 0.1],
  ["--text", "--surface-nav-glow", 7.0, 0.1],
  ["--text-muted-glass", "--surface-nav", 6.5, 0.1],
  ["--text-muted-glass", "--surface-nav-glow", 5.3, 0.1],
  ["--text", "--surface-nav-active", 6.3, 0.1],
  ["--text-muted-glass", "--surface-nav-active", 4.8, 0.1],
  ["--text", "--surface-name-pill", 5.3, 0.1],
  ["--text", "--surface-card-top", 6.2, 0.1],
  ["--text-muted-glass", "--surface-card-top", 4.7, 0.1],
  ["--text", "--surface-card-bottom", 9.4, 0.1],
  ["--text-muted-glass", "--surface-card-bottom", 7.1, 0.1],
  ["--text", "--surface-panel", 6.5, 0.1],
  ["--text-muted-glass", "--surface-panel", 4.9, 0.1],
  ["--text", "--surface-pill", 5.3, 0.1],
  ["--text", "--surface-road", 11.4, 0.1],
  ["--text-muted-glass", "--surface-road", 8.6, 0.1],
  ["--on-cream", "--cream-fill", 14.5, 0.1],
  ["--on-clay", "--clay-badge", 4.6, 0.1],
  ["--chip-success", "--status-chip-fill", 7.11, 0.02],
  ["--chip-warning", "--status-chip-fill", 8.0, 0.02],
  ["--chip-danger", "--status-chip-fill", 5.77, 0.02],
  ["--chip-info", "--status-chip-fill", 7.11, 0.02],
  ["--text", "--status-chip-fill", 16.2, 0.1],
];

// DESIGN.md 4.5, light theme text variants on the page background, and 4.4 muted text.
const LIGHT_TABLE: Array<[string, string, number, number]> = [
  ["--success-text", "--bg-base", 5.38, 0.02],
  ["--warning-text", "--bg-base", 5.0, 0.02],
  ["--danger-text", "--bg-base", 4.77, 0.02],
  ["--info-text", "--bg-base", 4.94, 0.02],
  ["--text-muted-page", "--bg-base", 5.6, 0.15],
];

async function allText(page: Page) {
  // Overlays are shown one at a time, so each is measured while it is open.
  const pairs = await textPairs(page);
  for (const [button, closer] of [
    ["Open dialog", "Escape"],
    ["Open sheet", "Escape"],
  ] as const) {
    await page.getByRole("button", { name: button }).click();
    pairs.push(...(await textPairs(page)));
    await page.keyboard.press(closer);
  }
  await page.getByRole("button", { name: "Show toast" }).click();
  await expect(page.locator(".toast")).toBeVisible();
  pairs.push(...(await textPairs(page)));
  return pairs;
}

for (const theme of ["dark", "light"] as const) {
  test.describe(`${theme} theme`, () => {
    test(`every piece of text on every primitive passes WCAG AA`, async ({ page }) => {
      await page.goto(GALLERY);
      await setTheme(page, theme);
      const pairs = await allText(page);
      expect(pairs.length).toBeGreaterThan(30); // the gallery really was measured

      const failing = pairs
        .filter((pair) => worstRatio(pair) < neededRatio(pair))
        .map(
          (pair) =>
            `${pair.where} "${pair.text.slice(0, 30)}" ${worstRatio(pair).toFixed(2)} < ${neededRatio(pair)}`,
        );

      // Record the lowest ratio per distinct text and surface colour, for the evidence log.
      const summary = new Map<string, { ratio: number; samples: number }>();
      for (const pair of pairs) {
        const key = `rgb(${pair.fg.join(",")}) on ${pair.backgrounds.map((b) => `rgb(${b.join(",")})`).join(" / ")}`;
        const entry = summary.get(key) ?? { ratio: Infinity, samples: 0 };
        summary.set(key, {
          ratio: Math.min(entry.ratio, worstRatio(pair)),
          samples: entry.samples + 1,
        });
      }
      writeFileSync(
        `/test-results/contrast-${theme}.json`,
        JSON.stringify(
          { theme, measured: pairs.length, failing, pairs: Object.fromEntries(summary) },
          null,
          2,
        ),
      );
      expect(failing).toEqual([]);
    });

    test("the ratios match the tables in DESIGN.md", async ({ page }) => {
      await page.goto(GALLERY);
      await setTheme(page, theme);
      const table = theme === "dark" ? DARK_TABLE : LIGHT_TABLE;
      const rows: string[] = [];
      const wrong: string[] = [];
      for (const [textToken, surfaceToken, expected, tolerance] of table) {
        const measured = contrast(
          await tokenColour(page, textToken),
          await tokenColour(page, surfaceToken),
        );
        rows.push(`${textToken} on ${surfaceToken}: ${measured.toFixed(2)} (table ${expected})`);
        if (Math.abs(measured - expected) > tolerance) {
          wrong.push(`${textToken} on ${surfaceToken}: ${measured.toFixed(2)}, table says ${expected}`);
        }
      }
      writeFileSync(`/test-results/contrast-table-${theme}.txt`, rows.join("\n") + "\n");
      expect(wrong).toEqual([]);
    });
  });
}

test("light theme text on its surfaces also clears 4.5:1 (no table exists for these)", async ({
  page,
}) => {
  await page.goto(GALLERY);
  await setTheme(page, "light");
  const weak: string[] = [];
  for (const surface of [
    "--surface-nav",
    "--surface-card-top",
    "--surface-card-bottom",
    "--surface-panel",
    "--surface-pill",
    "--surface-nav-active",
    "--surface-name-pill",
  ]) {
    for (const text of ["--text", "--text-muted-glass"]) {
      const ratio = contrast(await tokenColour(page, text), await tokenColour(page, surface));
      if (ratio < 4.5) weak.push(`${text} on ${surface}: ${ratio.toFixed(2)}`);
    }
  }
  expect(weak).toEqual([]);
});
