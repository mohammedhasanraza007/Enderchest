import { describe, expect, it } from "vitest";
import {
  BLUR_MIN,
  DARK_MIN,
  FAR_HEIGHT,
  HOLD_MS,
  MIN_SHOWN_MS,
  QUIET,
  STALE_MS,
  choosePrompt,
  coverBox,
  glareFraction,
  grayscale,
  measure,
  medianHeight,
  nextPrompt,
  promptWords,
  worthReading,
} from "./coach";
import type { FrameBox, FrameReading, Metrics, PromptKind } from "./coach";

// Synthetic pixels only: regression checks of the rules, never evidence about real captures.

const W = 320;
const H = 180;

function image(pixel: (x: number, y: number) => number): Uint8ClampedArray {
  const rgba = new Uint8ClampedArray(W * H * 4);
  for (let y = 0; y < H; y += 1)
    for (let x = 0; x < W; x += 1) {
      const value = pixel(x, y);
      const p = (y * W + x) * 4;
      rgba[p] = value;
      rgba[p + 1] = value;
      rgba[p + 2] = value;
      rgba[p + 3] = 255;
    }
  return rgba;
}

/** Black and white stripes of `width` px: sharp edges, mid brightness, high contrast. */
const stripes = (width: number) => image((x) => (Math.floor(x / width) % 2 ? 230 : 30));
/** The same stripes, smoothed into a gentle ramp: still contrasty, no edges. */
const soft = image((x) => 130 + 100 * Math.sin((x / W) * Math.PI * 4));

const GOOD: Metrics = { sharpness: 400, brightness: 140, contrast: 50, glare: 0 };
const box = (h: number, conf = 0.9, kind: FrameBox["kind"] = "text"): FrameBox => ({
  x: 0.1,
  y: 0.1,
  w: 0.3,
  h,
  conf,
  kind,
});
const reading = (part: Partial<FrameReading>, at = 0): FrameReading => ({
  text_found: true,
  boxes: [box(0.06), box(0.06), box(0.06)],
  fields: {},
  at,
  ...part,
});

describe("client-tier metrics", () => {
  it("turns RGB into luma", () => {
    const rgba = new Uint8ClampedArray([255, 0, 0, 255, 0, 255, 0, 255, 0, 0, 255, 255]);
    expect(Array.from(grayscale(rgba, 3, 1))).toEqual([76, 149, 28]);
  });

  it("calls sharp stripes sharp and a smooth ramp blurry", () => {
    expect(measure(stripes(8), W, H).sharpness).toBeGreaterThan(BLUR_MIN);
    expect(measure(soft, W, H).sharpness).toBeLessThan(BLUR_MIN);
    expect(measure(soft, W, H).contrast).toBeGreaterThan(40);
  });

  it("measures brightness as mean luma", () => {
    expect(
      measure(
        image(() => 40),
        W,
        H,
      ).brightness,
    ).toBe(40);
    expect(
      measure(
        image(() => 40),
        W,
        H,
      ).contrast,
    ).toBe(0);
  });

  it("counts one big blown-out blob as glare, scattered bright pixels as not", () => {
    const blob = image((x, y) => (x >= 100 && x < 150 && y >= 50 && y < 100 ? 255 : 90));
    expect(glareFraction(grayscale(blob, W, H), W, H)).toBeCloseTo((50 * 50) / (W * H));
    const scattered = image((x, y) => ((x + y) % 2 === 0 ? 255 : 90));
    expect(measure(scattered, W, H).glare).toBeLessThan(0.001);
  });
});

