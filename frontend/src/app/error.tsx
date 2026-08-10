"use client";

import { Link } from "@/components/ui/link";
import { useEffect } from "react";

import { LogoWordmark } from "@/components/brand/logo";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * Shown when a page throws.
 *
 * Without this file the user gets Next's own error screen — a grey box reading
 * "Application error: a client-side exception has occurred", with no way back
 * and nothing to do. That is the default the first real production bug would
 * have met.
 *
 * The digest is included on purpose: it is the only handle that connects what
 * the user saw to a line in the server logs, and asking someone to describe a
 * grey box is not a bug report.
 */
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Goes to the browser console in development and to the platform's logs in
    // production. There is no error reporting service wired up yet.
    console.error(error);
  }, [error]);

  return (
    <main className="flex min-h-svh flex-col items-center justify-center px-6 text-center">
      <Link href="/" className="mb-10">
        <LogoWordmark className="text-lg" />
      </Link>

      <p className="text-sm font-medium text-danger-ink">Something broke</p>
      <h1 className="mt-2 text-2xl font-semibold tracking-tight">
        That page didn&apos;t load
      </h1>
      <p className="mt-2 max-w-sm text-sm text-muted-foreground">
        Nothing you did caused this, and nothing you had saved is affected.
        Trying again often works — the most common cause is a request that
        failed while the server was waking up.
      </p>

      <div className="mt-8 flex flex-wrap justify-center gap-3">
        <Button onClick={reset} className="h-10 px-5">
          Try again
        </Button>
        <Link
          href="/dashboard"
          className={cn(buttonVariants({ variant: "outline" }), "h-10 px-5")}
        >
          Go to dashboard
        </Link>
      </div>

      {error.digest && (
        <p className="mt-8 text-xs text-muted-foreground">
          Reference: <span className="font-mono">{error.digest}</span>
        </p>
      )}
    </main>
  );
}
