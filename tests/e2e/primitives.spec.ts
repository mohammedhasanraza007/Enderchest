// Phase 1, tests item 9: a render test of every primitive in both themes (the gallery page), plus
// the shape rules of DESIGN.md 5 and the check that the rupee sign renders (gate 7).

import { writeFileSync } from "node:fs";
import { expect, test } from "@playwright/test";
import { GALLERY, setTheme } from "./helpers";

for (const theme of ["dark", "light"] as const) {
  test(`every primitive renders in the ${theme} theme`, async ({ page }) => {
    const problems: string[] = [];
    page.on("pageerror", (error) => problems.push(error.message));
    page.on("console", (message) => {
      // A failed download is reported below with its address; here only real script errors.
      if (message.type() === "error" && !message.text().startsWith("Failed to load resource")) {
        problems.push(message.text());
      }
    });
    page.on("response", (response) => {
      if (response.status() >= 400) problems.push(`${response.status()} ${response.url()}`);
    });
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(GALLERY);
    await setTheme(page, theme);

    for (const name of [
      "Banners",
      "Buttons",
      "Chips and status",
      "Overlays and toast",
      "Skeleton and brand mark",
      "Fonts and the rupee sign",
    ]) {
      await expect(page.getByRole("region", { name })).toBeVisible();
    }
    await expect(page.getByRole("heading", { name: "A frosted card" })).toBeVisible();
    await expect(page.locator(".pill--primary").first()).toBeVisible();
    await expect(page.locator(".pill--secondary").first()).toBeVisible();
    await expect(page.locator(".pill--ghost").first()).toBeVisible();
    await expect(page.locator(".pill.is-loading .pill__dot")).toBeVisible();
    await expect(page.locator(".pill:disabled + .pill__reason")).toHaveText("Nothing to save yet.");
    await expect(page.getByLabel("With an error")).toHaveAttribute("aria-invalid", "true");
    await expect(page.getByText("Enter a name of 1 to 40 characters.")).toBeVisible();
    await expect(page.getByRole("switch")).toHaveCount(2);
    await expect(page.getByRole("switch", { name: "A switch" })).toHaveAttribute("aria-checked", "true");
    await expect(page.locator(".status-chip")).toHaveCount(7); // four chips and one in each banner
    await expect(page.locator(".skeleton")).toHaveCount(1);
    await expect(page.locator("img.brand-mark")).toHaveCount(4); // nav, 32, 72, 96
    await expect(page.locator(".live-badge")).toHaveText("LIVE");

    // Dialog and sheet open on the card material and close on Escape.
    for (const [open, title] of [
      ["Open dialog", "A dialog"],
      ["Open sheet", "A sheet"],
    ] as const) {
      await page.getByRole("button", { name: open }).click();
      await expect(page.getByRole("dialog", { name: title })).toBeVisible();
      await page.keyboard.press("Escape");
      await expect(page.getByRole("dialog", { name: title })).toBeHidden();
    }
    // A toast with an action stays until it is used.
    await page.getByRole("button", { name: "Show toast" }).click();
    await expect(page.locator(".toast")).toContainText("Saved.");
    await page.locator(".toast").getByRole("button", { name: "Undo" }).click();
    await expect(page.locator(".toast")).toHaveCount(0);

    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - window.innerWidth,
    );
    expect(overflow).toBeLessThanOrEqual(0);
    expect(problems).toEqual([]);
    await page.screenshot({ path: `/test-results/gallery-${theme}.png`, fullPage: true });
  });
}

test("shape rules: pills everywhere, soft capsules for tall boxes in light, 24 px cards in dark", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(GALLERY);
  const radii = async () =>
    page.evaluate(() => {
      const pick = (selector: string) =>
        [...document.querySelectorAll(selector)].map((el) => {
          const rect = el.getBoundingClientRect();
          return {
            selector,
            height: Math.round(rect.height),
            radius: parseFloat(getComputedStyle(el).borderTopLeftRadius),
          };
        });
      return {
        pills: [
          ...pick(".pill"),
          ...pick(".field__control:not(.field__control--area)"),
          ...pick(".chip"),
          ...pick(".toggle"),
          ...pick(".status-chip"),
          ...pick(".name-pill"),
        ],
        area: pick(".field__control--area")[0],
        card: pick(".glass-card")[0],
        panel: pick(".inner-panel")[0],
        banner: pick(".banner")[0],
      };
    });

  await setTheme(page, "dark");
  const dark = await radii();
  expect(dark.card?.radius).toBe(24);
  expect(dark.panel?.radius).toBe(18);
  expect(dark.area?.radius).toBe(18); // a text area is a tall box: the panel radius
  for (const pill of dark.pills) expect(pill.radius).toBeGreaterThanOrEqual(pill.height / 2);

  await setTheme(page, "light");
  const light = await radii();
  expect(light.card?.radius).toBe(52);
  expect(light.panel?.radius).toBe(40);
  expect(light.area?.radius).toBe(28);
  expect(light.banner?.radius).toBeGreaterThanOrEqual(32); // multi-line text never sits in a full pill
  for (const pill of light.pills) expect(pill.radius).toBeGreaterThanOrEqual(pill.height / 2);
});

test("the rupee sign renders from a real font in every family (gate 7)", async ({ page }) => {
  await page.goto(GALLERY);
  await page.evaluate(() => document.fonts.ready);
  const client = await page.context().newCDPSession(page);
  await client.send("DOM.enable");
  await client.send("CSS.enable");
  const { root } = await client.send("DOM.getDocument");
  const report: Record<string, unknown> = {};
  for (const id of ["rupee-sans", "rupee-display", "rupee-mono"]) {
    const { nodeId } = await client.send("DOM.querySelector", {
      nodeId: root.nodeId,
      selector: `[data-testid=${id}]`,
    });
    const { fonts } = await client.send("CSS.getPlatformFontsForNode", { nodeId });
    const glyphs = fonts.reduce((sum, font) => sum + font.glyphCount, 0);
    report[id] = fonts.map((font) => `${font.familyName}${font.isCustomFont ? " (bundled)" : " (system)"}: ${font.glyphCount}`);
    expect(glyphs).toBe("₹1,24,500".length); // every glyph, the rupee sign included, was drawn
  }
  writeFileSync("/test-results/rupee-fonts.json", JSON.stringify(report, null, 2));
});
