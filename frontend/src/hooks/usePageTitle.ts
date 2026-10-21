import { useEffect } from "react";

/** The browser tab title: "Settings · Enderchest", or just "Enderchest" on the first screen. */
export function usePageTitle(page?: string): void {
  useEffect(() => {
    document.title = page ? `${page} · Enderchest` : "Enderchest";
  }, [page]);
}
