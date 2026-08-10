# Database schema

PostgreSQL 18 (Neon). All timestamps are `TIMESTAMPTZ` stored in UTC.
All primary keys are UUIDs. All user-owned tables carry `user_id` and are indexed on it.

This describes the tables that exist. Anything planned but not built lives in
`api-spec.md`, marked as such.

## Relationships

```
users
 ├── profiles                        (1:1)
 ├── resumes                         (1:N)
 └── applications                    (1:N)
      ├── interviews                 (1:N)
      ├── application_status_history (1:N)
      └── ai_outputs                 (1:N)

stored_files                         file bytes, keyed by path, owned by a user
```

Every child of `applications` also stores `user_id` directly. Denormalised on
purpose: ownership checks become a single indexed predicate instead of a join,
which makes it much harder to write an endpoint that leaks another user's data.

There is no `reminders` table. Reminders are derived from interviews and
application dates on each request, so nothing has to run on a schedule and a
reminder cannot outlive the thing that caused it.

---

## users

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| email | VARCHAR(320) | unique, indexed, lowercased before insert |
| password_hash | VARCHAR(255) | Argon2id |
| first_name | VARCHAR(100) | |
| last_name | VARCHAR(100) | |
| is_active | BOOLEAN | default true |
| created_at / updated_at | TIMESTAMPTZ | |

Deliberately not `CITEXT`: emails are normalised to lowercase in the schema
layer, so a plain unique index does the same job without depending on an
extension that would have to be installed identically on local, CI and Neon.

## profiles

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → users, unique, cascade delete |
| phone | VARCHAR(30) | |
| location | VARCHAR(200) | |
| linkedin_url / github_url / portfolio_url | TEXT | |
| timezone | VARCHAR(64) | IANA name, e.g. `Asia/Kolkata` |
| career_level | ENUM | student, entry, mid, senior, lead |
| years_experience | SMALLINT | |
| summary | TEXT | feeds AI context |
| created_at / updated_at | TIMESTAMPTZ | |

Every field is written at registration and there is currently no endpoint to
change any of them afterwards.

## applications

The central table.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → users, cascade, indexed |
| company_name | VARCHAR(200) | inline, not a shared companies table |
| company_website | TEXT | |
| job_title | VARCHAR(200) | |
| job_description | TEXT | what the AI features read |
| job_url | TEXT | |
| location | VARCHAR(200) | |
| work_mode | ENUM | onsite, hybrid, remote |
| employment_type | ENUM | full_time, part_time, contract, internship |
| salary_min / salary_max | INTEGER | check constraint: min ≤ max |
| salary_currency | VARCHAR(3) | default `INR` |
| status | ENUM | see below |
| source | VARCHAR(100) | free text — a fixed list just makes people pick "other" |
| resume_id | UUID | FK → resumes, **SET NULL** so deleting a resume keeps the application |
| date_posted | DATE | |
| date_applied | TIMESTAMPTZ | |
| position | INTEGER | ordering within a board column, sparse so a drag rewrites one row |
| created_at / updated_at | TIMESTAMPTZ | |

Indexed on `(user_id, status)`, `(user_id, created_at)` and
`(user_id, status, position)`.

### status enum

`wishlist`, `applied`, `assessment`, `phone_screen`, `technical_interview`,
`hr_interview`, `final_interview`, `offer`, `accepted`, `rejected`,
`withdrawn`, `on_hold`.

Not a state machine. Real job searches skip stages, go backwards, and revive
dead applications, so any transition is allowed and history records it.

## application_status_history

Append-only log of stage changes. Conversion rates and time-in-stage need the
journey, not just the current status, and it cannot be reconstructed later — so
it is written from the first day.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| application_id | UUID | FK → applications, cascade, indexed |
| user_id | UUID | FK → users, cascade, indexed |
| from_status | ENUM | NULL on the first entry, which records the status at creation |
| to_status | ENUM | |
| changed_at | TIMESTAMPTZ | indexed |

Everything on the analytics page is derived from this table.

## resumes

One row per **version**. Versions of the same document share a `family_id`.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → users, cascade, indexed |
| family_id | UUID | groups versions of the same resume |
| version | INTEGER | 1, 2, 3 … within a family |
| is_current | BOOLEAN | one per family |
| title | VARCHAR(200) | |
| notes | TEXT | what this version is tuned for |
| original_filename | VARCHAR(255) | |
| content_type | VARCHAR(100) | |
| size_bytes | INTEGER | |
| content_hash | VARCHAR(64) | SHA-256, detects a re-upload of the same file |
| storage_key | VARCHAR(500) | key into `stored_files`, not a filesystem path |
| extraction_status | ENUM | pending, ok, empty, failed |
| extracted_text | TEXT | what the AI features read |
| extraction_error | TEXT | shown to the user when the PDF is unreadable |
| created_at / updated_at | TIMESTAMPTZ | |

An application records the exact file that was sent, so it points at one
version — which is why versions need their own ids rather than a separate
versions table.

`empty` is a distinct status from `failed`: a scanned resume parses fine and
yields no text, and saying so is more useful than showing a blank page.

## interviews

Finer-grained than `applications.status` on purpose — an application sits in one
stage, but a stage can contain several interviews.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| application_id | UUID | FK → applications, cascade, indexed |
| user_id | UUID | FK → users, cascade, indexed |
| round | ENUM | phone_screen, technical, take_home, system_design, hr, managerial, final, other |
| mode | ENUM | onsite, video, phone |
| scheduled_at | TIMESTAMPTZ | rejected if it arrives without an offset |
| duration_minutes | INTEGER | |
| location | TEXT | address, or the meeting link |
| interviewer | VARCHAR(200) | |
| notes / feedback | TEXT | |
| outcome | ENUM | pending, passed, failed, cancelled |
| created_at / updated_at | TIMESTAMPTZ | |

`pending` covers both "hasn't happened yet" and "happened, still waiting" — the
scheduled time separates the two without a second column.

## ai_outputs

One row per application per task. Generations are cached because they cost money
and take seconds.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| application_id | UUID | FK → applications, cascade |
| user_id | UUID | FK → users, cascade |
| task | ENUM | jd_analysis, resume_match, interview_questions, cover_letter |
| content | JSONB | structured answers |
| text | TEXT | used by cover_letter, which is prose rather than fields |
| input_hash | VARCHAR(64) | fingerprint of the job description and attached resume |
| model / provider | VARCHAR | echoed back so an answer is traceable |
| generated_at | TIMESTAMPTZ | |
| created_at / updated_at | TIMESTAMPTZ | |

`input_hash` is what makes an answer go stale: editing the job description or
swapping the resume changes the hash, and the UI flags the stored answer as
describing older text instead of silently keeping it.

## stored_files

Uploaded bytes, addressed by key.

| Column | Type | Notes |
|--------|------|-------|
| key | VARCHAR(500) | PK |
| owner_id | UUID | FK → users, cascade |
| content | BYTEA | the file itself |
| size_bytes | BIGINT | |
| created_at | TIMESTAMPTZ | |

Files live in the database rather than on disk because the free host wipes its
filesystem on every deploy. Writes go through the same session as the row that
describes them, so a file and its metadata commit or roll back together and
neither can outlive the other.

---

## Conventions

- Enums are native Postgres types, so the database rejects invalid states rather
  than trusting the application. Adding a value needs a migration.
- Enum columns store the *value* (`full_time`), not the Python member name.
- `ondelete` is chosen per relationship, not by habit: `CASCADE` where the child
  is meaningless alone, `SET NULL` where history must survive
  (`applications.resume_id`).
- Every schema change is an Alembic migration; none are applied by hand.
