"use client";

import { format } from "date-fns";
import { AlertTriangle, CalendarClock } from "lucide-react";
import Link from "next/link";

import { Skeleton } from "@/components/ui/skeleton";
import { ROUND_LABELS } from "@/lib/interview-meta";
import { useReminders, useUpcomingInterviews } from "@/lib/interviews";
import type { Reminder } from "@/lib/types";

export function RemindersPanel() {
  const { data, isPending } = useReminders();

  return (
    <section className="rounded-xl border border-border bg-card p-5">
      <h2 className="text-sm font-medium text-muted-foreground">Needs attention</h2>

      {isPending ? (
        <div className="mt-4 space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-14 w-full rounded-lg" />
          ))}
        </div>
      ) : !data || data.items.length === 0 ? (
        <p className="mt-4 text-sm text-muted-foreground">
          Nothing needs chasing. Interviews in the next week and applications that have
          gone quiet will show up here.
        </p>
      ) : (
        <ul className="mt-4 space-y-2">
          {data.items.slice(0, 6).map((reminder, index) => (
            <li key={`${reminder.kind}-${reminder.interview_id ?? reminder.application_id}-${index}`}>
              <ReminderRow reminder={reminder} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function ReminderRow({ reminder }: { reminder: Reminder }) {
  const warning = reminder.severity === "warning";
  const Icon = warning ? AlertTriangle : CalendarClock;

  return (
    <Link
      href={`/applications/${reminder.application_id}`}
      className={`flex gap-3 rounded-lg border p-3 transition-colors ${
        warning
          ? "border-warning/35 bg-warning-subtle hover:border-warning/60"
          : "border-border hover:border-primary/40 hover:bg-accent/40"
      }`}
    >
      <Icon
        className="mt-0.5 size-4 shrink-0"
        style={{ color: warning ? "var(--warning)" : "var(--primary)" }}
        aria-hidden
      />
      <div className="min-w-0">
        {/* Deliberately not --warning-foreground: that pairs with the solid
            --warning background, and on the subtle one it is dark-on-dark. */}
        <p className="truncate text-sm font-medium text-foreground">{reminder.title}</p>
        <p
          className="mt-0.5 text-xs"
          style={{ color: warning ? "var(--warning)" : "var(--muted-foreground)" }}
        >
          {reminder.detail}
        </p>
      </div>
    </Link>
  );
}

export function UpcomingInterviews() {
  const { data, isPending } = useUpcomingInterviews(5);

  if (!isPending && (!data || data.length === 0)) return null;

  return (
    <section className="rounded-xl border border-border bg-card p-5">
      <h2 className="text-sm font-medium text-muted-foreground">Coming up</h2>

      {isPending ? (
        <div className="mt-4 space-y-2">
          {Array.from({ length: 2 }).map((_, i) => (
            <Skeleton key={i} className="h-14 w-full rounded-lg" />
          ))}
        </div>
      ) : (
        <ul className="mt-4 space-y-2">
          {data?.map((interview) => (
            <li key={interview.id}>
              <Link
                href={`/applications/${interview.application_id}`}
                className="block rounded-lg border border-border p-3 transition-colors hover:border-primary/40 hover:bg-accent/40"
              >
                <div className="flex items-baseline justify-between gap-2">
                  <p className="truncate text-sm font-medium">{interview.company_name}</p>
                  <span className="shrink-0 text-xs text-muted-foreground">
                    {format(new Date(interview.scheduled_at), "d MMM, HH:mm")}
                  </span>
                </div>
                <p className="mt-0.5 truncate text-xs text-muted-foreground">
                  {ROUND_LABELS[interview.round]} · {interview.job_title}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
