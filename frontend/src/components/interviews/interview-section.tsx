"use client";

import { format } from "date-fns";
import { CalendarPlus, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ThemedSelect } from "@/components/ui/themed-select";
import { ApiError } from "@/lib/api-client";
import {
  ALL_MODES,
  ALL_OUTCOMES,
  ALL_ROUNDS,
  MODE_LABELS,
  OUTCOME_META,
  ROUND_LABELS,
  fromLocalInputValue,
  toLocalInputValue,
} from "@/lib/interview-meta";
import {
  useCreateInterview,
  useDeleteInterview,
  useInterviews,
  useUpdateInterview,
} from "@/lib/interviews";
import type { Interview, InterviewMode, InterviewOutcome, InterviewRound } from "@/lib/types";
import { useNow } from "@/lib/use-now";
import { cn } from "@/lib/utils";

export function InterviewSection({ applicationId }: { applicationId: string }) {
  const { data: interviews, isPending } = useInterviews(applicationId);
  const [adding, setAdding] = useState(false);

  return (
    <section className="rounded-xl border border-border bg-card p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-medium text-muted-foreground">Interviews</h2>
        {!adding && (
          <Button variant="outline" className="h-8 px-3 text-xs" onClick={() => setAdding(true)}>
            <CalendarPlus className="mr-1.5 size-3.5" aria-hidden />
            Schedule one
          </Button>
        )}
      </div>

      {adding && (
        <InterviewForm
          applicationId={applicationId}
          onDone={() => setAdding(false)}
          className="mt-4"
        />
      )}

      {isPending ? (
        <Skeleton className="mt-4 h-20 w-full rounded-lg" />
      ) : interviews && interviews.length > 0 ? (
        <ul className="mt-4 space-y-2">
          {interviews.map((interview) => (
            <li key={interview.id}>
              <InterviewRow interview={interview} />
            </li>
          ))}
        </ul>
      ) : (
        !adding && (
          <p className="mt-4 text-sm text-muted-foreground">
            Nothing scheduled. Add a round and it&apos;ll show on your dashboard as it
            approaches.
          </p>
        )
      )}
    </section>
  );
}

function InterviewRow({ interview }: { interview: Interview }) {
  const [editing, setEditing] = useState(false);
  const update = useUpdateInterview(interview.id);
  const remove = useDeleteInterview();
  const [confirming, setConfirming] = useState(false);

  const now = useNow();
  const meta = OUTCOME_META[interview.outcome];
  const when = new Date(interview.scheduled_at);
  // null until hydrated, so the server and the first client render agree.
  const needsOutcome =
    now !== null && when.getTime() < now && interview.outcome === "pending";

  if (editing) {
    return (
      <InterviewForm
        applicationId={interview.application_id}
        initial={interview}
        onDone={() => setEditing(false)}
        className="rounded-lg border border-border p-3"
      />
    );
  }

  return (
    <div
      className={cn(
        "rounded-lg border p-3",
        needsOutcome ? "border-warning/40 bg-warning-subtle" : "border-border",
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-medium">
            {ROUND_LABELS[interview.round]}
            {interview.mode ? (
              <span className="font-normal text-muted-foreground">
                {" · "}
                {MODE_LABELS[interview.mode]}
              </span>
            ) : null}
          </p>
          <p className="mt-0.5 text-sm text-muted-foreground">
            {format(when, "EEE d MMM yyyy, HH:mm")}
            {interview.duration_minutes ? ` · ${interview.duration_minutes} min` : ""}
            {interview.interviewer ? ` · ${interview.interviewer}` : ""}
          </p>
        </div>

        <span
          className="shrink-0 rounded-md px-1.5 py-0.5 text-xs font-medium"
          style={{ background: `var(${meta.token})`, color: "white" }}
        >
          {meta.label}
        </span>
      </div>

      {interview.location && (
        <p className="mt-2 truncate text-sm">
          {/^https?:\/\//.test(interview.location) ? (
            <a
              href={interview.location}
              target="_blank"
              rel="noreferrer noopener"
              className="text-primary hover:underline"
            >
              {interview.location}
            </a>
          ) : (
            <span className="text-muted-foreground">{interview.location}</span>
          )}
        </p>
      )}

      {interview.notes && (
        <p className="mt-2 whitespace-pre-wrap text-sm text-muted-foreground">
          {interview.notes}
        </p>
      )}

      {interview.feedback && (
        <p className="mt-2 rounded-md bg-muted p-2 text-sm whitespace-pre-wrap">
          {interview.feedback}
        </p>
      )}

      {needsOutcome && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="text-xs" style={{ color: "var(--warning-foreground)" }}>
            How did it go?
          </span>
          {(["passed", "failed", "cancelled"] as InterviewOutcome[]).map((outcome) => (
            <Button
              key={outcome}
              variant="outline"
              className="h-7 px-2 text-xs"
              onClick={() =>
                update.mutate(
                  { outcome },
                  {
                    onSuccess: () => toast.success("Outcome recorded"),
                    onError: () => toast.error("Couldn't record the outcome"),
                  },
                )
              }
            >
              {OUTCOME_META[outcome].label}
            </Button>
          ))}
        </div>
      )}

      <div className="mt-3 flex gap-2">
        <Button variant="ghost" className="h-7 px-2 text-xs" onClick={() => setEditing(true)}>
          Edit
        </Button>

        {confirming ? (
          <>
            <Button
              className="h-7 px-2 text-xs"
              style={{ background: "var(--danger)", color: "var(--danger-foreground)" }}
              onClick={() =>
                remove.mutate(interview.id, {
                  onSuccess: () => toast.success("Interview removed"),
                  onError: () => toast.error("Couldn't remove it"),
                })
              }
            >
              Confirm
            </Button>
            <Button
              variant="ghost"
              className="h-7 px-2 text-xs"
              onClick={() => setConfirming(false)}
            >
              Cancel
            </Button>
          </>
        ) : (
          <Button
            variant="ghost"
            className="h-7 px-2 text-xs text-danger"
            onClick={() => setConfirming(true)}
          >
            <Trash2 className="mr-1 size-3" aria-hidden />
            Remove
          </Button>
        )}
      </div>
    </div>
  );
}

