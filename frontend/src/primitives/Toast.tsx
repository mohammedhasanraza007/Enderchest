import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { ReactNode } from "react";

// Toasts (DESIGN.md 6.12, PAGES.md 2): one at a time at the bottom centre. A toast with an
// action such as Undo stays longer (10 s) than a plain one (5 s).

interface ToastRequest {
  message: string;
  actionLabel?: string;
  onAction?: () => void;
}
interface ToastItem extends ToastRequest {
  id: number;
}

const ToastContext = createContext<((toast: ToastRequest) => void) | null>(null);

export function useToast(): (toast: ToastRequest) => void {
  const show = useContext(ToastContext);
  if (show === null) throw new Error("useToast needs a ToastProvider above it");
  return show;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<ToastItem | null>(null);
  const timer = useRef<number | undefined>(undefined);
  const counter = useRef(0);

  const show = useCallback((request: ToastRequest) => {
    window.clearTimeout(timer.current);
    counter.current += 1;
    setToast({ ...request, id: counter.current });
    timer.current = window.setTimeout(() => setToast(null), request.onAction ? 10_000 : 5_000);
  }, []);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  const value = useMemo(() => show, [show]);
  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-region" role="status" aria-live="polite">
        {toast ? (
          <div className="toast" key={toast.id}>
            <span>{toast.message}</span>
            {toast.actionLabel && toast.onAction ? (
              <button
                type="button"
                className="pill pill--ghost toast__action"
                onClick={() => {
                  toast.onAction?.();
                  setToast(null);
                }}
              >
                {toast.actionLabel}
              </button>
            ) : null}
          </div>
        ) : null}
      </div>
    </ToastContext.Provider>
  );
}
