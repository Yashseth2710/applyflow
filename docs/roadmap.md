# Roadmap

Build order is deliberate: the reliable core first, AI last. AI is an enhancement,
never a dependency of the core product.

| # | Milestone | Status |
|---|-----------|--------|
| 0 | Environment & tooling | ✅ done |
| 1 | Foundation — repo, docs, app skeletons, health check, CI | 🚧 in progress |
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

## Milestone 1 — Foundation 🚧

- [x] Docs: README, architecture, database schema, API spec
- [ ] Backend: settings, database session, declarative base
- [ ] Backend: FastAPI app + `/api/v1/health` with a real database probe
- [ ] Alembic initialised
- [ ] Backend tests
- [ ] Frontend: Query provider, API client, health page
- [ ] GitHub Actions CI
- [ ] Repo pushed

**Done when:** both apps run locally, the frontend displays live backend + database
status, and CI passes on push.

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
