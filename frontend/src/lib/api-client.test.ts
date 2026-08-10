import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, api } from "./api-client";
import { clearAccessToken, getAccessToken, setAccessToken } from "./auth-token";

const BASE = "http://localhost:8000/api/v1";

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function fetchMock() {
  const mock = vi.fn();
  vi.stubGlobal("fetch", mock);
  return mock;
}

/** The path each call was made to, in order. */
function paths(mock: ReturnType<typeof fetchMock>): string[] {
  return mock.mock.calls.map((call) => String(call[0]).replace(BASE, ""));
}

beforeEach(() => {
  clearAccessToken();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("sending a request", () => {
  it("attaches the access token when there is one", async () => {
    const mock = fetchMock();
    mock.mockResolvedValue(json({ ok: true }));
    setAccessToken("token-123");

    await api.get("/applications");

    const headers = mock.mock.calls[0][1].headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer token-123");
  });

  it("sends no Authorization header when signed out", async () => {
    const mock = fetchMock();
    mock.mockResolvedValue(json({ ok: true }));

    await api.get("/health");

    const headers = mock.mock.calls[0][1].headers as Record<string, string>;
    expect(headers.Authorization).toBeUndefined();
  });

  it("leaves FormData to set its own content type", async () => {
    const mock = fetchMock();
    mock.mockResolvedValue(json({ id: "1" }));

    await api.upload("/resumes", new FormData());

    const headers = mock.mock.calls[0][1].headers as Record<string, string>;
    // Setting it by hand drops the multipart boundary and the server cannot
    // parse the body.
    expect(headers["Content-Type"]).toBeUndefined();
  });

  it("returns nothing for 204 rather than trying to parse a body", async () => {
    const mock = fetchMock();
    mock.mockResolvedValue(new Response(null, { status: 204 }));

    await expect(api.delete("/applications/1")).resolves.toBeUndefined();
  });
});

describe("refreshing an expired token", () => {
  it("refreshes once and replays the original request", async () => {
    const mock = fetchMock();
    setAccessToken("stale");

    mock
      .mockResolvedValueOnce(json({ detail: "Not authenticated" }, 401))
      .mockResolvedValueOnce(json({ access_token: "fresh" }))
      .mockResolvedValueOnce(json({ items: [] }));

    const result = await api.get<{ items: unknown[] }>("/applications");

    expect(result).toEqual({ items: [] });
    expect(paths(mock)).toEqual(["/applications", "/auth/refresh", "/applications"]);
    expect(getAccessToken()).toBe("fresh");
  });

  it("gives up after one retry instead of looping", async () => {
    const mock = fetchMock();
    setAccessToken("stale");

    // The replayed request 401s too — a server that keeps rejecting must not
    // send the client around the refresh loop forever.
    mock
      .mockResolvedValueOnce(json({ detail: "Not authenticated" }, 401))
      .mockResolvedValueOnce(json({ access_token: "fresh" }))
      .mockResolvedValueOnce(json({ detail: "Not authenticated" }, 401));

    await expect(api.get("/applications")).rejects.toBeInstanceOf(ApiError);
    expect(paths(mock)).toEqual(["/applications", "/auth/refresh", "/applications"]);
  });

  it("clears the token and surfaces the 401 when the refresh fails", async () => {
    const mock = fetchMock();
    setAccessToken("stale");

    mock
      .mockResolvedValueOnce(json({ detail: "Not authenticated" }, 401))
      .mockResolvedValueOnce(json({ detail: "Expired" }, 401));

    await expect(api.get("/applications")).rejects.toMatchObject({ status: 401 });
    expect(getAccessToken()).toBeNull();
  });

  it("refreshes once for several requests that expire together", async () => {
    const mock = fetchMock();
    setAccessToken("stale");

    // Whether a request succeeds depends on the token it carried, so all three
    // in-flight requests genuinely 401 before any refresh has finished.
    mock.mockImplementation((url: string, init: RequestInit) => {
      if (String(url).endsWith("/auth/refresh")) {
        return Promise.resolve(json({ access_token: "fresh" }));
      }
      const auth = (init.headers as Record<string, string>).Authorization;
      return Promise.resolve(
        auth === "Bearer fresh" ? json({ ok: true }) : json({ detail: "Not authenticated" }, 401),
      );
    });

    await Promise.all([api.get("/applications"), api.get("/resumes"), api.get("/interviews")]);

    const refreshes = paths(mock).filter((p) => p === "/auth/refresh");
    // Three concurrent 401s must not mean three refresh calls.
    expect(refreshes).toHaveLength(1);
  });

  it("does not try to refresh on the auth endpoints themselves", async () => {
    const mock = fetchMock();
    mock.mockResolvedValue(json({ detail: "Incorrect email or password" }, 401));

    await expect(
      api.post("/auth/login", { email: "a@b.com", password: "wrong" }, { skipAuth: true }),
    ).rejects.toMatchObject({ status: 401 });

    // A failed login is an answer, not an expired session.
    expect(paths(mock)).toEqual(["/auth/login"]);
  });
});

describe("turning errors into something readable", () => {
  it("uses FastAPI's string detail as the message", async () => {
    const mock = fetchMock();
    mock.mockResolvedValue(json({ detail: "Application not found" }, 404));

    await expect(api.get("/applications/nope")).rejects.toMatchObject({
      status: 404,
      message: "Application not found",
    });
  });

  it("names the field for a validation error", async () => {
    const mock = fetchMock();
    mock.mockResolvedValue(
      json({ detail: [{ loc: ["body", "email"], msg: "not a valid email" }] }, 422),
    );

    await expect(api.post("/auth/register", {})).rejects.toMatchObject({
      message: "email: not a valid email",
    });
  });

  it("reports an unreachable server rather than a raw network error", async () => {
    const mock = fetchMock();
    mock.mockRejectedValue(new TypeError("Failed to fetch"));

    await expect(api.get("/health")).rejects.toMatchObject({
      status: 0,
      message: "Cannot reach the server. Is the backend running?",
    });
  });

  it("reports a timeout as its own thing", async () => {
    const mock = fetchMock();
    mock.mockRejectedValue(new DOMException("aborted", "AbortError"));

    await expect(api.get("/analytics/summary")).rejects.toMatchObject({ status: 408 });
  });
});
