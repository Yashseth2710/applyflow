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
   ┌────────────────────┐        ┌──────────────────────┐
   │ PostgreSQL (Neon)  │        │  AI Provider         │
   │ SQLAlchemy+Alembic │        │  mock | ollama |     │
   │ rows + file bytes  │        │  gemini              │
   └────────────────────┘        └──────────────────────┘
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

### 5. Host chosen up front, and later changed

**Why choose early:** a host is not a deployment detail, it is a design
constraint. Free Python hosts suspend after inactivity, so the first request
pays a 30–50s cold start — which is why AI endpoints are async-friendly, the
frontend has honest loading states, and health checks have generous timeouts.
Discovering that at deployment time would have meant reworking finished
features.

**The original answer was Render for the API and Vercel for the frontend.** It
was replaced by a single Vercel project once the app was ready to deploy: the
user wanted one place, and Vercel's Services feature builds a `frontend/` Next
app and a `backend/` FastAPI app as two services behind one domain. Both
answers were free; this one has fewer moving parts.

The switch is not neutral, and the concessions are worth stating plainly:

**Same origin, which is a real gain.** The API is reached at `/api/...` on the
same domain, so there is no CORS at all, and the refresh cookie's
`SameSite=lax` keeps working. Split across two hosts it would have had to
become `SameSite=None`, which is a weaker position to be in.

**Uploads drop from 5 MB to 4 MB.** The platform rejects any request body over
4.5 MB before the app sees it. Sitting under that means a rejection the user
gets an explanation for, rather than one from infrastructure they cannot see.

**The in-memory rate limiter stops meaning much.** Each invocation can be a
fresh process, so slowapi's counters no longer accumulate. The durable,
database-backed limits — failed sign-ins per email, registrations per address,
AI per day, uploads per hour, reset emails per address — are unaffected, and
those were always the layer that mattered. Decision 10 explains why they exist
separately; this is that reasoning collecting on its bet.

**The reset email is sent inline instead of after the response.** A serverless
process can be frozen the moment it responds, so work queued for "afterwards"
may never run, and an email that silently fails to arrive is worse than a
slower request. Sending inline reintroduces a timing difference between an
address that has an account and one that does not, so the endpoint now holds
both paths to the same floor (`MIN_FORGOT_PASSWORD_SECONDS`). That is weaker
than a background task and much stronger than nothing: it leaks only when a
send runs slower than the floor, rather than announcing "instant means no
account" every time.

**Connections must go through Neon's pooler.** Serverless opens a connection
per invocation, so `DATABASE_URL` uses the `-pooler` hostname in production.
Locally it stays direct, which is why `.env.example` still says to avoid it
there.

**Link prefetching is off.** Found by opening the deployed app and reading the
network tab: around forty-five 404s per session, all of them Next 16 segment
prefetches. Proven with curl — the same URL answers 200 without the
`Next-Router-Segment-Prefetch` header and 404 with it, matched to `/404` by the
platform. Nothing user-facing broke, because a missed prefetch just means the
page is fetched on click.

Next 16.3 has no switch for it. `experimental.clientSegmentCache` no longer
exists and the build rejects it; `prefetchInlining: false` splits prefetches
into *more* requests, not fewer. Both were tried. So every `next/link` import
now points at `components/ui/link.tsx`, which sets `prefetch={false}` — and a
browser run against a production build confirms zero prefetch requests, rather
than assuming it.

The trade is cheap here specifically: pages are shells that load their data
client-side through TanStack Query, so prefetch was warming the RSC payload and
not the data. Leaving it meant a network tab full of red, which reads as a
broken app to anyone who looks. Revisit when the platform serves segment
prefetches correctly.

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

### 7. Uploaded files live in the database

A `Storage` interface with two implementations: `LocalStorage` writes to disk for
poking at files by hand, `PostgresStorage` writes bytes to the `stored_files`
table. `STORAGE_BACKEND` selects one; the default is Postgres.

**Why:** Render's free tier gives an ephemeral filesystem — every deploy and
every idle restart wipes it. A resume uploaded on Monday would be a broken
download on Tuesday, with the row still there insisting the file exists.

The database backend shares the caller's session deliberately, so a file and the
row describing it commit or roll back together and neither can outlive the
other. It also means deletes must be issued *before* the commit: a delete after
committing would open a second transaction that nothing ever commits, leaving
the bytes behind after the row that described them is gone.

