import { useCallback, useEffect, useRef, useState } from "react";
import { facingOf, isBlank, nextCamera, switchLabel } from "../lib/cameras";
import type { Facing } from "../lib/cameras";
import { useCameraLive } from "../patterns/CameraLive";

// The webcam (PAGES.md P-06): asks for permission, shows the stream in a <video>, and stops the
// stream when the page is left or the tab is hidden (it starts again when the tab comes back).
// The nav's LIVE badge follows `live`, so it is on only while a stream really runs.
// Cameras are found by themselves (D-126): the list follows cameras being connected or removed, a
// camera connected while none worked starts at once, and on opening a camera that sends only black
// (a phone webcam app with no phone connected) is passed over for the next one. Switch camera flips
// front and back where the camera can, and otherwise moves to the next camera.

export type CameraState =
  | "starting"
  | "live"
  | "denied"
  | "no_device"
  | "in_use"
  | "lost"
  | "paused"
  | "unsupported"
  | "no_picture";

const BLANK_CHECK_MS = 1500; // a camera that shows only black this long sends no picture
const BLANK_SAMPLES = 5;
const RESTART_STATES: CameraState[] = ["no_device", "lost", "no_picture"];

interface Choice {
  deviceId?: string;
  facing?: Facing;
  byOwner: boolean; // the owner picked it: never passed over automatically
}

interface Active {
  deviceId?: string;
  facing: Facing | null;
  canFlip: boolean; // one camera that can face both ways (phones and tablets)
}

function stateFor(error: unknown): CameraState {
  const name = error instanceof DOMException ? error.name : "";
  if (name === "NotAllowedError" || name === "SecurityError") return "denied";
  if (name === "NotFoundError" || name === "OverconstrainedError") return "no_device";
  if (name === "NotReadableError" || name === "AbortError") return "in_use";
  return "lost";
}

/** True when the first moments of the stream are exact black, or no frame arrives at all. */
async function sendsNoPicture(video: HTMLVideoElement, cancelled: () => boolean): Promise<boolean> {
  const canvas = document.createElement("canvas");
  canvas.width = 160;
  canvas.height = 90;
  const context = canvas.getContext("2d", { willReadFrequently: true });
  if (!context) return false;
  for (let sample = 0; sample < BLANK_SAMPLES; sample += 1) {
    await new Promise((resolve) => window.setTimeout(resolve, BLANK_CHECK_MS / BLANK_SAMPLES));
    if (cancelled()) return false;
    if (video.videoWidth === 0) continue;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    if (!isBlank(context.getImageData(0, 0, canvas.width, canvas.height).data)) return false;
  }
  return true;
}

export function useCamera() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [state, setState] = useState<CameraState>("starting");
  const stateRef = useRef<CameraState>("starting");
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [choice, setChoice] = useState<Choice>({ byOwner: false });
  const [active, setActive] = useState<Active>({ facing: null, canFlip: false });
  const [skipped, setSkipped] = useState<string[]>([]); // names of cameras passed over
  const skippedIds = useRef(new Set<string>());
  const [attempt, setAttempt] = useState(0);
  const { setLive } = useCameraLive();

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setLive(false);
  }, [setLive]);

  useEffect(() => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setState("unsupported");
      return;
    }
    if (document.hidden) {
      setState("paused");
      return;
    }
    let cancelled = false;
    setState("starting");
    navigator.mediaDevices
      .getUserMedia({
        audio: false,
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          ...(choice.deviceId ? { deviceId: { exact: choice.deviceId } } : {}),
          ...(choice.facing ? { facingMode: { exact: choice.facing } } : {}),
        },
      })
      .then(async (stream) => {
        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }
        streamRef.current = stream;
        const video = videoRef.current;
        if (video) {
          video.srcObject = stream;
          await video.play().catch(() => undefined);
        }
        const track = stream.getVideoTracks()[0];
        track?.addEventListener("ended", () => {
          setLive(false);
          setState("lost");
        });
        const settings = track?.getSettings() ?? {};
        const modes = track?.getCapabilities?.().facingMode ?? [];
        const all = await navigator.mediaDevices.enumerateDevices();
        if (cancelled) return;
        const cameras = all.filter((device) => device.kind === "videoinput");
        setDevices(cameras);
        const label =
          cameras.find((device) => device.deviceId === settings.deviceId)?.label ??
          track?.label ??
          "";
        setActive({
          deviceId: settings.deviceId,
          facing: facingOf(label, settings.facingMode),
          canFlip: modes.includes("user") && modes.includes("environment"),
        });
        setState("live");
        setLive(true);
        // On opening, a camera that sends only black is passed over for the next one.
        if (choice.byOwner || cameras.length < 2 || !video) return;
        if (!(await sendsNoPicture(video, () => cancelled))) return;
        if (settings.deviceId) skippedIds.current.add(settings.deviceId);
        setSkipped((names) => [...names, label || "A camera"]);
        const next = cameras.find((device) => !skippedIds.current.has(device.deviceId));
        if (next) {
          setChoice({ deviceId: next.deviceId, byOwner: false });
        } else {
          stop();
          setState("no_picture");
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) setState(stateFor(error));
      });
    return () => {
      cancelled = true;
      stop();
    };
  }, [choice, attempt, stop, setLive]);

  // A hidden tab stops the stream; showing the tab again starts it again.
  useEffect(() => {
    function onVisibility() {
      if (document.hidden) {
        stop();
        setState("paused");
      } else {
        setAttempt((value) => value + 1);
      }
    }
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, [stop]);

  // Cameras connected or removed while the page is open: the list follows, and a camera that
  // appears while none works is started at once.
  useEffect(() => {
    const media = navigator.mediaDevices;
    if (!media?.addEventListener) return;
    function onChange() {
      void media.enumerateDevices().then((all) => {
        const cameras = all.filter((device) => device.kind === "videoinput");
        setDevices(cameras);
        if (cameras.length > 0 && RESTART_STATES.includes(stateRef.current)) {
          skippedIds.current.clear();
          setSkipped([]);
          setChoice({ byOwner: false });
        }
      });
    }
    media.addEventListener("devicechange", onChange);
    return () => media.removeEventListener("devicechange", onChange);
  }, []);

  /** The current frame as a JPEG, or null when there is no picture yet. */
  const capture = useCallback(async (): Promise<Blob | null> => {
    const video = videoRef.current;
    if (!video || video.videoWidth === 0) return null;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")?.drawImage(video, 0, 0);
    return new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.92));
  }, []);

  const flipTo: Facing | null = active.canFlip
    ? active.facing === "environment"
      ? "user"
      : "environment"
    : null;

  return {
    videoRef,
    state,
    devices,
    activeId: active.deviceId,
    skipped,
    canSwitch: devices.length > 1 || active.canFlip,
    switchText: switchLabel(devices, active.deviceId, flipTo),
    switchCamera: () => {
      if (flipTo) setChoice({ facing: flipTo, byOwner: true });
      else {
        const next = nextCamera(devices, active.deviceId);
        if (next) setChoice({ deviceId: next.deviceId, byOwner: true });
      }
    },
    chooseDevice: (deviceId: string) => setChoice({ deviceId, byOwner: true }),
    retry: () => {
      if (state === "no_picture") {
        skippedIds.current.clear();
        setSkipped([]);
        setChoice({ byOwner: false });
      }
      setAttempt((value) => value + 1);
    },
    capture,
  };
}
