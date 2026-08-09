import Link from "next/link";

import { LogoWordmark } from "@/components/brand/logo";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export default function NotFound() {
  return (
    <main className="flex min-h-svh flex-col items-center justify-center px-6 text-center">
      <Link href="/" className="mb-10">
        <LogoWordmark className="text-lg" />
      </Link>

      <p className="text-sm font-medium text-primary">404</p>
      <h1 className="mt-2 text-2xl font-semibold tracking-tight">
        We couldn&apos;t find that page
      </h1>
      <p className="mt-2 max-w-sm text-sm text-muted-foreground">
        The link may be broken, or the page may have moved.
      </p>

      <div className="mt-8 flex flex-wrap justify-center gap-3">
        <Link href="/" className={cn(buttonVariants(), "h-10 px-5")}>
          Back to home
        </Link>
        <Link
          href="/dashboard"
          className={cn(buttonVariants({ variant: "outline" }), "h-10 px-5")}
        >
          Go to dashboard
        </Link>
      </div>
    </main>
  );
}