function InterviewForm({
  applicationId,
  initial,
  onDone,
  className,
}: {
  applicationId: string;
  initial?: Interview;
  onDone: () => void;
  className?: string;
}) {
  const create = useCreateInterview();
  const update = useUpdateInterview(initial?.id ?? "");

  const [round, setRound] = useState<InterviewRound>(initial?.round ?? "technical");
  const [mode, setMode] = useState<InterviewMode | "">(initial?.mode ?? "");
  const [outcome, setOutcome] = useState<InterviewOutcome>(initial?.outcome ?? "pending");
  const [when, setWhen] = useState(
    initial ? toLocalInputValue(initial.scheduled_at) : defaultWhen(),
  );
  const [duration, setDuration] = useState(initial?.duration_minutes?.toString() ?? "");
  const [location, setLocation] = useState(initial?.location ?? "");
  const [interviewer, setInterviewer] = useState(initial?.interviewer ?? "");
  const [notes, setNotes] = useState(initial?.notes ?? "");
  const [feedback, setFeedback] = useState(initial?.feedback ?? "");

  const pending = create.isPending || update.isPending;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!when) return;

    const payload = {
      round,
      mode: mode || null,
      scheduled_at: fromLocalInputValue(when),
      duration_minutes: duration ? Number(duration) : null,
      location: location.trim() || null,
      interviewer: interviewer.trim() || null,
      notes: notes.trim() || null,
      feedback: feedback.trim() || null,
      outcome,
    };

    const onError = (err: unknown) =>
      toast.error("Couldn't save", {
        description: err instanceof ApiError ? err.message : undefined,
      });

    if (initial) {
      update.mutate(payload, {
        onSuccess: () => {
          toast.success("Interview updated");
          onDone();
        },
        onError,
      });
    } else {
      create.mutate(
        { ...payload, application_id: applicationId },
        {
          onSuccess: () => {
            toast.success("Interview scheduled");
            onDone();
          },
          onError,
        },
      );
    }
  }

  const id = (name: string) => `interview-${initial?.id ?? "new"}-${name}`;

  return (
    <form onSubmit={submit} className={cn("space-y-3", className)}>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Round" htmlFor={id("round")}>
          <ThemedSelect
            id={id("round")}
            aria-label="Round"
            value={round}
            onChange={(v) => setRound(v as InterviewRound)}
            options={ALL_ROUNDS.map((r) => ({ value: r, label: ROUND_LABELS[r] }))}
          />
        </Field>

        <Field label="Format" htmlFor={id("mode")}>
          <ThemedSelect
            id={id("mode")}
            aria-label="Format"
            placeholder="Not specified"
            value={mode}
            onChange={(v) => setMode(v as InterviewMode | "")}
            options={[
              { value: "", label: "Not specified" },
              ...ALL_MODES.map((m) => ({ value: m, label: MODE_LABELS[m] })),
            ]}
          />
        </Field>

        <Field label="When" htmlFor={id("when")}>
          <Input
            id={id("when")}
            type="datetime-local"
            value={when}
            onChange={(e) => setWhen(e.target.value)}
            required
          />
        </Field>

        <Field label="Duration (minutes)" htmlFor={id("duration")}>
          <Input
            id={id("duration")}
            type="number"
            inputMode="numeric"
            placeholder="60"
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
          />
        </Field>

        <Field label="Link or place" htmlFor={id("location")}>
          <Input
            id={id("location")}
            placeholder="https://meet… or an address"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
          />
        </Field>

        <Field label="Interviewer" htmlFor={id("interviewer")}>
          <Input
            id={id("interviewer")}
            placeholder="Name, if you know it"
            value={interviewer}
            onChange={(e) => setInterviewer(e.target.value)}
          />
        </Field>
      </div>

      <Field label="Prep notes" htmlFor={id("notes")}>
        <Textarea
          id={id("notes")}
          rows={2}
          placeholder="What to revise, questions to ask…"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
      </Field>

      {initial && (
        <>
          <Field label="Outcome" htmlFor={id("outcome")}>
            <ThemedSelect
              id={id("outcome")}
              aria-label="Outcome"
              value={outcome}
              onChange={(v) => setOutcome(v as InterviewOutcome)}
              options={ALL_OUTCOMES.map((o) => ({
                value: o,
                label: OUTCOME_META[o].label,
              }))}
            />
          </Field>

          <Field label="How it went" htmlFor={id("feedback")}>
            <Textarea
              id={id("feedback")}
              rows={2}
              placeholder="What they asked, how you felt it went…"
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
            />
          </Field>
        </>
      )}

      <div className="flex gap-2">
        <Button type="submit" className="h-9 px-4" disabled={pending}>
          {pending ? "Saving…" : initial ? "Save changes" : "Schedule"}
        </Button>
        <Button type="button" variant="outline" className="h-9 px-4" onClick={onDone}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

function Field({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
    </div>
  );
}

/** Tomorrow at 10:00 — nearly always closer than "now" for something being booked. */
function defaultWhen(): string {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  d.setHours(10, 0, 0, 0);
  return toLocalInputValue(d.toISOString());
}
