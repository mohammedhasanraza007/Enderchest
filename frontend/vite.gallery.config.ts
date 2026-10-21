import { resolve } from "node:path";
import { defineConfig } from "vite";
import { sharedStatic } from "./vite.shared.ts";

// The component gallery: a test-only page that shows every primitive and pattern, so the browser
// tests can check contrast and rendering in both themes. It is built into dist-e2e, never into
// the app (dist), and is not in the Docker runtime image.
export default defineConfig({
  plugins: [sharedStatic("dist-e2e")],
  build: {
    outDir: "dist-e2e",
    emptyOutDir: true,
    target: "es2022",
    rollupOptions: { input: resolve(import.meta.dirname, "gallery.html") },
  },
});
