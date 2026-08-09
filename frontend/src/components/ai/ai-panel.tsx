"use client";

import { formatDistanceToNow } from "date-fns";
import { Copy, RefreshCw, Sparkles } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAIOutputs, useAIStatus, useGenerate } from "@/lib/ai";
import { ApiError } from "@/lib/api-client";
import type {
  AIOutput,
  AITask,
  InterviewPrep,
  InterviewQuestion,
  JDAnalysis,
  ResumeMatch,
} from "@/lib/types";
import { cn } from "@/lib/utils";

const TASKS: { task: AITask; label: string; blurb: string }[] = [
  {
    task: "jd_analysis",
    label: "Analyse the posting",
    blurb: "Pull out what they actually want",
  },
  {
    task: "resume_match",
    label: "Match my resume",
    blurb: "Where you fit, and where you don't",
  },
  {
    task: "interview_questions",
    label: "Interview prep",
    blurb: "Questions worth rehearsing",
  },
  { task: "cover_letter", label: "Cover letter", blurb: "A draft to edit, not to send" },
];

export function AIPanel({ applicationId }: { applicationId: string }) {
  const { data: status } = useAIStatus();
  const { data, isPending } = useAIOutputs(applicationId);
  const generate = useGenerate(applicationId);
  const [active, setActive] = useState<AITask>("jd_analysis");

  const outputs = new Map((data?.items ?? []).map((o) => [o.task, o]));
  const current = outputs.get(active);
  const running = generate.isPending && generate.variables?.task === active;

  function run(task: AITask, force = false) {
    generate.mutate(
      { task, force },
      {
        onError: (err) => {
          const message =
            err instanceof ApiError ? err.message : "Something went wrong. Try again.";
          // 422 means the application is missing an input, which is a normal
          // state rather than a failure worth shouting about.
          const soft = err instanceof ApiError && err.status === 422;
          if (soft) toast.warning(message);
          else toast.error("Couldn't generate", { description: message });
        },
      },
    );
  }

  return (
    <section className="rounded-xl border border-border bg-card p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <Sparkles className="size-4" style={{ color: "var(--primary)" }} aria-hidden />
          Assistant
        </h2>
        {status && !status.enabled && (
          <span className="text-xs text-muted-foreground">{status.detail}</span>
        )}
      </div>

      <div className="mt-4 flex flex-wrap gap-1.5">
        {TASKS.map((item) => {
          const has = outputs.has(item.task);
          return (
            <button
              key={item.task}
              onClick={() => setActive(item.task)}
              className={cn(
                "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                active === item.task
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              {item.label}
              {has && (
                <>
                  <span
                    className="ml-1.5 inline-block size-1.5 rounded-full align-middle"
                    style={{ background: "var(--success)" }}
                    aria-hidden
                  />
                  {/* The dot is decorative; this is what a screen reader reads. */}
                  <span className="sr-only">, already generated</span>
                </>
              )}
            </button>
          );
        })}
      </div>

      <div className="mt-4">
        {isPending ? (
          <Skeleton className="h-32 w-full rounded-lg" />
        ) : running ? (
          <Running />
        ) : current ? (
          <Result
            output={current}
            onRegenerate={() => run(active, true)}
            disabled={!status?.enabled}
          />
        ) : (
          <Empty
            blurb={TASKS.find((t) => t.task === active)?.blurb ?? ""}
            onRun={() => run(active)}
            disabled={!status?.enabled}
          />
        )}
      </div>
    </section>
  );
}

function Running() {
  return (
    <div className="rounded-lg border border-border bg-surface p-6 text-center">
      <div className="mx-auto size-6 animate-spin rounded-full border-2 border-border border-t-primary" />
      <p className="mt-3 text-sm font-medium">Thinking…</p>
      <p className="mt-1 text-xs text-muted-foreground">
        Usually a few seconds. The answer is saved, so you only wait once.
      </p>
    </div>
  );
}

function Empty({
  blurb,
  onRun,
  disabled,
}: {
  blurb: string;
  onRun: () => void;
  disabled?: boolean;
}) {
  return (
    <div className="rounded-lg border border-dashed border-border bg-surface p-6 text-center">
      <p className="text-sm text-muted-foreground">{blurb}</p>
      <Button className="mt-4 h-9 px-4" onClick={onRun} disabled={disabled}>
        <Sparkles className="mr-1.5 size-4" aria-hidden />
        Generate
      </Button>
    </div>
  );
}

function Result({
  output,
  onRegenerate,
  disabled,
}: {
  output: AIOutput;
  onRegenerate: () => void;
  disabled?: boolean;
}) {
  return (
    <div>
      {/* Not --warning-foreground: that pairs with the solid --warning
          background, and on the subtle one it renders dark on dark. */}
      {output.stale && (
        <p className="mb-3 rounded-lg border border-warning/35 bg-warning-subtle px-3 py-2 text-xs text-foreground">
          This was written before you changed the job description or resume, so it
          describes the older text. Regenerate to bring it up to date.
        </p>
      )}

      {output.analysis && <Analysis data={output.analysis} />}
      {output.match && <Match data={output.match} />}
      {output.prep && <Prep data={output.prep} />}
      {output.task === "cover_letter" && <Letter text={output.text ?? ""} />}

      <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-border pt-3">
        <Button
          variant="outline"
          className="h-8 px-3 text-xs"
          onClick={onRegenerate}
          disabled={disabled}
        >
          <RefreshCw className="mr-1.5 size-3.5" aria-hidden />
          Regenerate
        </Button>
        <span className="text-xs text-muted-foreground">
          {output.model} ·{" "}
          {formatDistanceToNow(new Date(output.generated_at), { addSuffix: true })}
        </span>
      </div>
    </div>
  );
}

function Chips({ items, tone }: { items: string[]; tone?: string }) {
  if (items.length === 0) return <p className="text-sm text-muted-foreground">—</p>;
  return (
    <ul className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <li
          key={item}
          className="rounded-md border px-2 py-0.5 text-xs"
          style={
            tone
              ? { borderColor: `var(${tone})`, color: `var(${tone})` }
              : { borderColor: "var(--border)", color: "var(--muted-foreground)" }
          }
        >
          {item}
        </li>
      ))}
    </ul>
  );
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="mb-1.5 text-xs font-medium text-muted-foreground">{title}</h3>
      {children}
    </div>
  );
}

