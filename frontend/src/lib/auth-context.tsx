"use client";

import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { api, refreshAccessToken } from "./api-client";
import { clearAccessToken, setAccessToken } from "./auth-token";
import type { AuthResponse, LoginPayload, RegisterPayload, User } from "./types";

interface AuthContextValue {
  user: User | null;
  /** True until the initial session restore finishes. Guards against a flash
   *  of the login page for users who are actually signed in. */
  isLoading: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/** The browser's IANA zone, e.g. "Asia/Kolkata". Captured at registration so
 *  timestamps render in the user's own time without them configuring anything. */
function detectTimezone(): string | undefined {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || undefined;
  } catch {
    return undefined;
  }
}

/**
 * Readable flag the backend sets alongside the httpOnly refresh cookie.
 *
 * Without it there is no way to know a session might exist, so every logged-out
 * visitor triggers a /auth/refresh that 401s — a wasted round-trip before first
 * paint and a red console error on every public page. This is only a hint: the
 * real token is still required, so forging it achieves nothing.
 */
function hasSessionHint(): boolean {
  if (typeof document === "undefined") return false;
  return document.cookie
    .split(";")
    .some((c) => c.trim().startsWith("applyflow_session="));
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  // On mount the access token is gone (it only ever lived in memory), but the
  // httpOnly refresh cookie may still be valid — so try to restore the session.
  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        // Nothing to restore, and no reason to ask the server.
        if (!hasSessionHint()) return;

        const refreshed = await refreshAccessToken();
        if (!refreshed || cancelled) return;

        const me = await api.get<User>("/auth/me");
        if (!cancelled) setUser(me);
      } catch {
        // Expired or revoked session. Not an error worth surfacing.
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const applyAuth = useCallback((res: AuthResponse) => {
    setAccessToken(res.token.access_token);
    setUser(res.user);
  }, []);

  const login = useCallback(
    async (payload: LoginPayload) => {
      const res = await api.post<AuthResponse>("/auth/login", payload, {
        skipAuth: true,
      });
      applyAuth(res);
    },
    [applyAuth],
  );

  const register = useCallback(
    async (payload: RegisterPayload) => {
      const res = await api.post<AuthResponse>(
        "/auth/register",
        { ...payload, timezone: payload.timezone ?? detectTimezone() },
        { skipAuth: true },
      );
      applyAuth(res);
    },
    [applyAuth],
  );

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout", undefined, { skipAuth: true });
    } finally {
      // Clear local state even if the request failed — the user asked to
      // leave, so honour that regardless of the network.
      clearAccessToken();
      // Drop the hint too, so a failed logout request doesn't leave the next
      // page load attempting a refresh that cannot succeed.
      document.cookie = "applyflow_session=; Max-Age=0; path=/";
      setUser(null);
      router.push("/login");
    }
  }, [router]);

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
