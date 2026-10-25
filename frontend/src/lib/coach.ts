import { formatDay } from "./format";

// The camera coach's rules (Phase 7 spec; DESIGN.md 9; D-121 to D-123), kept pure so they are
// tested without a camera. The client tier measures every video frame on a 320 px grayscale copy;
// the server tier (POST /capture/frame) says whether there is text, where, and which fields were
// read. The prompt is chosen from both, one at a time, by a fixed priority.

/** The client tier's working width, in pixels. */
export const PREVIEW_WIDTH = 320;
/** The width of the frame sent to the server tier. */
export const SEND_WIDTH = 640;
export const SEND_EVERY_MS = 1000;
export const SEND_QUALITY = 0.7;

// Starting values (spec Build 1 and 2), to be tuned on the owner's real captures and recorded.
export const BLUR_MIN = 80; // variance of the Laplacian below this is blurry
export const DARK_MIN = 60; // mean luma (0 to 255) below this is too dark
export const GLARE_LUMA = 250; // a pixel brighter than this is blown out
export const GLARE_BLOB = 0.04; // one bright blob over 4% of the frame is glare
// Median text box under 3.5% of the frame height: move closer. The spec starts at 2%, but the OCR
// engine pads its boxes, so the smallest text it still reads measures 2.2 to 3.3% at 640 px and
// 2% could never fire (D-125).
export const FAR_HEIGHT = 0.035;
export const TEXT_CONFIDENCE = 0.5; // a box counts as read text from this confidence
// A frame this flat (standard deviation of luma) has nothing to focus on: it cannot be judged
// blurry, and it holds no label (an empty desk or a wall). Starting value, like the others.
export const FLAT_CONTRAST = 12;

// Timing (D-122, D-123).
export const HOLD_MS = 300; // a new prompt must hold this long before it shows
export const MIN_SHOWN_MS = 1500; // a shown prompt stays at least this long
export const STALE_MS = 2500; // a server answer older than this is unknown

export interface Metrics {
  sharpness: number;
  brightness: number;
  contrast: number;
  glare: number; // the largest bright blob, as a fraction of the frame
}

export interface FrameBox {
  x: number;
  y: number;
  w: number;
  h: number;
  conf: number;
  kind: "text" | "model" | "date";
}

export interface FrameReading {
  text_found: boolean;
  boxes: FrameBox[];
  fields: { model?: string | null; date?: string | null };
  at: number; // when the answer arrived (ms, same clock as `now`)
}

/** Luma (BT.601) of each pixel of an RGBA image. */
export function grayscale(rgba: Uint8ClampedArray, width: number, height: number): Uint8Array {
  const gray = new Uint8Array(width * height);
  for (let i = 0, p = 0; i < gray.length; i += 1, p += 4) {
    gray[i] = (77 * rgba[p]! + 150 * rgba[p + 1]! + 29 * rgba[p + 2]!) >> 8;
  }
  return gray;
}

/** Variance of the 4-neighbour Laplacian over the inner pixels: low means blurry. */
export function sharpness(gray: Uint8Array, width: number, height: number): number {
  let sum = 0;
  let squares = 0;
  let count = 0;
  for (let y = 1; y < height - 1; y += 1) {
    for (let x = 1; x < width - 1; x += 1) {
      const i = y * width + x;
      const value =
        gray[i - width]! + gray[i + width]! + gray[i - 1]! + gray[i + 1]! - 4 * gray[i]!;
      sum += value;
      squares += value * value;
      count += 1;
    }
  }
  if (count === 0) return 0;
  const mean = sum / count;
  return squares / count - mean * mean;
}

/** Mean and standard deviation of the luma. */
export function lightness(gray: Uint8Array): { mean: number; deviation: number } {
  if (gray.length === 0) return { mean: 0, deviation: 0 };
  let sum = 0;
  let squares = 0;
  for (const value of gray) {
    sum += value;
    squares += value * value;
  }
  const mean = sum / gray.length;
  return { mean, deviation: Math.sqrt(Math.max(0, squares / gray.length - mean * mean)) };
}

/** The largest 4-connected blob of blown-out pixels, as a fraction of the frame. */
export function glareFraction(gray: Uint8Array, width: number, height: number): number {
  const seen = new Uint8Array(gray.length);
  const stack = new Int32Array(gray.length);
  let top = 0;
  const visit = (i: number) => {
    if (!seen[i] && gray[i]! > GLARE_LUMA) {
      seen[i] = 1;
      stack[top++] = i;
    }
  };
  let largest = 0;
  for (let start = 0; start < gray.length; start += 1) {
    if (seen[start] || gray[start]! <= GLARE_LUMA) continue;
    let size = 0;
    visit(start);
    while (top > 0) {
      const i = stack[--top]!;
      size += 1;
      const x = i % width;
      if (x > 0) visit(i - 1);
      if (x < width - 1) visit(i + 1);
      if (i >= width) visit(i - width);
      if (i < gray.length - width) visit(i + width);
    }
    largest = Math.max(largest, size);
  }
  return gray.length === 0 ? 0 : largest / (width * height);
}

export function measure(rgba: Uint8ClampedArray, width: number, height: number): Metrics {
  const gray = grayscale(rgba, width, height);
  const { mean, deviation } = lightness(gray);
  return {
    sharpness: sharpness(gray, width, height),
    brightness: mean,
    contrast: deviation,
    glare: glareFraction(gray, width, height),
  };
}

