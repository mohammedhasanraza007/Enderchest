import { useEffect, useId, useRef } from "react";
import type { ReactNode } from "react";
import { X } from "lucide-react";

// Dialog (centred) and Sheet (from the right), both on the browser's own <dialog> element, which
// traps focus, closes on Escape and returns focus to what opened it (PAGES.md 2, keyboard).

interface OverlayProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}

function Overlay({ variant, open, onClose, title, children }: OverlayProps & { variant: string }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const opener = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    if (open && !element.open) {
      opener.current = document.activeElement as HTMLElement | null;
      element.showModal();
    }
    if (!open && element.open) element.close();
  }, [open]);

  // A parent may unmount an open dialog; the browser gives focus back only on a real close.
  useEffect(() => {
    const element = dialog.current;
    return () => {
      if (element?.open) opener.current?.focus();
    };
  }, []);

  return (
    <dialog
      ref={dialog}
      className={`overlay overlay--${variant}`}
      aria-labelledby={titleId}
      // Escape: let the parent decide, so the open state has one owner.
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      // A click on the dimmed area (the dialog element itself) closes it.
      onClick={(event) => {
        if (event.target === dialog.current) onClose();
      }}
    >
      <div className="overlay__body">
        <div className="overlay__head">
          <h2 id={titleId} className="overlay__title">
            {title}
          </h2>
          <button type="button" className="overlay__close" aria-label="Close" onClick={onClose}>
            <X size={20} strokeWidth={1.5} aria-hidden="true" />
          </button>
        </div>
        {children}
      </div>
    </dialog>
  );
}

export function Dialog(props: OverlayProps) {
  return <Overlay variant="dialog" {...props} />;
}

export function Sheet(props: OverlayProps) {
  return <Overlay variant="sheet" {...props} />;
}
