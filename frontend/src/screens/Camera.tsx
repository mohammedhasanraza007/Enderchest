import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent, RefObject } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import jsQR from "jsqr";
import { ApiError } from "../api/client";
import { api } from "../api/endpoints";
import { useRefreshInventory } from "../api/queries";
import { useCamera } from "../hooks/useCamera";
import type { CameraState } from "../hooks/useCamera";
import { usePageTitle } from "../hooks/usePageTitle";
import { isPublicId } from "../lib/ids";
import { ItemFormSheet } from "../patterns/ItemFormSheet";
import { Button } from "../primitives/Button";
import { Chip } from "../primitives/Chip";
import { GlassCard, InnerPanel } from "../primitives/Glass";
import { Input, Select } from "../primitives/Input";
import { OwnControls } from "./OwnCheck";

// P-06, the camera hub. Add mode: the shutter, Upload photos, drag and drop and paste all make
// drafts (one per photo, up to 20) and open the review. Scan mode reads printed QR labels with a
// JavaScript decoder about five times a second (D-055) and offers a typed-ID field. "Do I own
// this?" (P-13, Phase 6) checks a photo or words against the inventory (OwnCheck.tsx). The stream
// stops when this page is left or the tab is hidden.

const MAX_FILES = 20;
const IMAGE_TYPES = "image/jpeg,image/png,image/webp";
const SCAN_EVERY_MS = 200;

const CAMERA_TEXT: Record<Exclude<CameraState, "live">, { title: string; body: string }> = {
  starting: {
    title: "Asking for the camera",
    body: "Your browser asks once. The camera is used only while this page is open, and photos stay on this computer.",
  },
  denied: {
    title: "The camera is blocked",
    body: "Allow it with the camera icon at the right of the address bar, then press Try again. You can upload photos or enter an item by hand instead.",
  },
  no_device: {
    title: "No camera found",
    body: "Connect a webcam and press Try again, or upload photos or enter an item by hand.",
  },
  in_use: {
    title: "The camera is busy",
    body: "Another app is using it. Close that app, then press Try again.",
  },
  lost: {
    title: "The camera stopped",
    body: "The picture was lost (the camera may have been unplugged). Press Try again.",
  },
  paused: {
    title: "The camera is paused",
    body: "It stops while this tab is hidden and starts again when you come back.",
  },
  unsupported: {
    title: "This browser cannot use a camera here",
    body: "Upload photos or enter an item by hand instead.",
  },
};

export function Camera() {
  usePageTitle("Camera");
  const [params, setParams] = useSearchParams();
  const wanted = params.get("mode");
  const mode = wanted === "scan" || wanted === "own" ? wanted : "add";
  const camera = useCamera();
  const live = camera.state === "live";
  // Each Try again is counted, so a second failure says so instead of looking like nothing.
  const [retries, setRetries] = useState(0);

  return (
    <div className="camera-page">
      <div className="page-head">
        <h1 className="page-title">Camera</h1>
        <div className="chip-row" role="radiogroup" aria-label="Camera mode">
          <Chip
            role="radio"
            selected={mode === "add"}
            onSelect={() => setParams({ mode: "add" }, { replace: true })}
          >
            Add item
          </Chip>
          <Chip
            role="radio"
            selected={mode === "scan"}
            onSelect={() => setParams({ mode: "scan" }, { replace: true })}
          >
            Scan label
          </Chip>
          <Chip
            role="radio"
            selected={mode === "own"}
            onSelect={() => setParams({ mode: "own" }, { replace: true })}
          >
            Do I own this?
          </Chip>
        </div>
      </div>
      <GlassCard className="camera-card">
        <div className="camera-view">
          <video
            ref={camera.videoRef}
            className="camera-view__video"
            playsInline
            muted
            aria-label="Camera picture"
          />
          {camera.state === "live" ? null : (
            <div className="camera-view__message" role="status">
              <h2>{CAMERA_TEXT[camera.state].title}</h2>
              <p>{CAMERA_TEXT[camera.state].body}</p>
              {retries > 0 && camera.state !== "starting" ? (
                <p className="section-note">
                  Tried again {retries === 1 ? "once" : `${retries} times`}; it is still not
                  working.
                </p>
              ) : null}
              {camera.state === "starting" || camera.state === "paused" ? null : (
                <Button
                  variant="secondary"
                  onClick={() => {
                    setRetries((count) => count + 1);
                    camera.retry();
                  }}
                >
                  Try again
                </Button>
              )}
            </div>
          )}
        </div>
        {camera.devices.length > 1 ? (
          <Select
            label="Camera"
            value={camera.deviceId ?? ""}
            onChange={(event) => camera.chooseDevice(event.target.value || undefined)}
            options={[
              { value: "", label: "Default camera" },
              ...camera.devices.map((device, index) => ({
                value: device.deviceId,
                label: device.label || `Camera ${index + 1}`,
              })),
            ]}
          />
        ) : null}
        {mode === "add" ? <AddControls live={live} capture={camera.capture} /> : null}
        {mode === "scan" ? <ScanControls live={live} videoRef={camera.videoRef} /> : null}
        {mode === "own" ? <OwnControls live={live} capture={camera.capture} /> : null}
      </GlassCard>
    </div>
  );
}

