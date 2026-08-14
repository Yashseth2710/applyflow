"use client";

import { formatDays } from "@/lib/analytics";
import { STATUS_META } from "@/lib/application-status";
import type { ApplicationStatus, StageDuration } from "@/lib/types";

export function Timing({ stages }: { stages: StageDuration[] }) {
  const longest = Math.max(1, ...stages.map((s) => s.median_days));

  return (
    <section className="rounded-xl border border-border bg-card p-5 sm:p-6">
      <h2 className="eyebrow">
        How long each stage takes
      </h2>
      <p className="mt-1 text-xs text-muted-foreground">
        Typical time before moving on. Stages you’re still sitting in
        aren’t counted — they haven’t finished.
      </p>

      {stages.length === 0 ? (
        <p className="mt-6 text-sm text-muted-foreground">
          Nothing has moved between stages yet.
        </p>
      ) : (
        <ul className="mt-5 space-y-3">
          {stages.map((stage) => {
            const meta = STATUS_META[stage.status as ApplicationStatus];
            return (
              <li key={stage.status} className="flex items-center gap-3">
                <span className="w-28 shrink-0 truncate text-xs text-muted-foreground">
                  {meta.short}
                </span>

                <div
                  className="h-2 flex-1 overflow-hidden rounded-full bg-muted"
                  aria-hidden
                >
                  <div
                    className="h-full rounded-full"
                    style={{
                      // A floor, so a stage that took two hours is still a
                      // visible mark rather than nothing at all.
                      width: `${Math.max(4, (stage.median_days / longest) * 100)}%`,
                      backgroundColor: `var(${meta.token})`,
                    }}
                  />
                </div>

                <span className="w-24 shrink-0 text-right text-xs">
                  {formatDays(stage.median_days)}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
