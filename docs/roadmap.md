# Roadmap

Build order is deliberate: the reliable core first, AI last. AI is an enhancement,
never a dependency of the core product.

| # | Milestone | Status |
|---|-----------|--------|
| 0 | Environment & tooling | ✅ done |
| 1 | Foundation — repo, docs, app skeletons, health check, CI | ✅ done |
| 2 | Authentication — register, login, refresh, profile | ⬜ |
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

### Next up — Milestone 2

1. `User` and `Profile` models + first Alembic migration
2. Argon2 password hashing, JWT issue/verify
3. `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/me`
4. `get_current_user` dependency
5. Frontend auth context, login/register forms, protected routes
6. Timezone captured at registration from the browser

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
