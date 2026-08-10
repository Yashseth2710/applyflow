"use client";

import Link from "next/link";

import { ALL_STATUSES, STATUS_META } from "@/lib/application-status";
import type { ApplicationStatus, StatusCount } from "@/lib/types";

export function StatusSplit({ statuses }: { statuses: StatusCount[] }) {
  const counts = new Map(
    statuses.map((s) => [s.status as ApplicationStatus, s.count]),
  );
  const total = statuses.reduce((sum, s) => sum + s.count, 0);

  // Pipeline order, and only the statuses actually in use — a list of twelve
  // rows where nine read zero says less than a list of three.
  const present = ALL_STATUSES.filter(
    (status) => (counts.get(status) ?? 0) > 0,
  );

  return (
    <section className="rounded-xl border border-border bg-card p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-medium text-muted-foreground">
          Where things stand
        </h2>
        <Link
          href="/applications/board"
          className="text-xs text-primary hover:underline"
        >
          Open board →
        </Link>
      </div>

      {total === 0 ? (
        <p className="mt-6 text-sm text-muted-foreground">
          Nothing tracked yet.
        </p>
      ) : (
        <>
          <div
            className="mt-5 flex h-2.5 overflow-hidden rounded-full"
            aria-hidden
          >
            {present.map((status) => (
              <div
                key={status}
                style={{
                  width: `${((counts.get(status) ?? 0) / total) * 100}%`,
                  backgroundColor: `var(${STATUS_META[status].token})`,
                }}
              />
            ))}
          </div>

          <ul className="mt-4 space-y-2">
            {present.map((status) => (
              <li
                key={status}
                className="flex items-center justify-between gap-3 text-sm"
              >
                <span className="flex min-w-0 items-center gap-2">
                  <span
                    className="size-2 shrink-0 rounded-full"
                    style={{
                      backgroundColor: `var(${STATUS_META[status].token})`,
                    }}
                    aria-hidden
                  />
                  <span className="truncate">{STATUS_META[status].label}</span>
                </span>
                <span className="tabular shrink-0">{counts.get(status)}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
