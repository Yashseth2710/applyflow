/**
 * API response types.
 *
 * From Milestone 2 these are generated from the backend's OpenAPI schema rather
 * than hand-written (see docs/architecture.md decision 3). Health is small
 * enough to declare by hand for now.
 */

export interface DatabaseHealth {
  connected: boolean;
  latency_ms: number | null;
  error: string | null;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  version: string;
  environment: string;
  database: DatabaseHealth;
}
