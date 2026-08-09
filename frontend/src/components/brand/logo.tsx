"use client";

import { useId } from "react";

// "mono" is for the violet brand panel, where the gradient would be invisible.
// Gradient IDs are per-instance: hardcoded ones collide when the logo renders
// twice and the second inherits the first's gradient.

const A_PATH = "M8 40 L20 10 L32 40";
const ARROW_PATH = "M8.5 31 C17 41, 31 37, 40 18";
const ARROWHEAD_PATH = "M44.4 9.4 L45.6 19.2 L36.2 14.6 Z";

export function Logo({
  size = 26,
  variant = "gradient",
  className,
}: {
  size?: number;
  variant?: "gradient" | "mono";
  className?: string;
}) {
  // useId returns something like ":r0:". Colons are legal in HTML ids but are
  // parsed as a pseudo-class inside CSS/SVG `url(#...)` references, which
  // breaks the gradient in some browsers. Strip them.
  const id = useId().replace(/:/g, "");
  const aId = `a-${id}`;
  const arrowId = `arrow-${id}`;

  const aStroke = variant === "mono" ? "currentColor" : `url(#${aId})`;
  const arrowStroke = variant === "mono" ? "currentColor" : `url(#${arrowId})`;

  return (
    <svg
      width={size}
      // viewBox is 50x48, so height is scaled to keep the mark from squashing.
      height={Math.round(size * (48 / 50))}
      viewBox="0 0 50 48"
      fill="none"
      aria-hidden
      className={className}
    >
      {variant === "gradient" && (
        <defs>
          <linearGradient
            id={aId}
            x1="6"
            y1="6"
            x2="34"
            y2="44"
            gradientUnits="userSpaceOnUse"
          >
            {/* Token-driven so the mark brightens in dark mode; the
                light-mode indigo end vanishes against a dark ground. */}
            <stop stopColor="var(--logo-a-from)" />
            <stop offset="0.5" stopColor="var(--logo-a-mid)" />
            <stop offset="1" stopColor="var(--logo-a-to)" />
          </linearGradient>
          <linearGradient
            id={arrowId}
            x1="8"
            y1="34"
            x2="46"
            y2="10"
            gradientUnits="userSpaceOnUse"
          >
            <stop stopColor="var(--logo-arrow-from)" />
            <stop offset="0.5" stopColor="var(--logo-arrow-mid)" />
            <stop offset="1" stopColor="var(--logo-arrow-to)" />
          </linearGradient>
        </defs>
      )}

      <path
        d={A_PATH}
        stroke={aStroke}
        strokeWidth="7.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity={variant === "mono" ? 0.9 : 1}
      />
      <path
        d={ARROW_PATH}
        stroke={arrowStroke}
        strokeWidth="5.6"
        strokeLinecap="round"
        fill="none"
      />
      {/* Stroked as well as filled, so the head keeps its weight at small sizes. */}
      <path
        d={ARROWHEAD_PATH}
        fill={arrowStroke}
        stroke={arrowStroke}
        strokeWidth="2.4"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Mark plus wordmark. Used by every header, so the pairing stays consistent. */
export function LogoWordmark({
  size = 26,
  variant = "gradient",
  className,
}: {
  size?: number;
  variant?: "gradient" | "mono";
  className?: string;
}) {
  return (
    <span className={`inline-flex items-center gap-2.5 ${className ?? ""}`}>
      <Logo size={size} variant={variant} />
      <span className="font-semibold tracking-tight">ApplyFlow</span>
    </span>
  );
}
