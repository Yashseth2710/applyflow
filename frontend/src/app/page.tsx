"use client";

import { useQuery } from "@tanstack/react-query";

import { api, API_BASE_URL } from "@/lib/api-client";
import type { HealthResponse } from "@/lib/types";

function StatusDot({ state }: { state: "ok" | "bad" | "pending" }) {
  const color =
    state === "ok"
      ? "bg-emerald-500"
      : state === "bad"
        ? "bg-red-500"
        : "bg-amber-400 animate-pulse";
  return <span className={`inline-block h-2.5 w-2.5 rounded-full ${color}`} />;
}

function Row({
  label,
  value,
  state,
}: {
  label: string;
  value: string;
  state?: "ok" | "bad" | "pending";
}) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-black/5 py-2.5 last:border-0 dark:border-white/10">
      <span className="text-sm text-neutral-500 dark:text-neutral-400">
        {label}
      </span>
      <span className="flex items-center gap-2 font-mono text-sm">
        {state && <StatusDot state={state} />}
        {value}
      </span>
    </div>
  );
}

export default function Home() {
  const { data, isPending, isError, error, refetch, isFetching } =
    useQuery<HealthResponse>({
      queryKey: ["health"],
      queryFn: () => api.get<HealthResponse>("/health"),
    });

  const dbState = isPending
    ? "pending"
    : data?.database.connected
      ? "ok"
      : "bad";

  return (
    <main className="mx-auto flex w-full max-w-xl flex-1 flex-col justify-center px-6 py-16">
      <h1 className="text-3xl font-semibold tracking-tight">ApplyFlow</h1>
      <p className="mt-2 text-sm text-neutral-500 dark:text-neutral-400">
        Milestone 1 — foundation. This page verifies the full stack end to end.
      </p>

      <section className="mt-8 rounded-xl border border-black/10 p-5 dark:border-white/15">
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-neutral-500">
          System status
        </h2>

        {isError ? (
          <div className="rounded-lg bg-red-50 p-4 text-sm dark:bg-red-950/40">
            <p className="font-medium text-red-700 dark:text-red-300">
              Cannot reach the API
            </p>
            <p className="mt-1 text-red-600/80 dark:text-red-400/80">
              {error instanceof Error ? error.message : "Unknown error"}
            </p>
            <p className="mt-3 font-mono text-xs text-red-600/70 dark:text-red-400/70">
              Start it with: uvicorn app.main:app --reload
            </p>
          </div>
        ) : (
          <div>
            <Row
              label="API"
              value={isPending ? "checking…" : (data?.status ?? "—")}
              state={isPending ? "pending" : data?.status === "ok" ? "ok" : "bad"}
            />
            <Row
              label="Database"
              value={
                isPending
                  ? "checking…"
                  : data?.database.connected
                    ? `connected · ${data.database.latency_ms}ms`
                    : (data?.database.error ?? "unreachable")
              }
              state={dbState}
            />
            <Row label="Version" value={data?.version ?? "—"} />
            <Row label="Environment" value={data?.environment ?? "—"} />
          </div>
        )}

        <div className="mt-4 flex items-center justify-between">
          <span className="font-mono text-xs text-neutral-400">
            {API_BASE_URL}
          </span>
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="rounded-md border border-black/10 px-3 py-1.5 text-xs font-medium transition-colors hover:bg-black/5 disabled:opacity-50 dark:border-white/15 dark:hover:bg-white/5"
          >
            {isFetching ? "Checking…" : "Re-check"}
          </button>
        </div>
      </section>
    </main>
  );
}
