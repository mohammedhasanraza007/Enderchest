import { useEffect } from "react";
import { setPageName } from "../lib/title";

/** The browser tab title: "Settings · Enderchest", or just "Enderchest" on the first screen.
 *  The open-reminder count is added in front by the notification poll (lib/title.ts). */
export function usePageTitle(page?: string): void {
  useEffect(() => {
    setPageName(page);
  }, [page]);
}
