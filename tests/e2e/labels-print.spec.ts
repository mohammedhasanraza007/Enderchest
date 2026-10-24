// Labels on paper (Phase 2 gate 4), checked in the PRINT output rather than on screen: the PDF
// Chromium prints has one A4 page per 21 labels (or one 50 × 30 mm page per single label), and
// the labels sit at the pitch of a standard 21-up A4 sheet. Added by the Phase 2 verification.
// A real printer and a real webcam stay the owner's acceptance run (D-056).

import { expect, test } from "@playwright/test";
import { makeItem, resetApp, saveProfile } from "./helpers";

const MM = 96 / 25.4; // CSS pixels per millimetre
const PT = 72 / 25.4; // PDF points per millimetre

/** The page sizes, in millimetres, of a PDF that Chromium wrote. */
function pdfPages(pdf: Buffer): { width: number; height: number }[] {
  const text = pdf.toString("latin1");
  const boxes = [
    ...text.matchAll(/\/Type\s*\/Page\b(?!s)[\s\S]*?\/MediaBox\s*\[\s*0 0 ([\d.]+) ([\d.]+)\s*\]/g),
  ];
  return boxes.map((m) => ({ width: Number(m[1]) / PT, height: Number(m[2]) / PT }));
}

test.beforeEach(async ({ request }) => {
  await resetApp(request);
  await saveProfile(request, { name: "Mohammed", timezone: "Asia/Kolkata" });
});

test("the A4 sheet prints one A4 page per 21 labels at the standard 21-up pitch", async ({
  page,
  request,
}) => {
  const ids: string[] = [];
  for (let n = 1; n <= 22; n += 1) ids.push(await makeItem(request, { name: `Box ${n}` }));
  await page.goto(`/labels?ids=${ids.join(",")}`);
  await expect(page.locator(".print-label")).toHaveCount(22);

  await page.emulateMedia({ media: "print" });
  const sheet = (await page.locator(".print-sheet--a4").first().boundingBox())!;
  const boxes = await page
    .locator(".print-label")
    .evaluateAll((labels) =>
      labels.slice(0, 4).map((label) => label.getBoundingClientRect().toJSON() as DOMRect),
    );
  const [first, second, , fourth] = boxes;
  expect(Math.abs((first!.x - sheet.x) / MM - 7.25)).toBeLessThan(0.5);
  expect(Math.abs((first!.y - sheet.y) / MM - 15.15)).toBeLessThan(0.5);
  expect(Math.abs((second!.x - first!.x) / MM - 66)).toBeLessThan(0.5); // 63.5 + 2.5 gap
  expect(Math.abs((fourth!.y - first!.y) / MM - 38.1)).toBeLessThan(0.5);

  const pages = pdfPages(await page.pdf({ preferCSSPageSize: true, printBackground: true }));
  expect(pages).toHaveLength(2);
  for (const size of pages) {
    expect(Math.abs(size.width - 210)).toBeLessThan(1);
    expect(Math.abs(size.height - 297)).toBeLessThan(1);
  }
});

test("single labels print one 50 × 30 mm page each", async ({ page, request }) => {
  const ids = [
    await makeItem(request, { name: "Drill" }),
    await makeItem(request, { name: "Saw" }),
    await makeItem(request, { name: "Glue" }),
  ];
  await page.goto(`/labels?ids=${ids.join(",")}`);
  await page.getByRole("radio", { name: "Single label (50 × 30 mm)" }).click();
  await expect(page.locator(".print-sheet--single")).toHaveCount(3);

  const pages = pdfPages(await page.pdf({ preferCSSPageSize: true, printBackground: true }));
  expect(pages).toHaveLength(3);
  for (const size of pages) {
    expect(Math.abs(size.width - 50)).toBeLessThan(1);
    expect(Math.abs(size.height - 30)).toBeLessThan(1);
  }
});

test("the served QR decodes to the public id and nothing else", async ({ page, request }) => {
  const id = await makeItem(request, { name: "Spirit level", notes: "private note" });
  await page.goto("/inventory");
  await page.addScriptTag({ path: "/frontend/node_modules/jsqr/dist/jsQR.js" });
  const decoded = await page.evaluate(async (publicId) => {
    const image = new Image();
    image.src = `/api/v1/items/${publicId}/qr.svg`;
    await image.decode();
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 400;
    const context = canvas.getContext("2d")!;
    context.fillStyle = "#fff";
    context.fillRect(0, 0, 400, 400);
    context.drawImage(image, 0, 0, 400, 400);
    const pixels = context.getImageData(0, 0, 400, 400);
    const read = (
      window as unknown as {
        jsQR: (d: Uint8ClampedArray, w: number, h: number) => { data: string } | null;
      }
    ).jsQR;
    return read(pixels.data, 400, 400)?.data ?? null;
  }, id);
  expect(decoded).toBe(id);
});
