# Interview Prep Kit — Backend

Turns a job description (JD), a company website and a number of days into a structured,
editable interview preparation Kit (Appendix A of the brief).

## Stack (and why Python)

- **Backend: Python 3.12 + FastAPI** (Pydantic v2, httpx). The brief prefers Node/Express
  but allows equivalents with justification (see `docs/adr/0001-python-fastapi-backend.md`):
  the pipeline is retrieval + typed validation + deterministic allocation, where Pydantic
  strict models, `hypothesis` property tests and FastAPI's OpenAPI schema give the most
  leverage. The mandated `npm run evaluate` / `npm run setup` commands work from the root
  `package.json` as thin wrappers over the Python batch runner.
- **DB: MongoDB** when `MONGODB_URI` is set (collections `users`, `sessions`
  (TTL), `kits`, `jobs` (partial unique index: one active job per Kit), `practice`,
  `page_cache` (TTL), `throttles`); the same behavioural contract suite runs against
  the in-memory and MongoDB implementations. In-memory repositories back the CLI and
  tests so the batch needs no database. Run the database locally with
  `docker compose up -d mongo`, then `MONGODB_URI=mongodb://127.0.0.1:27017 npm run dev`
  (or `npm run dev:mongo`). Restarting the server preserves everything; production
  startup refuses to start without a database, model key and allowed origins, naming
  every problem. Create users with `npm run users:create -- --email you@x.co --password '...'`.
- **LLM: one Gemini Flash-tier model** behind the structured-generation interface
  (`GEMINI_MODEL` env-pickable). Only `GEMINI_API_KEY` is required.
- **Decisions: heuristics + the same LLM** — classification, link ranking and hiring-signal
  flags are deterministic heuristics checked against the LLM's structured output; no second
  provider, no extra keys. **No AI orchestration framework** (see ADR-0003).

## Setup and batch commands

```bash
npm run setup                                        # creates apps/api/.venv, installs package
GEMINI_API_KEY=... npm run evaluate -- --input <cases.json> --output <kits.json>
# offline / tests:
FAKE_LLM=1 npm run evaluate -- --input fixtures/cases.json --output out.json
npm test                                             # pytest: unit + property + integration
```

Sample input: `fixtures/cases.json`. Sample output: `fixtures/sample-output.json`.
Exported structure schema: `fixtures/kit.schema.json` (generated from the Pydantic models
via `apps/api/export_schema.py`).

## LLM provider and model

Single `GEMINI_MODEL` (default `gemini-2.0-flash`). One shared pooled client sends the
key in the `x-goog-api-key` header (never in URLs or errors). A process-wide
request/token limiter is shared by every concurrent run. Retries happen only for
genuine provider conditions (429 honouring `Retry-After`, 5xx with bounded backoff,
network failures) — programming errors fail immediately. Truncated output is retried
once with a smaller prompt; output is deep-validated against its schema with exactly
**one** repair call that enjoys the same retry protection; usage and latency are
recorded per call. Page/JD text is truncated to a per-prompt token budget. The scripted
fake model is available only through the explicit `FAKE_LLM` setting — with no key and
no explicit fake, the batch command and the server fail fast with `MISSING_CREDENTIALS`.

## Architecture

`pipeline.run(case, deps, on_event) -> Kit` is pure orchestration — no Mongo, no FastAPI.
The API saves its output; the CLI writes JSON. Layers: `domain` / `scheduling` /
`coverage` / `validation` / `practice` (pure, import nothing) → `pipeline` (depends on
`LLMProvider` / `Fetcher` interfaces) → `retrieval` / `llm`
(infrastructure) → `api` (thin) → `jobs` / `persistence`. Full diagram: `docs/ARCHITECTURE.md`.

## Retrieval approach and sources

- **Company site:** priority-queue crawl from the company URL (budget 12 pages, depth ≤ 2,
  ≤ 1 req/s per host enforced under concurrency, `Crawl-delay` honoured up to a cap).
  Redirects are followed manually (max 5 hops) with every hop validated before it is
  requested; a redirect to a non-routable address is refused without contacting it.
  Scope is the public-suffix-aware registrable domain plus an exact-domain ATS
  allowlist (greenhouse, lever, ashby, workable) one hop — `greenhouse.io.evil.example`
  never matches, and a `.co.uk` company never leads to other `.co.uk` sites. URLs are
  normalised (trivial variants fetched once), retrieved pages count against the budget,
  and links per page are bounded. Static HTML only.
