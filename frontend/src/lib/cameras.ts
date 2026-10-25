// Choosing a camera (P-06, D-126), kept pure so it is tested without one. The browser lists every
// camera it can open; a phone used as a webcam through an app often adds cameras that send only
// black while the phone is not connected. Front and back are known when the camera says which way
// it faces, or when its name says so.

export type Facing = "user" | "environment";

export interface CameraInfo {
  deviceId: string;
  label: string;
}

/** Which way a camera faces, from what the browser reports or else from its name. */
export function facingOf(label: string, reported?: string): Facing | null {
  if (reported === "user" || reported === "environment") return reported;
  if (/\b(front|user|facetime)\b/i.test(label)) return "user";
  if (/\b(back|rear|environment|world)\b/i.test(label)) return "environment";
  return null;
}

/** The camera after the active one, going round the list; null with one camera or none. */
export function nextCamera(cameras: CameraInfo[], activeId: string | undefined): CameraInfo | null {
  if (cameras.length < 2) return null;
  const index = cameras.findIndex((camera) => camera.deviceId === activeId);
  return cameras[(index + 1) % cameras.length] ?? null;
}

/** What the Switch camera button will do, said plainly (its accessible name and tooltip). */
export function switchLabel(
  cameras: CameraInfo[],
  activeId: string | undefined,
  flip: Facing | null,
): string {
  if (flip) return flip === "environment" ? "Use the back camera" : "Use the front camera";
  const next = nextCamera(cameras, activeId);
  if (!next) return "Switch camera";
  const facing = facingOf(next.label);
  if (facing === "environment") return "Use the back camera";
  if (facing === "user") return "Use the front camera";
  return next.label ? `Switch to ${next.label}` : "Switch to the next camera";
}

/** A frame with no picture at all: every pixel black. A dark room still has sensor noise; an
 *  idle virtual camera sends exact black. */
export function isBlank(rgba: Uint8ClampedArray): boolean {
  for (let p = 0; p < rgba.length; p += 4) {
    if (rgba[p]! > 2 || rgba[p + 1]! > 2 || rgba[p + 2]! > 2) return false;
  }
  return true;
}
