import { describe, expect, it } from "vitest";
import { facingOf, isBlank, nextCamera, switchLabel } from "./cameras";

const laptop = [
  { deviceId: "a", label: "Mohammed Hasan's M35 (Windows Virtual Camera)" },
  { deviceId: "b", label: "Iriun Webcam" },
  { deviceId: "c", label: "Iriun Webcam #2" },
];
const phone = [
  { deviceId: "f", label: "camera2 1, facing front" },
  { deviceId: "r", label: "camera2 0, facing back" },
];

describe("choosing a camera", () => {
  it("knows front and back from the browser, else from the name, else not at all", () => {
    expect(facingOf("Iriun Webcam", "environment")).toBe("environment");
    expect(facingOf("camera2 1, facing front")).toBe("user");
    expect(facingOf("Rear Camera")).toBe("environment");
    expect(facingOf("Iriun Webcam")).toBeNull();
  });

  it("goes round the list from the active camera", () => {
    expect(nextCamera(laptop, "a")?.deviceId).toBe("b");
    expect(nextCamera(laptop, "c")?.deviceId).toBe("a");
    expect(nextCamera(laptop, undefined)?.deviceId).toBe("a");
    expect(nextCamera(laptop.slice(0, 1), "a")).toBeNull();
  });

  it("says what the switch will do", () => {
    expect(switchLabel(laptop, "a", null)).toBe("Switch to Iriun Webcam");
    expect(switchLabel(phone, "f", null)).toBe("Use the back camera");
    expect(switchLabel(phone, "r", null)).toBe("Use the front camera");
    expect(switchLabel(laptop.slice(0, 1), "a", "environment")).toBe("Use the back camera");
    expect(
      switchLabel(
        [
          { deviceId: "x", label: "" },
          { deviceId: "y", label: "" },
        ],
        "x",
        null,
      ),
    ).toBe("Switch to the next camera");
  });

  it("calls exact black blank and a noisy dark frame not blank", () => {
    expect(isBlank(new Uint8ClampedArray([0, 0, 0, 255, 1, 2, 0, 255]))).toBe(true);
    expect(isBlank(new Uint8ClampedArray([0, 0, 0, 255, 3, 1, 4, 255]))).toBe(false);
  });
});
