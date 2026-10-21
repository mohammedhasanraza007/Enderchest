// Gate 6 of Phase 1: a theme switch persists across reload with no flash; reduced motion is
// honoured.

import { expect, test } from "@playwright/test";
import { resetApp, saveProfile } from "./helpers";

const DARK_BASE = "rgb(22, 17, 13)"; // --bg-base, dark
const LIGHT_BASE = "rgb(244, 241, 234)"; // --bg-base, light

test.beforeEach(async ({ request }) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata" });
});

async function choose(page: import("@playwright/test").Page, name: "System" | "Light" | "Dark") {
  await page.getByRole("radiogroup", { name: "Theme" }).first().getByRole("radio", { name }).click();
}

test("the choice is saved on the server and survives a reload", async ({ page, request }) => {
  await page.emulateMedia({ colorScheme: "light" });
  await page.goto("/settings");
  await choose(page, "Dark");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect.poll(async () => (await (await request.get("/api/v1/profile")).json()).theme).toBe("dark");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.getByRole("radio", { name: "Dark" }).first()).toHaveAttribute("aria-checked", "true");
});

test("there is no flash: the theme is on the page before any script of the app runs", async ({
  page,
}) => {
  await page.goto("/settings");
  await choose(page, "Dark");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");

  // Hold back every script of the app, then load the page again. With the app not running at
  // all, the page must already be dark, from the server's hint and the inline script.
  await page.route("**/assets/*.js", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 2500));
    await route.continue();
  });
  await page.goto("/settings", { waitUntil: "commit" });
  await page.waitForSelector("html[data-theme]", { state: "attached" });
  const early = await page.evaluate(() => ({
    theme: document.documentElement.getAttribute("data-theme"),
    appDrawn: (document.getElementById("root")?.childElementCount ?? 0) > 0,
    background: getComputedStyle(document.documentElement).backgroundColor,
  }));
  expect(early.appDrawn).toBe(false);
  expect(early.theme).toBe("dark");
  expect(early.background).toBe(DARK_BASE);
  await page.unroute("**/assets/*.js");

  // And the same for light.
  await page.goto("/settings");
  await choose(page, "Light");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.route("**/assets/*.js", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 2500));
    await route.continue();
  });
  await page.goto("/settings", { waitUntil: "commit" });
  await page.waitForSelector("html[data-theme]", { state: "attached" });
  const earlyLight = await page.evaluate(() => ({
    appDrawn: (document.getElementById("root")?.childElementCount ?? 0) > 0,
    background: getComputedStyle(document.documentElement).backgroundColor,
  }));
  expect(earlyLight.appDrawn).toBe(false);
  expect(earlyLight.background).toBe(LIGHT_BASE);
});

test("System follows the operating system, live", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "light" });
  await page.goto("/settings");
  await choose(page, "System");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.emulateMedia({ colorScheme: "dark" });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.locator("html")).toHaveAttribute("data-theme-pref", "system");
});

test("the name menu changes the theme too", async ({ page }) => {
  await page.goto("/settings");
  await page.getByRole("button", { name: "Mohammed" }).click();
  await page.getByRole("radiogroup", { name: "Theme" }).last().getByRole("radio", { name: "Light" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
});

test("reduced motion is honoured: no crossfade, no transitions, no running animations", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/settings");
  const durations = await page.evaluate(() => {
    const css = getComputedStyle(document.documentElement);
    return ["--dur-instant", "--dur-fast", "--dur-base", "--dur-slow"].map((name) =>
      css.getPropertyValue(name).trim(),
    );
  });
  expect(durations).toEqual(["0ms", "0ms", "0ms", "0ms"]);

  // Watch for the crossfade class while the theme changes.
  await page.evaluate(() => {
    (window as unknown as { __fade: boolean }).__fade = false;
    new MutationObserver(() => {
      if (document.documentElement.classList.contains("theme-fade")) {
        (window as unknown as { __fade: boolean }).__fade = true;
      }
    }).observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
  });
  await choose(page, "Light");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.waitForTimeout(400);
  expect(await page.evaluate(() => (window as unknown as { __fade: boolean }).__fade)).toBe(false);

  const running = await page.evaluate(() => document.getAnimations().length);
  expect(running).toBe(0);
});

test("without reduced motion the theme change crossfades briefly", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.goto("/settings");
  await page.evaluate(() => {
    (window as unknown as { __fade: boolean }).__fade = false;
    new MutationObserver(() => {
      if (document.documentElement.classList.contains("theme-fade")) {
        (window as unknown as { __fade: boolean }).__fade = true;
      }
    }).observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
  });
  await choose(page, "Light");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  expect(await page.evaluate(() => (window as unknown as { __fade: boolean }).__fade)).toBe(true);
});
