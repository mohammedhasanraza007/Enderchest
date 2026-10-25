import { useEffect, useState } from "react";
import type { RefObject } from "react";
import { ApiError } from "../api/client";
import { api } from "../api/endpoints";
import {
  PREVIEW_WIDTH,
  QUIET,
  SEND_EVERY_MS,
  SEND_QUALITY,
  SEND_WIDTH,
  STALE_MS,
  choosePrompt,
  coverBox,
  measure,
  nextPrompt,
  promptWords,
  worthReading,
} from "../lib/coach";
import type { FrameReading, Metrics, PromptKind, PromptState } from "../lib/coach";

// The camera coach on the live view (Phase 7 spec; DESIGN.md 9). Every video frame is measured
// on a 320 px copy (sharpness, light, glare); about once a second, only when the frame is lit and
// sharp, one 640 px JPEG goes to the server tier, never two at once. A `busy` or `rate_limited`
// answer drops the frame; any other failure pauses the sending and the coach stays quiet, because
// it is a help and never a blocker. Turning the coach off ends the loops and aborts the request
// in flight, so no prompt and no server call remain.

const PAUSE_AFTER_ERROR_MS = 10_000;
// The camera is moving or blind: chips from an earlier frame would point at the wrong place.
const NO_CHIPS: ReadonlySet<PromptKind | null> = new Set(["dark", "blur", "no_text"]);

export interface CoachChip {
  kind: "model" | "date";
  left: number; // percent of the view
  top: number;
  below: boolean; // the box is at the top edge, so the chip sits under it
}

function placeChips(video: HTMLVideoElement, reading: FrameReading): CoachChip[] {
  const chips: CoachChip[] = [];
  for (const box of reading.boxes) {
    if (box.kind === "text" || chips.some((chip) => chip.kind === box.kind)) continue;
    const placed = coverBox(
      box,
      { width: video.videoWidth, height: video.videoHeight },
      { width: video.clientWidth, height: video.clientHeight },
    );
    if (!placed) continue;
    const below = placed.top < 10;
    chips.push({
      kind: box.kind,
      left: placed.left,
      top: below ? placed.top + placed.height : placed.top,
      below,
    });
  }
  return chips;
}

export function useCoach(
  videoRef: RefObject<HTMLVideoElement | null>,
  active: boolean,
): { message: string | null; chips: CoachChip[] } {
  const [message, setMessage] = useState<string | null>(null);
  const [chips, setChips] = useState<CoachChip[]>([]);

  useEffect(() => {
    if (!active) return;
    const preview = document.createElement("canvas");
    const previewContext = preview.getContext("2d", { willReadFrequently: true });
    const sender = document.createElement("canvas");
    const senderContext = sender.getContext("2d");
    const controller = new AbortController();
    let metrics: Metrics | null = null;
    let reading: FrameReading | null = null;
    let chipsFrom: FrameReading | null = null;
    let prompt: PromptState = QUIET;
    let inFlight = false;
    let pausedUntil = 0;
    let stopped = false;
    let frameHandle = 0;
    let onVideoFrames = false;

    function schedule() {
      const video = videoRef.current;
      onVideoFrames = !!video && typeof video.requestVideoFrameCallback === "function";
      frameHandle =
        video && onVideoFrames
          ? video.requestVideoFrameCallback(onFrame)
          : requestAnimationFrame(onFrame);
    }

    function onFrame() {
      if (stopped) return;
      const video = videoRef.current;
      if (video && previewContext && video.videoWidth > 0) {
        const width = PREVIEW_WIDTH;
        const height = Math.round((video.videoHeight / video.videoWidth) * width);
        if (preview.width !== width || preview.height !== height) {
          preview.width = width;
          preview.height = height;
        }
        previewContext.drawImage(video, 0, 0, width, height);
        metrics = measure(previewContext.getImageData(0, 0, width, height).data, width, height);
        const now = performance.now();
        const kind = choosePrompt(metrics, reading, now);
        prompt = nextPrompt(prompt, kind ? promptWords(kind, reading) : null, now);
        setMessage(prompt.shown);
        const wanted =
          reading && now - reading.at <= STALE_MS && !NO_CHIPS.has(kind) ? reading : null;
        if (wanted !== chipsFrom) {
          chipsFrom = wanted;
          setChips(wanted ? placeChips(video, wanted) : []);
        }
      }
      schedule();
    }

    function send() {
      const video = videoRef.current;
      const ready = metrics !== null && worthReading(metrics);
      if (inFlight || !ready || !video || !senderContext || video.videoWidth === 0) return;
      if (document.hidden || performance.now() < pausedUntil) return;
      inFlight = true;
      const width = Math.min(SEND_WIDTH, video.videoWidth);
      sender.width = width;
      sender.height = Math.round((video.videoHeight / video.videoWidth) * width);
      senderContext.drawImage(video, 0, 0, sender.width, sender.height);
      sender.toBlob(
        (blob) => {
          if (!blob || stopped) {
            inFlight = false;
            return;
          }
          api
            .captureFrame(blob, controller.signal)
            .then((answer) => {
              if (!stopped) reading = { ...answer, at: performance.now() };
            })
            .catch((error: unknown) => {
              if (stopped) return;
              const dropped =
                error instanceof ApiError &&
                (error.code === "busy" || error.code === "rate_limited");
              if (!dropped) pausedUntil = performance.now() + PAUSE_AFTER_ERROR_MS;
            })
            .finally(() => {
              inFlight = false;
            });
        },
        "image/jpeg",
        SEND_QUALITY,
      );
    }

    schedule();
    const timer = window.setInterval(send, SEND_EVERY_MS);
    return () => {
      stopped = true;
      controller.abort();
      window.clearInterval(timer);
      const video = videoRef.current;
      if (onVideoFrames && video) video.cancelVideoFrameCallback(frameHandle);
      else cancelAnimationFrame(frameHandle);
      setMessage(null);
      setChips([]);
    };
  }, [active, videoRef]);

  return { message, chips };
}
