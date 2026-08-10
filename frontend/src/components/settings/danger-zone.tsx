"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { SettingsSection } from "@/components/settings/section";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useDeleteAccount } from "@/lib/account";
import { ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

export function DangerZone() {
  const { user, forgetSession } = useAuth();
  const router = useRouter();
  const remove = useDeleteAccount();

  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function confirm(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    try {
      await remove.mutateAsync({ password });
      // Locally rather than through logout(): the account is gone, so there is
      // nothing left on the server to log out of, and calling it would only
      // produce a 401.
      forgetSession();
      toast.success("Your account has been deleted.");
      // replace, not push: there is no account behind this page any more, so
      // Back should not lead to it. And it has to be /login rather than the
      // home page — dropping the user leaves this page inside RequireAuth,
      // which redirects there anyway, and two navigations racing is not
      // something to leave in.
      router.replace("/login");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Could not delete your account.",
      );
    }
  }

  return (
    <SettingsSection
      tone="danger"
      title="Delete account"
      description="This removes your account and everything in it. There is no undo, and nothing is kept."
    >
      <ul className="mb-5 space-y-1 text-sm text-muted-foreground">
        <li>Every application, with its full stage history</li>
        <li>Every resume and every version of it</li>
        <li>Every interview, note and piece of feedback</li>
        <li>Everything the assistant has written for you</li>
      </ul>

      <AlertDialog
        open={open}
        onOpenChange={(next) => {
          setOpen(next);
          // Never leave a password sitting in state behind a closed dialog.
          if (!next) {
            setPassword("");
            setError(null);
          }
        }}
      >
        <AlertDialogTrigger
          render={<Button variant="destructive" className="h-10 px-5" />}
        >
          Delete my account
        </AlertDialogTrigger>

        <AlertDialogContent>
          <form onSubmit={confirm} noValidate>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete {user?.email}?</AlertDialogTitle>
              <AlertDialogDescription>
                Everything in this account is removed immediately and cannot be
                recovered. Enter your password to confirm.
              </AlertDialogDescription>
            </AlertDialogHeader>

            <div className="mt-4 space-y-2">
              <Label htmlFor="delete_password">Password</Label>
              <Input
                id="delete_password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                aria-invalid={!!error}
                aria-describedby={error ? "delete_password-error" : undefined}
              />
              {error && (
                <p
                  id="delete_password-error"
                  role="alert"
                  className="text-sm text-danger-ink"
                >
                  {error}
                </p>
              )}
            </div>

            <AlertDialogFooter className="mt-6">
              <AlertDialogCancel render={<Button variant="outline" />}>
                Keep my account
              </AlertDialogCancel>
              <Button
                type="submit"
                variant="destructive"
                // Nothing to confirm without it, and an empty submit would
                // spend one of the account's sign-in attempts for nothing.
                disabled={remove.isPending || password.length === 0}
              >
                {remove.isPending ? "Deleting…" : "Delete permanently"}
              </Button>
            </AlertDialogFooter>
          </form>
        </AlertDialogContent>
      </AlertDialog>
    </SettingsSection>
  );
}
