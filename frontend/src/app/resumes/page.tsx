"use client";

import { formatDistanceToNow } from "date-fns";
import { FileText } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { AppShell } from "@/components/layout/app-shell";
import { UploadDropzone } from "@/components/resumes/upload-dropzone";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api-client";
import { EXTRACTION_META, formatBytes } from "@/lib/resume-format";
import { useResumes, useUploadResume } from "@/lib/resumes";
import type { Resume } from "@/lib/types";

export default function ResumesPage() {
  return (
    <AppShell>
      <ResumesList />
    </AppShell>
  );
}

function ResumesList() {
  const { data: resumes, isPending, isError, error } = useResumes();
  const upload = useUploadResume();
  const [uploadingName, setUploadingName] = useState<string | null>(null);

  function handleFile(file: File) {
    setUploadingName(file.name);
    upload.mutate(
      { file },
      {
        onSuccess: (resume) => {
          if (resume.duplicate_of_title) {
            toast.warning("Looks like a duplicate", {
              description: `Identical to "${resume.duplicate_of_title}". It has been kept anyway.`,
            });
          } else if (resume.extraction_status === "ok") {
            toast.success(`Uploaded "${resume.title}"`);
          } else {
            toast.warning(`Uploaded "${resume.title}"`, {
              description: resume.extraction_error ?? undefined,
            });
          }
        },
        onError: (err) => {
          toast.error("Upload failed", {
            description:
              err instanceof ApiError ? err.message : "Something went wrong. Try again.",
          });
        },
        onSettled: () => setUploadingName(null),
      },
    );
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Resumes</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {resumes ? `${resumes.length} ${resumes.length === 1 ? "resume" : "resumes"}` : "Loading…"}
          {" · "}
          Upload a new version any time — old ones are kept.
        </p>
      </div>

      <UploadDropzone
        className="mt-6"
        onFile={handleFile}
        disabled={upload.isPending}
        // Full size while it's the only thing to do; out of the way once there
        // are resumes to look at.
        compact={Boolean(resumes && resumes.length > 0)}
        label={
          uploadingName
            ? `Uploading ${uploadingName}…`
            : "Drop a PDF here, or click to choose one"
        }
      />

      <div className="mt-8">
        {isError ? (
          <div className="rounded-xl border border-danger/25 bg-danger-subtle p-6 text-sm">
            <p className="font-medium text-danger">Couldn&apos;t load resumes</p>
            <p className="mt-1 text-danger/80">
              {error instanceof Error ? error.message : "Failed to load"}
            </p>
          </div>
        ) : isPending ? (
          <div className="grid gap-3 sm:grid-cols-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-28 w-full rounded-xl" />
            ))}
          </div>
        ) : resumes.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border bg-surface p-12 text-center">
            <h2 className="text-lg font-medium">No resumes yet</h2>
            <p className="mx-auto mt-2 max-w-sm text-sm text-muted-foreground">
              Upload the resume you send to employers. You&apos;ll be able to attach it
              to applications and keep track of which version went where.
            </p>
          </div>
        ) : (
          <ul className="grid gap-3 sm:grid-cols-2">
            {resumes.map((resume) => (
              <li key={resume.id}>
                <ResumeCard resume={resume} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}

function ResumeCard({ resume }: { resume: Resume }) {
  const meta = EXTRACTION_META[resume.extraction_status];

  return (
    <Link
      href={`/resumes/${resume.id}`}
      className="flex h-full gap-4 rounded-xl border border-border bg-card p-4 transition-colors hover:border-primary/40 hover:bg-accent/40"
    >
      <span
        className="mt-0.5 inline-flex size-10 shrink-0 items-center justify-center rounded-lg"
        style={{ background: "var(--accent)", color: "var(--primary)" }}
      >
        <FileText className="size-5" aria-hidden />
      </span>

      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <p className="truncate font-medium">{resume.title}</p>
          {resume.version > 1 && (
            <span className="shrink-0 rounded-md bg-muted px-1.5 py-0.5 text-xs font-medium text-muted-foreground">
              v{resume.version}
            </span>
          )}
        </div>

        <p className="mt-0.5 truncate text-sm text-muted-foreground">
          {resume.original_filename}
        </p>

        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <span
              className="size-1.5 rounded-full"
              style={{ background: `var(${meta.tone})` }}
              aria-hidden
            />
            {meta.label}
          </span>
          <span>{formatBytes(resume.size_bytes)}</span>
          <span>
            {formatDistanceToNow(new Date(resume.created_at), { addSuffix: true })}
          </span>
        </div>
      </div>
    </Link>
  );
}
