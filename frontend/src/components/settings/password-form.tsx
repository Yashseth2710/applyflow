"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { SettingsSection } from "@/components/settings/section";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useChangePassword } from "@/lib/account";
import { ApiError } from "@/lib/api-client";

const schema = z
  .object({
    current_password: z.string().min(1, "Enter your current password"),
    new_password: z.string().min(8, "Use at least 8 characters"),
    confirm: z.string().min(1, "Type the new password again"),
  })
  .refine((v) => v.new_password === v.confirm, {
    message: "These do not match",
    path: ["confirm"],
  });

type Values = z.infer<typeof schema>;

export function PasswordForm() {
  const change = useChangePassword();
  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { current_password: "", new_password: "", confirm: "" },
  });

  async function submit(values: Values) {
    try {
      await change.mutateAsync({
        current_password: values.current_password,
        new_password: values.new_password,
      });
      reset();
      toast.success("Password changed");
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Could not change your password.";
      // Attached to the field it is about rather than thrown at a toast, so
      // the wrong-password case lands where the person is already looking.
      if (err instanceof ApiError && err.status === 403) {
        setError("current_password", { message });
      } else {
        toast.error(message);
      }
    }
  }

  return (
    <SettingsSection
      title="Security"
      description="Changing your password signs nothing else out — this app has one session per browser."
    >
      <form onSubmit={handleSubmit(submit)} className="space-y-4" noValidate>
        {/* Not rendered, but present and filled by a password manager. Without
            it, managers cannot tell which account the new password belongs to
            and often refuse to offer an update. */}
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

        <PasswordField
          label="Current password"
          id="current_password"
          autoComplete="current-password"
          error={errors.current_password?.message}
          {...register("current_password")}
        />
        <PasswordField
          label="New password"
          id="new_password"
          autoComplete="new-password"
          hint="At least 8 characters."
          error={errors.new_password?.message}
          {...register("new_password")}
        />
        <PasswordField
          label="Confirm new password"
          id="confirm"
          autoComplete="new-password"
          error={errors.confirm?.message}
          {...register("confirm")}
        />

        <Button type="submit" variant="outline" className="h-10 px-5" disabled={isSubmitting}>
          {isSubmitting ? "Changing…" : "Change password"}
        </Button>
      </form>
    </SettingsSection>
  );
}

function PasswordField({
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
    <div className="max-w-md space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        type="password"
        aria-invalid={!!error}
        aria-describedby={describedBy}
        {...input}
      />
      {error ? (
        <p id={`${id}-error`} className="text-sm text-danger-ink">
          {error}
        </p>
      ) : hint ? (
        <p id={`${id}-hint`} className="text-xs text-muted-foreground">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
