import { useEffect, useRef, useState } from "react";
import { reducedMotion, tokenMs, tween } from "../lib/motion";

/**
 * A number that counts to its new value only when the real value changes (DESIGN.md 10.2).
 * `from` is where the first showing starts: 0 during the dashboard entrance, else the value
 * itself (no count). When `skip` turns true (an input ended the entrance) a running count jumps
 * to its end. Reduced motion shows the value at once.
 */
export function useCountUp(
  value: number | null,
  from: number | null,
  skip: boolean,
): number | null {
  const [shown, setShown] = useState<number | null>(from ?? value);
  const last = useRef<number | null>(from ?? value);
  const frame = useRef(0);

  useEffect(() => {
    const start = last.current;
    last.current = value;
    const ms = tokenMs("--dur-ring");
    if (value === null || start === null || start === value || ms === 0 || reducedMotion()) {
      setShown(value);
      return;
    }
    const began = performance.now();
    const step = (now: number) => {
      const t = (now - began) / ms;
      setShown(tween(start, value, t));
      if (t < 1) frame.current = requestAnimationFrame(step);
    };
    frame.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame.current);
  }, [value]);

  useEffect(() => {
    if (!skip) return;
    cancelAnimationFrame(frame.current);
    setShown(last.current);
  }, [skip]);

  return shown;
}
