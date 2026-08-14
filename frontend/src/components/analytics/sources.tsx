"use client";

import { formatRate } from "@/lib/analytics";
import type { SourceStat } from "@/lib/types";

export function Sources({ sources }: { sources: SourceStat[] }) {
  const busiest = Math.max(1, ...sources.map((s) => s.total));

  return (
    <section className="rounded-xl border border-border bg-card p-5 sm:p-6">
      <h2 className="eyebrow">
        Where they came from
      </h2>
      <p className="mt-1 text-xs text-muted-foreground">
        Grouped exactly as you typed them.
      </p>

      {sources.length === 0 ? (
        <p className="mt-6 text-sm text-muted-foreground">
          Nothing to compare yet. Set a source on an application and it will
          show up here.
        </p>
      ) : (
        <ul className="mt-5 space-y-4">
          {sources.map((source) => (
            <li key={source.source ?? "unrecorded"}>
              <div className="flex items-baseline justify-between gap-3">
                <span className="truncate text-sm font-medium">
                  {source.source ?? (
                    <span className="text-muted-foreground italic">
                      No source recorded
                    </span>
                  )}
                </span>
                <span className="tabular shrink-0 text-sm">{source.total}</span>
              </div>

              <div
                className="mt-1.5 flex h-2 overflow-hidden rounded-full bg-muted"
                aria-hidden
              >
                {/* Two segments of one bar: interviews sit inside the total, so
                    stacking them shows the share without a second chart. */}
                <div
                  style={{
                    width: `${(source.interviews / busiest) * 100}%`,
                    backgroundColor: "var(--stage-technical)",
                  }}
                />
                <div
                  style={{
                    width: `${((source.total - source.interviews) / busiest) * 100}%`,
                    backgroundColor: "var(--muted-foreground)",
                    opacity: 0.25,
                  }}
                />
              </div>

              <p className="mt-1 text-xs text-muted-foreground">
                {source.sent === 0 ? (
                  "still on the wishlist"
                ) : (
                  <>
                    {source.interviews} of {source.sent} sent reached an
                    interview
                    {source.interview_rate !== null &&
                      ` (${formatRate(source.interview_rate)})`}
                    {source.offers > 0 &&
                      ` · ${source.offers} offer${source.offers === 1 ? "" : "s"}`}
                  </>
                )}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
