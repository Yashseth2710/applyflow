"use client";

import { useTheme } from "next-themes";
import Link from "next/link";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { initials } from "@/lib/account";
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

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label="Account and settings"
        className="flex size-9 items-center justify-center overflow-hidden rounded-full bg-accent text-sm font-semibold text-accent-foreground outline-none transition-colors hover:bg-accent/70 focus-visible:ring-3 focus-visible:ring-ring/50"
      >
        {user?.avatar ? (
          // A data URI has nothing for next/image to optimise — the bytes are
          // already inline, already 256px, and already WebP.
          // eslint-disable-next-line @next/next/no-img-element
          <img src={user.avatar} alt="" className="size-full object-cover" />
        ) : (
          initials(user)
        )}
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

        {/* A radio group rather than three toggle buttons. Inside a menu only
            menu items, groups and separators are legal children, so plain
            buttons here are both invalid markup and skipped by the menu's own
            arrow-key navigation — the control is visible but unreachable. */}
        <DropdownMenuRadioGroup
          aria-label="Theme"
          // Before mount `theme` is undefined on the client, so nothing is
          // marked active rather than briefly highlighting the wrong one.
          value={mounted ? (theme ?? "") : ""}
          onValueChange={(next) => setTheme(next as string)}
        >
          <div className="px-2 py-1.5">
            <p className="mb-2 text-xs font-medium text-muted-foreground">Theme</p>
            <div className="grid grid-cols-3 gap-1 rounded-lg bg-muted p-1">
              {THEMES.map(({ value, label, icon: Icon }) => (
                <DropdownMenuRadioItem
                  key={value}
                  value={value}
                  indicator={false}
                  // Picking a theme is something you might do twice in a row to
                  // compare, so the menu stays open.
                  closeOnClick={false}
                  className="flex-col justify-center gap-1 px-1.5 py-2 text-[0.7rem] font-medium text-muted-foreground transition-colors hover:text-foreground data-checked:bg-surface-raised data-checked:text-foreground data-checked:shadow-sm"
                >
                  <Icon />
                  {label}
                </DropdownMenuRadioItem>
              ))}
            </div>
          </div>
        </DropdownMenuRadioGroup>

        <DropdownMenuSeparator />

        {/* Reached from here rather than the main nav: settings is somewhere
            you go occasionally, and a sixth nav item would compete with the
            five you use every day. */}
        <DropdownMenuItem render={<Link href="/settings" />}>
          <SettingsIcon />
          Settings
        </DropdownMenuItem>

        <DropdownMenuItem
          onClick={() => void logout()}
          className="text-danger-ink focus:bg-danger-subtle focus:text-danger-ink"
        >
          <LogOutIcon />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function SettingsIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <circle cx="12" cy="12" r="3.2" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" />
    </svg>
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
