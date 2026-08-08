/**
 * ApplyFlow brand mark.
 *
 * Three ascending bars with a rising path through them: applications moving
 * forward through pipeline stages. Monochrome via `currentColor`, so the same
 * component works on the light background, on the teal brand panel, and in
 * dark mode — the parent sets the colour.
 *
 * Depth comes from opacity rather than extra hues, which keeps it legible at
 * favicon size where a multi-colour mark would turn to mush.
 */

export function Logo({
  size = 26,
  className,
}: {
  size?: number;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden
      className={className}
    >
      {/* Tile */}
      <rect width="32" height="32" rx="9" fill="currentColor" opacity="0.14" />

      {/* Pipeline bars, ascending left to right. Opacity implies progression:
          early stages sit back, the final stage is solid. */}
      <rect x="7" y="19" width="4" height="7" rx="2" fill="currentColor" opacity="0.45" />
      <rect x="14" y="15" width="4" height="11" rx="2" fill="currentColor" opacity="0.7" />
      <rect x="21" y="9" width="4" height="17" rx="2" fill="currentColor" />

      {/* Rising path across the bars — the "flow". */}
      <path
        d="M7.5 14.5 15 10l3.2 2.6L25.5 6"
        stroke="currentColor"
        strokeWidth="2.1"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.9"
      />
      {/* Endpoint dot: the offer. */}
      <circle cx="25.5" cy="6" r="2.4" fill="currentColor" />
    </svg>
  );
}

/** Mark plus wordmark, for headers and the auth panel. */
export function LogoWordmark({
  size = 26,
  className,
}: {
  size?: number;
  className?: string;
}) {
  return (
    <span className={`inline-flex items-center gap-2.5 ${className ?? ""}`}>
      <Logo size={size} />
      <span className="text-lg font-semibold tracking-tight">ApplyFlow</span>
    </span>
  );
}
