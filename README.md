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
- **DB: MongoDB** document per Kit (collections `users`, `sessions`, `kits`, `jobs`,
  `practice_progress`, `fetch_cache`); in-memory repositories back the CLI and tests so the
  batch needs no database.
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

Single `GEMINI_MODEL` (default `gemini-2.0-flash`). Native JSON-schema mode → Pydantic validate → exactly
**one** repair call → recorded step failure. Backoff with jitter honouring `Retry-After`
(max 4 attempts), then a recorded step failure — one quota to reason about. Page/JD text is
truncated to a per-prompt token budget.

## Architecture

`pipeline.run(case, deps, on_event) -> Kit` is pure orchestration — no Mongo, no FastAPI.
The API saves its output; the CLI writes JSON. Layers: `domain` / `scheduling` /
`coverage` / `validation` / `practice` (pure, import nothing) → `pipeline` (depends on
`LLMProvider` / `Fetcher` interfaces) → `retrieval` / `llm`
(infrastructure) → `api` (thin) → `jobs` / `persistence`. Full diagram: `docs/ARCHITECTURE.md`.

## Retrieval approach and sources

- **Company site:** priority-queue crawl from the company URL (budget 12 pages, depth ≤ 2,
  ≤ 3 concurrent, ≤ 1 req/s per host, `Crawl-delay` honoured). Same registrable domain plus
  an ATS allowlist (greenhouse, lever, ashby, workable) one hop; relative links followed;
  static HTML only. No fixed path list — a heuristic link ranker finds hiring pages
  wherever they are buried.
- **Public discussion:** Hacker News via the Algolia API (keyless) + optional `SEARCH_API_KEY`;
  skipped with reason when the company URL is private.
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

Every item carries `{origin, edited, pinned, rev, order}` (see ADR-0004).
**Protected** = user-written, edited or pinned. Regenerating a Category replaces only
unprotected items in one atomic single-document update that also keeps any item whose `rev`
changed since the job started (in-flight edits survive). Moving a Question across Categories
counts as an edit; reordering within one changes only the fractional-index `order` key.
Brief regeneration on an edited brief returns a **proposal**. Manual Schedule edits are kept
until an explicit rebuild (warns before replacing); the Schedule is marked stale when
Questions change; deleted Question ids are stripped immediately. Metadata is stripped on
export so output matches Appendix A exactly.

## Schedule allocation

Pure, deterministic (`scheduling/allocator.py`): weight `w = difficulty × (must 2 | nice 1)`,
sorted desc (ties: Category order, then id). Minutes by `(Category, difficulty)` lookup.
Questions ≥ days: earlier days get the extra questions (hard/high-priority first, last day
lightest). Questions < days: one per day in weight order, then spaced-review days repeating
top-weight Questions. 1 day: everything, honest minutes. Zero Questions: N empty days with
explanatory focus. Overload warning above 180 min/day average. Property-tested.

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

## Edge cases

Invalid/404/timeout company → `ok` + honest brief + research-log entry. No hiring page →
recorded, generic mix. Two-line JD → `thin_jd` flag, small Kit, warning, nothing invented.
No discussion → "nothing found" recorded, brief says so. Invalid model JSON → one repair,
then step failure. Rate limits → backoff with jitter, then recorded step failure. Duplicate submit → existing Kit
(`force_new` overrides; failed Kits retried in place). 1-day / 60-day → always exactly N days.

## Key decisions, trade-offs, limitations

- Single API instance assumed (in-process worker; stale jobs requeued once, then retryable).
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
  "session expired" flow back to login.

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