function Bullets({ items }: { items: string[] }) {
  if (items.length === 0) return <p className="text-sm text-muted-foreground">—</p>;
  return (
    <ul className="space-y-1 text-sm">
      {items.map((item) => (
        <li key={item} className="flex gap-2">
          <span className="text-muted-foreground">•</span>
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

function Analysis({ data }: { data: JDAnalysis }) {
  return (
    <div className="space-y-4">
      <p className="text-sm leading-relaxed">{data.summary}</p>
      <Block title="Seniority">
        <p className="text-sm capitalize">{data.seniority}</p>
      </Block>
      <Block title="Must have">
        <Chips items={data.must_have_skills} tone="--primary" />
      </Block>
      <Block title="Nice to have">
        <Chips items={data.nice_to_have_skills} />
      </Block>
      <Block title="What you'd be doing">
        <Bullets items={data.responsibilities} />
      </Block>
      {data.watch_outs.length > 0 && (
        <Block title="Worth noticing">
          <Bullets items={data.watch_outs} />
        </Block>
      )}
    </div>
  );
}

function Match({ data }: { data: ResumeMatch }) {
  // Bands, not a gradient: a score is a rough signal and shouldn't imply
  // more precision than the model has.
  const tone =
    data.score >= 70 ? "--success" : data.score >= 45 ? "--warning" : "--stage-rejected";

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <div
          className="flex size-16 shrink-0 items-center justify-center rounded-full border-4 text-lg font-semibold"
          style={{ borderColor: `var(${tone})`, color: `var(${tone})` }}
        >
          {data.score}
        </div>
        <p className="text-sm leading-relaxed">{data.verdict}</p>
      </div>

      <Block title="You have">
        <Chips items={data.matched_skills} tone="--success" />
      </Block>
      <Block title="They want, you haven't shown">
        <Chips items={data.missing_skills} tone="--warning" />
      </Block>
      <Block title="Strengths">
        <Bullets items={data.strengths} />
      </Block>
      <Block title="Worth changing">
        <Bullets items={data.suggestions} />
      </Block>
    </div>
  );
}

function Prep({ data }: { data: InterviewPrep }) {
  return (
    <div className="space-y-4">
      <ol className="space-y-3">
        {data.questions.map((q: InterviewQuestion, index: number) => (
          <li key={`${q.question}-${index}`} className="rounded-lg border border-border p-3">
            <p className="text-sm font-medium">{q.question}</p>
            <p className="mt-1 text-xs text-muted-foreground capitalize">{q.category}</p>
            {q.hint && <p className="mt-2 text-sm text-muted-foreground">{q.hint}</p>}
          </li>
        ))}
      </ol>

      {data.questions_to_ask.length > 0 && (
        <Block title="Ask them">
          <Bullets items={data.questions_to_ask} />
        </Block>
      )}
    </div>
  );
}

function Letter({ text }: { text: string }) {
  const [draft, setDraft] = useState(text);

  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground">
        A starting point, not a finished letter. Edit it before you send it — the
        specifics are what make it yours.
      </p>

      <textarea
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        rows={14}
        className="w-full rounded-lg border border-border bg-surface-raised p-3 text-sm leading-relaxed"
        aria-label="Cover letter draft"
      />

      <Button
        variant="outline"
        className="h-8 px-3 text-xs"
        onClick={() => {
          void navigator.clipboard.writeText(draft);
          toast.success("Copied");
        }}
      >
        <Copy className="mr-1.5 size-3.5" aria-hidden />
        Copy
      </Button>
    </div>
  );
}
