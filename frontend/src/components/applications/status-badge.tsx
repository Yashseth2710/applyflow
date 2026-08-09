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
        color: `var(${meta.token})`,
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