Object storage (S3, R2) would be the normal answer and remains the upgrade path —
the interface exists so that is one new class. It was rejected here only because
every free tier needed a credit card.

### 8. Accessibility: axe in CI, contrast by eye

`axe-core` runs inside the Vitest suite over the components a keyboard or screen
reader user actually meets — forms, the account menu, the analytics panels, the
upload zone. It runs on every push.

**What it deliberately does not check: colour contrast.** jsdom has no layout
engine, so nothing has a size and `var(--foreground)` never resolves to a
colour. Left enabled, the rule reports every element as "incomplete" — noise
that looks like coverage. The rule is disabled with that reason written next to
it in `src/test/axe.ts`.

Contrast is instead measured by loading the real pages in a browser and running
axe there. That pass is manual, because doing it in CI means booting the API,
the database and the frontend for every push, and the free tier does not stretch
to it.

It is worth being blunt about which one has actually caught things. The jsdom
suite found two structural bugs: theme buttons inside a `role="menu"`, which is
markup a menu may not contain and which the menu's own arrow-key handling
skipped entirely; and form errors that had ids but nothing pointing at them, so
a screen reader said "invalid" and never said why. The browser pass found five
contrast failures the jsdom suite is structurally incapable of seeing, and later
a sixth: `text-success` on `bg-success-subtle` reads 3.02:1 in light mode, which
had been sitting on the resume version list since long before the page that
turned it up.

**Fills and text are separate tokens.** The stage colours are pitched to look
right as bars, dots and chart series. As 12px text on their own 16% tint they
land between 2.6:1 and 3.5:1 in light mode. Darkening the colours themselves
would have muted every chart on the site, so each has an `-ink` variant — the
same hue and chroma, dark enough to read — and only text uses it. On a dark
ground the fills already clear 4.5:1, so there the ink tokens simply alias them
and a component never has to know which theme it is in.

The same applies to the feedback colours: `--success-ink`, `--warning-ink`,
`--danger-ink`. Any text sitting on a `-subtle` background wants the ink, and
the plain token is for fills and icons only. That is the rule the resume list
broke, so it is written down here rather than left to be rediscovered.

### 9. Rate limits are per endpoint, and count the right thing

Four endpoints are capped rather than one blanket default: a blanket limit has
to be loose enough for the chattiest route, which makes it useless on the
expensive ones.

| Endpoint | Limit | Counted by | Why |
|----------|-------|------------|-----|
| `POST /auth/register` | 5/hour | address | Registering is a once-in-a-lifetime act; five leaves room for a typo'd email |
| `POST /auth/login` | 10/min **and** 60/hour | address | The minute limit stops a fast script, the hourly one stops a slow script sitting just under it all day |
| `POST /auth/refresh` | 30/min | address | Called on every page load, so this catches something pathological rather than policing normal use |
| `POST /ai/applications/…` | 20/hour | **account** | The only endpoint that spends money |

**Counting by account on the AI route, not by address.** Quota is spent per
account, so that is what the allowance should follow. An address gets it wrong
in both directions: an office behind one NAT would share a single allowance
between everyone in it, and one person on a phone would be handed a fresh one
every time the network moved them. The token is decoded rather than used as a
string, because access tokens rotate every fifteen minutes and keying on the
string would hand out a clean slate on every refresh.

**Working out the caller's address.** The host terminates TLS in front of the
process, so `request.client.host` is the proxy on every request — limiting on
it would put the whole world in one bucket and the first attacker would lock
everyone else out. `X-Forwarded-For` carries the chain, but the client writes
the left-hand entries and the proxy appends to them. Only what the proxy added
can be believed, so the address is counted in from the *right* by
`RATE_LIMIT_PROXY_DEPTH` — 0 locally, 1 behind Render. Too low counts everyone
as one address; too high trusts a header the caller wrote.

**IPv6 is bucketed by /64, not by address.** A home IPv6 line is handed a whole
/64 as a matter of course — eighteen quintillion addresses belonging to one
person. Counting the full address there means a fresh allowance on every
request, which is not a limit at all.

**Production refuses to start if `RATE_LIMIT_PROXY_DEPTH` was not set on
purpose.** Inheriting the default of 0 behind a proxy is worse than having no
limit, and the damage is invisible until somebody is already locked out.
Setting it explicitly to 0 is accepted; the objection is to inheriting it.

