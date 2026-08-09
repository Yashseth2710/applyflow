"use client";

import { useEffect, useState } from "react";

/**
 * True only after the first client render.
 *
 * Needed for anything that depends on client-only state the server cannot
 * know — here, the resolved theme. Rendering the real value immediately causes
 * a hydration mismatch, because the server has no idea whether the user's OS
 * prefers dark.
 *
 * react-hooks/set-state-in-effect flags this, and it's normally right: setting
 * state in an effect usually means the value should have been derived instead.
 * Mount detection is the genuine exception — "has hydration happened" cannot be
 * derived from props or state, only observed.
 */
export function useMounted(): boolean {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true);
  }, []);

  return mounted;
}
