/**
 * API response types.
 *
 * From Milestone 3 these are generated from the backend's OpenAPI schema
 * (docs/architecture.md decision 3). Hand-written for now while the surface
 * is small.
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

export type CareerLevel = "student" | "entry" | "mid" | "senior" | "lead";

export interface Profile {
  timezone: string;
  phone: string | null;
  location: string | null;
  linkedin_url: string | null;
  github_url: string | null;
  portfolio_url: string | null;
  career_level: CareerLevel | null;
  years_experience: number | null;
  summary: string | null;
}

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  created_at: string;
  profile: Profile | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthResponse {
  user: User;
  token: TokenResponse;
}

export interface RegisterPayload {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  timezone?: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}
