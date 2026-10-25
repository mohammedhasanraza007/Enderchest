// Phase 7 gate 1 on real captures (`test.bat coach`): both coach tiers on the owner's photos.
// Each photo in tests\fixtures\private\phase7 is named by what it shows: dark-, shake-, glare-,
// empty-, far- or good- (any other name is measured without an expectation). The browser decodes
// and scales the photo as the camera page scales a video frame (1280 px, then 320 px); the rules
// are the app's own lib/coach.ts; the server tier is the test app's real POST /capture/frame. The
// table is written to /results/coach-table.txt. Runs only with E2E_PROJECT=coach.

import { mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import {
  BLUR_MIN,
  DARK_MIN,
  FAR_HEIGHT,
  FLAT_CONTRAST,
  GLARE_BLOB,
  PREVIEW_WIDTH,
  SEND_QUALITY,
  SEND_WIDTH,
  choosePrompt,
  measure,
  medianHeight,
  promptWords,
  worthReading,
} from "../../frontend/src/lib/coach";
import type {
  FrameReading,
  Metrics,
  PromptKind,
} from "../../frontend/src/lib/coach";

const CAPTURES = process.env["COACH_CAPTURES"] ?? "/captures";
const RESULTS = process.env["COACH_RESULTS"] ?? "/results";
const VIDEO_WIDTH = 1280; // a camera frame is at most this wide (P-06 asks for 1280 x 720)

// What each named condition should produce; null is the quiet coach.
const EXPECTED: Record<string, Array<PromptKind | null>> = {
  dark: ["dark"],
  shake: ["blur"],
  glare: ["glare"],
  empty: ["no_text"],
  far: ["far"],
  good: [null, "model", "date", "model_date"],
};

interface Sent {
  status: number;
  ms: number;
  body: Omit<FrameReading, "at"> | null;
}

/** The photo scaled like a video frame, then to the client tier's 320 px, as RGBA. */
async function preview(
  page: Page,
  jpeg: string,
): Promise<{ rgba: Uint8ClampedArray; h: number }> {
  const result = await page.evaluate(
    async ({ data, videoWidth, previewWidth }) => {
      const image = new Image();
      image.src = `data:image/jpeg;base64,${data}`;
      await image.decode();
      const frame = document.createElement("canvas");
      frame.width = Math.min(videoWidth, image.naturalWidth);
      frame.height = Math.round(
        (image.naturalHeight / image.naturalWidth) * frame.width,
      );
      frame.getContext("2d")!.drawImage(image, 0, 0, frame.width, frame.height);
      const small = document.createElement("canvas");
      small.width = previewWidth;
      small.height = Math.round((frame.height / frame.width) * previewWidth);
      const context = small.getContext("2d", { willReadFrequently: true })!;
      context.drawImage(frame, 0, 0, small.width, small.height);
      const pixels = context.getImageData(0, 0, small.width, small.height).data;
      let text = "";
      for (let i = 0; i < pixels.length; i += 1)
        text += String.fromCharCode(pixels[i]!);
      return { pixels: btoa(text), height: small.height };
    },
    { data: jpeg, videoWidth: VIDEO_WIDTH, previewWidth: PREVIEW_WIDTH },
  );
  return {
    rgba: new Uint8ClampedArray(Buffer.from(result.pixels, "base64")),
    h: result.height,
  };
}

/** The 640 px frame the camera page would send, posted to the real server tier. */
async function send(page: Page, jpeg: string): Promise<Sent> {
  return page.evaluate(
    async ({ data, videoWidth, sendWidth, quality }) => {
      const image = new Image();
      image.src = `data:image/jpeg;base64,${data}`;
      await image.decode();
      const frame = document.createElement("canvas");
      frame.width = Math.min(videoWidth, image.naturalWidth);
      frame.height = Math.round(
        (image.naturalHeight / image.naturalWidth) * frame.width,
      );
      frame.getContext("2d")!.drawImage(image, 0, 0, frame.width, frame.height);
      const sent = document.createElement("canvas");
      sent.width = Math.min(sendWidth, frame.width);
      sent.height = Math.round((frame.height / frame.width) * sent.width);
      sent.getContext("2d")!.drawImage(frame, 0, 0, sent.width, sent.height);
      const blob = await new Promise<Blob>((resolve) =>
        sent.toBlob((made) => resolve(made!), "image/jpeg", quality),
      );
      const form = new FormData();
      form.append("image", blob, "frame.jpg");
      const started = performance.now();
      const response = await fetch("/api/v1/capture/frame", {
        method: "POST",
        headers: { "X-Enderchest": "1" },
        body: form,
      });
      const ms = Math.round(performance.now() - started);
      return {
        status: response.status,
        ms,
        body: response.ok ? await response.json() : null,
      };
    },
    {
      data: jpeg,
      videoWidth: VIDEO_WIDTH,
      sendWidth: SEND_WIDTH,
      quality: SEND_QUALITY,
    },
  );
}

const pct = (value: number) => `${(value * 100).toFixed(1)}%`;

test("coach tiers on the owner's captures", async ({ page }) => {
  test.setTimeout(30 * 60_000);
  const files = readdirSync(CAPTURES)
    .filter((name) => /\.jpe?g$/i.test(name))
    .sort();
  expect(files.length, `no JPEG captures in ${CAPTURES}`).toBeGreaterThan(0);
  await page.goto("/health");

  const rows: string[] = [];
  let matched = 0;
  let judged = 0;
  for (const name of files) {
    const jpeg = readFileSync(join(CAPTURES, name)).toString("base64");
    const { rgba, h } = await preview(page, jpeg);
    const metrics: Metrics = measure(rgba, PREVIEW_WIDTH, h);
    let reading: FrameReading | null = null;
    let sent: Sent | null = null;
    if (worthReading(metrics)) {
      for (let attempt = 0; attempt < 6; attempt += 1) {
        await page.waitForTimeout(700); // the server takes at most two frames a second
        sent = await send(page, jpeg);
        if (sent.status !== 409 && sent.status !== 429) break;
      }
      if (sent?.body) reading = { ...sent.body, at: 0 };
    }
    const kind = choosePrompt(metrics, reading, 0);
    const condition = name.split(/[-_.]/)[0]!.toLowerCase();
    const expected = EXPECTED[condition];
    let verdict = "-";
    if (expected) {
      judged += 1;
      verdict = expected.includes(kind) ? "match" : "MISMATCH";
      if (verdict === "match") matched += 1;
    }
    const height = reading
      ? medianHeight(reading.boxes, reading.text_found ? 0.5 : 0)
      : null;
    rows.push(
      [
        name,
        condition,
        metrics.sharpness.toFixed(0),
        metrics.brightness.toFixed(0),
        metrics.contrast.toFixed(0),
        pct(metrics.glare),
        sent ? `${sent.status} ${sent.ms} ms` : "not sent",
        reading ? String(reading.text_found) : "-",
        reading ? String(reading.boxes.length) : "-",
        height === null ? "-" : pct(height),
        reading ? JSON.stringify(reading.fields) : "-",
        kind ?? "quiet",
        kind ? promptWords(kind, reading) : "",
        verdict,
      ].join(" | "),
    );
  }

  const report = [
    `Phase 7 coach on real captures, ${new Date().toISOString()}`,
    `Thresholds: blurry below ${BLUR_MIN}, dark below ${DARK_MIN}, flat below ${FLAT_CONTRAST} sd,` +
      ` glare blob above ${pct(GLARE_BLOB)}, move closer below ${pct(FAR_HEIGHT)} box height`,
    "file | condition | sharpness | brightness | contrast sd | glare | server | text_found |" +
      " boxes | median box h | fields | prompt | words | verdict",
    ...rows,
    `Named conditions matched: ${matched} of ${judged}`,
  ].join("\n");
  mkdirSync(RESULTS, { recursive: true });
  writeFileSync(join(RESULTS, "coach-table.txt"), `${report}\n`);
  console.log(report);
});
