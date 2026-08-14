"use client";

import { Link } from "@/components/ui/link";

import { LogoWordmark } from "@/components/brand/logo";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { buttonVariants } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";
import { cn } from "@/lib/utils";

/*
  What this page used to be: a pill badge, a centred headline, a centred
  paragraph, two centred buttons, and three identically sized cards each
  holding a coloured square, a heading and two lines of text.

  Every one of those is a stock move, and the card row was the worst of them —
  it described the product three times in the same shape instead of showing it
  once. A job tracker's entire argument is "here is your search, laid out". So
  the page lays one out.
*/

/** The stages shown in the preview, with the real counts a mid-search user has. */
const PREVIEW_STAGES = [
  { label: "Applied", token: "--stage-applied", count: 14 },
  { label: "Assessment", token: "--stage-assessment", count: 5 },
  { label: "Interviewing", token: "--stage-technical", count: 3 },
  { label: "Offer", token: "--stage-offer", count: 1 },
] as const;

export default function Home() {
  const { user, isLoading } = useAuth();

  // No redirect for signed-in visitors. The landing page is a page in its own
  // right, and auto-navigating away from it the moment the session finishes
  // restoring looks like a stray scroll or click threw you into the app.
  // Signed-in users get a link to the dashboard instead, and choose for
  // themselves.
  const signedIn = !isLoading && !!user;

  return (
    <div className="min-h-svh bg-background">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <LogoWordmark />

          <div className="flex items-center gap-1.5">
            <ThemeToggle />
            {/* While isLoading, neither set of buttons renders. Showing "Sign
                in" to someone already signed in, then swapping it a second
                later, is its own kind of wrong. */}
            {isLoading ? (
              <span className="h-9 w-40" aria-hidden />
            ) : signedIn ? (
              <Link href="/dashboard" className={cn(buttonVariants(), "h-9 px-3.5")}>
                Go to dashboard
              </Link>
            ) : (
              <>
                <Link
                  href="/login"
                  className={cn(buttonVariants({ variant: "ghost" }), "h-9 px-3.5")}
                >
                  Sign in
                </Link>
                <Link href="/register" className={cn(buttonVariants(), "h-9 px-3.5")}>
                  Create account
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6">
        {/* Asymmetric, and left-aligned. Centred type is the default that makes
            a page look like a template; it also gives the eye no fixed left
            edge to return to, which is why centred paragraphs read slower. */}
        <section className="grid items-center gap-12 py-16 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)] lg:gap-16 lg:py-24">
          <div>
            <h1 className="display text-[clamp(2.5rem,6vw,3.5rem)] leading-[1.05] tracking-[-0.028em]">
              Where am I in my
              <br className="hidden sm:block" /> job search, and{" "}
              <em className="not-italic text-primary">what’s next?</em>
            </h1>

            <p className="measure mt-6 text-lg leading-relaxed text-muted-foreground">
              ApplyFlow keeps every application, resume version, interview and
              follow-up in one place — so nothing slips while you’re
              applying to thirty companies at once.
            </p>

            <div className="mt-9 flex min-h-11 flex-wrap items-center gap-3">
              {isLoading ? null : signedIn ? (
                <Link
                  href="/dashboard"
                  className={cn(buttonVariants(), "h-11 px-6 text-[0.95rem]")}
                >
                  Open your dashboard
                </Link>
              ) : (
                <>
                  <Link
                    href="/register"
                    className={cn(buttonVariants(), "h-11 px-6 text-[0.95rem]")}
                  >
                    Create your account
                  </Link>
                  <Link
                    href="/login"
                    className={cn(
                      buttonVariants({ variant: "ghost" }),
                      // Same padding as the filled button beside it. With a
                      // smaller value the two labels stop lining up the moment
                      // the pair wraps onto two rows on a phone.
                      "h-11 px-6 text-[0.95rem]",
                    )}
                  >
                    I already have one
                  </Link>
                </>
              )}
            </div>

            <p className="mt-6 text-sm text-muted-foreground">
              Free to use. Your resumes are never shared or made public.
            </p>
          </div>

          <PipelinePreview />
        </section>

        {/* Not three cards. Three claims, at different weights, separated by
            rules — so the eye reads them in order instead of scanning a row and
            registering "features". */}
        <section className="border-t border-border py-16 lg:py-20">
          <div className="grid gap-12 lg:grid-cols-[minmax(0,20rem)_minmax(0,1fr)] lg:gap-16">
            {/* Sticky, because the column is short and the one beside it is
                tall — left as-is it was two thirds empty, and a void that size
                reads as a layout bug rather than as breathing room. Travelling
                with the reader also keeps the question the list is answering
                on screen while they read the answers. */}
            <h2 className="display text-[1.75rem] leading-tight lg:sticky lg:top-16 lg:self-start">
              The parts of a job search that go missing
            </h2>

            <dl className="space-y-10">
              <Claim
                term="Which resume did I send them?"
                detail="Every application links to the exact resume version you used. Upload a new one and the old versions stay, tied to the jobs that got them."
              />
              <Claim
                term="What was I supposed to do this week?"
                detail="Interviews, follow-ups and reminders sit on the dashboard, not in a calendar you forgot to check."
              />
              <Claim
                term="Is any of this actually working?"
                detail="Which sources get you interviews, which roles convert, and where applications go quiet. Numbers you can act on, not a chart for its own sake."
              />
            </dl>
          </div>
        </section>
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-8 text-sm text-muted-foreground">
          <LogoWordmark size={20} className="text-foreground" />
          <p>Built for one job search at a time.</p>
        </div>
      </footer>
    </div>
  );
}

function Claim({ term, detail }: { term: string; detail: string }) {
  return (
    <div className="border-t border-border pt-6 first:border-t-0 first:pt-0">
      <dt className="text-lg font-semibold tracking-tight">{term}</dt>
      <dd className="measure mt-2 leading-relaxed text-muted-foreground">{detail}</dd>
    </div>
  );
}

/**
 * A still of the product, built from the app's own tokens.
 *
 * Deliberately not a screenshot: a PNG goes stale the first time the board
 * changes, ships a few hundred kilobytes, and cannot follow the theme. This is
 * markup, so it is sharp at every density, flips to dark with the rest of the
 * page, and costs nothing.
 */
function PipelinePreview() {
  const max = Math.max(...PREVIEW_STAGES.map((s) => s.count));

  return (
    <div className="relative" aria-hidden>
      {/* There was a blurred violet radial wash behind this panel. It is one
          of the reliable generated-page tells, and it was doing no work the
          shadow was not already doing — a coloured haze does not make an
          object sit in light, it just tints the page. */}

      {/* Shadow, no border: this is the one element on the page that is
          genuinely meant to read as lifted off it. */}
      <div className="overflow-hidden rounded-2xl bg-surface-raised shadow-[var(--shadow-overlay)]">
        {/* Not three grey dots pretending to be a macOS title bar. That is a
            costume, and it makes the preview a picture of a window rather than
            a piece of the product. This is the app's own header instead. */}
        <div className="flex items-center justify-between gap-3 border-b border-border bg-surface px-4 py-3">
          <span className="eyebrow">Your pipeline</span>
          <span className="text-xs text-muted-foreground">23 tracked</span>
        </div>

        <div className="space-y-4 p-5 sm:p-6">
          {PREVIEW_STAGES.map((stage) => (
            <div key={stage.label} className="flex items-center gap-3">
              <span className="w-24 shrink-0 text-xs text-muted-foreground">
                {stage.label}
              </span>
              <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${(stage.count / max) * 100}%`,
                    backgroundColor: `var(${stage.token})`,
                  }}
                />
              </div>
              <span className="tabular w-5 text-right text-sm font-medium">
                {stage.count}
              </span>
            </div>
          ))}

          <div className="mt-5 space-y-2 border-t border-border pt-5">
            <PreviewRow
              role="Senior Frontend Engineer"
              company="Rippling"
              stage="Technical"
              token="--stage-technical"
            />
            <PreviewRow
              role="Product Engineer"
              company="Linear"
              stage="Offer"
              token="--stage-offer"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function PreviewRow({
  role,
  company,
  stage,
  token,
}: {
  role: string;
  company: string;
  stage: string;
  token: string;
}) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-border bg-card px-3 py-2.5">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium">{role}</p>
        <p className="truncate text-xs text-muted-foreground">{company}</p>
      </div>
      <span
        className="shrink-0 rounded-md px-2 py-0.5 text-xs font-medium"
        style={{
          backgroundColor: `color-mix(in oklch, var(${token}), transparent 88%)`,
          color: `var(${token}-ink)`,
        }}
      >
        {stage}
      </span>
    </div>
  );
}
