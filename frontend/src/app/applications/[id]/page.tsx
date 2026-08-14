"use client";

import { ExternalLink } from "lucide-react";
import { Link } from "@/components/ui/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { StatusBadge } from "@/components/applications/status-badge";
import { AIPanel } from "@/components/ai/ai-panel";
import { InterviewSection } from "@/components/interviews/interview-section";
import { AppShell } from "@/components/layout/app-shell";
import { BackLink } from "@/components/ui/back-link";
import { Button, buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ThemedSelect } from "@/components/ui/themed-select";
import { ALL_STATUSES, STATUS_META } from "@/lib/application-status";
import {
  useApplication,
  useChangeStatus,
  useDeleteApplication,
} from "@/lib/applications";
import { formatBytes } from "@/lib/resume-format";
import { openResumeFile, useResume } from "@/lib/resumes";
import type { ApplicationDetail, ApplicationStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function ApplicationDetailPage() {
  return (
    <AppShell>
      <Detail />
    </AppShell>
  );
}

function Detail() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data, isPending, isError } = useApplication(id);
  const changeStatus = useChangeStatus();
  const remove = useDeleteApplication();
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  if (isPending) {
    return (
      <main className="mx-auto max-w-4xl space-y-4 px-6 py-8">
        <Skeleton className="h-9 w-72" />
        <Skeleton className="h-64 w-full rounded-xl" />
      </main>
    );
  }

  if (isError || !data) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-8">
        <h1 className="display text-2xl">Application not found</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          It may have been deleted.{" "}
          <Link href="/applications" className="text-primary hover:underline">
            Back to applications
          </Link>
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-8">
      <BackLink href="/applications">Applications</BackLink>

      <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="display text-[1.75rem] leading-tight">
            {data.job_title}
          </h1>
          <p className="mt-1 text-muted-foreground">
            {data.company_website ? (
              <a
                href={data.company_website}
                target="_blank"
                rel="noreferrer noopener"
                className="hover:text-foreground hover:underline"
              >
                {data.company_name}
              </a>
            ) : (
              data.company_name
            )}
            {data.location ? ` · ${data.location}` : ""}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Link
            href={`/applications/${id}/edit`}
            className={cn(buttonVariants({ variant: "outline" }), "h-9 px-3")}
          >
            Edit
          </Link>
          <Button
            variant="destructive"
            className="h-9 px-3"
            onClick={() => setConfirmingDelete(true)}
          >
            Delete
          </Button>
        </div>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-6">
          <section className="rounded-xl border border-border bg-card p-5 sm:p-6">
            <h2 className="eyebrow">Stage</h2>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <StatusBadge status={data.status} />
              <ThemedSelect
                className="w-56"
                aria-label="Change stage"
                value={data.status}
                onChange={(v) => {
                  const next = v as ApplicationStatus;
                  if (next === data.status) return;
                  changeStatus.mutate(
                    { id, status: next },
                    {
                      onSuccess: () =>
                        toast.success(`Moved to ${STATUS_META[next].label}`),
                      onError: () => toast.error("Couldn't change the stage"),
                    },
                  );
                }}
                options={ALL_STATUSES.map((s) => ({
                  value: s,
                  label: STATUS_META[s].label,
                }))}
              />
            </div>
          </section>

          <section className="rounded-xl border border-border bg-card p-5 sm:p-6">
            <h2 className="eyebrow">Details</h2>
            <dl className="mt-3 grid gap-x-6 gap-y-3 sm:grid-cols-2">
              <Detail_ label="Work mode" value={labelise(data.work_mode)} />
              <Detail_
                label="Employment type"
                value={labelise(data.employment_type)}
              />
              <Detail_ label="Source" value={data.source} />
              <Detail_ label="Salary" value={formatSalary(data)} />
              <Detail_ label="Applied" value={formatDate(data.date_applied)} />
              <Detail_ label="Posted" value={formatDate(data.date_posted)} />
            </dl>

            {data.job_url && (
              <a
                href={data.job_url}
                target="_blank"
                rel="noreferrer noopener"
                className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
              >
                View the job posting
                <ExternalLink className="size-3.5" aria-hidden />
              </a>
            )}
          </section>

          <AIPanel applicationId={id} />

          <InterviewSection applicationId={id} />

          {data.resume_id && <LinkedResume resumeId={data.resume_id} />}

          {data.job_description && (
            <section className="rounded-xl border border-border bg-card p-5 sm:p-6">
              <h2 className="eyebrow">
                Job description
              </h2>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed">
                {data.job_description}
              </p>
            </section>
          )}
        </div>

        <aside className="rounded-xl border border-border bg-card p-5 sm:p-6">
          <h2 className="eyebrow">History</h2>
          <ol className="mt-4 space-y-4">
            {[...data.status_history].reverse().map((entry, index) => (
              <li key={`${entry.changed_at}-${index}`} className="flex gap-3">
                <div className="flex flex-col items-center">
                  <span
                    className="mt-1 size-2.5 shrink-0 rounded-full"
                    style={{
                      backgroundColor: `var(${STATUS_META[entry.to_status].token})`,
                    }}
                  />
                  {index < data.status_history.length - 1 && (
                    <span className="mt-1 w-px flex-1 bg-border" />
                  )}
                </div>
                <div className="pb-1">
                  <p className="text-sm">
                    {entry.from_status ? (
                      <>
                        Moved to{" "}
                        <strong className="font-medium">
                          {STATUS_META[entry.to_status].label}
                        </strong>
                      </>
                    ) : (
                      <>
                        Added as{" "}
                        <strong className="font-medium">
                          {STATUS_META[entry.to_status].label}
                        </strong>
                      </>
                    )}
                  </p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {formatDateTime(entry.changed_at)}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </aside>
      </div>

      {confirmingDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-6">
          <div className="w-full max-w-sm rounded-xl border border-border bg-popover p-6">
            <h2 className="text-lg font-semibold">Delete this application?</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              {data.job_title} at {data.company_name}. Its history and notes go
              too. This can’t be undone.
            </p>
            <div className="mt-6 flex justify-end gap-2">
              <Button
                variant="outline"
                className="h-9 px-3"
                onClick={() => setConfirmingDelete(false)}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                className="h-9 px-3"
                onClick={() =>
                  remove.mutate(id, {
                    onSuccess: () => {
                      toast.success("Application deleted");
                      router.push("/applications");
                    },
                    onError: () => toast.error("Couldn't delete that"),
                  })
                }
                disabled={remove.isPending}
              >
                {remove.isPending ? "Deleting…" : "Delete"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

/** The resume that was actually sent. Fetched separately so the applications
 *  endpoint stays a single query. */
function LinkedResume({ resumeId }: { resumeId: string }) {
  const { data: resume, isPending, isError } = useResume(resumeId);

  if (isPending) {
    return <Skeleton className="h-24 w-full rounded-xl" />;
  }

  // The link can outlive the file if the resume was deleted from another tab.
  if (isError || !resume) return null;

  return (
    <section className="rounded-xl border border-border bg-card p-5 sm:p-6">
      <h2 className="eyebrow">Resume sent</h2>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <Link
            href={`/resumes/${resume.id}`}
            className="font-medium hover:text-primary hover:underline"
          >
            {resume.title}
            {resume.version > 1 ? ` (v${resume.version})` : ""}
          </Link>
          <p className="mt-0.5 truncate text-sm text-muted-foreground">
            {resume.original_filename} · {formatBytes(resume.size_bytes)}
          </p>
        </div>

        <Button
          variant="outline"
          className="h-9 px-3"
          onClick={() =>
            void openResumeFile(resume.id, resume.original_filename).catch(() =>
              toast.error("Couldn't open the file"),
            )
          }
        >
          Open
        </Button>
      </div>
    </section>
  );
}

function Detail_({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-0.5 text-sm">{value ?? "—"}</dd>
    </div>
  );
}

function labelise(value: string | null | undefined): string | null {
  if (!value) return null;
  return value.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
}

function formatSalary(application: ApplicationDetail): string | null {
  const { salary_min, salary_max, salary_currency } = application;
  if (salary_min == null && salary_max == null) return null;

  const format = (n: number) =>
    new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: salary_currency || "INR",
      maximumFractionDigits: 0,
    }).format(n);

  if (salary_min != null && salary_max != null) {
    return `${format(salary_min)} – ${format(salary_max)}`;
  }
  return format((salary_min ?? salary_max) as number);
}

/** Timestamps are stored UTC; Intl renders them in the viewer's zone. */
function formatDate(value: string | null | undefined): string | null {
  if (!value) return null;
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
