"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Link } from "@/components/ui/link";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { AuthShell } from "@/components/auth/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, api } from "@/lib/api-client";
import type { ForgotPasswordPayload } from "@/lib/types";

const schema = z.object({
  email: z.string().min(1, "Email is required").email("Enter a valid email"),
});

type FormValues = z.infer<typeof schema>;

export default function ForgotPasswordPage() {
  const [sentTo, setSentTo] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  async function onSubmit(values: FormValues) {
    setFormError(null);
    try {
      const payload: ForgotPasswordPayload = { email: values.email };
      await api.post("/auth/forgot-password", payload, { skipAuth: true });
      // The server answers the same way whether or not that address has an
      // account, and so does this page. Saying "no account with that email"
      // here would give away exactly what the endpoint refuses to.
      setSentTo(values.email);
    } catch (err) {
      setFormError(
        err instanceof ApiError ? err.message : "Something went wrong. Try again.",
      );
    }
  }

  return (
    <AuthShell
      title={sentTo ? "Check your email" : "Forgot your password?"}
      subtitle={
        sentTo
          ? "If that address has an account, a reset link is on its way."
          : "Enter your email and we'll send you a link to set a new one."
      }
      footer={
        <>
          Remembered it?{" "}
          <Link href="/login" className="font-medium text-primary hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      {sentTo ? (
        <div className="space-y-4">
          <div
            role="status"
            className="rounded-lg border border-success/25 bg-success-subtle px-3.5 py-3 text-sm text-success-ink"
          >
            {/* No number here on purpose: the expiry is a server setting, and
                the email states it. Repeating it in the UI is a copy of a
                constant on the far side of an API, which drifts silently. */}
            We sent a link to <span className="font-medium">{sentTo}</span>. It
            only works once, and it expires shortly.
          </div>
          <p className="text-sm text-muted-foreground">
            Nothing arrived after a few minutes? Check the spam folder, or{" "}
            <button
              type="button"
              onClick={() => setSentTo(null)}
              className="font-medium text-primary hover:underline"
            >
              try a different address
            </button>
            .
          </p>
        </div>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
          {formError && (
            <div
              role="alert"
              className="rounded-lg border border-danger/25 bg-danger-subtle px-3.5 py-3 text-sm text-danger"
            >
              {formError}
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              aria-invalid={!!errors.email}
              aria-describedby={errors.email ? "email-error" : undefined}
              {...register("email")}
            />
            {errors.email && (
              <p id="email-error" className="text-sm text-danger-ink">
                {errors.email.message}
              </p>
            )}
          </div>

          <Button type="submit" className="h-10 w-full" disabled={isSubmitting}>
            {isSubmitting ? "Sending…" : "Send reset link"}
          </Button>
        </form>
      )}
    </AuthShell>
  );
}
