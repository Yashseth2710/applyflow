import { STATUS_META } from "@/lib/application-status";
import type { ApplicationStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

// Tinted rather than solid fill — a row of twelve saturated pills is hard to
// look at, and the tint still separates stages at a glance.
export function StatusBadge({
  status,
  className,
  short = false,
}: {
  status: ApplicationStatus;
  className?: string;
  short?: boolean;
}) {
  const meta = STATUS_META[status];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
        className,
      )}
      style={{
        backgroundColor: `color-mix(in oklch, var(${meta.token}) 16%, transparent)`,
        // The ink variant of the same token. The stage colours are tuned to
        // look right as fills, and at 12px on their own tint they read between
        // 2.6:1 and 3.5:1 in light mode. Every stage defines `-ink` in both
        // themes, so appending the suffix always resolves.
        color: `var(${meta.token}-ink)`,
      }}
    >
      <span
        className="size-1.5 rounded-full"
        style={{ backgroundColor: `var(${meta.token})` }}
      />
      {short ? meta.short : meta.label}
    </span>
  );
}