describe("prompt choice", () => {
  const now = 10_000;

  it("follows the spec's priority: dark > blur > glare > no text > too far > found", () => {
    const all: Metrics = { sharpness: 10, brightness: 20, contrast: 30, glare: 0.5 };
    expect(choosePrompt(all, null, now)).toBe("dark");
    expect(choosePrompt({ ...all, brightness: 140 }, null, now)).toBe("blur");
    expect(choosePrompt({ ...GOOD, glare: 0.05 }, null, now)).toBe("glare");
    const noText = reading({ text_found: false, boxes: [] }, now);
    expect(choosePrompt(GOOD, noText, now)).toBe("no_text");
    const far = reading({ boxes: [box(0.01), box(0.01), box(0.015)] }, now);
    expect(choosePrompt(GOOD, far, now)).toBe("far");
    expect(choosePrompt(GOOD, reading({ fields: { model: "AB-1234X" } }, now), now)).toBe("model");
    expect(choosePrompt(GOOD, reading({ fields: { date: "2027-03-14" } }, now), now)).toBe("date");
    const both = reading({ fields: { model: "AB-1234X", date: "2027-03-14" } }, now);
    expect(choosePrompt(GOOD, both, now)).toBe("model_date");
  });

  it("is quiet when text is found and nothing is wrong, or when nothing is known yet", () => {
    expect(choosePrompt(GOOD, reading({}, now), now)).toBeNull();
    expect(choosePrompt(GOOD, null, now)).toBeNull();
    expect(
      choosePrompt(GOOD, reading({ text_found: false, boxes: [] }, 0), STALE_MS + 1),
    ).toBeNull();
  });

  it("says 'almost' when some text was seen but not enough", () => {
    const unsure = reading({ text_found: false, boxes: [box(0.05, 0.3)] }, now);
    expect(choosePrompt(GOOD, unsure, now)).toBe("unsure");
  });

  it("says 'move closer' for small text, read or unsure (D-125)", () => {
    const smallUnsure = reading({ text_found: false, boxes: [box(0.028, 0.9), box(0.03, 0.3)] });
    expect(choosePrompt(GOOD, { ...smallUnsure, at: now }, now)).toBe("far");
    const justBigEnough = reading({ boxes: [box(0.036), box(0.04), box(0.05)] }, now);
    expect(choosePrompt(GOOD, justBigEnough, now)).toBeNull();
  });

  it("treats a blank, flat frame as no label rather than blurry, and never sends it", () => {
    const flat: Metrics = { sharpness: 2, brightness: 150, contrast: 4, glare: 0 };
    expect(choosePrompt(flat, null, now)).toBe("no_text");
    expect(worthReading(flat)).toBe(false);
  });

  it("sends only lit, sharp, non-blank frames", () => {
    expect(worthReading(GOOD)).toBe(true);
    expect(worthReading({ ...GOOD, brightness: DARK_MIN - 1 })).toBe(false);
    expect(worthReading({ ...GOOD, sharpness: BLUR_MIN - 1 })).toBe(false);
    expect(worthReading({ ...GOOD, glare: 0.3 })).toBe(true); // glare still reads text
  });

  it("measures far from the confident boxes, or from every box when asked", () => {
    expect(medianHeight([box(0.01, 0.2), box(0.05), box(0.07)])).toBeCloseTo(0.06);
    expect(medianHeight([box(0.05, 0.1)])).toBeNull();
    expect(medianHeight([box(0.05, 0.1)], 0)).toBeCloseTo(0.05);
    expect(medianHeight([box(FAR_HEIGHT - 0.001)])).toBeLessThan(FAR_HEIGHT);
  });

  it("keeps every message to 12 words or fewer, and never asks a question", () => {
    const kinds: PromptKind[] = [
      "dark",
      "blur",
      "glare",
      "no_text",
      "unsure",
      "far",
      "model",
      "date",
      "model_date",
    ];
    const dated = reading({ fields: { date: "2027-03-14" } });
    for (const kind of kinds) {
      const words = promptWords(kind, dated);
      expect(words.split(/\s+/).length).toBeLessThanOrEqual(12);
      expect(words).not.toContain("?");
    }
    expect(promptWords("date", dated)).toBe("Date spotted: 14 Mar 2027.");
  });
});

describe("prompt timing", () => {
  it("shows a new prompt only after it holds, then keeps it at least 1.5 s", () => {
    let state = nextPrompt(QUIET, "Hold steady.", 0);
    expect(state.shown).toBeNull();
    state = nextPrompt(state, "Hold steady.", HOLD_MS);
    expect(state.shown).toBe("Hold steady.");
    state = nextPrompt(state, null, HOLD_MS + 10);
    state = nextPrompt(state, null, HOLD_MS + 10 + HOLD_MS);
    expect(state.shown).toBe("Hold steady."); // held, but not yet on screen for 1.5 s
    state = nextPrompt(state, null, HOLD_MS + MIN_SHOWN_MS);
    expect(state.shown).toBeNull();
  });

  it("does not flicker when the candidate changes every frame", () => {
    let state = QUIET;
    for (let t = 0; t < 3000; t += 33)
      state = nextPrompt(state, t % 66 === 0 ? "Hold steady." : "Too dark", t);
    expect(state.shown).toBeNull();
  });

  it("replaces a long-shown prompt as soon as the new one holds", () => {
    let state = nextPrompt(QUIET, "Hold steady.", 0);
    state = nextPrompt(state, "Hold steady.", HOLD_MS);
    state = nextPrompt(state, "Got the model number.", 5000);
    state = nextPrompt(state, "Got the model number.", 5000 + HOLD_MS);
    expect(state.shown).toBe("Got the model number.");
    expect(state.shownAt).toBe(5000 + HOLD_MS);
  });
});

describe("chip placement over object-fit: cover", () => {
  it("maps directly when the shapes match", () => {
    const placed = coverBox(
      { x: 0.25, y: 0.5, w: 0.5, h: 0.1 },
      { width: 1280, height: 720 },
      { width: 640, height: 360 },
    );
    expect(placed).toEqual({ left: 25, top: 50, width: 50, height: 10 });
  });

  it("accounts for the cropped sides of a 4:3 camera in a 16:9 view", () => {
    // 640x480 scaled to 640 wide is 480 tall in a 360 view: 60 px cut off the top and bottom.
    const placed = coverBox(
      { x: 0, y: 0.5, w: 1, h: 0.25 },
      { width: 640, height: 480 },
      { width: 640, height: 360 },
    );
    expect(placed?.top).toBeCloseTo(50);
    expect(placed?.height).toBeCloseTo((120 / 360) * 100);
    expect(
      coverBox(
        { x: 0, y: 0, w: 1, h: 0.05 },
        { width: 640, height: 480 },
        { width: 640, height: 360 },
      ),
    ).toBeNull();
  });
});