`RATE_LIMIT_ENABLED=false` in the test suite, whose requests all come from one
address; `tests/test_rate_limit.py` turns it back on for itself.

### 10. A second layer of limits that survives a restart

The counters above live in process memory, which has two blind spots.

They are lost on restart, and this host sleeps after a few idle minutes, so a
restart is routine rather than exceptional — an hourly limit held in memory is
not really hourly. And they count addresses, which is the right unit for a
flood and the wrong one for guessing: ten thousand attempts spread one per
address across a botnet never trip an address limit, and every one of them is
aimed at the same account.

So a second layer, backed by the `rate_events` table, counts the things whose
cost outlives the process:

| What | Limit | Bucket |
|------|-------|--------|
| Failed logins | 10 per 15 min | the **email**, whether or not it has an account |
| Registrations | 10/day | the address — there is no account yet to key on |
| AI generations | 60/day | the account |
| Resume uploads | 30/hour | the account |

`POST /auth/refresh` is deliberately **not** on this list. It is flood
protection for a request the client makes on every page load; a restart
resetting that counter costs nothing, and writing a database row per refresh
would be a worse trade than the limit is worth.

Both layers stay. The in-memory one is cheap and keeps most traffic away from
the database; the durable one is what actually holds.

**Failed logins are counted for emails that do not exist, too.** Counting only
real accounts would leak the thing login is careful not to say: an attacker
seeing 429 for one address and 401 for another has learned which is registered,
undoing the deliberate choice to answer "no such user" and "wrong password"
identically. The 429 body is byte-identical in both cases, and there is a test
asserting that.

**A correct password clears the count.** Those failures were somebody
misremembering their own password, and holding them against the next honest
attempt would lock out the person the limit exists to protect.

**The check happens before the password is verified.** Argon2 is deliberately
slow, so verifying a password for a request that will be refused anyway is the
cheapest way to make the server do expensive work.

**Cached AI answers do not count.** They never reach the model, so charging
them would mean reopening an application spends the day's budget.

Rows are pruned per bucket on every write, with an occasional sweep of
everything past a day — a run through ten thousand invented addresses should
not leave ten thousand rows behind.

### 11. Storage is capped per account, not just per file

`MAX_UPLOAD_SIZE_MB` bounds one file. It bounds nothing in total: the same five
megabytes uploaded two hundred times breaks no per-file rule and fills the free
500 MB database, which takes the site down for its actual user.
`MAX_STORAGE_PER_USER_MB` is the total, versions included, and `/resumes/limits`
reports what is used and left so the client can refuse a file before spending a
minute sending it.

A refused upload does not count against the hourly upload allowance — otherwise
a loop of invalid files would exhaust the caller's own quota, which is a way to
lock someone out of their own account. The same reasoning applies to
registration: a duplicate email created nothing, so it costs nothing.

**Rows are the other door into the same database.** The upload quota bounds
bytes arriving as files. It does nothing about `job_description`, `notes` and
`feedback`, which sit in unbounded `TEXT` columns — one request could write as
much as it liked, and no upload limit goes anywhere near that path. So the text
fields have explicit maximums (50,000 characters for a job description, 10,000
for notes), and accounts have row caps: `MAX_APPLICATIONS_PER_USER` and
`MAX_INTERVIEWS_PER_APPLICATION`.

Both return **409**, not 429. Waiting does not help; deleting something does,
and the message says so.

### 12. What this deliberately does not solve

Written down because a security note that only lists wins is not much use.

**Being locked out on purpose.** Anyone who knows your email can keep it in
15-minute lockouts indefinitely. That is inherent to counting by account. The
window is short, a correct password clears it instantly, and since decision 15 a
completed password reset clears it too — so there is a way out that does not
involve waiting. It is a mitigation rather than a fix.

**Failed logins now cost a database write.** Making the count durable means
unauthenticated traffic can make the database do work. Pruning bounds the
storage and the in-memory address limit blunts the cheap version, but this is a
trade made on purpose, not an oversight.

