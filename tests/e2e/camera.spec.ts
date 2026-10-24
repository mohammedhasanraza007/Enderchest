// The camera hub in the browser (PAGES.md P-06, P-07). Chromium's fake camera stands in for a
// webcam, and Scan mode is fed a QR drawn on a canvas: regression tools only (D-056). The real
// webcam and a printed label are the owner's acceptance run, BLOCKED until the owner does it.

import { expect, test } from "@playwright/test";
import { jpegBytes, makeItem, resetApp, saveProfile } from "./helpers";

test.use({
  permissions: ["camera"],
  launchOptions: { args: ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"] },
});

test.beforeEach(async ({ request }) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata" });
});

test("Add mode: the shutter makes a draft, confirm saves the item with its photo; LIVE only while streaming", async ({
  page,
}) => {
  await page.goto("/camera?mode=add");
  await expect(page.locator(".nav .live-badge")).toBeVisible();
  await page.getByRole("button", { name: "Take photo" }).click();
  await expect(page).toHaveURL(/\/add\/[0-9a-f-]{36}$/);
  await expect(page.locator(".nav .live-badge")).toHaveCount(0); // the stream stopped on leaving

  await page.getByLabel("Name", { exact: true }).fill("Webcam item");
  await expect(page.getByText("Changes are saved as you type.")).toBeVisible();
  await page.getByRole("button", { name: "Save item" }).click();
  await expect(page).toHaveURL(/\/items\/ENDR-/);
  await expect(page.getByRole("heading", { name: "Webcam item" })).toBeVisible();
  const publicId = page.url().split("/items/")[1]!;
  const body = (await (await page.request.get(`/api/v1/items/${publicId}`)).json()) as {
    photos: unknown[];
  };
  expect(body.photos).toHaveLength(1);
});

test("a hidden tab stops the stream and showing it starts it again", async ({ page }) => {
  await page.goto("/camera?mode=add");
  await expect(page.locator(".nav .live-badge")).toBeVisible();
  await page.evaluate(() => {
    Object.defineProperty(document, "hidden", { configurable: true, get: () => true });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await expect(page.locator(".nav .live-badge")).toHaveCount(0);
  await expect(page.getByText("The camera is paused")).toBeVisible();
  await page.evaluate(() => {
    Object.defineProperty(document, "hidden", { configurable: true, get: () => false });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await expect(page.locator(".nav .live-badge")).toBeVisible();
});

test("several uploads make a review queue; drafts count nowhere until saved", async ({
  page,
  request,
}) => {
  await page.goto("/camera?mode=add");
  const photos = await Promise.all(
    ["#884422", "#224488", "#228844"].map(async (colour, index) => ({
      name: `p${index}.jpg`,
      mimeType: "image/jpeg",
      buffer: await jpegBytes(page, colour),
    })),
  );
  await page.locator('input[type="file"]').setInputFiles(photos);
  await expect(page).toHaveURL(/\/add$/);
  await expect(page.getByRole("link", { name: "Untitled" })).toHaveCount(3);
  expect(((await (await request.get("/api/v1/items")).json()) as { total: number }).total).toBe(0);

  await page.getByRole("link", { name: "Review next" }).click();
  await page.getByLabel("Name", { exact: true }).fill("First");
  await page.getByRole("button", { name: "Save and add next" }).click();
  await expect(page.getByLabel("Name", { exact: true })).toHaveValue("");
  await page.getByLabel("Name", { exact: true }).fill("Second");
  await page.getByRole("button", { name: "Save and add next" }).click();
  await expect(page.getByLabel("Name", { exact: true })).toHaveValue(""); // the third draft is open
  await page.getByRole("button", { name: "Discard draft" }).click();
  await expect(page.getByText("Nothing waiting for review.")).toBeVisible();
  expect(((await (await request.get("/api/v1/items")).json()) as { total: number }).total).toBe(2);
});

test("HEIC and oversize files get a clear refusal and add nothing", async ({ page, request }) => {
  await page.goto("/camera?mode=add");
  const heic = Buffer.concat([
    Buffer.from([0, 0, 0, 0x18]),
    Buffer.from("ftypheic"),
    Buffer.alloc(64),
  ]);
  await page.locator('input[type="file"]').setInputFiles({
    name: "IMG_0001.HEIC",
    mimeType: "image/heic",
    buffer: heic,
  });
  await expect(page.getByText(/HEIC photos are not supported/)).toBeVisible();
  await page.locator('input[type="file"]').setInputFiles({
    name: "huge.jpg",
    mimeType: "image/jpeg",
    buffer: Buffer.concat([Buffer.from([0xff, 0xd8, 0xff]), Buffer.alloc(13 * 1024 * 1024)]),
  });
  await expect(page.getByText(/over 12 MB|too large/)).toBeVisible();
  expect(((await (await request.get("/api/v1/drafts")).json()) as { items: unknown[] }).items).toEqual(
    [],
  );
});

test("Scan mode opens the item whose QR is in front of the camera", async ({ page, request }) => {
  const publicId = await makeItem(request, { name: "Scanned drill" });
  // The camera sees a canvas with the item's own QR drawn on white paper.
  await page.addInitScript((id) => {
    navigator.mediaDevices.getUserMedia = async () => {
      const canvas = document.createElement("canvas");
      canvas.width = 640;
      canvas.height = 480;
      const context = canvas.getContext("2d")!;
      const image = new Image();
      image.src = `/api/v1/items/${id}/qr.svg`;
      await image.decode();
      const draw = () => {
        context.fillStyle = "#ffffff";
        context.fillRect(0, 0, 640, 480);
        context.drawImage(image, 170, 90, 300, 300);
      };
      draw();
      window.setInterval(draw, 100);
      return canvas.captureStream(10);
    };
  }, publicId);
  await page.goto("/camera?mode=scan");
  await expect(page).toHaveURL(new RegExp(`/items/${publicId}$`), { timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "Scanned drill" })).toBeVisible();
});

test("typed IDs: lowercase and look-alikes open the item, an unknown code says so", async ({
  page,
  request,
}) => {
  const publicId = await makeItem(request, { name: "Typed torch" });
  await page.goto("/camera?mode=scan");
  await page.getByLabel("Type the ID").fill("ENDR-ZZZZZZZZ");
  await page.getByRole("button", { name: "Open item" }).click();
  await expect(page.getByText("No item with that ID.")).toBeVisible();
  const typed = publicId.toLowerCase().replace(/0/g, "o").replace(/1/g, "l");
  await page.getByLabel("Type the ID").fill(typed);
  await page.getByRole("button", { name: "Open item" }).click();
  await expect(page).toHaveURL(new RegExp(`/items/${publicId}$`));
});
