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

// ---- account ----
export type ProfileUpdate = Schemas["ProfileUpdate"];
export type PasswordChange = Schemas["PasswordChange"];
export type AccountDelete = Schemas["AccountDelete"];

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

// ---- resumes ----
export type Resume = Schemas["ResumeResponse"];
export type ResumeDetail = Schemas["ResumeDetailResponse"];
export type ResumeUpload = Schemas["ResumeUploadResponse"];
export type ResumeUpdate = Schemas["ResumeUpdate"];
export type ResumeText = Schemas["ResumeTextResponse"];
export type ResumeUsage = Schemas["ResumeUsageResponse"];
export type ExtractionStatus = Schemas["ExtractionStatus"];

// ---- interviews ----
export type Interview = Schemas["InterviewResponse"];
export type InterviewWithApplication = Schemas["InterviewWithApplication"];
export type InterviewCreate = Schemas["InterviewCreate"];
export type InterviewUpdate = Schemas["InterviewUpdate"];
export type InterviewRound = Schemas["InterviewRound"];
export type InterviewMode = Schemas["InterviewMode"];
export type InterviewOutcome = Schemas["InterviewOutcome"];
export type Reminder = Schemas["Reminder"];
export type ReminderList = Schemas["ReminderList"];

// ---- ai ----
export type AITask = Schemas["AITask"];
export type AIStatus = Schemas["AIStatus"];
export type AIOutput = Schemas["AIOutputResponse"];
export type AIOutputList = Schemas["AIOutputList"];
export type JDAnalysis = Schemas["JDAnalysis"];
export type ResumeMatch = Schemas["ResumeMatch"];
export type InterviewPrep = Schemas["InterviewPrep"];
export type InterviewQuestion = Schemas["InterviewQuestion"];

// ---- analytics ----
export type AnalyticsSummary = Schemas["AnalyticsSummary"];
export type AnalyticsTotals = Schemas["Totals"];
export type FunnelStep = Schemas["FunnelStep"];
export type StatusCount = Schemas["StatusCount"];
export type StageDuration = Schemas["StageDuration"];
export type SourceStat = Schemas["SourceStat"];
export type VolumePoint = Schemas["VolumePoint"];
