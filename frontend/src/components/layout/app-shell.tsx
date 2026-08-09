"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { RequireAuth } from "@/components/auth/require-auth";
import { LogoWordmark } from "@/components/brand/logo";
import { UserMenu } from "@/components/layout/user-menu";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/applications", label: "Applications" },
  { href: "/applications/board", label: "Board" },
  { href: "/resumes", label: "Resumes" },
  { href: "/analytics", label: "Analytics" },
] as const;

/** Chrome shared by every signed-in page: header, nav, auth guard. */
export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <RequireAuth>
      <div className="min-h-svh bg-background">
        <header className="sticky top-0 z-30 border-b border-border bg-surface/85 backdrop-blur">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3">
            <Link href="/dashboard" className="shrink-0">
              <LogoWordmark />
            </Link>

            <nav className="flex items-center gap-1">
              {NAV.map((item) => {
                // The board lives under /applications, so an exact match is
                // needed or both tabs highlight at once.
                const active =
                  item.href === "/applications"
                    ? pathname === "/applications"
                    : pathname.startsWith(item.href);

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                      active
                        ? "bg-accent text-accent-foreground"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground",
                    )}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </nav>

            <UserMenu />
          </div>
        </header>

        {children}
      </div>
    </RequireAuth>
  );
}
