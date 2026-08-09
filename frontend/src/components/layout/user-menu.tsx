"use client";

import { useTheme } from "next-themes";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/lib/auth-context";
import { useMounted } from "@/lib/use-mounted";

const THEMES = [
  { value: "light", label: "Light", icon: SunIcon },
  { value: "dark", label: "Dark", icon: MoonIcon },
  { value: "system", label: "System", icon: MonitorIcon },
] as const;

/**
 * Account menu: who you're signed in as, theme, and sign out.
 *
 * Theme is a three-way segmented control rather than a binary toggle, because
 * "system" is a real preference — a plain toggle silently opts the user out of
 * following their OS setting with no way back.
 */
export function UserMenu() {
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const mounted = useMounted();

  const initials =
    `${user?.first_name?.[0] ?? ""}${user?.last_name?.[0] ?? ""}`.toUpperCase() ||
    "?";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label="Account and settings"
        className="flex size-9 items-center justify-center rounded-full bg-accent text-sm font-semibold text-accent-foreground outline-none transition-colors hover:bg-accent/70 focus-visible:ring-3 focus-visible:ring-ring/50"
      >
        {initials}
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="w-64">
        {/* DropdownMenuLabel is a Base UI Menu.GroupLabel and throws unless it
            sits inside a Menu.Group. This is static text, not a group heading,
            so a plain element is the honest markup. */}
        <div className="px-2 py-1.5">
          <p className="text-sm font-medium">
            {user?.first_name} {user?.last_name}
          </p>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {user?.email}
          </p>
        </div>

        <DropdownMenuSeparator />

        <div className="px-2 py-1.5">
          <p className="mb-2 text-xs font-medium text-muted-foreground">Theme</p>
          <div className="grid grid-cols-3 gap-1 rounded-lg bg-muted p-1">
            {THEMES.map(({ value, label, icon: Icon }) => {
              // Before mount `theme` is undefined on the client, so nothing is
              // marked active rather than briefly highlighting the wrong one.
              const active = mounted && theme === value;
              return (
                <button
                  key={value}
                  type="button"
                  onClick={() => setTheme(value)}
                  aria-pressed={active}
                  className={`flex flex-col items-center gap-1 rounded-md px-1.5 py-2 text-[0.7rem] font-medium transition-colors ${
                    active
                      ? "bg-surface-raised text-foreground shadow-sm dark:bg-surface-raised"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <Icon />
                  {label}
                </button>
              );
            })}
          </div>
        </div>

        <DropdownMenuSeparator />

        <DropdownMenuItem
          onClick={() => void logout()}
          className="text-danger focus:bg-danger-subtle focus:text-danger"
        >
          <LogOutIcon />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function SunIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" aria-hidden>
      <circle cx="12" cy="12" r="4.2" />
      <path d="M12 2.5v2M12 19.5v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M2.5 12h2M19.5 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M20.5 14.4A8.5 8.5 0 1 1 9.6 3.5a6.8 6.8 0 0 0 10.9 10.9Z" />
    </svg>
  );
}

function MonitorIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <rect x="2.5" y="3.5" width="19" height="13" rx="2" />
      <path d="M8.5 20.5h7M12 16.5v4" />
    </svg>
  );
}

function LogOutIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M9.5 3.5h-4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h4M16 16.5l4.5-4.5L16 7.5M20 12H9" />
    </svg>
  );
}
