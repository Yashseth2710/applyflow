"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Logo } from "@/components/brand/logo";
import { buttonVariants } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";
import { cn } from "@/lib/utils";

const FEATURES = [
  {
    tone: "stage-applied",
    title: "One record per application",
    body: "Company, job description, resume used, recruiter, interviews and notes — together instead of scattered.",
  },
  {
    tone: "stage-technical",
    title: "A pipeline you can see",
    body: "Move applications through stages on a board. Know what needs attention without rereading your inbox.",
  },
  {
    tone: "stage-offer",
    title: "Know what's working",
    body: "Which sources get you interviews, which roles convert, where applications stall.",
  },
] as const;

export default function Home() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && user) router.replace("/dashboard");
  }, [isLoading, user, router]);

  return (
    <div className="min-h-svh bg-background">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2.5">
            <span className="text-primary">
              <Logo />
            </span>
            <span className="font-semibold tracking-tight">ApplyFlow</span>
          </div>

          <div className="flex items-center gap-2">
            <Link
              href="/login"
              className={cn(buttonVariants({ variant: "ghost" }), "h-9 px-3.5")}
            >
              Sign in
            </Link>
            <Link
              href="/register"
              className={cn(buttonVariants(), "h-9 px-3.5")}
            >
              Get started
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6">
        <section className="py-20 text-center sm:py-28">
          <span className="inline-flex items-center gap-2 rounded-full border border-border bg-accent px-3 py-1 text-xs font-medium text-accent-foreground">
            <span className="size-1.5 rounded-full bg-primary" />
            Job search, organised
          </span>

          <h1 className="mx-auto mt-6 max-w-2xl text-4xl font-semibold tracking-tight sm:text-5xl">
            Where am I in my job search, and what&apos;s next?
          </h1>

          <p className="mx-auto mt-5 max-w-xl text-lg text-muted-foreground">
            ApplyFlow keeps every application, resume version, interview and
            follow-up in one place — so nothing slips while you&apos;re applying
            to thirty companies at once.
          </p>

          <div className="mt-9 flex flex-wrap justify-center gap-3">
            <Link
              href="/register"
              className={cn(buttonVariants(), "h-11 px-6 text-[0.95rem]")}
            >
              Create your account
            </Link>
            <Link
              href="/login"
              className={cn(
                buttonVariants({ variant: "outline" }),
                "h-11 px-6 text-[0.95rem]",
              )}
            >
              I already have one
            </Link>
          </div>
        </section>

        <section className="grid gap-4 pb-24 sm:grid-cols-3">
          {FEATURES.map((f) => (
            <article
              key={f.title}
              className="rounded-xl border border-border bg-card p-6"
            >
              <span
                className="inline-block size-8 rounded-lg"
                style={{ background: `var(--${f.tone})`, opacity: 0.9 }}
              />
              <h2 className="mt-4 font-medium">{f.title}</h2>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                {f.body}
              </p>
            </article>
          ))}
        </section>
      </main>
    </div>
  );
}
