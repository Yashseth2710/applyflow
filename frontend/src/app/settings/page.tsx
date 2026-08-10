"use client";

import { AppShell } from "@/components/layout/app-shell";
import { DangerZone } from "@/components/settings/danger-zone";
import { PasswordForm } from "@/components/settings/password-form";
import { ProfileForm } from "@/components/settings/profile-form";
import { useAuth } from "@/lib/auth-context";

export default function SettingsPage() {
  return (
    <AppShell>
      <Settings />
    </AppShell>
  );
}

function Settings() {
  const { user } = useAuth();

  // The forms read their initial values from the user, so they cannot be
  // mounted before it exists — react-hook-form captures defaults once, and an
  // empty first render would leave every field blank.
  if (!user) return null;

  return (
    <main className="mx-auto max-w-3xl px-6 py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold">Settings</h1>
        <p className="mt-1 text-muted-foreground">
          Your details, and what happens to them.
        </p>
      </header>

      <div className="space-y-6">
        {/* Keyed on the user so a fresh sign-in rebuilds the form with the new
            account's values rather than keeping the previous one's. */}
        <ProfileForm key={user.id} />
        <PasswordForm />
        <DangerZone />
      </div>
    </main>
  );
}
