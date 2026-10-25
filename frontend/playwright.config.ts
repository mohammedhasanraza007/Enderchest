import { defineConfig } from "@playwright/test";

// Browser tests (ARCHITECTURE 10). They run in the official Playwright image, which shares the
// test app's network (compose.test.yaml), so the app is at 127.0.0.1:8470 and the Host header
// passes the localhost check. `E2E_PROJECT=nobackups` runs the one spec that needs an app with
// no /backups mount; `E2E_PROJECT=coach` runs only the measurement on the owner's captures
// (`test.bat coach`); everything else runs against the normal test app.

const project = process.env["E2E_PROJECT"] ?? "main";
const MATCH: Record<string, RegExp> = {
  nobackups: /nobackups\.spec\.ts$/,
  coach: /coach-measure\.spec\.ts$/,
  main: /^(?!.*(nobackups|coach-measure)).*\.spec\.ts$/,
};

export default defineConfig({
  testDir: "../tests/e2e",
  testMatch: MATCH[project] ?? MATCH["main"],
  outputDir: "/test-results/playwright",
  reporter: [["list"], ["json", { outputFile: `/test-results/e2e-${project}.json` }]],
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  use: { baseURL: "http://127.0.0.1:8470" },
  // The component gallery (test-only) is built and served for the contrast and rendering specs.
  webServer:
    project === "main"
      ? {
          command:
            "npx vite build -c vite.gallery.config.ts && npx vite preview -c vite.gallery.config.ts --host 127.0.0.1 --port 4173",
          url: "http://127.0.0.1:4173/gallery.html",
          reuseExistingServer: false,
          timeout: 120_000,
        }
      : undefined,
});
