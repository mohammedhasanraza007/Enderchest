// The camera coach in the browser (Phase 7 spec, gates 1 to 3). Scenes are drawn on a canvas that
// stands in for the webcam: regression tools only (D-056). Gate 1 on real captures is
// `test.bat coach`; gate 4 is the owner's live check with the real webcam.

import { expect, test } from "@playwright/test";
import type { Page, Request } from "@playwright/test";
import { resetApp, saveProfile } from "./helpers";

type Scene = "good" | "plain" | "dark" | "shake" | "glare" | "empty";

/** The webcam becomes a 1280 x 720 canvas showing `scene` on a textured desk. */
async function feed(page: Page, scene: Scene) {
  await page.addInitScript((name: Scene) => {
    navigator.mediaDevices.getUserMedia = async () => {
      const canvas = document.createElement("canvas");
      canvas.width = 1280;
      canvas.height = 720;
      const c = canvas.getContext("2d")!;
      let seed = 7;
      const random = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
      const blocks = Array.from({ length: 900 }, () => [
        random() * 1280,
        random() * 720,
        8 + random() * 24,
        60 + random() * 120,
      ]);
      // The scene is drawn once; each frame copies it (blurred for "shake") and moves it a pixel.
      const still = document.createElement("canvas");
      still.width = 1280;
      still.height = 720;
      const s = still.getContext("2d")!;
      s.fillStyle = "#8a7a6a";
      s.fillRect(0, 0, 1280, 720);
      for (const [x, y, size, shade] of blocks) {
        s.fillStyle = `rgb(${shade},${shade! * 0.9},${shade! * 0.8})`;
        s.fillRect(x!, y!, size!, size! / 3);
      }
      if (name !== "empty") {
        const lines =
          name === "plain"
            ? ["FRESH OAT DRINK", "SHAKE WELL", "KEEP COOL"]
            : ["OAT MILK BARISTA", "MODEL AB-1234X", "EXP 14/03/2027"];
        s.fillStyle = "#e6e1d8"; // paper, not blown out
        s.fillRect(200, 140, 880, 440);
        s.fillStyle = "#000000";
        s.textBaseline = "top";
        lines.forEach((line, row) => {
          s.font = `bold ${row === 0 ? 72 : 60}px sans-serif`;
          s.fillText(line, 250, 190 + row * 120);
        });
      }
      let tick = 0;
      const draw = () => {
        tick += 1;
        c.filter = name === "shake" ? "blur(10px)" : "none";
        c.drawImage(still, tick % 2, 0);
        c.filter = "none";
        if (name === "glare") {
          c.fillStyle = "#ffffff";
          c.beginPath();
          c.ellipse(900, 260, 260, 170, 0, 0, Math.PI * 2);
          c.fill();
        }
        if (name === "dark") {
          c.fillStyle = "rgba(0,0,0,0.9)";
          c.fillRect(0, 0, 1280, 720);
        }
      };
      draw();
      window.setInterval(draw, 50);
      return canvas.captureStream(20);
    };
  }, scene);
}

/** Every /capture/frame request with when it started and ended. */
function watchFrames(page: Page) {
  const spans: Array<{ start: number; end?: number }> = [];
  const open = new Map<Request, { start: number; end?: number }>();
  page.on("request", (request) => {
    if (!request.url().includes("/api/v1/capture/frame")) return;
    const span = { start: Date.now() };
    spans.push(span);
    open.set(request, span);
  });
  const close = (request: Request) => {
    const span = open.get(request);
    if (span) span.end = Date.now();
  };
  page.on("requestfinished", close);
  page.on("requestfailed", close);
  return spans;
}

const pill = (page: Page) => page.locator(".coach-pill");

test.beforeEach(async ({ request }) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata" });
});

