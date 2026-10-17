import { useEffect, useRef, useState } from "react";

/** Presentation-only interpolation; source values remain unchanged in the realtime store. */
export function AnimatedNumber({
  value,
  precision = 0,
}: {
  value?: number | null;
  precision?: number;
}) {
  const current = useRef(value ?? 0);
  const [shown, setShown] = useState(value ?? 0);
  useEffect(() => {
    if (value == null) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      current.current = value;
      setShown(value);
      return;
    }
    const start = performance.now(),
      from = current.current;
    let frame = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / 200);
      current.current = from + (value - from) * (1 - (1 - t) ** 3);
      setShown(current.current);
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value]);
  return <>{value == null ? "—" : shown.toFixed(precision)}</>;
}
