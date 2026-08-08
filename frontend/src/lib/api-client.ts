/**
 * Typed fetch wrapper for the ApplyFlow API.
 *
 * `credentials: "include"` is set on every request because the refresh token
 * lives in an httpOnly cookie (see docs/architecture.md decision 2). Milestone 2
 * adds the access-token header and the silent-refresh-on-401 retry here.
 */

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
  /** Aborts the request after this many ms. Render's free tier cold-starts,
   *  so this is deliberately generous. */
  timeoutMs?: number;
}

async function request<T>(
  path: string,
  { timeoutMs = 30_000, ...init }: RequestOptions = {},
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      credentials: "include",
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...init.headers,
      },
    });

    const isJson = res.headers
      .get("content-type")
      ?.includes("application/json");
    const body = isJson ? await res.json() : await res.text();

    if (!res.ok) {
      const detail =
        typeof body === "object" && body !== null && "detail" in body
          ? String((body as { detail: unknown }).detail)
          : res.statusText;
      throw new ApiError(res.status, detail, body);
    }

    return body as T;
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError(408, "Request timed out");
    }
    if (err instanceof ApiError) throw err;
    throw new ApiError(0, "Cannot reach the API. Is the backend running?");
  } finally {
    clearTimeout(timer);
  }
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
};

export { API_BASE_URL };
