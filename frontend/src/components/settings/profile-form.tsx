"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { cloneElement } from "react";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { AvatarField } from "@/components/settings/avatar-field";
import { SettingsSection } from "@/components/settings/section";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ThemedSelect } from "@/components/ui/themed-select";
import { timezones, useUpdateProfile } from "@/lib/account";
import { ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { CareerLevel, ProfileUpdate } from "@/lib/types";

const CAREER_LEVELS: { value: CareerLevel; label: string }[] = [
  { value: "student", label: "Student" },
  { value: "entry", label: "Entry level" },
  { value: "mid", label: "Mid level" },
  { value: "senior", label: "Senior" },
  { value: "lead", label: "Lead" },
];

// Mirrors the backend rules so mistakes surface before a round trip. The
// backend re-validates regardless — this is convenience, not enforcement.
const schema = z.object({
  first_name: z.string().trim().min(1, "First name is required").max(100),
  last_name: z.string().trim().min(1, "Last name is required").max(100),
  summary: z.string().max(2000, "Keep this under 2,000 characters").optional(),
  career_level: z.string().optional(),
  years_experience: z.string().optional(),
  location: z.string().max(200).optional(),
  phone: z.string().max(30).optional(),
  linkedin_url: z.string().max(2000).optional(),
  github_url: z.string().max(2000).optional(),
  portfolio_url: z.string().max(2000).optional(),
  timezone: z.string().min(1),
});

type Values = z.infer<typeof schema>;

/** Empty inputs arrive as ""; the API wants null so "no value" has one
 *  representation rather than two. */
function orNull(value: string | undefined): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed : null;
}

