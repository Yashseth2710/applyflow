"use client";

import { useEffect, useState } from "react";

/**
 * The current time, as a timestamp, or null until the first client render.
 *
 * Reading the clock during render is impure and mismatches hydration — the
 * server rendered at a different moment than the browser. Like mount detection,
 * "what time is it" cannot be derived from props or state, only observed, so
 * the same deliberate exception applies.
 *
 * Ticks so a row can move from "upcoming" to "needs an outcome" while the page
 * is open, rather than waiting for a reload.
 */
export function useNow(intervalMs = 60_000): number | null {
  const [now, setNow] = useState<number | null>(null);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setNow(Date.now());

    const timer = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(timer);
  }, [intervalMs]);

  return now;
}
