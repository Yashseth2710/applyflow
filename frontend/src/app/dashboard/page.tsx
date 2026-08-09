"use client";

import Link from "next/link";
import { useMemo } from "react";

import { StatusBadge } from "@/components/applications/status-badge";
import {
  RemindersPanel,
  UpcomingInterviews,
} from "@/components/interviews/reminders-panel";
import { AppShell } from "@/components/layout/app-shell";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  BOARD_COLUMNS,
  CLOSED_STATUSES,
  isClosed,
  type BoardColumnDef,
} from "@/lib/application-status";
import { useBoard } from "@/lib/applications";
import { useAuth } from "@/lib/auth-context";
import type { Application, ApplicationStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const INTERVIEW_STATUSES: ApplicationStatus[] = [
  "phone_screen",
  "technical_interview",
  "hr_interview",
  "final_interview",
];

export default function DashboardPage() {
  return (
    <AppShell>
      <Dashboard />
    </AppShell>
  );
}

function Dashboard() {
  const { user } = useAuth();
  const { data, isPending } = useBoard();

  const today = new Intl.DateTimeFormat("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
    timeZone: user?.profile?.timezone || undefined,
  }).format(new Date());

  const all = useMemo(
    () => (data?.columns ?? []).flatMap((c) => c.items),
    [data],
  );

  const counts = useMemo(() => {
    const by = (predicate: (a: Application) => boolean) =>
      all.filter(predicate).length;
    return {
      total: all.length,
      active: by((a) => !isClosed(a.status as ApplicationStatus)),
      interviews: by((a) =>
        INTERVIEW_STATUSES.includes(a.status as ApplicationStatus),
      ),
      offers: by((a) => a.status === "offer" || a.status === "accepted"),
      rejections: by((a) => a.status === "rejected"),
    };
  }, [all]);

  const recent = useMemo(
    () =>
      [...all]
        .sort(
          (a, b) =>
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
        )
        .slice(0, 5),
    [all],
  );

  const tiles = [
    { label: "Applications", value: counts.total, token: "--stage-applied" },
    // "Interviewing", not "Interviews" — this counts applications sitting at an
    // interview stage, which is a different number from how many interviews are
    // booked, and the two panels below show that number.
    { label: "Interviewing", value: counts.interviews, token: "--stage-technical" },
    { label: "Offers", value: counts.offers, token: "--stage-offer" },
    { label: "Rejections", value: counts.rejections, token: "--stage-rejected" },
  ];

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Welcome back, {user?.first_name}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">{today}</p>
        </div>
        <Link href="/applications/new" className={cn(buttonVariants(), "h-10 px-4")}>
          Add application
        </Link>
      </div>

      <section className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {tiles.map((tile) => (
          <div
            key={tile.label}
            className="rounded-xl border border-border bg-card p-5"
          >
            <div className="flex items-center gap-2">
              <span
                className="size-2 rounded-full"
                style={{ backgroundColor: `var(${tile.token})` }}
              />
              <span className="text-sm text-muted-foreground">{tile.label}</span>
            </div>
            {isPending ? (
              <Skeleton className="mt-3 h-9 w-12" />
            ) : (
              <p className="tabular mt-3 text-3xl font-semibold">{tile.value}</p>
            )}
          </div>
        ))}
      </section>

      {!isPending && counts.total === 0 ? (
        <section className="mt-8 rounded-xl border border-dashed border-border bg-surface p-12 text-center">
          <h2 className="text-lg font-medium">No applications yet</h2>
          <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
            Add the first job you&apos;re tracking. You&apos;ll see it here, on
            the board, and in your analytics later.
          </p>
          <Link
            href="/applications/new"
            className={cn(buttonVariants(), "mt-6 h-10 px-4")}
          >
            Add your first application
          </Link>
        </section>
      ) : (
        <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_340px]">
          <div className="space-y-6">
            <RemindersPanel />
            <Pipeline data={data} isPending={isPending} />
          </div>
          <div className="space-y-6">
            <UpcomingInterviews />
            <Recent applications={recent} isPending={isPending} />
          </div>
        </div>
      )}
    </main>
  );
}

function Pipeline({
  data,
  isPending,
}: {
  data: ReturnType<typeof useBoard>["data"];
  isPending: boolean;
}) {
  const countFor = (column: BoardColumnDef) =>
    (data?.columns ?? [])
      .filter((c) => column.statuses.includes(c.status as ApplicationStatus))
      .reduce((sum, c) => sum + c.count, 0);

  const closedCount = (data?.columns ?? [])
    .filter((c) => CLOSED_STATUSES.includes(c.status as ApplicationStatus))
    .reduce((sum, c) => sum + c.count, 0);

  const max = Math.max(1, ...BOARD_COLUMNS.map(countFor));

  return (
    <section className="rounded-xl border border-border bg-card p-5">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-medium text-muted-foreground">Pipeline</h2>
        <Link
          href="/applications/board"
          className="text-xs text-primary hover:underline"
        >
          Open board →
        </Link>
      </div>

      {isPending ? (
        <Skeleton className="mt-4 h-40 w-full" />
      ) : (
        <>
          <div className="mt-5 space-y-3">
            {BOARD_COLUMNS.map((column) => {
              const count = countFor(column);
              return (
                <div key={column.id} className="flex items-center gap-3">
                  <span className="w-24 shrink-0 text-xs text-muted-foreground">
                    {column.label}
                  </span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full transition-[width]"
                      style={{
                        width: `${(count / max) * 100}%`,
                        backgroundColor: `var(${column.token})`,
                      }}
                    />
                  </div>
                  <span className="tabular w-6 text-right text-sm">{count}</span>
                </div>
              );
            })}
          </div>

          {closedCount > 0 && (
            <p className="mt-4 border-t border-border pt-3 text-xs text-muted-foreground">
              {closedCount} closed
            </p>
          )}
        </>
      )}
    </section>
  );
}

function Recent({
  applications,
  isPending,
}: {
  applications: Application[];
  isPending: boolean;
}) {
  return (
    <section className="rounded-xl border border-border bg-card p-5">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-medium text-muted-foreground">
          Recently added
        </h2>
        <Link href="/applications" className="text-xs text-primary hover:underline">
          See all →
        </Link>
      </div>

      {isPending ? (
        <div className="mt-4 space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full rounded-lg" />
          ))}
        </div>
      ) : (
        <ul className="mt-4 space-y-2">
          {applications.map((application) => (
            <li key={application.id}>
              <Link
                href={`/applications/${application.id}`}
                className="block rounded-lg border border-border p-3 transition-colors hover:border-primary/40 hover:bg-accent/40"
              >
                <p className="truncate text-sm font-medium">
                  {application.job_title}
                </p>
                <div className="mt-1.5 flex items-center gap-2">
                  <StatusBadge status={application.status} short />
                  <span className="truncate text-xs text-muted-foreground">
                    {application.company_name}
                  </span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
