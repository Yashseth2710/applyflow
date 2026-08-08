# Database schema

PostgreSQL 18 (Neon). All timestamps are `TIMESTAMPTZ` stored in UTC.
All primary keys are UUIDs. All user-owned tables carry `user_id` and are indexed on it.

## Relationships

```
users
 ├── profiles              (1:1)
 ├── resumes               (1:N)
 ├── user_skills           (1:N)
 └── applications          (1:N)
      ├── interviews       (1:N)
      ├── notes            (1:N)
      ├── documents        (1:N)
      ├── reminders        (1:N)
      └── job_analyses     (1:N)
```

Every child of `applications` also stores `user_id` directly. Denormalised on
purpose: ownership checks become a single indexed predicate instead of a join,
which makes it much harder to write an endpoint that leaks another user's data.

---

## users

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| email | CITEXT | unique, case-insensitive |
| password_hash | TEXT | Argon2id |
| first_name | VARCHAR(100) | |
| last_name | VARCHAR(100) | |
| is_active | BOOLEAN | default true |
| created_at / updated_at | TIMESTAMPTZ | |

## profiles

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → users, unique, cascade delete |
| phone | VARCHAR(30) | |
| linkedin_url / github_url / portfolio_url | TEXT | |
| location | VARCHAR(200) | |
| timezone | VARCHAR(64) | IANA name, e.g. `Asia/Kolkata` |
| career_level | ENUM | student, entry, mid, senior, lead |
| summary | TEXT | feeds AI context |
| years_experience | SMALLINT | |

## applications

The central table.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → users, cascade, indexed |
| company_name | VARCHAR(200) | not null — stored inline, see ADR 1 |
| company_website | TEXT | |
| job_title | VARCHAR(200) | not null |
| job_description | TEXT | |
| job_url | TEXT | |
| location | VARCHAR(200) | |
| work_mode | ENUM | onsite, hybrid, remote |
| employment_type | ENUM | full_time, part_time, contract, internship |
| salary_min / salary_max | INTEGER | |
| salary_currency | CHAR(3) | default `INR` |
| status | ENUM | see below |
| source | VARCHAR(100) | LinkedIn, referral, careers page… — drives "what's working" analytics |
| resume_id | UUID | FK → resumes, nullable, `ON DELETE SET NULL` |
| date_posted | DATE | |
| date_applied | TIMESTAMPTZ | |
| position | INTEGER | ordering within a Kanban column |
| created_at / updated_at | TIMESTAMPTZ | |

Indexes: `(user_id, status)`, `(user_id, created_at DESC)`, GIN full-text on
`company_name || job_title`.

### status enum

```
wishlist → applied → assessment → phone_screen → technical_interview
        → hr_interview → final_interview → offer → accepted
```
Terminal: `rejected`, `withdrawn`, `on_hold`

Status is a plain column, not a state machine — real job searches skip stages and
move backwards.

## application_status_history

Append-only. Written on every status change; powers conversion analytics and
time-in-stage metrics.

| Column | Type |
|--------|------|
| id | UUID PK |
| application_id | UUID FK, cascade |
| user_id | UUID FK |
| from_status / to_status | ENUM (from nullable on create) |
| changed_at | TIMESTAMPTZ |

## resumes

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK, cascade |
| name | VARCHAR(200) | e.g. "Backend Developer Resume" |
| version | VARCHAR(50) | user-supplied label |
| file_path | TEXT | storage key, never a public URL |
| file_size | INTEGER | bytes |
| mime_type | VARCHAR(100) | `application/pdf` only for now |
| extracted_text | TEXT | cached pypdf output — avoids re-parsing on every AI call |
| is_default | BOOLEAN | |

## interviews

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| application_id | UUID | FK, cascade |
| user_id | UUID | FK, indexed |
| round_name | VARCHAR(200) | "Technical Round 1" |
| interview_type | ENUM | phone_screen, technical, behavioural, hr, system_design, final |
| scheduled_at | TIMESTAMPTZ | UTC |
| timezone | VARCHAR(64) | **optional** display override — the interviewer's zone |
| duration_minutes | SMALLINT | |
| interviewer_name / interviewer_role | VARCHAR(200) | |
| meeting_url | TEXT | |
| notes | TEXT | |
| result | ENUM | pending, passed, failed, cancelled |
| feedback | TEXT | |

## reminders

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK, cascade |
| application_id | UUID | FK, nullable, cascade |
| title | VARCHAR(200) | |
| description | TEXT | |
| remind_at | TIMESTAMPTZ | |
| completed | BOOLEAN | |
| completed_at | TIMESTAMPTZ | |

Index `(user_id, completed, remind_at)` — serves the dashboard's "upcoming" query.
MVP reminders are in-app: a filtered query, no background worker.

## notes

| Column | Type |
|--------|------|
| id | UUID PK |
| application_id | UUID FK, cascade |
| user_id | UUID FK |
| content | TEXT |
| created_at / updated_at | TIMESTAMPTZ |

## documents

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| application_id | UUID | FK, cascade |
| user_id | UUID | FK |
| name | VARCHAR(200) | |
| file_path | TEXT | |
| file_size | INTEGER | |
| mime_type | VARCHAR(100) | |
| document_type | ENUM | cover_letter, offer_letter, assignment, other |

## user_skills

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK, cascade |
| name | VARCHAR(100) | normalised lowercase for matching |
| proficiency | ENUM | beginner, intermediate, advanced, expert |
| years | SMALLINT | |

Unique on `(user_id, name)`.

## job_analyses

Cached AI output, so re-opening an application doesn't re-run the model.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| application_id | UUID | FK, cascade |
| user_id | UUID | FK |
| required_skills | JSONB | |
| preferred_skills | JSONB | |
| responsibilities | JSONB | |
| experience_required | VARCHAR(100) | |
| summary | TEXT | |
| match_score | SMALLINT | 0–100, computed against `user_skills` |
| matched / partial / missing_skills | JSONB | |
| provider | VARCHAR(50) | `mock` / `ollama` — which produced this |
| model | VARCHAR(100) | e.g. `llama3.2:3b` |
| source_hash | CHAR(64) | SHA-256 of the JD; re-analyse only when it changes |
| created_at | TIMESTAMPTZ | |

`match_score` is ApplyFlow's own transparent metric, computed from skill overlap.
It is **not** an ATS score and must never be presented as one.

---

## Conventions

- UUID PKs — safe to expose in URLs, no enumeration
- `ON DELETE CASCADE` from `users` down, so account deletion is complete (privacy requirement)
- `resume_id` uses `SET NULL` — deleting a resume must not delete application history
- Enums as native PG types, migrated via Alembic
- `updated_at` maintained by SQLAlchemy `onupdate`
- No soft deletes in the MVP
