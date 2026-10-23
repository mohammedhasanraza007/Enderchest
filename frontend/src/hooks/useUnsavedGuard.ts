import { useEffect } from "react";

/**
 * While a form has unsaved edits, closing or reloading the tab asks first (PAGES.md 2).
 * Leaving inside the app is guarded by the form itself (its sheet or page asks).
 */
export function useUnsavedGuard(dirty: boolean): void {
  useEffect(() => {
    if (!dirty) return;
    function onBeforeUnload(event: BeforeUnloadEvent) {
      event.preventDefault();
    }
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [dirty]);
}
