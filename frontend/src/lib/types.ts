/**
 * Application-facing types.
 *
 * These alias the generated OpenAPI schema rather than restating it — see
 * docs/architecture.md decision 3. Hand-written duplicates drift silently; a
 * renamed backend field should break the build, not fail at runtime.
 *
 * Regenerate after changing any backend schema:
 *     npm run gen:api      (backend must be running)
 */

import type { components } from "./api-schema";

type Schemas = components["schemas"];

// ---- auth ----
export type User = Schemas["UserResponse"];
export type Profile = Schemas["ProfileResponse"];
export type TokenResponse = Schemas["TokenResponse"];
export type AuthResponse = Schemas["AuthResponse"];
export type RegisterPayload = Schemas["RegisterRequest"];
export type LoginPayload = Schemas["LoginRequest"];
export type CareerLevel = Schemas["CareerLevel"];

// ---- health ----
export type HealthResponse = Schemas["HealthResponse"];
export type DatabaseHealth = Schemas["DatabaseHealth"];

// ---- applications ----
export type Application = Schemas["ApplicationResponse"];
export type ApplicationDetail = Schemas["ApplicationDetailResponse"];
export type ApplicationCreate = Schemas["ApplicationCreate"];
export type ApplicationUpdate = Schemas["ApplicationUpdate"];
export type ApplicationStatus = Schemas["ApplicationStatus"];
export type StatusHistoryEntry = Schemas["StatusHistoryEntry"];
export type WorkMode = Schemas["WorkMode"];
export type EmploymentType = Schemas["EmploymentType"];
export type BoardResponse = Schemas["BoardResponse"];
export type BoardColumn = Schemas["BoardColumn"];
export type ApplicationPage = Schemas["Page_ApplicationResponse_"];