- **URL guard:** strict by default — only globally routable addresses (no private,
  loopback, link-local, multicast, shared-address, reserved or IPv4-mapped-private
  forms, every resolved address checked); production additionally allows only ports
  80/443. The CLI opts out explicitly for fixture hosts.
- **robots.txt:** fetched per host and cached with expiry; missing allows, server-error
  or unreachable disallows. Bodies stream with a 2 MB mid-download cutoff; content
  types allowlisted; the page cache is bounded and expiring. Every outcome is a page
  or a recorded skip reason in the `research_log` — one dead source never fails the run. Unreachable company → `ok` Kit with
  a deterministic honest brief ("We could not retrieve …", no LLM call).
- **Public discussion:** Hacker News via the Algolia API (keyless) queried with the
  resolved company name (JD → site-declared name/title → domain); skipped with reason
  when the company URL is private. Glassdoor/LinkedIn are not scraped.
- **Hiring signals:** computed only from pages typed as hiring-related with strict
  round-level patterns, so an about page mentioning "coding" or "values" sets no
  signal. The research log records the hiring page found, or that none exists.
- **Sources:** the company's own site; Hacker News; optional search API. Glassdoor/LinkedIn
  are not scraped (terms + blocking). `robots.txt` honoured per RFC 9309; disallowed,
  oversize, wrong-type, 4xx/5xx and timed-out pages are skipped and recorded in the
  `research_log` — one dead source never fails the run. Unreachable company → `ok` Kit with
  a deterministic honest brief ("We could not retrieve …", no LLM call).

## Step sequencing and responsibilities
`ingest` (normalise, thin-JD flag) → `extract_requirements` ∥ `crawl_company` ∥
`research_discussion` (independent, concurrent) → `classify` (kind/priority/seniority) +
`analyze_hiring_signals` → `write_brief` (only from fetched text) → `generate_questions`
(one call **per Category** with its own prompt; empty Categories skipped, never padded) →
`coverage_loop` → `generate_flashcards` (must + technical) → `build_schedule` (code) →
`assemble_kit` (Pydantic + semantic validation). Hiring signals change the questions: a
take-home adds scoping/trade-off questions; a system-design round switches that Category on.

## Generated / edited / pinned state

