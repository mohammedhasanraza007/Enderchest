import { useRef } from "react";

/**
 * Ignore a second click that arrives before the first request has finished (PAGES.md 2, double
 * submit). A button's `loading` state is not fast enough on its own: both clicks of a double click
 * are handled before React draws the screen again. A ref changes at once.
 *
 * Usage: `once((done) => mutation.mutate(data, { onSettled: done }))`.
 */
export function useSingleFlight(): (start: (done: () => void) => void) => void {
  const busy = useRef(false);
  return (start) => {
    if (busy.current) return;
    busy.current = true;
    start(() => {
      busy.current = false;
    });
  };
}
