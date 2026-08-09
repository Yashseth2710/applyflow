"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ThemedSelect } from "@/components/ui/themed-select";
import { ApiError } from "@/lib/api-client";
import { ALL_STATUSES, STATUS_META } from "@/lib/application-status";
import { useResumes } from "@/lib/resumes";
import type { ApplicationDetail, ApplicationStatus } from "@/lib/types";

// Mirrors the backend rules so mistakes surface before a round trip. The
// backend re-validates regardless — this is convenience, not enforcement.
const schema = z
  .object({
    company_name: z.string().trim().min(1, "Company is required").max(200),
    job_title: z.string().trim().min(1, "Job title is required").max(200),
    status: z.enum(ALL_STATUSES as [ApplicationStatus, ...ApplicationStatus[]]),
    location: z.string().max(200).optional(),
    work_mode: z.enum(["", "onsite", "hybrid", "remote"]).optional(),
    employment_type: z
      .enum(["", "full_time", "part_time", "contract", "internship"])
      .optional(),
    source: z.string().max(100).optional(),
    resume_id: z.string().optional(),
    job_url: z.string().max(2000).optional(),
    salary_min: z.string().optional(),
    salary_max: z.string().optional(),
    job_description: z.string().optional(),
  })
  .refine(
    (v) => {
      const min = v.salary_min ? Number(v.salary_min) : null;
      const max = v.salary_max ? Number(v.salary_max) : null;
      return min === null || max === null || min <= max;
    },
    { message: "Minimum cannot exceed maximum", path: ["salary_max"] },
  );

export type ApplicationFormValues = z.infer<typeof schema>;

/** Empty numeric inputs arrive as ""; the API wants null, not 0. */
function toNumberOrNull(value: string | undefined): number | null {
  if (!value || !value.trim()) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function toStringOrNull(value: string | undefined): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed : null;
}