const PROMPTS: Array<[Scene, RegExp]> = [
  ["dark", /It's dark here/],
  ["shake", /Hold steady/],
  ["glare", /lose the glare/],
  ["empty", /can't see a label yet/],
  ["good", /Model and date found|Got the model number|Date spotted/],
];

for (const [scene, words] of PROMPTS) {
  test(`the coach names the ${scene} scene`, async ({ page }) => {
    await feed(page, scene);
    await page.goto("/camera?mode=add");
    await expect(pill(page)).toHaveText(words, { timeout: 20_000 });
    await expect(pill(page)).toHaveAttribute("role", "status");
  });
}

test("a fine label keeps the coach quiet", async ({ page }) => {
  await feed(page, "plain");
  const answered = page.waitForResponse(
    (response) =>
      response.url().includes("/capture/frame") && response.status() === 200,
    { timeout: 20_000 },
  );
  await page.goto("/camera?mode=add");
  await answered;
  await page.waitForTimeout(2500);
  await expect(pill(page)).toHaveText("");
});

test("never two frames in flight, about one a second", async ({ page }) => {
  await feed(page, "good");
  const spans = watchFrames(page);
  await page.goto("/camera?mode=add");
  await page.waitForTimeout(8000);
  expect(spans.length).toBeGreaterThanOrEqual(3);
  for (let i = 1; i < spans.length; i += 1) {
    const previous = spans[i - 1]!;
    expect(previous.end, "the earlier frame had finished").toBeDefined();
    expect(spans[i]!.start).toBeGreaterThanOrEqual(previous.end!);
    // The send timer ticks every 1000 ms, but a request starts only after the JPEG encode
    // (toBlob), whose time varies per frame, so starts jitter (896 ms seen in the verification).
    // The server's own gap is 500 ms; 800 still proves "about one a second".
    expect(spans[i]!.start - previous.start).toBeGreaterThanOrEqual(800);
  }
});

test("with the coach off there is no prompt and no frame request", async ({
  page,
}) => {
  await feed(page, "dark");
  const spans = watchFrames(page);
  await page.goto("/settings");
  const toggle = page.getByRole("switch", { name: "Show camera tips" });
  await expect(toggle).toHaveAttribute("aria-checked", "true");
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-checked", "false");
  await page.goto("/camera?mode=add");
  await expect(page.getByRole("button", { name: "Take photo" })).toBeVisible();
  await page.waitForTimeout(5000);
  await expect(pill(page)).toHaveCount(0);
  expect(spans).toHaveLength(0);
});

test("Scan mode has no coach", async ({ page }) => {
  await feed(page, "good");
  const spans = watchFrames(page);
  await page.goto("/camera?mode=scan");
  await page.waitForTimeout(4000);
  await expect(pill(page)).toHaveCount(0);
  expect(spans).toHaveLength(0);
});

test("a busy answer drops the frame and the coach carries on", async ({
  page,
}) => {
  await feed(page, "good");
  let refused = 0;
  await page.route("**/api/v1/capture/frame", async (route) => {
    if (refused < 2) {
      refused += 1;
      await route.fulfill({
        status: 409,
        contentType: "application/json",
        body: JSON.stringify({
          error: { code: "busy", message: "busy", details: {} },
        }),
      });
    } else await route.continue();
  });
  await page.goto("/camera?mode=add");
  await expect(pill(page)).toHaveText(
    /Model and date found|Got the model|Date spotted/,
    {
      timeout: 20_000,
    },
  );
  expect(refused).toBe(2);
});

test("frame rate and /health while frames are read (measured, gate 2)", async ({
  page,
  request,
}) => {
  // Headless Chromium paints slower than a real screen, so the coach is compared with itself off;
  // the 60 fps gate is the owner's laptop.
  const gapsOf = () =>
    page.evaluate(
      () =>
        new Promise<number[]>((resolve) => {
          const gaps: number[] = [];
          let last = performance.now();
          const end = last + 6000;
          const step = (now: number) => {
            gaps.push(now - last);
            last = now;
            if (now < end) requestAnimationFrame(step);
            else resolve(gaps);
          };
          requestAnimationFrame(step);
        }),
    );
  const middle = (gaps: number[]) =>
    [...gaps].sort((a, b) => a - b)[Math.floor(gaps.length / 2)]!;
  await feed(page, "good");
  await request.patch("/api/v1/settings", {
    headers: { "X-Enderchest": "1" },
    data: { coach_enabled: false },
  });
  await page.goto("/camera?mode=add");
  await expect(page.getByRole("button", { name: "Take photo" })).toBeVisible();
  const off = middle(await gapsOf());
  await request.patch("/api/v1/settings", {
    headers: { "X-Enderchest": "1" },
    data: { coach_enabled: true },
  });
  await page.reload();
  await page.waitForResponse((r) => r.url().includes("/capture/frame"), {
    timeout: 20_000,
  });
  const health: number[] = [];
  const polling = (async () => {
    for (let i = 0; i < 24; i += 1) {
      const started = Date.now();
      expect((await request.get("/health")).ok()).toBe(true);
      health.push(Date.now() - started);
      await page.waitForTimeout(250);
    }
  })();
  const frames = await gapsOf();
  await polling;
  const median = middle(frames);
  const p95 = [...frames].sort((a, b) => a - b)[
    Math.floor(frames.length * 0.95)
  ]!;
  console.log(
    `COACH-FPS coach-off median=${off.toFixed(1)}ms coach-on frames=${frames.length} ` +
      `median=${median.toFixed(1)}ms p95=${p95.toFixed(1)}ms health max=${Math.max(...health)}ms`,
  );
  expect(Math.max(...health)).toBeLessThan(200);
  expect(median).toBeLessThanOrEqual(off + 2);
});

test("reduced motion: the prompt appears without a fade", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await feed(page, "dark");
  await page.goto("/camera?mode=add");
  await expect(pill(page)).toHaveText(/It's dark here/, { timeout: 20_000 });
  const duration = await pill(page).evaluate(
    (el) => getComputedStyle(el).transitionDuration,
  );
  expect(duration).toBe("0s");
});

// Shots for the look check (D-097): the coach over the camera, both themes, 1280 and 1024 px.
const SHOTS = "/test-results/shots-phase-7";
for (const theme of ["dark", "light"] as const) {
  test(`coach shots (${theme})`, async ({ page, request }) => {
    await saveProfile(request, {
      name: "Mohammed",
      timezone: "Asia/Kolkata",
      theme,
    });
    await feed(page, "good");
    for (const width of [1280, 1024]) {
      await page.setViewportSize({ width, height: 800 });
      await page.goto("/camera?mode=add");
      await expect(pill(page)).toHaveText(/found|spotted|model/, {
        timeout: 20_000,
      });
      await page.screenshot({
        path: `${SHOTS}/coach-found-${theme}-${width}.png`,
      });
    }
    await page.goto("/settings");
    await page
      .getByRole("heading", { name: "Camera coach" })
      .scrollIntoViewIfNeeded();
    await page.screenshot({
      path: `${SHOTS}/settings-coach-${theme}-1024.png`,
    });
  });
}
