"use client";

import { Link } from "@/components/ui/link";

import { Activity } from "@/components/analytics/activity";
import { Funnel } from "@/components/analytics/funnel";
import { Sources } from "@/components/analytics/sources";
import { StatusSplit } from "@/components/analytics/status-split";
import { Timing } from "@/components/analytics/timing";
import { AppShell } from "@/components/layout/app-shell";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDays, formatRate, useAnalytics } from "@/lib/analytics";
import type { AnalyticsSummary } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function AnalyticsPage() {
  return (
    <AppShell>
      <Analytics />
    </AppShell>
  );
}

function Analytics() {
  const { data, isPending, isError } = useAnalytics();

  if (isPending) return <Loading />;

  if (isError || !data) {
    return (
      <main className="mx-auto max-w-6xl px-6 py-10">
        <h1 className="display text-[1.75rem] leading-tight">Analytics</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Couldn’t load your numbers just now. Refresh and they should come
          back.
        </p>
      </main>
    );
  }

  if (data.totals.applications === 0) return <Empty />;

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <header>
        <h1 className="display text-[1.75rem] leading-tight">Analytics</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Your search so far, worked out from every stage change you’ve
          recorded.
        </p>
      </header>

      <Headline summary={data} />

      {!data.has_enough_data && <EarlyDaysNote summary={data} />}

      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_340px]">
        <Funnel steps={data.funnel} />
        <StatusSplit statuses={data.statuses} />
      </div>

      <div className="mt-6">
        <Activity volume={data.volume} />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Sources sources={data.sources} />
        <Timing stages={data.stage_durations} />
      </div>
    </main>
  );
}

function Headline({ summary }: { summary: AnalyticsSummary }) {
  const { totals } = summary;
  const reachedInterview =
    summary.funnel.find((step) => step.key === "interview")?.count ?? 0;

  const tiles = [
    {
      label: "Applications sent",
      value: String(totals.applied),
      note:
        totals.applications > totals.applied
          ? `${totals.applications - totals.applied} still on the wishlist`
          : "everything you're tracking",
      token: "--stage-applied",
    },
    {
      label: "Heard back",
      value: formatRate(totals.response_rate),
      note:
        totals.median_days_to_response !== null
          ? `usually within ${formatDays(totals.median_days_to_response)}`
          : `${totals.response_samples} replied so far`,
      token: "--stage-assessment",
    },
    {
      label: "Reached an interview",
      value: formatRate(totals.interview_rate),
      // How many applications got that far, not how many interviews are in the
      // calendar — someone can reach the stage without having booked anything,
      // and "50%" above "0 interviews booked" reads like a contradiction.
      note:
        `${reachedInterview} of ${totals.applied}` +
        (totals.interviews_scheduled > 0
          ? ` · ${totals.interviews_scheduled} booked`
          : ""),
      token: "--stage-technical",
    },
    {
      label: "Offers",
      value: formatRate(totals.offer_rate),
      note: `${totals.offers} of ${totals.applied}`,
      token: "--stage-offer",
    },
  ];

  return (
    <section className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {tiles.map((tile) => (
        <div
          key={tile.label}
          className="rounded-xl border border-border bg-card p-5 sm:p-6"
        >
          <div className="flex items-center gap-2">
            <span
              className="size-2 rounded-full"
              style={{ backgroundColor: `var(${tile.token})` }}
              aria-hidden
            />
            <span className="text-sm text-muted-foreground">{tile.label}</span>
          </div>
          <p className="tabular mt-3 text-3xl font-semibold">{tile.value}</p>
          <p className="mt-1 text-xs text-muted-foreground">{tile.note}</p>
        </div>
      ))}
    </section>
  );
}

function EarlyDaysNote({ summary }: { summary: AnalyticsSummary }) {
  const remaining = summary.min_sample - summary.totals.applied;

  return (
    // --warning-foreground pairs with the solid --warning background; on the
    // subtle one it reads dark on dark.
    <p className="mt-6 rounded-xl border border-warning/35 bg-warning-subtle px-4 py-3 text-sm text-foreground">
      <span className="font-medium" style={{ color: "var(--warning)" }}>
        Percentages are on hold.
      </span>{" "}
      One offer out of two applications is a 50% offer rate, and that number
      would be nonsense. Counts and timings below are accurate now;{" "}
      {remaining === 1
        ? "one more application sent"
        : `${remaining} more applications sent`}{" "}
      and the rates fill in.
    </p>
  );
}

function Empty() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <h1 className="display text-[1.75rem] leading-tight">Analytics</h1>

      <section className="mt-8 rounded-xl border border-dashed border-border bg-surface p-12 text-center">
        <h2 className="text-lg font-medium">Nothing to measure yet</h2>
        <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
          Every stage change you record gets counted here — how far applications
          get, how long each stage takes, and which sources are worth your time.
        </p>
        <Link
          href="/applications/new"
          className={cn(buttonVariants(), "mt-6 h-10 px-4")}
        >
          Add your first application
        </Link>
      </section>
    </main>
  );
}

function Loading() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <Skeleton className="h-8 w-40" />
      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-32 rounded-xl" />
        ))}
      </div>
      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_340px]">
        <Skeleton className="h-80 rounded-xl" />
        <Skeleton className="h-80 rounded-xl" />
      </div>
      <Skeleton className="mt-6 h-72 rounded-xl" />
    </main>
  );
}
