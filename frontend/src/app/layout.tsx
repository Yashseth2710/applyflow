import type { Metadata } from "next";
import { Fraunces, Geist_Mono, Public_Sans } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

/*
  Two families, with different jobs.

  Display is an old-style serif, and it appears only at page-title size and
  above — never on a 13px section label, where serifs turn to mush. Its job is
  to give the product a voice in the two seconds before anyone reads a word.

  Body is a humanist sans with proper tabular figures, which this app leans on
  hard: every count, date and pipeline number has to align in a column.

  Both are fetched at build time and served from our own origin, so the CSP in
  next.config.ts needs no font-src exception and there is no third-party
  request on first paint.
*/
const display = Fraunces({
  variable: "--font-display",
  subsets: ["latin"],
  // Fraunces carries an optical-size axis: the browser thins the serifs as the
  // type grows. Without it the hero looks like the 14px cut blown up.
  axes: ["opsz"],
  display: "swap",
});

const sans = Public_Sans({
  variable: "--font-sans-ui",
  subsets: ["latin"],
  display: "swap",
});

const mono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "ApplyFlow",
  description:
    "Track job applications, resumes, interviews and reminders in one place.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      // next-themes sets the `dark` class on <html> before hydration, which
      // React would otherwise report as a server/client mismatch.
      suppressHydrationWarning
      className={`${sans.variable} ${display.variable} ${mono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
