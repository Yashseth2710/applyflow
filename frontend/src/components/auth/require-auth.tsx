"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/lib/auth-context";

/**
 * Client-side route guard.
 *
 * This is a UX affordance, not a security boundary — every protected endpoint
 * is enforced server-side by `get_current_user`. Bypassing this component
 * shows an empty shell, not anyone's data.
 */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) router.replace("/login");
  }, [isLoading, user, router]);

  // isLoading covers the silent-refresh window. Without it, a signed-in user
  // reloading the page would be bounced to /login before the session restores.
  if (isLoading) {
    return (
      <div className="flex min-h-svh items-center justify-center">
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          <span className="size-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          Loading…
        </div>
      </div>
    );
  }

  if (!user) return null;

  return <>{children}</>;
}