/** The server tier is asked only about frames that are lit, sharp and not blank. */
export function worthReading(metrics: Metrics): boolean {
  return (
    metrics.brightness >= DARK_MIN &&
    metrics.contrast >= FLAT_CONTRAST &&
    metrics.sharpness >= BLUR_MIN
  );
}

export type PromptKind =
  "dark" | "blur" | "glare" | "no_text" | "unsure" | "far" | "model" | "date" | "model_date";

/** The middle height of the boxes read with at least `minConfidence`, as a fraction of the
 *  frame height. */
export function medianHeight(boxes: FrameBox[], minConfidence = TEXT_CONFIDENCE): number | null {
  const heights = boxes
    .filter((box) => box.conf >= minConfidence)
    .map((box) => box.h)
    .sort((a, b) => a - b);
  if (heights.length === 0) return null;
  const middle = Math.floor(heights.length / 2);
  return heights.length % 2 ? heights[middle]! : (heights[middle - 1]! + heights[middle]!) / 2;
}

function fresh(reading: FrameReading | null, now: number): reading is FrameReading {
  return reading !== null && now - reading.at <= STALE_MS;
}

/** Which prompt fits now, by the spec's priority: dark > blur > glare > no text > too far >
 *  found. `null` is quiet: all is well, or nothing is known yet. */
export function choosePrompt(
  metrics: Metrics,
  reading: FrameReading | null,
  now: number,
): PromptKind | null {
  if (metrics.brightness < DARK_MIN) return "dark";
  const flat = metrics.contrast < FLAT_CONTRAST;
  if (!flat && metrics.sharpness < BLUR_MIN) return "blur";
  if (metrics.glare > GLARE_BLOB) return "glare";
  if (flat) return "no_text";
  if (!fresh(reading, now)) return null;
  if (reading.boxes.length === 0) return "no_text";
  // Small text is "move closer" whether or not it was read confidently (D-125); larger text that
  // is still unsure is "almost".
  const height = medianHeight(reading.boxes, reading.text_found ? TEXT_CONFIDENCE : 0);
  if (height !== null && height < FAR_HEIGHT) return "far";
  if (!reading.text_found) return "unsure";
  const { model, date } = reading.fields;
  if (model && date) return "model_date";
  if (date) return "date";
  if (model) return "model";
  return null;
}

/** The words for a prompt (DESIGN.md 9, D-122): 12 words or fewer, calm, specific. */
export function promptWords(kind: PromptKind, reading: FrameReading | null): string {
  switch (kind) {
    case "dark":
      return "It's dark here. Find some light.";
    case "blur":
      return "Hold steady.";
    case "glare":
      return "Tilt it slightly to lose the glare.";
    case "no_text":
      return "I can't see a label yet. Try the side with printing.";
    case "unsure":
      return "Almost. Hold it still for a second.";
    case "far":
      return "Move a little closer to the label.";
    case "model":
      return "Got the model number.";
    case "date":
      return reading?.fields.date
        ? `Date spotted: ${formatDay(reading.fields.date)}.`
        : "Date spotted.";
    case "model_date":
      return "Model and date found. Take the photo.";
  }
}

export interface PromptState {
  shown: string | null;
  shownAt: number;
  candidate: string | null;
  candidateSince: number;
}

export const QUIET: PromptState = { shown: null, shownAt: 0, candidate: null, candidateSince: 0 };

/** One step of the prompt machine: a new message (or quiet) must hold `HOLD_MS` before it
 *  shows, and a shown message stays at least `MIN_SHOWN_MS`, so nothing flickers. */
export function nextPrompt(state: PromptState, candidate: string | null, now: number): PromptState {
  const next = candidate === state.candidate ? state : { ...state, candidate, candidateSince: now };
  if (next.candidate === next.shown) return next;
  const held = now - next.candidateSince >= HOLD_MS;
  const shownLongEnough = next.shown === null || now - next.shownAt >= MIN_SHOWN_MS;
  if (!held || !shownLongEnough) return next;
  return { ...next, shown: next.candidate, shownAt: now };
}

/** Where a box of the frame lands in a view that shows the video with `object-fit: cover`, as
 *  percentages of the view; null when it falls outside the visible part. */
export function coverBox(
  box: Pick<FrameBox, "x" | "y" | "w" | "h">,
  video: { width: number; height: number },
  view: { width: number; height: number },
): { left: number; top: number; width: number; height: number } | null {
  if (!video.width || !video.height || !view.width || !view.height) return null;
  const scale = Math.max(view.width / video.width, view.height / video.height);
  const offsetX = (view.width - video.width * scale) / 2;
  const offsetY = (view.height - video.height * scale) / 2;
  const left = box.x * video.width * scale + offsetX;
  const top = box.y * video.height * scale + offsetY;
  const width = box.w * video.width * scale;
  const height = box.h * video.height * scale;
  if (left + width <= 0 || top + height <= 0 || left >= view.width || top >= view.height)
    return null;
  return {
    left: (left / view.width) * 100,
    top: (top / view.height) * 100,
    width: (width / view.width) * 100,
    height: (height / view.height) * 100,
  };
}
