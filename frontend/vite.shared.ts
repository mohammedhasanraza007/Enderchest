import { copyFileSync, existsSync, mkdirSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { Plugin } from "vite";

const here = dirname(fileURLToPath(import.meta.url));
const logo = (name: string) => resolve(here, "../assets/logo", name);

// Files served unhashed at the site root: the tokens (shared with the plain-HTML boot pages) and
// the supplied logo and favicons (DESIGN.md 4.9, used exactly as supplied).
const SHARED: Array<{ url: string; source: string; type: string }> = [
  { url: "/tokens.css", source: resolve(here, "src/tokens/tokens.css"), type: "text/css" },
  { url: "/favicon.ico", source: logo("favicon.ico"), type: "image/x-icon" },
  { url: "/icon-16.png", source: logo("icon-16.png"), type: "image/png" },
  { url: "/icon-32.png", source: logo("icon-32.png"), type: "image/png" },
  { url: "/icon-48.png", source: logo("icon-48.png"), type: "image/png" },
  { url: "/enderchest-logo.svg", source: logo("enderchest-logo.svg"), type: "image/svg+xml" },
];

/** Serve the shared files in `vite dev`, and copy them next to the bundle in `vite build`. */
export function sharedStatic(outDir = "dist"): Plugin {
  return {
    name: "enderchest-shared-static",
    configureServer(server) {
      server.middlewares.use((request, response, next) => {
        const path = (request.url ?? "").split("?")[0];
        const file = SHARED.find((entry) => entry.url === path);
        if (!file) return next();
        response.setHeader("Content-Type", file.type);
        response.end(readFileSync(file.source));
      });
    },
    closeBundle() {
      const out = resolve(here, outDir);
      mkdirSync(out, { recursive: true });
      for (const file of SHARED) {
        if (!existsSync(file.source)) throw new Error(`missing shared file ${file.source}`);
        copyFileSync(file.source, resolve(out, file.url.slice(1)));
      }
    },
  };
}
