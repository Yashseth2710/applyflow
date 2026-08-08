import Link from "next/link";

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
      <aside className="relative hidden overflow-hidden bg-primary lg:flex lg:flex-col lg:justify-between lg:p-12">
        {/* Soft radial washes: depth without a literal gradient banner. */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-70"
          style={{
            background:
              "radial-gradient(60% 55% at 15% 10%, oklch(0.72 0.13 178 / 0.55), transparent 70%), radial-gradient(50% 50% at 90% 90%, oklch(0.45 0.12 205 / 0.6), transparent 70%)",
          }}
        />

        <Link
          href="/"
          className="relative z-10 inline-flex items-center gap-2.5 text-primary-foreground"
        >
          <LogoMark />
          <span className="text-lg font-semibold tracking-tight">ApplyFlow</span>
        </Link>

        <div className="relative z-10 max-w-md">
          <h2 className="text-3xl font-semibold leading-tight text-primary-foreground">
            Every application, resume and interview in one place.
          </h2>
          <p className="mt-4 text-primary-foreground/80">
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
                className="flex items-start gap-3 text-sm text-primary-foreground/90"
              >
                <CheckMark />
                {item}
              </li>
            ))}
          </ul>
        </div>

        <p className="relative z-10 text-xs text-primary-foreground/60">
          Your data stays yours. Resumes are never shared or made public.
        </p>
      </aside>

      {/* Form panel */}
      <main className="flex items-center justify-center bg-background px-6 py-12">
        <div className="w-full max-w-sm">
          <Link
            href="/"
            className="mb-8 inline-flex items-center gap-2 text-foreground lg:hidden"
          >
            <span className="text-primary">
              <LogoMark />
            </span>
            <span className="text-lg font-semibold tracking-tight">ApplyFlow</span>
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

function LogoMark() {
  return (
    <svg
      width="26"
      height="26"
      viewBox="0 0 26 26"
      fill="none"
      aria-hidden
      className="shrink-0"
    >
      <rect width="26" height="26" rx="7" fill="currentColor" opacity="0.18" />
      <path
        d="M7.5 16.5 11 13l3 3 5-6.5"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
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
