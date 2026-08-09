// Fetch wrapper: attaches the access token, and on a 401 refreshes once and
// replays the request so an expiring token is invisible to the user.
// credentials: "include" throughout, because the refresh token is a cookie.

import { clearAccessToken, getAccessToken, setAccessToken } from "./auth-token";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public body?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface RequestOptions extends RequestInit {
  /** Aborts after this many ms. Generous because Render's free tier
   *  cold-starts and Neon wakes from suspend. */
  timeoutMs?: number;
  /** Internal: prevents a refresh loop. */
  _isRetry?: boolean;
  /** Skip the token/refresh machinery (used by the auth endpoints). */
  skipAuth?: boolean;
  /** Return the Response untouched, for downloads and other non-JSON bodies. */
  rawResponse?: boolean;
}

/** Shared across concurrent 401s so five parallel requests trigger one
 *  refresh, not five. */
let refreshPromise: Promise<boolean> | null = null;

async function refreshAccessToken(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok) {
        clearAccessToken();
        return false;
      }
      const data = (await res.json()) as { access_token: string };
      setAccessToken(data.access_token);
      return true;
    } catch {
      clearAccessToken();
      return false;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

async function request<T>(
  path: string,
  {
    timeoutMs = 30_000,
    _isRetry = false,
    skipAuth = false,
    rawResponse = false,
    ...init
  }: RequestOptions = {},
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const token = skipAuth ? null : getAccessToken();

    // FormData sets its own Content-Type, including the multipart boundary.
    // Setting it by hand produces a body the server cannot parse.
    const isFormData = init.body instanceof FormData;

    const res = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      credentials: "include",
      signal: controller.signal,
      headers: {
        ...(isFormData ? {} : { "Content-Type": "application/json" }),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init.headers,
      },
    });

    if (res.status === 401 && !_isRetry && !skipAuth) {
      const refreshed = await refreshAccessToken();
      if (refreshed) {
        return request<T>(path, {
          ...init,
          timeoutMs,
          skipAuth,
          rawResponse,
          _isRetry: true,
        });
      }
    }

    if (!res.ok) {
      const isJson = res.headers.get("content-type")?.includes("application/json");
      const body = isJson ? await res.json() : await res.text();
      throw new ApiError(res.status, extractDetail(body, res.statusText), body);
    }

    // Checked before reading the body — a raw caller wants it unconsumed.
    if (rawResponse) return res as T;

    if (res.status === 204) return undefined as T;

    const isJson = res.headers.get("content-type")?.includes("application/json");
    return (isJson ? await res.json() : await res.text()) as T;
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError(408, "Request timed out. Please try again.");
    }
    if (err instanceof ApiError) throw err;
    throw new ApiError(0, "Cannot reach the server. Is the backend running?");
  } finally {
    clearTimeout(timer);
  }
}

/** FastAPI returns `detail` as a string, or as an array of objects for
 *  validation errors. Both need to become one readable message. */
function extractDetail(body: unknown, fallback: string): string {
  if (typeof body !== "object" || body === null) return fallback;
  const detail = (body as { detail?: unknown }).detail;

  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    const first = detail[0] as { msg?: string; loc?: unknown[] } | undefined;
    if (first?.msg) {
      const field = Array.isArray(first.loc) ? first.loc.at(-1) : undefined;
      return field ? `${String(field)}: ${first.msg}` : first.msg;
    }
  }

  return fallback;
}

export const api = {
  get: <T>(path: string, opts?: RequestOptions) =>
    request<T>(path, { ...opts, method: "GET" }),

  post: <T>(path: string, data?: unknown, opts?: RequestOptions) =>
    request<T>(path, {
      ...opts,
      method: "POST",
      body: data === undefined ? undefined : JSON.stringify(data),
    }),

  patch: <T>(path: string, data?: unknown, opts?: RequestOptions) =>
    request<T>(path, {
      ...opts,
      method: "PATCH",
      body: data === undefined ? undefined : JSON.stringify(data),
    }),

  delete: <T>(path: string, opts?: RequestOptions) =>
    request<T>(path, { ...opts, method: "DELETE" }),

  // Longer timeout than the default: uploads carry megabytes, and the server
  // parses the file before it answers.
  upload: <T>(path: string, form: FormData, opts?: RequestOptions) =>
    request<T>(path, { timeoutMs: 120_000, ...opts, method: "POST", body: form }),

  /** For file bodies. The caller reads the Response itself. */
  raw: (path: string, opts?: RequestOptions) =>
    request<Response>(path, { timeoutMs: 120_000, ...opts, rawResponse: true }),
};

export { API_BASE_URL, refreshAccessToken };