export function ProfileForm() {
  const { user, applyUser } = useAuth();
  const update = useUpdateProfile();
  const zones = timezones();

  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isDirty, isSubmitting },
    reset,
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      first_name: user?.first_name ?? "",
      last_name: user?.last_name ?? "",
      summary: user?.profile?.summary ?? "",
      career_level: user?.profile?.career_level ?? "",
      years_experience: user?.profile?.years_experience?.toString() ?? "",
      location: user?.profile?.location ?? "",
      phone: user?.profile?.phone ?? "",
      linkedin_url: user?.profile?.linkedin_url ?? "",
      github_url: user?.profile?.github_url ?? "",
      portfolio_url: user?.profile?.portfolio_url ?? "",
      timezone: user?.profile?.timezone ?? "",
    },
  });

  async function submit(values: Values) {
    const payload: ProfileUpdate = {
      first_name: values.first_name.trim(),
      last_name: values.last_name.trim(),
      summary: orNull(values.summary),
      career_level: (values.career_level || null) as CareerLevel | null,
      years_experience: values.years_experience
        ? Number(values.years_experience)
        : null,
      location: orNull(values.location),
      phone: orNull(values.phone),
      linkedin_url: orNull(values.linkedin_url),
      github_url: orNull(values.github_url),
      portfolio_url: orNull(values.portfolio_url),
      timezone: values.timezone,
    };

    try {
      const updated = await update.mutateAsync(payload);
      applyUser(updated);
      // Reset to what was saved, so the form stops reporting itself as dirty
      // and the "unsaved changes" state is honest.
      reset(values);
      toast.success("Settings saved");
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.message : "Could not save. Try again.",
      );
    }
  }

  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-6" noValidate>
      <SettingsSection
        title="Profile"
        description="How you appear in the app, and what the assistant knows about you."
      >
        <div className="space-y-6">
          <AvatarField />

          <div className="grid gap-4 sm:grid-cols-2">
            <Field
              label="First name"
              htmlFor="first_name"
              error={errors.first_name?.message}
            >
              <Input
                id="first_name"
                aria-invalid={!!errors.first_name}
                {...register("first_name")}
              />
            </Field>
            <Field
              label="Last name"
              htmlFor="last_name"
              error={errors.last_name?.message}
            >
              <Input
                id="last_name"
                aria-invalid={!!errors.last_name}
                {...register("last_name")}
              />
            </Field>
          </div>

          <Field
            label="Email"
            htmlFor="email"
            hint="Changing this needs a verification email, which the app cannot send yet."
          >
            <Input id="email" value={user?.email ?? ""} readOnly disabled />
          </Field>

          <Field
            label="Summary"
            htmlFor="summary"
            hint="A short description of what you do. The assistant reads this when tailoring cover letters."
            error={errors.summary?.message}
          >
            <Textarea
              id="summary"
              rows={4}
              placeholder="Backend engineer with four years on Python and Postgres…"
              aria-invalid={!!errors.summary}
              {...register("summary")}
            />
          </Field>
        </div>
      </SettingsSection>

      <SettingsSection
        title="Career"
        description="Context for the assistant, and for your own reference."
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Career level" htmlFor="career_level">
            <Controller
              control={control}
              name="career_level"
              render={({ field }) => (
                <ThemedSelect
                  id="career_level"
                  aria-label="Career level"
                  // Base UI does not match an empty string to an option, so the
                  // placeholder is what renders when nothing is set.
                  placeholder="Not specified"
                  value={field.value ?? ""}
                  onChange={field.onChange}
                  options={[
                    { value: "", label: "Not specified" },
                    ...CAREER_LEVELS.map((c) => ({ value: c.value, label: c.label })),
                  ]}
                />
              )}
            />
          </Field>

          <Field label="Years of experience" htmlFor="years_experience">
            <Input
              id="years_experience"
              type="number"
              inputMode="numeric"
              min={0}
              max={70}
              placeholder="4"
              {...register("years_experience")}
            />
          </Field>

          <Field label="Location" htmlFor="location">
            <Input id="location" placeholder="Bengaluru" {...register("location")} />
          </Field>

          <Field label="Phone" htmlFor="phone">
            <Input
              id="phone"
              type="tel"
              placeholder="+91 98765 43210"
              {...register("phone")}
            />
          </Field>
        </div>
      </SettingsSection>

      <SettingsSection title="Links" description="Where else your work lives.">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="LinkedIn" htmlFor="linkedin_url">
            <Input
              id="linkedin_url"
              placeholder="https://linkedin.com/in/…"
              {...register("linkedin_url")}
            />
          </Field>
          <Field label="GitHub" htmlFor="github_url">
            <Input
              id="github_url"
              placeholder="https://github.com/…"
              {...register("github_url")}
            />
          </Field>
          <Field label="Portfolio" htmlFor="portfolio_url">
            <Input
              id="portfolio_url"
              placeholder="https://…"
              {...register("portfolio_url")}
            />
          </Field>
        </div>
      </SettingsSection>

      <SettingsSection
        title="Preferences"
        description="Theme lives in the account menu. Everything else is here."
      >
        <Field
          label="Timezone"
          htmlFor="timezone"
          hint="Every date in the app is shown in this zone."
        >
          <Controller
            control={control}
            name="timezone"
            render={({ field }) => (
              <ThemedSelect
                id="timezone"
                aria-label="Timezone"
                value={field.value ?? ""}
                onChange={field.onChange}
                options={zones.map((z) => ({
                  value: z,
                  label: z.replace(/_/g, " "),
                }))}
              />
            )}
          />
        </Field>
      </SettingsSection>

      {/* Sticky, because this form is longer than a screen and a save button
          at the bottom of it is a save button nobody finds. */}
      <div className="sticky bottom-4 flex items-center gap-3 rounded-xl border border-border bg-surface-raised/95 px-4 py-3 shadow-sm backdrop-blur">
        <Button type="submit" className="h-10 px-5" disabled={isSubmitting || !isDirty}>
          {isSubmitting ? "Saving…" : "Save changes"}
        </Button>
        <p aria-live="polite" className="text-sm text-muted-foreground">
          {isDirty ? "You have unsaved changes." : "Everything is saved."}
        </p>
      </div>
    </form>
  );
}

/**
 * `htmlFor` is required, and the hint or error is wired to the control with
 * `aria-describedby` — `aria-invalid` on its own announces "invalid" and never
 * says why.
 */
function Field({
  label,
  htmlFor,
  error,
  hint,
  children,
}: {
  label: string;
  htmlFor: string;
  error?: string;
  hint?: string;
  children: React.ReactElement<{ "aria-describedby"?: string }>;
}) {
  const describedBy = error ? `${htmlFor}-error` : hint ? `${htmlFor}-hint` : undefined;
  const control = describedBy
    ? cloneElement(children, { "aria-describedby": describedBy })
    : children;

  return (
    <div className="space-y-2">
      <Label htmlFor={htmlFor}>{label}</Label>
      {control}
      {error ? (
        <p id={`${htmlFor}-error`} className="text-sm text-danger-ink">
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

