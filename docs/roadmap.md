# Roadmap

Build order is deliberate: the reliable core first, AI last. AI is an enhancement,
never a dependency of the core product.

| # | Milestone | Status |
|---|-----------|--------|
| 0 | Environment & tooling | ✅ done |
| 1 | Foundation — repo, docs, app skeletons, health check, CI | ✅ done |
| 2 | Authentication — register, login, refresh, profile | ✅ done |
| 3 | Applications — CRUD, search, filters, Kanban | ⬜ |
| 4 | Resumes — upload, versioning, association | ⬜ |
| 5 | Interviews & reminders | ⬜ |
| 6 | AI — JD analysis, resume analysis, cover letters, interview prep | ⬜ |
| 7 | Analytics — dashboard, charts, conversion metrics | ⬜ |
| 8 | Quality — tests, security, accessibility, performance | ⬜ |
| 9 | Deployment — Vercel, Render, production database | ⬜ |

---

## Milestone 0 — Environment ✅

- Python 3.12.10, venv, 52 backend packages
- Node 24, 513 frontend packages, Playwright Chromium
- Ollama 0.32.6 + llama3.2:3b — benchmarked at ~17.5 tok/s generation on CPU
- Neon PostgreSQL 18.4 connected
- Git repo, verified `.gitignore`, GitHub CLI authenticated

## Milestone 1 — Foundation ✅

- [x] Docs: README, architecture, database schema, API spec
- [x] Backend: settings, database session, declarative base
- [x] Backend: FastAPI app + `/api/v1/health` with a real database probe
- [x] Alembic initialised, URL sourced from settings (no credentials in `alembic.ini`)
- [x] Backend tests — 4 passing, incl. failure path and error-leak checks
- [x] Frontend: Query provider, typed API client, live status page
- [x] GitHub Actions CI — green on both jobs
- [x] Repo pushed, `main` + `develop` branches

**Verified:** `/api/v1/health` returned `connected: true` against live Neon;
ruff, mypy, pytest, eslint, tsc and `next build` all pass locally and in CI.

## Milestone 2 — Authentication ✅

- [x] Design system: teal brand + 12-colour pipeline scale, light and dark
- [x] `User` and `Profile` models, migration `b0eb60dcce1c` applied
- [x] Argon2id hashing with transparent rehash on login
- [x] JWT with enforced token type — a refresh token cannot act as an access token
- [x] `/auth/register`, `/login`, `/refresh`, `/logout`, `/me`
- [x] `get_current_user` dependency; identical 401 for every failure mode
- [x] Frontend auth context with silent refresh, login/register/dashboard, route guard
- [x] Browser timezone captured at registration, unknown zones fall back to IST
- [x] 29 backend tests; 17-check live end-to-end run against Neon

**Security decisions worth remembering**

- Access token lives in a module variable, never `localStorage` — XSS cannot read it
- Refresh token is httpOnly + SameSite=Lax, scoped to `/api/v1/auth`, rotated on use
- Login returns one message for unknown-email and wrong-password, and verifies a
  dummy hash when no user exists so response timing cannot reveal registered emails
- Password capped at 128 chars: Argon2 hashes the whole input, so an unbounded
  password is a cheap way to burn server CPU

### Next up — Milestone 3

Planned in two halves so there's a review checkpoint mid-milestone.

**Backend first**

1. `Application` model + migration — company inline, status enum, work mode,
   employment type, salary range, `source`, `position` for board ordering
2. `application_status_history` — append-only, written on every stage change.
   Current status alone cannot answer "where do I stall" or "what is my
   interview conversion rate", and the journey is unrecoverable if not
   recorded from the start
3. Repository scoped by `user_id` at the data layer, so an endpoint cannot
   forget the ownership filter
4. CRUD + search, filters, sorting, pagination; `/applications/board` grouped
   by status
5. Tests, including that another user's record returns 404 rather than 403 —
   403 would confirm the ID exists

**Then frontend**

6. Applications list with search and filters
7. Kanban board with drag-and-drop, using the stage colour tokens
8. Create/edit form and application detail page

#### Decision: board shows 6 active columns, not 12

Twelve stages at a usable column width is ~3,300px — horizontal scrolling on
every screen, with terminal states occupying as much space as live ones.

The board shows the stages you actively move through (Wishlist, Applied,
Assessment, Interview, Final, Offer), with `phone_screen` / `technical` /
`hr` grouped under Interview and expandable. Rejected, Withdrawn and On hold
move to a collapsible "Closed" section — still one drag away, but not
competing for prime space.

The database keeps all twelve statuses. This is a presentation choice only,
so analytics still see full granularity.

---

## Decisions locked

1. Company stored as fields on `applications`, not a shared table
2. JWT — in-memory access token + httpOnly refresh cookie
3. TypeScript types generated from the OpenAPI schema
4. `TIMESTAMPTZ` UTC storage, per-user timezone display, IST fallback
5. Render for backend hosting

## Deferred

- Rotate the Neon password before production (current one was shared in chat)
- Prompt tuning for llama3.2:3b — needed at Milestone 6, see architecture.md
- Object storage provider for resumes — decide at Milestone 4

## Explicitly out of scope for MVP

Auto-apply, LinkedIn automation, recruiter messaging, payments, mobile app, Gmail
automation, calendar sync, voice interviews, recommendation engines, microservices,
Kubernetes, multi-tenancy.
