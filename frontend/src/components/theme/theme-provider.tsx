"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";

/**
 * Wraps next-themes.
 *
 * `attribute="class"` toggles `.dark` on <html>, which is what the
 * `@custom-variant dark (&:is(.dark *))` rule in globals.css keys off.
 *
 * next-themes injects a blocking inline script that sets the class before
 * first paint. Without it, a dark-mode user gets a white flash on every page
 * load while React hydrates.
 */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      // Transitions on colour tokens make theme switching look like a smear.
      disableTransitionOnChange
    >
      {children}
    </NextThemesProvider>
  );
}
