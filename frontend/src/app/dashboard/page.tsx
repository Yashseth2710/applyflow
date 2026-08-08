"use client";

import { RequireAuth } from "@/components/auth/require-auth";
import { Logo } from "@/components/brand/logo";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";

/** Placeholder tiles. Milestone 3 replaces these with real counts. */
const TILES = [
  { label: "Applications", value: 0, tone: "stage-applied" },
  { label: "Interviews", value: 0, tone: "stage-technical" },
  { label: "Offers", value: 0, tone: "stage-offer" },
  { label: "Rejections", value: 0, tone: "stage-rejected" },
] as const;

export default function DashboardPage() {
  return (
    <RequireAuth>
      <Dashboard />
    </RequireAuth>
  );
}

function Dashboard() {
  const { user, logout } = useAuth();

  const timezone = user?.profile?.timezone ?? "—";
  const today = new Intl.DateTimeFormat("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
    timeZone: user?.profile?.timezone || undefined,
  }).format(new Date());

  return (
    <div className="min-h-svh bg-background">
      <header className="border-b border-border bg-surface">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2.5">
            <span className="text-primary">
              <Logo />
            </span>
            <span className="font-semibold tracking-tight">ApplyFlow</span>
          </div>

          <div className="flex items-center gap-4">
            <span className="hidden text-sm text-muted-foreground sm:inline">
              {user?.email}
            </span>
            <Button variant="outline" size="sm" onClick={() => void logout()}>
              Sign out
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-10">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Welcome back, {user?.first_name}
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {today} · {timezone}
            </p>
          </div>
        </div>

        <section className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {TILES.map((tile) => (
            <div
              key={tile.label}
              className="rounded-xl border border-border bg-card p-5"
            >
              <div className="flex items-center gap-2">
                <span
                  className="size-2 rounded-full"
                  style={{ background: `var(--${tile.tone})` }}
                />
                <span className="text-sm text-muted-foreground">{tile.label}</span>
              </div>
              <p className="tabular mt-3 text-3xl font-semibold">{tile.value}</p>
            </div>
          ))}
        </section>

        <section className="mt-8 rounded-xl border border-dashed border-border bg-surface p-10 text-center">
          <h2 className="text-lg font-medium">No applications yet</h2>
          <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
            Application tracking arrives in the next milestone. Your account,
            profile and timezone are already set up and working.
          </p>
        </section>
      </main>
    </div>
  );
}
