// Access token lives in memory, not localStorage — anything in storage is
// readable by any script on the page. Client-only: a module variable on the
// server would be shared across requests.

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