**Refresh tokens still cannot be revoked.** `issue_tokens` mints a pair with no
server-side record, so a stolen refresh cookie is good for seven days and
logout only clears it from the browser it was in. The fix is a sessions table
with rotation and reuse detection. Not built. This is also why a password reset
does not end other sessions: there is nothing to end them from. Worth knowing if
the reason for resetting was that someone else had the old password.

**The CSP allows inline script.** Headers and dependency scanning arrived in
decision 16, but the policy is not nonce-based, so `script-src` does not stop an
injected script the way a strict policy would. The reasoning and what would
change the answer are in that decision.

### 13. Profile pictures are re-encoded, never stored as uploaded

Whatever arrives is decoded with Pillow, centre-cropped, resized to 256px and
written back out as WebP. Two reasons.

A photo taken on a phone carries EXIF, and EXIF routinely carries the exact
coordinates it was taken at. Serving the original back publishes someone's home
address alongside their face. Re-encoding drops every metadata block, because
Pillow only writes what it is asked to write.

And decoding is the only real check that a file is an image. A content type is
a string the client chose and magic bytes are four characters anyone can
prepend; if Pillow cannot open it, it is not a picture. SVG is refused outright
rather than handled — it is a document that can contain script, and serving one
back from our own origin is a stored cross-site scripting hole, not an avatar.

**Served as a data URI inside the user response, not as a URL.** The access
token lives in memory and travels as an `Authorization` header, so a plain
`<img src>` arrives unauthenticated and gets a 401 — the same trap already hit
once with resume downloads. At 256px WebP the inlined picture is around 7 KB on
a response the client already makes on every page load.

The centre crop is deliberate: squashing a portrait into a square is the
obvious shortcut and makes every face look wrong.

### 14. One settings page, and email is not on it

`/settings` is a single page — profile, career, links, preferences, security
and the danger zone — reached from the account menu rather than the main nav,
because it is somewhere you go occasionally and a sixth nav item would compete
with the five you use daily.

`PATCH /users/me` takes the name and every profile field together, because on
screen they are one form and a form that can half-save is worse than a slow one.

**Email is deliberately absent.** Changing it needs a verify-the-new-address
flow and somewhere to send mail from; accepting a new address without proving
it is reachable would lock people out of their own accounts. The field is shown
read-only with that reason, rather than left out and wondered about.

**Password change and account deletion both re-ask for the password**, on top
of a valid session. Otherwise an unattended laptop is enough to take an account
permanently or destroy it. Deletion cascades from `users` through every table
including `stored_files`, and the row is removed rather than flagged — a soft
delete would leave the address unusable for signing up again.

### 15. Password reset: a signed link, no table, no provider

Someone who has forgotten their password needs a way back in that does not
depend on an administrator. Two things were rejected before this one.

**Mailing a newly generated password** was the first idea and is worse than it
looks: anyone who knows an address could then force a reset and lock the owner
out of their own account repeatedly, and the working password would sit in a
mailbox in plain text forever. A link changes nothing until the real owner
clicks it.

**A hosted email provider** was the second. Resend and its peers require a
verified sending domain, which means owning a domain, which is not ₹0. Gmail
with an app password sends the same message through `smtplib` in about thirty
lines of standard library.

**The token is a JWT, and there is no table.** Type `reset`, 30 minutes, subject
= user id, plus `fp`: a SHA-256 fingerprint of the password hash the account had
when the link was issued. Using the link changes the password, which changes the
hash, which changes the fingerprint — so the link stops working, single use with
nothing stored. Changing the password anywhere else invalidates outstanding
links for free. The hash itself never travels in the token: a JWT is signed, not
encrypted, and everything in it is readable by whoever holds the link.

**`POST /auth/forgot-password` always answers 204.** An address with no account
gets exactly the same status, the same empty body, and — because the send is a
background task rather than part of the request — the same response time.
Anything else turns the endpoint into a way to ask whether a given person has an
account here, which login and registration both refuse to answer. The 429 is
safe to show because the limit is counted for unknown addresses too.

**Three requests per address per hour, durable.** Keyed on the address being
mailed rather than the caller's, because the harm here is not load on the
server — it is a stranger's inbox filling up, and the inbox is chosen by the
email in the request.

**A successful reset clears the login-attempt bucket.** The failed attempts are
what sent the person to this page; leaving the account locked for another
fifteen minutes after they have proved they can read its mailbox would be a dead
end.

