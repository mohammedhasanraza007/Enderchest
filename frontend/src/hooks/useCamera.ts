import { useCallback, useEffect, useRef, useState } from "react";
import { useCameraLive } from "../patterns/CameraLive";

// The webcam (PAGES.md P-06): asks for permission, shows the stream in a <video>, and stops the
// stream when the page is left or the tab is hidden (it starts again when the tab comes back).
// The nav's LIVE badge follows `live`, so it is on only while a stream really runs.

export type CameraState =
  "starting" | "live" | "denied" | "no_device" | "in_use" | "lost" | "paused" | "unsupported";

function stateFor(error: unknown): CameraState {
  const name = error instanceof DOMException ? error.name : "";
  if (name === "NotAllowedError" || name === "SecurityError") return "denied";
  if (name === "NotFoundError" || name === "OverconstrainedError") return "no_device";
  if (name === "NotReadableError" || name === "AbortError") return "in_use";
  return "lost";
}

export function useCamera() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [state, setState] = useState<CameraState>("starting");
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [deviceId, setDeviceId] = useState<string | undefined>(undefined);
  const [attempt, setAttempt] = useState(0);
  const { setLive } = useCameraLive();

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
          ...(deviceId ? { deviceId: { exact: deviceId } } : {}),
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
        stream.getVideoTracks()[0]?.addEventListener("ended", () => {
          setLive(false);
          setState("lost");
        });
        setState("live");
        setLive(true);
        const all = await navigator.mediaDevices.enumerateDevices();
        if (!cancelled) setDevices(all.filter((device) => device.kind === "videoinput"));
      })
      .catch((error: unknown) => {
        if (!cancelled) setState(stateFor(error));
      });
    return () => {
      cancelled = true;
      stop();
    };
  }, [deviceId, attempt, stop, setLive]);

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

  return {
    videoRef,
    state,
    devices,
    deviceId,
    chooseDevice: setDeviceId,
    retry: () => setAttempt((value) => value + 1),
    capture,
  };
}
