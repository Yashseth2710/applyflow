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
        const refreshed = await refreshAccessToken();
        if (!refreshed || cancelled) return;

        const me = await api.get<User>("/auth/me");
        if (!cancelled) setUser(me);
      } catch {
        // No valid session. Not an error — this is every logged-out visitor.
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
