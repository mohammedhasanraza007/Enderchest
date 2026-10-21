import { defineConfig } from "vitest/config";
import { sharedStatic } from "./vite.shared.ts";

export default defineConfig({
  plugins: [sharedStatic("dist")],
  build: { outDir: "dist", emptyOutDir: true, target: "es2022" },
  server: {
    // dev.bat: Vite in front of the test app. The app only accepts local Host and Origin values,
    // so the proxy presents the app's own.
    proxy: {
      "/api": {
        target: "http://dev:8470",
        headers: { Host: "127.0.0.1:8470", Origin: "http://127.0.0.1:8470" },
      },
      "/health": { target: "http://dev:8470", headers: { Host: "127.0.0.1:8470" } },
    },
  },
  test: { environment: "node", include: ["src/**/*.test.ts", "src/**/*.test.tsx"] },
});
