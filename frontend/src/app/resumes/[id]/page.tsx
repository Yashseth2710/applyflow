"use client";

import { format, formatDistanceToNow } from "date-fns";
import { Check, Download, ExternalLink, Trash2 } from "lucide-react";
import { Link } from "@/components/ui/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { AppShell } from "@/components/layout/app-shell";
import { BackLink } from "@/components/ui/back-link";
import { UploadDropzone } from "@/components/resumes/upload-dropzone";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api-client";
import { EXTRACTION_META, formatBytes } from "@/lib/resume-format";
import {
  openResumeFile,
  useDeleteResume,
  useResume,
  useResumeText,
  useResumeUsage,
  useSetCurrentVersion,
  useUpdateResume,
  useUploadResume,
} from "@/lib/resumes";
import type { Resume, ResumeDetail } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function ResumeDetailPage() {
  return (
    <AppShell>
      <Detail />
    </AppShell>
  );
}

function Detail() {
  const { id } = useParams<{ id: string }>();
  const { data, isPending, isError } = useResume(id);

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
        <h1 className="display text-2xl">Resume not found</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          It may have been deleted.{" "}
          <Link href="/resumes" className="text-primary hover:underline">
            Back to resumes
          </Link>
        </p>
      </main>
    );
  }

  return <Loaded resume={data} />;
}

function Loaded({ resume }: { resume: ResumeDetail }) {
  const router = useRouter();
  const meta = EXTRACTION_META[resume.extraction_status];

  const upload = useUploadResume();
  const setCurrent = useSetCurrentVersion();
  const remove = useDeleteResume();

  const [busy, setBusy] = useState(false);

  function uploadNewVersion(file: File) {
    setBusy(true);
    upload.mutate(
      { file, replacesId: resume.id },
      {
        onSuccess: (created) => {
          toast.success(`Version ${created.version} uploaded`);
          // The new version is a different row, so move to it.
          router.push(`/resumes/${created.id}`);
        },
        onError: (err) =>
          toast.error("Upload failed", {
            description:
              err instanceof ApiError ? err.message : "Something went wrong. Try again.",
          }),
        onSettled: () => setBusy(false),
      },
    );
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-8">
      <BackLink href="/resumes">Resumes</BackLink>

      <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="display text-[1.75rem] leading-tight">{resume.title}</h1>
          <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
            <span>{resume.original_filename}</span>
            <span>{formatBytes(resume.size_bytes)}</span>
            <span>Version {resume.version}</span>
            <span>
              Uploaded {format(new Date(resume.created_at), "d MMM yyyy")}
            </span>
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            className="h-9 px-3"
            onClick={() =>
              void openResumeFile(resume.id, resume.original_filename).catch(() =>
                toast.error("Couldn't open the file"),
              )
            }
          >
            <ExternalLink className="mr-1.5 size-4" aria-hidden />
            Open
          </Button>
          <Button
            variant="outline"
            className="h-9 px-3"
            onClick={() =>
              void openResumeFile(resume.id, resume.original_filename, true).catch(() =>
                toast.error("Couldn't download the file"),
              )
            }
          >
            <Download className="mr-1.5 size-4" aria-hidden />
            Download
          </Button>
        </div>
      </div>

      {meta.actionable && (
        <div
          role="status"
          className="mt-6 rounded-xl border border-warning/30 bg-warning-subtle px-4 py-3 text-sm"
        >
          {/* --warning-foreground belongs on the solid --warning background;
              here it would be dark-on-dark. */}
          <p className="font-medium" style={{ color: "var(--warning)" }}>
            {meta.label}
          </p>
          <p className="mt-1 text-foreground">{resume.extraction_error}</p>
        </div>
      )}

      <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_18rem]">
        <div className="space-y-8">
          <DetailsForm resume={resume} />
          <ExtractedText resumeId={resume.id} status={resume.extraction_status} />
        </div>

        <aside className="space-y-8">
          <section>
            <h2 className="eyebrow">New version</h2>
            <UploadDropzone
              className="mt-3"
              onFile={uploadNewVersion}
              disabled={busy}
              label={busy ? "Uploading…" : "Replace with an updated PDF"}
            />
          </section>

          <Versions
            resume={resume}
            onSetCurrent={(versionId) =>
              setCurrent.mutate(versionId, {
                onSuccess: () => toast.success("Current version updated"),
                onError: () => toast.error("Couldn't update the current version"),
              })
            }
          />

          <DangerZone
            resume={resume}
            onDelete={() =>
              remove.mutate(resume.id, {
                onSuccess: () => {
                  toast.success("Resume deleted");
                  router.push("/resumes");
                },
                onError: () => toast.error("Couldn't delete the resume"),
              })
            }
          />
        </aside>
      </div>
    </main>
  );
}