**It does not sign them in.** A link from an email is weaker evidence than a
password, and a stale link in an old inbox is the case most likely to be opened
by the wrong person. The flow ends at the login page with the password they just
chose.

With `SMTP_HOST` unset the message is written to the log instead of sent. That
is how development and the whole test suite run: no network, no provider, and
the reset link visible in the console.

Known limits, accepted: Gmail allows roughly 500 messages a day, mail from a
personal address can land in a stranger's spam folder, and if the host blocks
outbound SMTP the one email module has to be swapped for an API sender.

### 16. Response headers, and dependencies that are actually checked

Both halves of this are about the same thing: problems that arrive without
anyone writing a bug.

**Headers.** The API sends `X-Content-Type-Options: nosniff`,
`X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, a
`Permissions-Policy` denying camera, microphone and location, and
`Content-Security-Policy: default-src 'none'` — an endpoint that answers in JSON
has no business loading anything. `Strict-Transport-Security` is sent **only in
production and only over HTTPS**: from a plain-HTTP localhost it would pin every
project on the developer's machine to HTTPS, which is genuinely awkward to
undo. Because the host terminates TLS, the scheme is read from
`x-forwarded-proto` — a header the client can lie about, which here costs
nothing, since the worst a liar achieves is pinning their own browser.

Referrer-Policy earns its place now rather than in the abstract: a password
reset link lives in a URL, and a full referrer is exactly how such a link ends
up in a third party's access log.

**The frontend CSP is deliberately not nonce-based.** A nonce must be unique per
request, so every one of the fifteen prerendered routes would become
server-rendered on every visit. What that buys is protection against injected
script — and nothing in this app renders HTML it did not write. There is no
`dangerouslySetInnerHTML` anywhere and React escapes the rest. What the policy
still does, and these are not decoration: `frame-ancestors` stops the app being
framed, `object-src 'none'` closes a perennial escape hatch, `base-uri` stops an
injected `<base>` repointing every relative URL, `form-action` stops a form
being made to post credentials elsewhere, and `connect-src` means script that
does somehow run cannot phone data home. `'unsafe-eval'` is allowed outside
production only, because React's dev-time refresh needs it.

**If the app ever renders HTML it did not write, this decision needs
revisiting** and the cost of nonces becomes worth paying.

**Dependencies.** `pip-audit` and `npm audit --audit-level=high` run in CI, and
Dependabot raises weekly grouped pull requests for pip, npm and the GitHub
Actions themselves. pip-audit reads the pinned requirements files rather than
the installed environment, so what is checked is what a deploy would install.

The first run was not academic — it found 64 advisories across four runtime
packages, and fixing them meant FastAPI 0.115 → 0.141 and Starlette 0.41 → 1.6,
a major version. That is the argument for the weekly cadence: a dependency left
alone for months is not stable, it is just unexamined, and the upgrade only gets
harder.

One warning is left after that upgrade and is deliberately not chased:
`starlette.testclient` says `httpx` is deprecated in favour of `httpx2`. It
comes from inside FastAPI's own module rather than from anything here, so the
fix belongs upstream. Everything the upgrade left in *our* code — the renamed
`HTTP_422_UNPROCESSABLE_CONTENT` and `HTTP_413_CONTENT_TOO_LARGE` constants —
was updated, so a warning appearing in a future run means something new rather
than something known.

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
| SQL injection | Bound parameters everywhere. The analytics aggregates are hand-written SQL, but every value — `user_id` included — is a bind parameter, never interpolated |
| CORS | Explicit origin list, credentials enabled |
| Uploads | PDF only, size-capped, content-type verified, stored as rows in the database rather than on disk |
| Rate limiting | Per endpoint, via `slowapi`. Registration 5/hour, login 10/minute and 60/hour, refresh 30/minute, AI generation 20/hour per account. See decision 9 |
| Secrets | Env vars only; `.env` gitignored and verified |
| Errors | Generic messages to clients; details logged server-side |
| Password reset | Signed link, single use via a hash fingerprint, no stored tokens. See decision 15 |
| Response headers | nosniff, frame denial, referrer, permissions and CSP on both apps; HSTS in production only. See decision 16 |
| Dependencies | `pip-audit` and `npm audit` in CI, weekly Dependabot. See decision 16 |

Authorization is enforced at the repository layer, so no endpoint can accidentally
omit the ownership filter.
