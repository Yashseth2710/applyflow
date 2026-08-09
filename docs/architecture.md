# Architecture

## Overview

```
                          Browser
                             │
                             ▼
                 ┌───────────────────────┐
                 │  Next.js (Vercel)     │
                 │  App Router, TS       │
                 │  TanStack Query       │
                 └───────────┬───────────┘
                             │  HTTPS / REST / JSON
                             │  Bearer access token
                             │  httpOnly refresh cookie
                             ▼
                 ┌───────────────────────┐
                 │  FastAPI (Render)     │
                 │  ┌─────────────────┐  │
                 │  │ API layer       │  │  routing, auth, validation
                 │  ├─────────────────┤  │
                 │  │ Service layer   │  │  business logic, AI
                 │  ├─────────────────┤  │
                 │  │ Repository      │  │  data access
                 │  └─────────────────┘  │
                 └───────┬───────┬───────┘
                         │       │
              ┌──────────┘       └──────────┐
              ▼                             ▼
   ┌────────────────────┐        ┌────────────────────┐
   │ PostgreSQL (Neon)  │        │  AI Provider       │
   │ SQLAlchemy+Alembic │        │  mock | ollama     │
   └────────────────────┘        └────────────────────┘
```

## Layering

Requests flow **API → Service → Repository → Database**. Each layer only talks to
the one below it.

| Layer | Responsibility | Must not |
|-------|----------------|----------|
| API (`app/api/`) | HTTP concerns: routing, status codes, auth dependencies, request/response schemas | Contain business logic or raw SQL |
| Service (`app/services/`) | Business rules, orchestration, AI calls | Know about HTTP or FastAPI |
| Repository (`app/repositories/`) | Queries, persistence | Contain business rules |
| Model (`app/models/`) | SQLAlchemy table definitions | Contain logic |

The point is testability: services are tested without spinning up HTTP,
repositories without mocking business rules.

---

## Key decisions

### 1. Company as fields, not a table

The spec proposed a `companies` table. We store company name/website directly on
`applications`.

**Why:** a shared company table needs deduplication ("Google" vs "Google India" vs
"google"), and getting that wrong corrupts every user's data. The MVP has no
feature that requires companies to be shared entities.

**Revisit when:** we want company-level analytics across users, or autocomplete
from a canonical list. It's an additive migration, not a rewrite.

### 2. JWT: in-memory access token + httpOnly refresh cookie

**Why not `localStorage`:** any XSS — including one from a dependency — can read it.
This app holds resumes, salary expectations, and interview notes.

**Design:**
- Access token: 15 min, held in JS memory only, sent as `Authorization: Bearer`
- Refresh token: 7 days, `httpOnly` + `Secure` + `SameSite=Lax` cookie, unreadable by JS
- On page load or 401, the client silently calls `/auth/refresh`

**Cost:** a refresh round-trip on load, and CORS needs `allow_credentials=True` with
explicit origins (wildcards are rejected by browsers when credentials are used).

### 3. Frontend types generated from OpenAPI

Pydantic schemas are the single source of truth. TypeScript types are generated
from FastAPI's OpenAPI document rather than hand-written.

**Why:** hand-maintained duplicates drift. A renamed backend field should break the
frontend build, not fail silently at runtime.

Zod is still used, but for **input validation** (form rules), not for redeclaring
response shapes.

### 4. Timestamps: UTC storage, per-user display

All timestamps are `TIMESTAMPTZ`, stored UTC. Rendering resolves in this order:

```
profiles.timezone  →  browser-detected  →  DEFAULT_TIMEZONE (Asia/Kolkata)
```

The browser zone is captured at registration via
`Intl.DateTimeFormat().resolvedOptions().timeZone` and is user-editable in settings.

Interviews additionally carry an **optional** timezone, so a candidate can see both
their local time and the interviewer's ("10:00 AM EST / 8:30 PM IST").

**Why:** storing local time as text makes an instant unrecoverable — you cannot
correctly re-render it for another zone, and DST breaks it.

### 5. Backend host chosen up front: Render

**Why now:** free Python hosts suspend after inactivity, so the first request pays a
30–50s cold start. That constrains design — AI endpoints must be async-friendly, the
frontend needs honest loading states, and health checks need generous timeouts.
Discovering this at deployment time would mean reworking finished features.

### 6. Analytics withholds percentages until the numbers earn them

Counts, timings and the weekly chart are shown from the first application. Rates are
not: below five sent applications the backend returns `null` for every rate rather
than a number, and the UI says so.

**Why:** one offer out of two applications is a 50% offer rate. It is arithmetically
correct and completely meaningless, and it is the number a new user sees first. A
tool that reports it teaches people to trust figures that are noise. The threshold
lives in the service, not the client, so every consumer of the API gets the same
answer.

The funnel is cumulative — reaching the offer stage counts towards every earlier
rung — because people log the interview they got without ever ticking "assessment",
and a funnel that widens further down looks broken.

---

## AI provider abstraction

```
  API endpoint  →  AIService  →  AIProvider (interface)
                                    ├── MockProvider    deterministic fixtures
                                    ├── OllamaProvider  local llama3.2:3b
                                    └── GeminiProvider  hosted, free tier
```

Every provider returns validated Pydantic models, never raw strings. Selected by
`AI_PROVIDER` env var; adding a hosted provider means one new class.

Ollama is a local-development option only — it needs 2–4 GB of RAM and the free host
gives 512 MB, so the deployed site runs Gemini. Tests pin the mock through dependency
injection rather than config, so no test run can reach a live API or spend quota.

**Local model reality (llama3.2:3b, CPU, benchmarked):** ~17.5 tok/s generation,
~66 tok/s prompt processing, reliable JSON via schema-constrained output. Extraction
quality needs prompt work — split calls, few-shot examples, schema enforcement, and
a validation retry pass. Good, not excellent. The abstraction exists precisely so
this is a config decision rather than an architectural one.

---

## Database connection

Neon free tier scales compute to zero after ~5 minutes idle. Pooled connections go
stale, so the engine uses:

```python
pool_pre_ping=True   # validate before checkout; transparently replace dead conns
pool_recycle=300     # never reuse a connection older than the suspend window
```

Without `pool_pre_ping`, wake-ups surface as intermittent
"server closed the connection unexpectedly" errors.

The direct (non-pooled) Neon endpoint is used deliberately — PgBouncer in transaction
mode breaks Alembic migrations and psycopg3 prepared statements.

---

## Security

| Concern | Approach |
|---------|----------|
| Passwords | Argon2id |
| Tokens | Short-lived access + rotating refresh; secret from env |
| Authorization | Every query scoped by `user_id`; ownership checked before mutation |
| SQL injection | SQLAlchemy parameterisation only, no string-built SQL |
| CORS | Explicit origin list, credentials enabled |
| Uploads | PDF only, size-capped, content-type verified, stored outside the repo |
| Rate limiting | slowapi on auth and AI endpoints |
| Secrets | Env vars only; `.env` gitignored and verified |
| Errors | Generic messages to clients; details logged server-side |

Authorization is enforced at the repository layer, so no endpoint can accidentally
omit the ownership filter.
