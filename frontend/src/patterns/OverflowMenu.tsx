import { useEffect, useId, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Ellipsis } from "lucide-react";

// The "⋯" menu (PAGES.md P-03 and P-04): a button that shows a short list of actions. Like the
// name menu it is a disclosure, so Tab walks it in order and Escape closes it.

export type OverflowAction =
  { label: string; to: string } | { label: string; onSelect: () => void };

export function OverflowMenu({ label, actions }: { label: string; actions: OverflowAction[] }) {
  const [open, setOpen] = useState(false);
  const container = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  const panelId = useId();

  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        button.current?.focus();
      }
    }
    function onPointer(event: PointerEvent) {
      if (!container.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPointer);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onPointer);
    };
  }, [open]);

  return (
    <div className="overflow-menu" ref={container}>
      <button
        ref={button}
        type="button"
        className="pill pill--secondary overflow-menu__button"
        aria-label={label}
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        onClick={() => setOpen((value) => !value)}
      >
        <Ellipsis size={20} strokeWidth={1.5} aria-hidden="true" />
      </button>
      {open ? (
        <div id={panelId} className="overflow-menu__panel">
          {actions.map((action): ReactNode =>
            "to" in action ? (
              <Link key={action.label} to={action.to} className="name-menu__link">
                {action.label}
              </Link>
            ) : (
              <button
                key={action.label}
                type="button"
                className="name-menu__link overflow-menu__item"
                onClick={() => {
                  setOpen(false);
                  action.onSelect();
                }}
              >
                {action.label}
              </button>
            ),
          )}
        </div>
      ) : null}
    </div>
  );
}
