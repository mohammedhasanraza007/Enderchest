// Finding and switching cameras (P-06, D-126). The cameras are canvases standing in for webcams:
// an idle phone-webcam driver that sends exact black, a front and a back camera. Regression tools
// only (D-056); the owner's own cameras are the acceptance check.

import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { resetApp, saveProfile } from "./helpers";

interface FakeCamera {
  deviceId: string;
  label: string;
  colour: string; // "#000000" sends no picture
}

const IDLE: FakeCamera = {
  deviceId: "idle",
  label: "Phone Webcam #2",
  colour: "#000000",
};
const FRONT: FakeCamera = {
  deviceId: "front",
  label: "Front Camera",
  colour: "#6b8f71",
};
const BACK: FakeCamera = {
  deviceId: "back",
  label: "Back Camera",
  colour: "#8f6b6b",
};

/** Replaces the browser's cameras with canvases; `window.plugIn(camera)` connects one later. */
async function fakeCameras(page: Page, cameras: FakeCamera[]) {
  await page.addInitScript((initial: FakeCamera[]) => {
    const list = [...initial];
    const opened: string[] = [];
    (window as unknown as { opened: string[] }).opened = opened;
    (window as unknown as { plugIn: (camera: FakeCamera) => void }).plugIn = (
      camera,
    ) => {
      list.push(camera);
      navigator.mediaDevices.dispatchEvent(new Event("devicechange"));
    };
    navigator.mediaDevices.enumerateDevices = async () =>
      list.map(
        (camera) =>
          ({
            deviceId: camera.deviceId,
            groupId: camera.deviceId,
            kind: "videoinput",
            label: camera.label,
            toJSON: () => ({}),
          }) as MediaDeviceInfo,
      );
    navigator.mediaDevices.getUserMedia = async (constraints) => {
      const video = (constraints?.video ?? {}) as MediaTrackConstraints;
      const wanted = (
        video.deviceId as ConstrainDOMStringParameters | undefined
      )?.exact;
      const camera = wanted
        ? list.find((one) => one.deviceId === wanted)
        : list[0];
      if (!camera) throw new DOMException("no camera", "NotFoundError");
      opened.push(camera.deviceId);
      const canvas = document.createElement("canvas");
      canvas.width = 640;
      canvas.height = 360;
      const context = canvas.getContext("2d")!;
      let tick = 0;
      const draw = () => {
        tick += 1;
        context.fillStyle = camera.colour;
        context.fillRect(0, 0, 640, 360);
        if (camera.colour !== "#000000") {
          context.fillStyle = "#f4efe6";
          context.fillRect(40 + (tick % 20), 40, 200, 120); // something in view, moving a little
        }
      };
      draw();
      window.setInterval(draw, 50);
      const stream = canvas.captureStream(20);
      const track = stream.getVideoTracks()[0]!;
      const settings = track.getSettings.bind(track);
      track.getSettings = () => ({ ...settings(), deviceId: camera.deviceId });
      return stream;
    };
  }, cameras);
}

const opened = (page: Page) =>
  page.evaluate(() => (window as unknown as { opened: string[] }).opened);

test.beforeEach(async ({ request }) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata" });
});

test("a camera that sends only black is skipped for the next one, and says so", async ({
  page,
}) => {
  await fakeCameras(page, [IDLE, FRONT, BACK]);
  await page.goto("/camera?mode=add");
  await expect(
    page.getByText("Skipped Phone Webcam #2: no picture."),
  ).toBeVisible();
  await expect(page.getByLabel("Camera", { exact: true })).toHaveValue("front");
  expect(await opened(page)).toEqual(["idle", "front"]);
  await expect(page.getByRole("button", { name: "Take photo" })).toBeVisible();
});

test("Switch camera goes from front to back and back again, named by where it faces", async ({
  page,
}) => {
  await fakeCameras(page, [FRONT, BACK]);
  await page.goto("/camera?mode=add");
  const toBack = page.getByRole("button", { name: "Use the back camera" });
  await expect(toBack).toBeVisible();
  await toBack.click();
  await expect(page.getByLabel("Camera", { exact: true })).toHaveValue("back");
  await page.getByRole("button", { name: "Use the front camera" }).click();
  await expect(page.getByLabel("Camera", { exact: true })).toHaveValue("front");
  expect(await opened(page)).toEqual(["front", "back", "front"]);
  // Front and back are known from the names, so the phone-app hint is not needed.
  await expect(page.getByText("Phone as webcam?")).toHaveCount(0);
});

test("one camera shows no switch and no picker", async ({ page }) => {
  await fakeCameras(page, [FRONT]);
  await page.goto("/camera?mode=add");
  await expect(page.getByRole("button", { name: "Take photo" })).toBeVisible();
  await expect(page.locator(".camera-switch")).toHaveCount(0);
  await expect(page.getByLabel("Camera", { exact: true })).toHaveCount(0);
});

test("a camera connected while none works starts by itself", async ({
  page,
}) => {
  await fakeCameras(page, []);
  await page.goto("/camera?mode=add");
  await expect(
    page.getByRole("heading", { name: "No camera found" }),
  ).toBeVisible();
  await page.evaluate(
    (camera) =>
      (window as unknown as { plugIn: (c: typeof camera) => void }).plugIn(
        camera,
      ),
    FRONT,
  );
  await expect(page.getByRole("button", { name: "Take photo" })).toBeVisible();
  await expect(page.locator(".nav .live-badge")).toBeVisible();
});

test("when every camera sends only black the page says so, and Try again looks again", async ({
  page,
}) => {
  await fakeCameras(page, [
    IDLE,
    { ...IDLE, deviceId: "idle2", label: "Phone Webcam" },
  ]);
  await page.goto("/camera?mode=add");
  await expect(
    page.getByRole("heading", { name: "No picture from the cameras" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Take photo" })).toHaveCount(0);
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(
    page.getByRole("heading", { name: "No picture from the cameras" }),
  ).toBeVisible();
  await expect
    .poll(async () => (await opened(page)).length, { timeout: 10_000 })
    .toBe(4);
});

test("cameras with unknown facing get the phone-app hint and a named switch", async ({
  page,
}) => {
  await fakeCameras(page, [
    {
      deviceId: "m35",
      label: "Phone (Windows Virtual Camera)",
      colour: "#6b8f71",
    },
    { deviceId: "iriun", label: "Iriun Webcam", colour: "#8f6b6b" },
  ]);
  await page.goto("/camera?mode=add");
  await expect(page.getByText("Phone as webcam?")).toBeVisible();
  await page.getByRole("button", { name: "Switch to Iriun Webcam" }).click();
  await expect(page.getByLabel("Camera", { exact: true })).toHaveValue("iriun");
});
