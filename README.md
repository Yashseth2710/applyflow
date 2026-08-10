# ApplyFlow

AI-powered job application management platform. Track every application, resume,
interview, and reminder in one place — and use AI to analyse job descriptions,
improve resume relevance, and prepare for interviews.

Work in progress. Applications, resumes, interviews, analytics and account
settings are built; deployment is not.

---

## Why

Job seekers manage applications across spreadsheets, email, job portals, bookmarks,
and calendars. Nothing connects them. People forget where they applied, miss
deadlines, submit the wrong resume version, and have no idea which parts of their
search are actually working.

ApplyFlow is one record per application, covering the whole journey from finding
the job to signing the offer.

---

## Stack

| Layer     | Choice |
|-----------|--------|
| Frontend  | Next.js 16 (App Router), TypeScript, Tailwind, shadcn/ui on Base UI |
| State     | TanStack Query |
| Forms     | React Hook Form + Zod |
| Charts    | Recharts |
| Backend   | Python 3.12, FastAPI, Pydantic v2 |
| ORM       | SQLAlchemy 2.0 + Alembic |
| Database  | PostgreSQL 18 (Neon) |
| Auth      | JWT — in-memory access token + httpOnly refresh cookie |
| Email     | `smtplib` and a Gmail app password — one message to send, no provider needed |
| Storage   | Uploaded files in Postgres — the free host wipes its disk on deploy |
| Images    | Pillow — avatars are re-encoded, which strips EXIF and its GPS data |
| AI        | Provider abstraction — `mock` / `ollama` (local only) / `gemini` |
| Testing   | pytest, Vitest + Testing Library, axe-core for accessibility |
| Hosting   | Vercel (frontend), Render (backend), Neon (database) — not yet deployed |

---

## Quick start

### Prerequisites

- Python 3.12+
- Node 20+
- A PostgreSQL connection string (Neon free tier works)

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements-dev.txt

cp .env.example .env            # then fill in DATABASE_URL and JWT_SECRET
alembic upgrade head
uvicorn app.main:app --reload
```

Backend runs at http://localhost:8000
API docs at http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Frontend runs at http://localhost:3000

---

## Verifying it works

```bash
curl http://localhost:8000/api/v1/health
```

```json
{
  "status": "ok",
  "database": { "connected": true, "latency_ms": 41.2 },
  "version": "0.1.0"
}
```

`database.connected` genuinely queries Postgres — it is not hardcoded.

---

## Layout

```
applyflow/
├── backend/
│   ├── app/
│   │   ├── api/v1/          REST endpoints
│   │   ├── core/            config, database, security
│   │   ├── models/          SQLAlchemy models
│   │   ├── schemas/         Pydantic request/response schemas
│   │   ├── services/        business logic (incl. AI providers)
│   │   └── repositories/    data access
│   ├── alembic/             migrations
│   └── tests/
├── frontend/
│   └── src/
│       ├── app/             App Router pages
│       ├── components/      UI components
│       └── lib/             API client, utilities
└── docs/
```

---

## Documentation

- [Architecture](docs/architecture.md) — system design and key decisions
- [Database schema](docs/database-schema.md) — tables and relationships
- [API specification](docs/api-spec.md) — endpoints


---

## Scripts

**Backend**

```bash
pytest                      # tests
pytest --cov=app            # with coverage
ruff check .                # lint
ruff format .               # format
mypy app                    # type check
alembic revision --autogenerate -m "message"
alembic upgrade head
```

**Frontend**

```bash
npm run dev
npm run build
npm run lint
npx tsc --noEmit            # type check
npx vitest                  # unit tests, including the accessibility audit
```

---

## Environment

Never commit `.env`. `.gitignore` blocks it; `.env.example` documents what is needed.

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Postgres connection string (needs `?sslmode=require` on Neon) |
| `JWT_SECRET` | Signing key — generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins |
| `FRONTEND_URL` | Where password reset links point. One address, unlike `CORS_ORIGINS` |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` | Sending account for reset emails. Leave `SMTP_HOST` empty and the message is logged instead of sent — which is how development and the tests run |
| `AI_PROVIDER` | `mock`, `ollama` or `gemini`. Defaults to `mock`, so nothing calls out unless asked |
| `GEMINI_API_KEY` | Only needed when `AI_PROVIDER=gemini` |
| `STORAGE_BACKEND` | `postgres` (default) or `local`. Local disk does not survive a deploy on the free tier |
| `DEFAULT_TIMEZONE` | Fallback when a user's timezone can't be detected |
| `RATE_LIMIT_ENABLED` | On by default. The test suite turns it off — every request there comes from one address |
| `RATE_LIMIT_PROXY_DEPTH` | How many proxies sit in front. `0` locally, `1` behind a host that terminates TLS. **Must be set explicitly in production** — the app refuses to start otherwise |
| `MAX_STORAGE_PER_USER_MB` | Total uploads per account, versions included. A per-file cap alone bounds nothing |

`.env.example` lists every variable, including the ones with sensible defaults
that are not worth setting by hand.

---

## License

MIT
