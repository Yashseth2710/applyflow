"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Link } from "@/components/ui/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { AuthShell } from "@/components/auth/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, api } from "@/lib/api-client";
import type { ResetPasswordPayload } from "@/lib/types";

const schema = z
  .object({
    password: z.string().min(8, "Use at least 8 characters"),
    confirm: z.string().min(1, "Type the password again"),
  })
  .refine((v) => v.password === v.confirm, {
    message: "These do not match",
    path: ["confirm"],
  });

type FormValues = z.infer<typeof schema>;

export default function ResetPasswordPage() {
  return (
    // useSearchParams needs one: without it the whole route opts out of static
    // rendering and the build says so.
    <Suspense fallback={<Shell>{null}</Shell>}>
      <ResetPassword />
    </Suspense>
  );
}

function ResetPassword() {
  const token = useSearchParams().get("token");
  const [done, setDone] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  async function onSubmit(values: FormValues) {
    // Unreachable: the form is not rendered without a token. Here so the
    // payload is the generated type rather than a hand-written shape — the
    // compiler cannot see the guard from inside this callback.
    if (!token) return;

    setFormError(null);
    try {
      const payload: ResetPasswordPayload = { token, password: values.password };
      await api.post("/auth/reset-password", payload, { skipAuth: true });
      setDone(true);
    } catch (err) {
      setFormError(
        err instanceof ApiError ? err.message : "Something went wrong. Try again.",
      );
    }
  }

  if (!token) {
    return (
      <Shell title="That link is incomplete">
        <p className="text-sm text-muted-foreground">
          The address is missing its reset code. Some mail clients cut long
          links in half — copying the whole thing from the email usually fixes
          it.
        </p>
        <Button render={<Link href="/forgot-password" />} className="mt-6 h-10 w-full">
          Send a new link
        </Button>
      </Shell>
    );
  }

  if (done) {
    return (
      <Shell title="Password changed" subtitle="You can sign in with it now.">
        <div
          role="status"
          className="rounded-lg border border-success/25 bg-success-subtle px-3.5 py-3 text-sm text-success-ink"
        >
          Your new password is saved. The link you used no longer works.
        </div>
        <Button render={<Link href="/login" />} className="mt-6 h-10 w-full">
          Go to sign in
        </Button>
      </Shell>
    );
  }

  return (
    <Shell>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
        {formError && (
          <div
            role="alert"
            className="rounded-lg border border-danger/25 bg-danger-subtle px-3.5 py-3 text-sm text-danger"
          >
            <p>{formError}</p>
            <Link
              href="/forgot-password"
              className="mt-1 inline-block font-medium underline"
            >
              Send a new link
            </Link>
          </div>
        )}

        {/* Not rendered, but a password manager reads it to know which account
            the new password belongs to. Without it many refuse to offer an
            update at all. */}
        <input
          type="text"
          name="username"
          autoComplete="username"
          className="sr-only"
          tabIndex={-1}
          aria-hidden
          readOnly
          value=""
        />

        <Field
          label="New password"
          id="password"
          hint="At least 8 characters."
          error={errors.password?.message}
          {...register("password")}
        />
        <Field
          label="Confirm new password"
          id="confirm"
          error={errors.confirm?.message}
          {...register("confirm")}
        />

        <Button type="submit" className="h-10 w-full" disabled={isSubmitting}>
          {isSubmitting ? "Saving…" : "Set new password"}
        </Button>
      </form>
    </Shell>
  );
}

function Shell({
  title = "Choose a new password",
  subtitle = "Pick something you have not used here before.",
  children,
}: {
  title?: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <AuthShell
      title={title}
      subtitle={subtitle}
      footer={
        <>
          Know your password?{" "}
          <Link href="/login" className="font-medium text-primary hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      {children}
    </AuthShell>
  );
}

function Field({
  label,
  id,
  hint,
  error,
  ...input
}: {
  label: string;
  id: string;
  hint?: string;
  error?: string;
} & React.ComponentProps<typeof Input>) {
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined;

  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        type="password"
        autoComplete="new-password"
        aria-invalid={!!error}
        aria-describedby={describedBy}
        {...input}
      />
      {error ? (
        <p id={`${id}-error`} className="text-sm text-danger-ink">
          {error}
        </p>
      ) : hint ? (
        <p id={`${id}-hint`} className="text-sm text-muted-foreground">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
