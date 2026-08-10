import { Link } from "@/components/ui/link";

import { LogoWordmark } from "@/components/brand/logo";
import { ThemeToggle } from "@/components/theme/theme-toggle";

/**
 * Two-column shell for the login and register pages.
 *
 * The brand panel is hidden below `lg` rather than stacked — on a phone it
 * would just push the form below the fold.
 */
export function AuthShell({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
  footer: React.ReactNode;
}) {
  return (
    <div className="grid min-h-svh lg:grid-cols-[1.1fr_1fr]">
      {/* Brand panel */}
      <aside className="relative hidden overflow-hidden bg-brand-panel lg:flex lg:flex-col lg:justify-between lg:p-12">
        {/* Soft radial washes: depth without a literal gradient banner. */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-70"
          style={{
            background:
              "radial-gradient(60% 55% at 15% 10%, oklch(0.66 0.21 315 / 0.55), transparent 70%), radial-gradient(50% 50% at 90% 90%, oklch(0.40 0.18 275 / 0.65), transparent 70%)",
          }}
        />

        <Link href="/" className="relative z-10 text-brand-panel-foreground">
          {/* mono: a violet gradient would vanish against the violet panel */}
          <LogoWordmark variant="mono" className="text-lg" />
        </Link>

        <div className="relative z-10 max-w-md">
          <h2 className="text-3xl font-semibold leading-tight text-brand-panel-foreground">
            Every application, resume and interview in one place.
          </h2>
          <p className="mt-4 text-brand-panel-foreground/80">
            Stop tracking your job search across six spreadsheets and a
            half-remembered inbox.
          </p>

          <ul className="mt-8 space-y-3">
            {[
              "Track applications through every stage",
              "Keep resume versions tied to the jobs you used them for",
              "See which sources actually get you interviews",
            ].map((item) => (
              <li
                key={item}
                className="flex items-start gap-3 text-sm text-brand-panel-foreground/90"
              >
                <CheckMark />
                {item}
              </li>
            ))}
          </ul>
        </div>

        <p className="relative z-10 text-xs text-brand-panel-foreground/75">
          Your data stays yours. Resumes are never shared or made public.
        </p>
      </aside>

      {/* Form panel */}
      <main className="relative flex items-center justify-center bg-background px-6 py-12">
        <div className="absolute right-5 top-5">
          <ThemeToggle />
        </div>

        <div className="w-full max-w-sm">
          <Link href="/" className="mb-8 block text-foreground lg:hidden">
            <LogoWordmark className="text-lg" />
          </Link>

          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          <p className="mt-1.5 text-sm text-muted-foreground">{subtitle}</p>

          <div className="mt-8">{children}</div>

          <div className="mt-6 text-center text-sm text-muted-foreground">
            {footer}
          </div>
        </div>
      </main>
    </div>
  );
}

function CheckMark() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 18 18"
      fill="none"
      aria-hidden
      className="mt-0.5 shrink-0"
    >
      <circle cx="9" cy="9" r="9" fill="currentColor" opacity="0.22" />
      <path
        d="m5.5 9.2 2.3 2.3 4.7-5"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