Every item carries `{origin, edited, pinned, rev, order}` (see ADR-0004); the brief
carries the same shape. **Protected** = user-written, edited or pinned. Creates and
patches are validated against typed per-collection schemas (unknown fields rejected;
Category, difficulty, kind, priority and Requirement references checked); ids are
server-assigned and every patch carries the revision (missing is rejected, stale is a
conflict). Deleting a Requirement prunes it from every Question, Flashcard and gap list
and reports Questions left without a Requirement. The Schedule is marked stale only by
changes that can affect it (never by pins, reorders or Flashcard edits), and each day's
minutes always equal the sum of its Questions' minutes. Regenerating a Category replaces only
unprotected items in one atomic single-document update that also keeps any item whose `rev`
changed since the job started (in-flight edits survive). Moving a Question across Categories
counts as an edit; reordering within one changes only the fractional-index `order` key
(exact rational midpoints in `app/domain/ordering.py`, mirrored in `lib/ordering.ts` from
shared vectors in `fixtures/ordering-vectors.json`; scopes rebalance to short keys past
32 characters, old keys keep sorting without migration). Regenerating a Category calls the
model (the Category's own prompt, hiring signals, kept prompts as an exclusion list) and
commits atomically, keeping protected items and in-flight edits, then recomputes coverage.
Brief regeneration on an edited brief returns a **proposal**. Manual Schedule edits are kept
until an explicit rebuild (warns before replacing); deleted Question ids are stripped immediately.
Metadata (including brief metadata) is stripped on export, and the export is validated
before serving — an invalid Kit yields a clear error, never a payload.

## Schedule allocation

Pure, deterministic (`scheduling/allocator.py`): weight `w = difficulty × (must 2 | nice 1)`,
sorted desc (ties: Category order, then id). Minutes by `(Category, difficulty)` lookup.
With at least as many Questions as days, the weight-ordered list is split into contiguous
minute-balanced days (day totals differ by at most the largest single Question's minutes),
so harder material never lands later. Questions < days: one per day in weight order, then
Review days repeating top-weight Questions in expanding cycles (first review always the
top Question). 1 day: everything, honest minutes. Zero Questions: N empty days with
explanatory focus. Overload warning above 180 min/day average. Property-tested
(balance, expanding review spacing, invariants).

## Second pass (coverage loop)

Coverage is set arithmetic in code: `gaps = requirements − ⋃ question.requirement_ids`.
Up to **3 Passes**: initial + up to 2 gap-fill rounds generating only for Gap ids with existing
prompts as an exclusion list; the last round targets `must` Gaps only. Stops on no gaps,
the Question cap, or no progress (identical Gap set twice). Remainder ships honestly in
`uncovered_requirement_ids`. Why 3: the first pass covers the bulk, the second targets the
remainder narrowly, the third is a last forced attempt for `must` — beyond that tokens are
better spent elsewhere.

## Creative feature: practice answer check

`POST kits/{id}/practice/check` — the candidate types an answer; each `outline_points[i]`
is judged covered/missing by literal word-overlap. Solves "I practised but can't tell if
my answer was any good" with zero extra LLM tokens. UI states its limits: literal reading,
coverage check not quality judgment.

## Generation jobs

Jobs are documents (`generation` and regeneration kinds) claimed atomically from the
database — oldest pending first — by a worker loop with enforced concurrency (default 2)
and per-user limits (default 1 concurrent generation; over-budget jobs stay queued).
A recovery pass runs continuously: a stale heartbeat requeues the job once, then fails it
retryable. Per-Step (60 s) and overall (180 s) deadlines bound every run, plus a job-level
backstop; a retried generation reuses already-cached pages instead of re-fetching.

## Edge cases

Invalid/404/timeout company → `ok` + honest brief + research-log entry. No hiring page →
recorded, generic mix. Two-line JD → `thin_jd` flag, small Kit, warning, nothing invented.
Descriptions over 30,000 characters are truncated with an explicit warning (never silently).
Days outside 1–60 fail the Case with `INVALID_INPUT`. Duplicate batch ids are made unique
with a recorded note; malformed cases files fail before any work, and output is written
atomically. One bad model value (difficulty 99, missing outline) is clamped or dropped —
never fails the Kit. Per-Step (60 s) and overall (180 s) generation deadlines return a
valid partial Kit as `ok` with warnings where requirements exist, else `TIMEOUT`.
No discussion → "nothing found" recorded, brief says so. Invalid model JSON → one repair,
then step failure. Rate limits → backoff with jitter, then recorded step failure. Duplicate submit → existing Kit
(`force_new` overrides; failed Kits retried in place). 1-day / 60-day → always exactly N days.

## Key decisions, trade-offs, limitations

- Single API instance assumed (in-process worker loop plus request-path dispatch bursts
  sharing one atomic claim; stale jobs requeued once, then retryable).
- Auth: login-only web app; registration closed by default and users are provisioned
  with `npm run users:create -- --email you@x.co --password '...'` (`REGISTRATION_OPEN=true`
  reopens it explicitly). Session cookies are `Secure` in production. Per-user quotas
  default to 10 Kits/day, 50 stored Kits and 1 concurrent generation; login is throttled
  per client address plus account in a bounded, expiring store; Argon2id only, hashed
  off the request loop, passwords bounded to 200 chars; mutating requests in production
  require an allowed origin and startup refuses to run without the setting.
- `failed` batch status reserved for no-valid-Kit cases (`INVALID_INPUT`, `LLM_UNAVAILABLE`,
  `KIT_INVALID`, `TIMEOUT`, `MISSING_CREDENTIALS`); unreachable company is `ok`.
- Single-provider LLM limits are volatile → backoff + limiter; verify at build time.
- No headless browser (JS-only pages are a documented gap). No DNS-rebinding defence beyond
  redirect re-validation. CloudFront→EC2 hop and secret manager out of scope.
- Appendix B's example shows unreachable company as failure; this build records it as `ok`
  per the FAQ ("a missing hiring page is not a failure") — a one-line switch if needed.

## Frontend (web app)

Next.js (App Router, strict TypeScript) + Tailwind CSS v4 + TanStack Query.
Source: `apps/web`. Design: `docs/prd-frontend.md`. Plan: `plans/frontend.md`.

### Setup

```bash
npm run web:install
API_ORIGIN=http://127.0.0.1:8000 npm run web:dev   # web on :3000, proxies /api/* to the backend
npm run dev                                          # backend on :8000 (FAKE_LLM=1 for offline)
npm run web:test                                     # vitest unit + component tests, then the OpenAPI drift check
npm run web:e2e                                      # login → create → watch → edit → regenerate (edit survives), FAKE_LLM mode
```

The only frontend environment variable is `API_ORIGIN` (see `apps/web/.env.example`).

### Architecture

- Routes: `/login`, `/kits`, `/kits/new` (single | batch tabs),
  `/kits/{id}` (Overview, or the progress screen while generating),
  `/kits/{id}/role|questions|flashcards|schedule|practice`, `/kits/{id}/print`.
  Middleware redirects signed-out visits with a return-to address.
- Data path: all Kit data is fetched client-side through the TanStack query
  cache (one entry per Kit, one for the list); the cache is the single source
  of truth; every mutation is optimistic with rollback.
- Same-origin API: the browser only talks to the web app; `/api/*` is proxied
  to the backend so cookies are first-party. Contract: types are generated from
  the committed `apps/api/openapi.json` (`npm run generate:types` in
  `apps/web`); `npm run web:test` fails on drift.
- Error model: the uniform envelope is decoded once (`lib/errors.ts`) into
  typed errors; every surface shows message + reference id; a 401 raises one
  "session expired" flow back to login. Post-login redirects accept in-app
  paths only; every response carries CSP, framing, referrer, sniffing and
  permissions headers; dependencies audit clean at release.

### State model for edits and regeneration

- Every item carries `{origin, edited, pinned, rev, order}`; badges derive
  from it; protected = user-written, edited or pinned.
- Editing (`lib/mutation-queue.ts` + `lib/editing.tsx`): autosave per field on
  blur or ~600 ms idle; optimistic apply; writes serialised per item with
  per-item Saving/Saved/Failed + retry; revision conflicts offer Keep mine /
  Use latest with the draft preserved. Reorder/move computes the backend's
  fractional order key locally (`lib/ordering.ts` mirrors
  `app/domain/ordering.py`), confirms with the server, rolls back on refusal.
- Regeneration (`lib/regen-controller.ts`): confirmation counts
  replaced/protected from metadata; protected items stay editable mid-run;
  new items badged; an edited/pinned brief yields a Proposal (Accept/Reject);
  Schedule rebuild warns that manual edits are replaced; Gaps offer
  "Generate a Question for this" (targeted endpoint, nothing else touched).

### Design decisions

- Visual system: the Tailorec tactile violet neumorphic system (`apps/web/app/tailorec.css`,
  tokens mirrored from its DESIGN.md) — blue-gray `#e0e5ec` canvas, graphite ink,
  signal violet `#6c63ff` for action/selection only, pale `#eeedff` eyebrows, teal
  success, risk-red danger; Plus Jakarta Sans display + DM Sans body; raised/inset
  surfaces; 4/8/12/16px radii with pills reserved for status; 1280px framed narrative;
  raised nav-shell with mobile menu; dark closing footer strip. The reference ships
  no dark theme, so the app is light-only (an intentional deviation from the earlier
  "follow the system" line).
- Light/dark follows the system (no toggle); reduced motion respected; skip
  link, live-region announcements, keyboard-first flows (Space/1/2/3/Backspace
  in Drills, keyboard + Move-menu reordering).
- Practice: Drills of 10 from a queue snapshot; reviews save optimistically;
  weak-spots report ranks by Confidence + coverage + priority with reasons;
  print view is a one-page summary via a print stylesheet. Kit view navigation
  uses the reference tabs pattern (violet active); Category groups use its
  native details/summary disclosure pattern; focus is the reference 3px violet outline.
- Stretch keyword self-check (`/practice/check`) is labelled
  "keyword match only" with its limits stated.

### Limitations

- No undo for deletes (no restore endpoint); no multi-tab live sync beyond
  per-item conflict handling; cross-Category drag is via the Move menu, not
  between columns; the fake-LLM server mode yields thin Kits, so the e2e adds
  items by hand like the backend's own API tests do.