function AddControls({ live, capture }: { live: boolean; capture: () => Promise<Blob | null> }) {
  const navigate = useNavigate();
  const refresh = useRefreshInventory();
  const picker = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [manual, setManual] = useState(false);

  const addFiles = useCallback(
    async (files: Blob[]) => {
      if (busy || files.length === 0) return;
      if (files.length > MAX_FILES) {
        setMessage(`Add up to ${MAX_FILES} photos at a time. You chose ${files.length}.`);
        return;
      }
      setBusy(true);
      setMessage(files.length === 1 ? "Saving the photo…" : `Saving ${files.length} photos…`);
      try {
        const { drafts } = await api.createDrafts(files);
        await refresh();
        const first = drafts[0];
        navigate(drafts.length === 1 && first ? `/add/${first.id}` : "/add");
      } catch (error) {
        setMessage(error instanceof ApiError ? error.message : "The photos could not be saved.");
      } finally {
        setBusy(false);
      }
    },
    [busy, navigate, refresh],
  );

  // Ctrl+V with an image on the clipboard adds it, anywhere on this page.
  useEffect(() => {
    function onPaste(event: ClipboardEvent) {
      const files = Array.from(event.clipboardData?.files ?? []).filter((f) =>
        f.type.startsWith("image/"),
      );
      if (files.length > 0) {
        event.preventDefault();
        void addFiles(files);
      }
    }
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [addFiles]);

  return (
    <div
      className="camera-controls"
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => {
        event.preventDefault();
        void addFiles(
          Array.from(event.dataTransfer.files).filter((f) => f.type.startsWith("image/")),
        );
      }}
    >
      {live ? (
        <button
          type="button"
          className="shutter"
          aria-label="Take photo"
          disabled={busy}
          onClick={() =>
            void capture().then((blob) => {
              if (blob) void addFiles([blob]);
              else setMessage("The camera has no picture yet. Wait a moment and try again.");
            })
          }
        />
      ) : null}
      <div className="chip-row">
        <input
          ref={picker}
          type="file"
          accept={IMAGE_TYPES}
          multiple
          hidden
          onChange={(event) => {
            const files = Array.from(event.target.files ?? []);
            event.target.value = "";
            void addFiles(files);
          }}
        />
        <Button variant="secondary" loading={busy} onClick={() => picker.current?.click()}>
          Upload photos
        </Button>
        <Button variant="ghost" onClick={() => setManual(true)}>
          Enter manually
        </Button>
      </div>
      <p className="section-note">
        Drop photos here or paste one with Ctrl+V. JPEG, PNG or WebP, up to 12 MB each, 20 at a
        time.
      </p>
      {message ? (
        <p role="status" className="camera-controls__message">
          {message}
        </p>
      ) : null}
      <ItemFormSheet open={manual} onClose={() => setManual(false)} onSaved={() => undefined} />
    </div>
  );
}

function ScanControls({
  live,
  videoRef,
}: {
  live: boolean;
  videoRef: RefObject<HTMLVideoElement | null>;
}) {
  const navigate = useNavigate();
  const [message, setMessage] = useState("Hold a printed label in front of the camera.");
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);
  const handling = useRef(false);
  const recent = useRef(new Map<string, number>());

  const open = useCallback(
    async (code: string) => {
      handling.current = true;
      try {
        const item = await api.lookup(code);
        navigate(`/items/${item.public_id}`);
      } catch (error) {
        setMessage(
          error instanceof ApiError ? error.message : "The lookup did not work. Try again.",
        );
      } finally {
        handling.current = false;
      }
    },
    [navigate],
  );

  // About five frames a second go to the decoder; a code seen in the last 3 s is not looked up again.
  useEffect(() => {
    if (!live) return;
    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d", { willReadFrequently: true });
    const timer = window.setInterval(() => {
      const video = videoRef.current;
      if (!video || !context || handling.current || video.videoWidth === 0) return;
      const scale = Math.min(1, 640 / video.videoWidth);
      canvas.width = Math.round(video.videoWidth * scale);
      canvas.height = Math.round(video.videoHeight * scale);
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      const frame = context.getImageData(0, 0, canvas.width, canvas.height);
      const found = jsQR(frame.data, frame.width, frame.height, {
        inversionAttempts: "dontInvert",
      });
      if (!found) return;
      const code = found.data.trim();
      const now = Date.now();
      if ((recent.current.get(code) ?? 0) > now - 3000) return;
      recent.current.set(code, now);
      if (isPublicId(code)) void open(code);
      else setMessage("That QR code is not an Enderchest label.");
    }, SCAN_EVERY_MS);
    return () => window.clearInterval(timer);
  }, [live, videoRef, open]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy || typed.trim() === "") return;
    setBusy(true);
    await open(typed.trim());
    setBusy(false);
  }

  return (
    <div className="camera-controls">
      <InnerPanel role="status" className="scan-status">
        {live ? message : "Scanning needs the camera. You can still type the ID below."}
      </InnerPanel>
      <form className="inline-add" onSubmit={(event) => void submit(event)}>
        <Input
          label="Type the ID"
          value={typed}
          placeholder="ENDR-7K2M9QXA"
          autoComplete="off"
          spellCheck={false}
          onChange={(event) => setTyped(event.target.value)}
        />
        {typed.trim() === "" ? (
          <Button type="submit" disabled disabledReason="Type an ID first.">
            Open item
          </Button>
        ) : (
          <Button type="submit" loading={busy}>
            Open item
          </Button>
        )}
      </form>
    </div>
  );
}
