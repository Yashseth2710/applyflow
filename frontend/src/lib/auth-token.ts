/**
 * In-memory access token store.
 *
 * Deliberately NOT localStorage or sessionStorage: anything stored there is
 * readable by any script on the page, so a single XSS — including one from a
 * dependency — hands over the session. Keeping the token in a module variable
 * means it dies with the tab, and the httpOnly refresh cookie restores the
 * session on reload without JavaScript ever seeing it.
 *
 * Client-only. Never import this from a server component: a module-level
 * variable on the server is shared across requests, which would leak one
 * user's token to another.
 */

let accessToken: string | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function clearAccessToken(): void {
  accessToken = null;
}