function DetailsForm({ resume }: { resume: ResumeDetail }) {
  const update = useUpdateResume(resume.id);
  const [title, setTitle] = useState(resume.title);
  const [notes, setNotes] = useState(resume.notes ?? "");

  const dirty = title.trim() !== resume.title || notes.trim() !== (resume.notes ?? "");

  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        if (!title.trim()) return;
        update.mutate(
          { title: title.trim(), notes: notes.trim() || null },
          {
            onSuccess: () => toast.success("Details saved"),
            onError: (err) =>
              toast.error("Couldn't save", {
                description: err instanceof ApiError ? err.message : undefined,
              }),
          },
        );
      }}
    >
      <h2 className="eyebrow">Details</h2>

      <div className="space-y-2">
        <Label htmlFor="resume-title">Title</Label>
        <Input
          id="resume-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          maxLength={200}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="resume-notes">Notes</Label>
        <Textarea
          id="resume-notes"
          rows={3}
          placeholder="What this version is tuned for…"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
      </div>

      <Button
        type="submit"
        className="h-9 px-4"
        disabled={!dirty || !title.trim() || update.isPending}
      >
        {update.isPending ? "Saving…" : "Save details"}
      </Button>
    </form>
  );
}

function ExtractedText({
  resumeId,
  status,
}: {
  resumeId: string;
  status: ResumeDetail["extraction_status"];
}) {
  const [shown, setShown] = useState(false);
  const { data, isPending } = useResumeText(resumeId, shown);

  if (status !== "ok") return null;

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <h2 className="eyebrow">Extracted text</h2>
        <Button
          variant="ghost"
          className="h-8 px-2 text-xs"
          onClick={() => setShown((s) => !s)}
        >
          {shown ? "Hide" : "Show"}
        </Button>
      </div>

      <p className="text-xs text-muted-foreground">
        This is what the AI features will read. If it looks wrong, the PDF is
        probably laid out in columns.
      </p>

      {shown &&
        (isPending ? (
          <Skeleton className="h-48 w-full rounded-xl" />
        ) : (
          <pre className="max-h-96 overflow-auto rounded-xl border border-border bg-surface p-4 text-xs leading-relaxed whitespace-pre-wrap">
            {data?.extracted_text}
          </pre>
        ))}
    </section>
  );
}

function Versions({
  resume,
  onSetCurrent,
}: {
  resume: ResumeDetail;
  onSetCurrent: (id: string) => void;
}) {
  if (resume.versions.length <= 1) return null;

  return (
    <section>
      <h2 className="eyebrow">Versions</h2>
      <ul className="mt-3 space-y-2">
        {resume.versions.map((version) => (
          <li key={version.id}>
            <VersionRow
              version={version}
              isOpen={version.id === resume.id}
              onSetCurrent={() => onSetCurrent(version.id)}
            />
          </li>
        ))}
      </ul>
    </section>
  );
}

function VersionRow({
  version,
  isOpen,
  onSetCurrent,
}: {
  version: Resume;
  isOpen: boolean;
  onSetCurrent: () => void;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border p-3 text-sm",
        isOpen ? "border-primary/40 bg-accent/40" : "border-border bg-card",
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <Link href={`/resumes/${version.id}`} className="font-medium hover:underline">
          Version {version.version}
        </Link>
        {version.is_current && (
          <span className="inline-flex items-center gap-1 rounded-md bg-success-subtle px-1.5 py-0.5 text-xs font-medium text-success-ink">
            <Check className="size-3" aria-hidden />
            Current
          </span>
        )}
      </div>

      <p className="mt-1 text-xs text-muted-foreground">
        {formatDistanceToNow(new Date(version.created_at), { addSuffix: true })} ·{" "}
        {formatBytes(version.size_bytes)}
      </p>

      {!version.is_current && (
        <Button variant="outline" className="mt-2 h-7 px-2 text-xs" onClick={onSetCurrent}>
          Make current
        </Button>
      )}
    </div>
  );
}

function DangerZone({ resume, onDelete }: { resume: ResumeDetail; onDelete: () => void }) {
  const [confirming, setConfirming] = useState(false);
  // Only asked for once the user reaches for delete — the count is a question
  // nobody has until then.
  const { data: usage } = useResumeUsage(resume.id, confirming);

  const isOnlyVersion = resume.versions.length <= 1;

  return (
    <section>
      <h2 className="eyebrow">Delete</h2>

      {confirming ? (
        <div className="mt-3 rounded-xl border border-danger/25 bg-danger-subtle p-3 text-sm">
          <p className="font-medium text-danger">
            Delete {isOnlyVersion ? "this resume" : `version ${resume.version}`}?
          </p>
          <p className="mt-1 text-danger/80">
            {usage === undefined
              ? "Checking where it's used…"
              : usage.application_count === 0
                ? "No applications use this file."
                : `${usage.application_count} application${
                    usage.application_count === 1 ? "" : "s"
                  } used this file. They'll be kept, but will no longer link to it.`}
          </p>

          <div className="mt-3 flex gap-2">
            <Button
              className="h-8 px-3 text-xs"
              style={{ background: "var(--danger)", color: "var(--danger-foreground)" }}
              onClick={onDelete}
            >
              <Trash2 className="mr-1.5 size-3.5" aria-hidden />
              Delete
            </Button>
            <Button
              variant="outline"
              className="h-8 px-3 text-xs"
              onClick={() => setConfirming(false)}
            >
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <Button
          variant="outline"
          className="mt-3 h-9 px-3 text-danger"
          onClick={() => setConfirming(true)}
        >
          <Trash2 className="mr-1.5 size-4" aria-hidden />
          Delete {isOnlyVersion ? "resume" : "this version"}
        </Button>
      )}
    </section>
  );
}