export function ApplicationForm({
  initial,
  submitLabel,
  onSubmit,
}: {
  initial?: ApplicationDetail;
  submitLabel: string;
  onSubmit: (payload: Record<string, unknown>) => Promise<void>;
}) {
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);
  const { data: resumes } = useResumes();

  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ApplicationFormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      company_name: initial?.company_name ?? "",
      job_title: initial?.job_title ?? "",
      status: initial?.status ?? "wishlist",
      location: initial?.location ?? "",
      work_mode: initial?.work_mode ?? "",
      employment_type: initial?.employment_type ?? "",
      source: initial?.source ?? "",
      resume_id: initial?.resume_id ?? "",
      job_url: initial?.job_url ?? "",
      salary_min: initial?.salary_min?.toString() ?? "",
      salary_max: initial?.salary_max?.toString() ?? "",
      job_description: initial?.job_description ?? "",
    },
  });

  async function submit(values: ApplicationFormValues) {
    setFormError(null);
    try {
      await onSubmit({
        company_name: values.company_name.trim(),
        job_title: values.job_title.trim(),
        status: values.status,
        location: toStringOrNull(values.location),
        work_mode: values.work_mode || null,
        employment_type: values.employment_type || null,
        source: toStringOrNull(values.source),
        resume_id: values.resume_id || null,
        job_url: toStringOrNull(values.job_url),
        salary_min: toNumberOrNull(values.salary_min),
        salary_max: toNumberOrNull(values.salary_max),
        job_description: toStringOrNull(values.job_description),
      });
    } catch (err) {
      setFormError(
        err instanceof ApiError ? err.message : "Something went wrong. Try again.",
      );
    }
  }

  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-8" noValidate>
      {formError && (
        <div
          role="alert"
          className="rounded-lg border border-danger/25 bg-danger-subtle px-3.5 py-3 text-sm text-danger"
        >
          {formError}
        </div>
      )}

      <section className="space-y-4">
        <h2 className="text-sm font-medium text-muted-foreground">The role</h2>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field
            label="Company"
            htmlFor="company_name"
            error={errors.company_name?.message}
            required
          >
            <Input
              id="company_name"
              autoFocus
              placeholder="Acme Corp"
              aria-invalid={!!errors.company_name}
              {...register("company_name")}
            />
          </Field>

          <Field
            label="Job title"
            htmlFor="job_title"
            error={errors.job_title?.message}
            required
          >
            <Input
              id="job_title"
              placeholder="Backend Engineer"
              aria-invalid={!!errors.job_title}
              {...register("job_title")}
            />
          </Field>

          <Field label="Stage" htmlFor="status">
            <Controller
              control={control}
              name="status"
              render={({ field }) => (
                <ThemedSelect
                  id="status"
                  aria-label="Stage"
                  value={field.value}
                  onChange={(v) => field.onChange(v as ApplicationStatus)}
                  options={ALL_STATUSES.map((s) => ({
                    value: s,
                    label: STATUS_META[s].label,
                  }))}
                />
              )}
            />
          </Field>

          <Field label="Location" htmlFor="location">
            <Input id="location" placeholder="Bengaluru" {...register("location")} />
          </Field>

          <Field label="Work mode" htmlFor="work_mode">
            <Controller
              control={control}
              name="work_mode"
              render={({ field }) => (
                <ThemedSelect
                  id="work_mode"
                  aria-label="Work mode"
                  // Base UI doesn't match an empty string to an option, so the
                  // placeholder is what actually renders when nothing is set.
                  placeholder="Not specified"
                  value={field.value ?? ""}
                  onChange={field.onChange}
                  options={[
                    { value: "", label: "Not specified" },
                    { value: "onsite", label: "On-site" },
                    { value: "hybrid", label: "Hybrid" },
                    { value: "remote", label: "Remote" },
                  ]}
                />
              )}
            />
          </Field>

          <Field label="Employment type" htmlFor="employment_type">
            <Controller
              control={control}
              name="employment_type"
              render={({ field }) => (
                <ThemedSelect
                  id="employment_type"
                  aria-label="Employment type"
                  placeholder="Not specified"
                  value={field.value ?? ""}
                  onChange={field.onChange}
                  options={[
                    { value: "", label: "Not specified" },
                    { value: "full_time", label: "Full time" },
                    { value: "part_time", label: "Part time" },
                    { value: "contract", label: "Contract" },
                    { value: "internship", label: "Internship" },
                  ]}
                />
              )}
            />
          </Field>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-sm font-medium text-muted-foreground">
          Where and how much
        </h2>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field
            label="Source"
            htmlFor="source"
            hint="LinkedIn, referral, careers page — drives your analytics later"
          >
            <Input id="source" placeholder="LinkedIn" {...register("source")} />
          </Field>

          <Field label="Job posting URL" htmlFor="job_url">
            <Input id="job_url" placeholder="https://…" {...register("job_url")} />
          </Field>

          <Field
            label="Resume used"
            htmlFor="resume_id"
            hint={
              resumes && resumes.length === 0
                ? "Upload one on the Resumes page to link it here"
                : "Which version you sent"
            }
          >
            <Controller
              control={control}
              name="resume_id"
              render={({ field }) => (
                <ThemedSelect
                  id="resume_id"
                  aria-label="Resume used"
                  placeholder="None"
                  value={field.value ?? ""}
                  onChange={field.onChange}
                  options={[
                    { value: "", label: "None" },
                    ...(resumes ?? []).map((r) => ({
                      value: r.id,
                      label: r.version > 1 ? `${r.title} (v${r.version})` : r.title,
                    })),
                  ]}
                />
              )}
            />
          </Field>

          <Field label="Salary from" htmlFor="salary_min">
            <Input
              id="salary_min"
              type="number"
              inputMode="numeric"
              placeholder="1200000"
              {...register("salary_min")}
            />
          </Field>

          <Field
            label="Salary to"
            htmlFor="salary_max"
            error={errors.salary_max?.message}
          >
            <Input
              id="salary_max"
              type="number"
              inputMode="numeric"
              placeholder="1800000"
              aria-invalid={!!errors.salary_max}
              {...register("salary_max")}
            />
          </Field>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-sm font-medium text-muted-foreground">
          Job description
        </h2>
        <Field
          label="Paste the description"
          htmlFor="job_description"
          hint="Kept for the job-description analyser"
        >
          <Textarea
            id="job_description"
            rows={8}
            placeholder="Paste the full job description here…"
            {...register("job_description")}
          />
        </Field>
      </section>

      <div className="flex flex-wrap gap-3 border-t border-border pt-6">
        <Button type="submit" className="h-10 px-5" disabled={isSubmitting}>
          {isSubmitting ? "Saving…" : submitLabel}
        </Button>
        <Button
          type="button"
          variant="outline"
          className="h-10 px-5"
          onClick={() => router.back()}
          disabled={isSubmitting}
        >
          Cancel
        </Button>
      </div>
    </form>
  );
}

/**
 * `htmlFor` is required, not optional. A label with no association is invisible
 * to screen readers and doesn't focus its input when clicked — and it is very
 * easy to forget, so the type makes it impossible.
 */
function Field({
  label,
  htmlFor,
  error,
  hint,
  required,
  children,
}: {
  label: string;
  htmlFor: string;
  error?: string;
  hint?: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={htmlFor}>
        {label}
        {required && (
          <span className="ml-0.5 text-danger" aria-hidden>
            *
          </span>
        )}
      </Label>
      {children}
      {error ? (
        <p id={`${htmlFor}-error`} className="text-sm text-danger">
          {error}
        </p>
      ) : hint ? (
        <p id={`${htmlFor}-hint`} className="text-xs text-muted-foreground">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
