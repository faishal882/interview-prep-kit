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
- **LLM: Gemini Flash-tier primary, Groq fallback** behind one structured-generation
  interface (`GEMINI_MODEL` / `GROQ_MODEL` env-pickable). Only `GEMINI_API_KEY` is required.
- **Decisions: Jev (TypeSafe), optional** — every use has a fallback; without a key the
  pipeline behaves as before. **No AI orchestration framework** (see ADR-0003).

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

Primary `GEMINI_MODEL` (default `gemini-2.0-flash`), fallback `GROQ_MODEL`
(default `llama-3.3-70b-versatile`). Native JSON-schema mode → Pydantic validate → exactly
**one** repair call → recorded step failure. Token-bucket limiter per provider, `Retry-After`
honoured, exponential backoff with jitter (max 4 attempts), then failover. Page/JD text is
truncated to a per-prompt token budget.

## Architecture

`pipeline.run(case, deps, on_event) -> Kit` is pure orchestration — no Mongo, no FastAPI.
The API saves its output; the CLI writes JSON. Layers: `domain` / `scheduling` /
`coverage` / `validation` / `practice` (pure, import nothing) → `pipeline` (depends on
`LLMProvider` / `Fetcher` / `JevClient` interfaces) → `retrieval` / `llm` / `jev`
(infrastructure) → `api` (thin) → `jobs` / `persistence`. Full diagram: `docs/ARCHITECTURE.md`.

## Retrieval approach and sources

- **Company site:** priority-queue crawl from the company URL (budget 12 pages, depth ≤ 2,
  ≤ 3 concurrent, ≤ 1 req/s per host, `Crawl-delay` honoured). Same registrable domain plus
  an ATS allowlist (greenhouse, lever, ashby, workable) one hop; relative links followed;
  static HTML only. No fixed path list — a heuristic link ranker (Jev scorer when keyed)
  finds hiring pages wherever they are buried.
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
Jev only *removes* dubious links (Noul "question tests requirement" < threshold). Up to
**3 Passes**: initial + up to 2 gap-fill rounds generating only for Gap ids with existing
prompts as an exclusion list; the last round targets `must` Gaps only. Stops on no gaps,
the Question cap, or no progress (identical Gap set twice). Remainder ships honestly in
`uncovered_requirement_ids`. Why 3: the first pass covers the bulk, the second targets the
remainder narrowly, the third is a last forced attempt for `must` — beyond that tokens are
better spent elsewhere.

## Creative feature: practice answer check

`POST kits/{id}/practice/check` — the candidate types an answer; each `outline_points[i]`
is judged covered/missing (one Jev Noul per point in parallel when keyed; literal word-overlap
fallback otherwise). Solves "I practised but can't tell if my answer was any good" with zero
extra LLM tokens. UI states its limits: literal reading, coverage check not quality judgment.

## Edge cases

Invalid/404/timeout company → `ok` + honest brief + research-log entry. No hiring page →
recorded, generic mix. Two-line JD → `thin_jd` flag, small Kit, warning, nothing invented.
No discussion → "nothing found" recorded, brief says so. Invalid model JSON → one repair,
then step failure. Rate limits → backoff + fallback. Duplicate submit → existing Kit
(`force_new` overrides; failed Kits retried in place). 1-day / 60-day → always exactly N days.

## Key decisions, trade-offs, limitations

- Single API instance assumed (in-process worker; stale jobs requeued once, then retryable).
- `failed` batch status reserved for no-valid-Kit cases (`INVALID_INPUT`, `LLM_UNAVAILABLE`,
  `KIT_INVALID`, `TIMEOUT`, `MISSING_CREDENTIALS`); unreachable company is `ok`.
- Jev free-tier terms unverified → optional with fallbacks everywhere. Free-tier LLM limits
  volatile → limiter + fallback; verify at build time.
- No headless browser (JS-only pages are a documented gap). No DNS-rebinding defence beyond
  redirect re-validation. CloudFront→EC2 hop and secret manager out of scope.
- Appendix B's example shows unreachable company as failure; this build records it as `ok`
  per the FAQ ("a missing hiring page is not a failure") — a one-line switch if needed.
