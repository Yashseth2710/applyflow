"use client";

import { ArrowRight } from "lucide-react";
import { Link } from "@/components/ui/link";
import { useMemo } from "react";

import { StatusBadge } from "@/components/applications/status-badge";
import {
  RemindersPanel,
  UpcomingInterviews,
} from "@/components/interviews/reminders-panel";
import { AppShell } from "@/components/layout/app-shell";
import { buttonVariants } from "@/components/ui/button";
import { Panel, PanelHeader } from "@/components/ui/panel";
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

  /*
    This was four equal cards, each holding a dot, a label and a 30px number —
    the hero-metric template, and the single most recognisable generated-UI
    scaffold there is. Four cards of identical weight also make the claim that
    the four numbers matter equally, and they do not: "Interviewing" is what
    you act on and "Rejections" is what you glance at.

    So it is one row now, inline, sharing a rule with the greeting. It takes a
    quarter of the vertical space, which matters more than it sounds — the
    reminders and interviews below are the reason anyone opens this page, and
    they were being pushed under the fold by a summary of themselves.
  */
  const stats = [
    { label: "Tracking", value: counts.total, token: "--stage-applied" },
    { label: "Active", value: counts.active, token: "--stage-assessment" },
    // "Interviewing", not "Interviews" — this counts applications sitting at an
    // interview stage, which is a different number from how many interviews are
    // booked, and the two panels below show that number.
    { label: "Interviewing", value: counts.interviews, token: "--stage-technical" },
    { label: "Offers", value: counts.offers, token: "--stage-offer" },
  ];

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="display text-[1.875rem] leading-tight">
            Welcome back, {user?.first_name}
          </h1>
          <p className="mt-1.5 text-sm text-muted-foreground">{today}</p>
        </div>
        <Link href="/applications/new" className={cn(buttonVariants(), "h-10 px-4")}>
          Add application
        </Link>
      </div>

      <section
        aria-label="Summary"
        className="mt-6 flex flex-wrap items-center gap-x-8 gap-y-4 border-y border-border py-4"
      >
        {stats.map((stat) => (
          <div key={stat.label} className="flex items-baseline gap-2.5">
            {isPending ? (
              <Skeleton className="h-7 w-8" />
            ) : (
              <span
                className="tabular text-2xl font-semibold"
                // The value carries the stage colour instead of a dot beside a
                // grey number. One element doing the job of two.
                style={{ color: `var(${stat.token}-ink)` }}
              >
                {stat.value}
              </span>
            )}
            <span className="text-sm text-muted-foreground">{stat.label}</span>
          </div>
        ))}
      </section>

      {!isPending && counts.total === 0 ? (
        <section className="mt-10 rounded-xl border border-dashed border-border-strong bg-surface px-6 py-14 text-center">
          <h2 className="display text-2xl">Nothing tracked yet</h2>
          <p className="mx-auto mt-3 max-w-md leading-relaxed text-muted-foreground">
            Add the first job you’re tracking. You’ll see it here, on
            the board, and in your analytics later.
          </p>
          <Link
            href="/applications/new"
            className={cn(buttonVariants(), "mt-7 h-10 px-4")}
          >
            Add your first application
          </Link>
        </section>
      ) : (
        <div className="mt-10 grid gap-6 lg:grid-cols-[1fr_340px]">
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
    <Panel>
      <PanelHeader
        title="Pipeline"
        action={
          <Link
            href="/applications/board"
            className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
          >
            Open board
            <ArrowRight className="size-3.5" aria-hidden />
          </Link>
        }
      />

      {isPending ? (
        <Skeleton className="mt-5 h-40 w-full" />
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
                      className="h-full rounded-full transition-[width] duration-500 ease-[cubic-bezier(0.2,0,0,1)]"
                      style={{
                        width: `${(count / max) * 100}%`,
                        backgroundColor: `var(${column.token})`,
                      }}
                    />
                  </div>
                  <span className="tabular w-6 text-right text-sm font-medium">
                    {count}
                  </span>
                </div>
              );
            })}
          </div>

          {closedCount > 0 && (
            <p className="mt-5 border-t border-border pt-3 text-xs text-muted-foreground">
              {closedCount} closed
            </p>
          )}
        </>
      )}
    </Panel>
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
    <Panel>
      <PanelHeader
        title="Recently added"
        action={
          <Link
            href="/applications"
            className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
          >
            See all
            <ArrowRight className="size-3.5" aria-hidden />
          </Link>
        }
      />

      {isPending ? (
        <div className="mt-5 space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-14 w-full rounded-lg" />
          ))}
        </div>
      ) : (
        /* Rows separated by rules rather than each wrapped in its own bordered
           box. Five boxes inside a box is the nested-card problem, and the
           borders were doing nothing the spacing did not already do. */
        <ul className="mt-4 divide-y divide-border">
          {applications.map((application) => (
            <li key={application.id}>
              <Link
                href={`/applications/${application.id}`}
                className="group -mx-2 block rounded-lg px-2 py-3 transition-colors duration-150 hover:bg-accent/50"
              >
                <p className="truncate text-sm font-medium group-hover:text-accent-foreground">
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
    </Panel>
  );
}
