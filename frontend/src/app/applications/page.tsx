"use client";

import { Link } from "@/components/ui/link";
import { useEffect, useState } from "react";

import { StatusBadge } from "@/components/applications/status-badge";
import { AppShell } from "@/components/layout/app-shell";
import { buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ThemedSelect } from "@/components/ui/themed-select";
import { ALL_STATUSES, STATUS_META } from "@/lib/application-status";
import { useApplications, useSources, type ListParams } from "@/lib/applications";
import type { ApplicationStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function ApplicationsPage() {
  return (
    <AppShell>
      <ApplicationsList />
    </AppShell>
  );
}

function ApplicationsList() {
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [status, setStatus] = useState<ApplicationStatus | "">("");
  const [source, setSource] = useState("");
  const [sort, setSort] = useState<`${NonNullable<ListParams["sort_by"]>}:${"asc" | "desc"}`>(
    "created_at:desc",
  );
  const [page, setPage] = useState(1);

  // Debounced so typing doesn't fire a request per keystroke.
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  const [sortBy, order] = sort.split(":") as [
    NonNullable<ListParams["sort_by"]>,
    "asc" | "desc",
  ];

  const { data, isPending, isError, error } = useApplications({
    search: debouncedSearch,
    status,
    source,
    sort_by: sortBy,
    order,
    page,
    page_size: 20,
  });
  const { data: sources } = useSources();

  const hasFilters = Boolean(debouncedSearch || status || source);

  return (
    <main className="mx-auto max-w-6xl px-6 py-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="display text-[1.75rem] leading-tight">Applications</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {data ? `${data.total} total` : "Loading…"}
          </p>
        </div>
        <Link
          href="/applications/new"
          className={cn(buttonVariants(), "h-10 px-4")}
        >
          Add application
        </Link>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Input
          placeholder="Search company, title or location…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search applications"
        />

        <ThemedSelect
          aria-label="Filter by stage"
          placeholder="All stages"
          value={status}
          onChange={(v) => {
            setStatus(v as ApplicationStatus | "");
            setPage(1);
          }}
          options={[
            { value: "", label: "All stages" },
            ...ALL_STATUSES.map((s) => ({
              value: s,
              label: STATUS_META[s].label,
            })),
          ]}
        />

        <ThemedSelect
          aria-label="Filter by source"
          placeholder="All sources"
          value={source}
          onChange={(v) => {
            setSource(v);
            setPage(1);
          }}
          options={[
            { value: "", label: "All sources" },
            ...(sources ?? []).map((s) => ({ value: s, label: s })),
          ]}
        />

        <ThemedSelect
          aria-label="Sort"
          value={sort}
          onChange={(v) => setSort(v as typeof sort)}
          options={[
            { value: "created_at:desc", label: "Newest first" },
            { value: "created_at:asc", label: "Oldest first" },
            { value: "date_applied:desc", label: "Recently applied" },
            { value: "company_name:asc", label: "Company A–Z" },
            { value: "job_title:asc", label: "Job title A–Z" },
          ]}
        />
      </div>

      <div className="mt-6">
        {isError ? (
          <ErrorState message={error instanceof Error ? error.message : "Failed to load"} />
        ) : isPending ? (
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-16 w-full rounded-xl" />
            ))}
          </div>
        ) : data.items.length === 0 ? (
          <EmptyState hasFilters={hasFilters} />
        ) : (
          /* Ruled, not boxed. Every row wrapped in its own bordered rectangle
             is depth that says nothing: the rows are siblings, and a hairline
             between them says so far more quietly. It also removes forty
             borders from a page of twenty applications, which is most of why
             the list read as heavy. */
          <ul className="divide-y divide-border border-y border-border">
            {data.items.map((application) => (
              <li key={application.id}>
                <Link
                  href={`/applications/${application.id}`}
                  className="flex items-center gap-4 px-3 py-3.5 transition-colors duration-150 hover:bg-accent/50"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{application.job_title}</p>
                    <p className="mt-0.5 truncate text-sm text-muted-foreground">
                      {application.company_name}
                      {application.location ? ` · ${application.location}` : ""}
                    </p>
                  </div>

                  {application.source && (
                    <span className="hidden shrink-0 text-xs text-muted-foreground md:inline">
                      {application.source}
                    </span>
                  )}

                  <StatusBadge status={application.status} short />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>

      {data && data.pages > 1 && (
        <div className="mt-6 flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Page {data.page} of {data.pages}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className={cn(
                buttonVariants({ variant: "outline" }),
                "h-9 px-3 disabled:opacity-40",
              )}
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={page >= data.pages}
              className={cn(
                buttonVariants({ variant: "outline" }),
                "h-9 px-3 disabled:opacity-40",
              )}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </main>
  );
}

function EmptyState({ hasFilters }: { hasFilters: boolean }) {
  return (
    <div className="rounded-xl border border-dashed border-border bg-surface p-12 text-center">
      <h2 className="text-lg font-medium">
        {hasFilters ? "Nothing matches those filters" : "No applications yet"}
      </h2>
      <p className="mx-auto mt-2 max-w-sm text-sm text-muted-foreground">
        {hasFilters
          ? "Try a different search or clear the filters."
          : "Add the first job you're tracking and it'll show up here and on the board."}
      </p>
      {!hasFilters && (
        <Link
          href="/applications/new"
          className={cn(buttonVariants(), "mt-6 h-10 px-4")}
        >
          Add your first application
        </Link>
      )}
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-danger/25 bg-danger-subtle p-6 text-sm">
      <p className="font-medium text-danger">Couldn’t load applications</p>
      <p className="mt-1 text-danger/80">{message}</p>
    </div>
  );
}
