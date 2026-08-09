"use client";

import { useTheme } from "next-themes";

import { Button } from "@/components/ui/button";
import { useMounted } from "@/lib/use-mounted";

/**
 * Light / dark toggle.
 *
 * Renders a fixed-size placeholder until mounted. The server has no idea which
 * theme the client resolved to, so rendering the real icon immediately causes a
 * hydration mismatch — and rendering nothing makes the header jump.
 */
export function ThemeToggle({ className }: { className?: string }) {
  const { resolvedTheme, setTheme } = useTheme();
  const mounted = useMounted();

  if (!mounted) {
    return <span className="inline-block size-9" aria-hidden />;
  }

  const isDark = resolvedTheme === "dark";

  return (
    <Button
      type="button"
      variant="ghost"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
      title={isDark ? "Switch to light theme" : "Switch to dark theme"}
      className={`size-9 rounded-lg p-0 ${className ?? ""}`}
    >
      {isDark ? <SunIcon /> : <MoonIcon />}
    </Button>
  );
}

function SunIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      aria-hidden
    >
      <circle cx="12" cy="12" r="4.2" />
      <path d="M12 2.5v2M12 19.5v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M2.5 12h2M19.5 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M20.5 14.4A8.5 8.5 0 1 1 9.6 3.5a6.8 6.8 0 0 0 10.9 10.9Z" />
    </svg>
  );
}
