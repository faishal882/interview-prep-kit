# Plan: Interview Prep Kit — Backend

> Source PRD: `docs/prd-backend.md` (user stories are numbered there). Vocabulary: `CONTEXT.md`. Decisions: `docs/adr/`. Design: `docs/ARCHITECTURE.md`.

## Architectural decisions

Durable decisions that apply across all phases:

- **Language/runtime**: Python 3.12 + FastAPI (ADR-0001). The mandated `npm run evaluate` is a thin wrapper over the Python batch runner; `npm run setup` performs the single documented install step.
- **Pipeline contract**: the pipeline takes (Case, dependencies, progress callback) and returns a Kit plus a research log. It never persists and never imports the web layer. The web API, the job worker and the batch runner all call this one entry point.
- **Responsibility split (ADR-0003)**: the LLM writes prose; Jev (optional) makes typed decisions; code decides schedule allocation, gap detection and evidence grounding. No AI orchestration framework.
- **Credentials**: only `GEMINI_API_KEY` is required (missing → fail fast with `MISSING_CREDENTIALS`). Groq, Jev, a search API and a telemetry endpoint are optional and degrade silently (logged).
- **Kit structure**: exactly Appendix A. Extensions are additive and optional: research log, the brief's hiring-process text, each Question's outline points. `kind` ∈ technical | behavioural | domain; `priority` ∈ must | nice; Question `category` ∈ technical | behavioural | system-design | company-fit; difficulty 1–3; minutes are integers.
- **Requirement**: atomic claim, one priority, verbatim evidence verified against the JD, ids `r1…rn`, cap ≈ 25. Default priority `must`.
- **Item state (ADR-0004)**: every editable item carries origin (generated | user), edited, pinned, revision, order key. Protected = user-written, edited or pinned. Metadata is stripped on export.
- **Kit limits**: ≤ 30 Questions, ≤ 20 Flashcards, ≤ 12 crawled pages, depth ≤ 2, ≤ 3 coverage Passes.
- **Routes** (all under `/api`):
  - Auth: `POST auth/register`, `POST auth/login`, `POST auth/logout`, `GET me`
  - Kits: `POST kits` (202 `{kit_id, job_id}`, or the existing Kit for duplicates), `POST kits/batch`, `GET kits`, `GET|DELETE kits/{id}`, `GET kits/{id}/export`
  - Jobs: `GET jobs/{id}` (status + per-step progress)
  - Items: create/patch/delete under `kits/{id}/{questions|flashcards|requirements|brief|schedule}`; `POST kits/{id}/questions/reorder` (target Category + predecessor)
  - Sections: `POST kits/{id}/sections/{brief|questions:<category>|schedule}/regenerate`
  - Practice: `GET kits/{id}/practice/queue`, `POST kits/{id}/practice/reviews`, `GET kits/{id}/practice/summary`, `POST kits/{id}/practice/check`
  - `GET health`
- **Error envelope** (every non-2xx): `{error: {code, message, details, trace_id}}`; `trace_id` falls back to a request id when telemetry is off.
- **Schema (MongoDB)**: collections `users`, `sessions` (TTL), `kits`, `jobs`, `practice_progress`, `fetch_cache` (TTL). A Kit is one document: input, Kit content with per-item metadata, research log, section revision counters, status. In-memory repositories back the CLI and tests.
- **Auth**: Argon2id; opaque session token stored only as a hash, server-side expiry; httpOnly + Secure + SameSite cookie; origin check on mutating requests; every Kit query filtered by owner; other users' Kits return 404.
- **Jobs (ADR-0002)**: Mongo documents claimed atomically by an in-process worker; heartbeat; stale → requeued once, then failed retryable; one active job per Kit; bounded concurrency (default 2).
- **Third-party boundaries**: Gemini (required) and Groq (optional) behind one structured-generation interface; Jev (optional) behind one typed-decision interface with a mandatory fallback per caller; company sites and Hacker News (Algolia) as untrusted retrieval; a Jev answer overrides only at confidence ≥ 0.7.
- **Security posture**: URL guard strict by default (the CLI opts out explicitly); allowlisted content types, size and time limits; fetched/pasted text framed as data; robots per RFC 9309.
- **Batch contract**: input array of Cases; output `{version, generated_at, kits:[{id, status ok|failed, kit|null, error|null}]}`. `failed` only when no valid Kit could be produced (empty JD, no LLM available, Kit unassemblable, deadline hit before a valid Kit, missing credentials). An unreachable company is `ok` with the failure recorded.

---

## Phase 1: Walking skeleton

**User stories**: 82, 84, 85, 86, 89, 91

### What to build

The thinnest complete path: a repository scaffold with the root commands (`setup`, `test`, `evaluate`), configuration loading, `.env.example`, the Appendix A Kit model with its semantic validator and exported structure schema, and a batch runner that reads a cases file, runs a stub pipeline behind a fake LLM, and writes a correctly-shaped results file. A missing required credential aborts before any work.

### Acceptance criteria

- [ ] From a clean clone, `npm run setup` then `npm run evaluate -- --input <cases> --output <out>` runs with no database and no optional keys
- [ ] Output matches the batch contract, with one entry per Case keyed by id
- [ ] A Case that raises is recorded as `failed` and the run continues
- [ ] The validator rejects duplicate ids, dangling references, wrong schedule length, non-integer minutes, bad difficulty
- [ ] A missing `GEMINI_API_KEY` aborts immediately with `MISSING_CREDENTIALS` (bypassed when a fake LLM is selected for tests)
- [ ] Validator tests pass

---

## Phase 2: Requirement extraction

**User stories**: 21–29, 93, 94

### What to build

The real structured-generation gateway (Gemini; optional Groq fallback) with rate limiting, backoff honouring provider hints, token budgeting and one repair attempt on invalid output. On top of it, requirement extraction: atomic Requirements with verbatim evidence checked in code, stable ids, dedupe, the cap, role metadata that is never guessed, heuristic kind/priority classification with `must` as default, and thin-description detection with an honest warning. The batch now emits real `role` content.

### Acceptance criteria

- [ ] A Requirement whose evidence is not verbatim in the JD is dropped; whitespace and bullet-marker differences are tolerated
- [ ] "React, TypeScript and Node.js; PostgreSQL a plus; Go or Rust" yields separate atomic Requirements, PostgreSQL `nice`, "Go or Rust" as one
- [ ] Responsibility lines stating a competency yield Requirements; pure tasks appear only in responsibilities
- [ ] Unknown company/location/seniority are never invented (`""` / `unspecified`)
- [ ] A two-line JD produces a thin Kit flagged as thin, with no invented Requirements
- [ ] Invalid model JSON triggers exactly one repair attempt, then a recorded step failure
- [ ] Rate-limit responses are retried with backoff and fall over to the fallback provider when configured
- [ ] Extraction, grounding and heuristic-classification tests pass (fake LLM)

---

## Phase 3: Questions and the second pass

**User stories**: 42, 44–52

### What to build

Per-Category question generation with its own instructions, routing from Requirement kind to Category, and gating so empty Categories are skipped rather than padded. The pure coverage checker computes Gaps by set arithmetic; the coverage loop generates only for Gaps and rechecks, up to three Passes, stopping on no gaps, the cap, or no progress, and shipping any remainder honestly listed. Flashcards are generated from must Requirements and technical Questions. Caps apply.

### Acceptance criteria

- [ ] Each Question references at least one existing Requirement id, has difficulty 1–3 and an answer outline
- [ ] Categories with no routed Requirements produce no Questions
- [ ] A fake LLM that initially omits a must Requirement causes a second Pass that generates only for that Gap and closes it
- [ ] A Gap the model never fills stops after the cap or on no progress, and appears in the uncovered list
- [ ] Coverage counts all Requirements as Gaps but the final Pass targets `must` only
- [ ] Coverage checker tests pass, including empty inputs
- [ ] Question and Flashcard caps are enforced

---

## Phase 4: Scheduler

**User stories**: 53–59

### What to build

The pure, deterministic scheduler: weights from difficulty and priority; front-loaded allocation when Questions ≥ days; Review days that repeat the highest-weight Questions at expanding intervals when Questions < days; integer-minute estimates by Category and difficulty; deterministic focus labels; zero-Question and 1-day handling; an overload warning above 180 min/day average. Wire it into the pipeline so batch Kits are complete.

### Acceptance criteria

- [ ] For any inputs, the Schedule has exactly the requested number of days, integer minutes, and only valid Question ids
- [ ] Every Question is scheduled at least once; every covered must Requirement therefore appears
- [ ] When Questions ≥ days, higher-weight Questions never land later than lower-weight ones
- [ ] 1-day and 60-day cases produce valid Schedules (60 days with few Questions uses Review days)
- [ ] Zero Questions yields the requested number of empty days with an explanatory focus
- [ ] Identical inputs yield identical output
- [ ] Property-based and example-based scheduler tests pass

---

## Phase 5: Company research

**User stories**: 30–35, 38–41, 96, 97

### What to build

The safe fetcher (strict-by-default URL guard with redirect re-validation, robots per RFC 9309 with crawl-delay, content-type/size/time limits, per-host rate limiting, backoff, cache), the crawler (priority queue, same registrable domain plus an ATS allowlist one hop, relative links, static HTML, page budget and depth) driven by a heuristic link ranker, page cleaning, page typing, the brief writer, `pages_used`, and the research log recording every skip with a reason. Fixture company sites (buried hiring page, none, 404, timeout) are added as shared test assets. An unreachable company yields an `ok` Kit with a deterministic honest brief.

### Acceptance criteria

- [ ] The crawler finds a hiring page placed at an unpredictable path on the fixture site by following ranked links, without a fixed path list
- [ ] Private, loopback, link-local and metadata addresses are rejected by default, including via redirects; the CLI opt-out permits fixture hosts
- [ ] Disallowed, oversize, wrong-type, 4xx/5xx and timed-out pages are skipped and recorded; the run still completes
- [ ] The brief cites only retrieved pages; with none retrieved it states so without calling the model
- [ ] `pages_used` lists only pages whose text entered a prompt
- [ ] The 404 and timeout fixture sites produce `ok` Kits with the failure in the research log
- [ ] Repeat runs use the cache instead of re-fetching
- [ ] URL-guard, robots and crawler tests pass

---

## Phase 6: Discussion, hiring signals and Jev

**User stories**: 36, 37, 43, 49, 92, 98, 99

### What to build

Public-discussion research (Hacker News via its API, optional search API; skipped and recorded when the company URL is private) and the hiring-signal analyzer whose flags change which Questions are generated (a take-home or system-design round alters the Kit). Then the optional Jev gateway: better classification, link ranking and page typing; verification of claimed Question–Requirement links before Gaps are computed; injection-style text flagged and the page dropped and logged. Every use has a fallback; without a Jev key the pipeline behaves as before.

### Acceptance criteria

- [ ] "Nothing found" and "not queried (reason)" are both recorded honestly and reflected in the brief
- [ ] A fixture site that publishes a take-home + system-design round yields a Kit that differs from one that says nothing
- [ ] With no Jev key, the full pipeline still completes and logs the fallback
- [ ] A Jev answer below 0.7 confidence does not override; disagreements are logged
- [ ] A Question whose claimed link to a Requirement is rejected no longer counts as covering it, and the resulting Gap is filled
- [ ] A fixture page containing "ignore previous instructions…" is dropped and does not influence output
- [ ] Discussion, signal and fallback tests pass

---

## Phase 7: Batch hardening

**User stories**: 83, 86, 87, 88, 90, 91, 92

### What to build

Make the batch command production-worthy: two Cases at a time sharing one provider limiter, a per-Case deadline that returns a valid partial Kit as `ok` with warnings when possible, the exact failure codes and `ok`/`failed` semantics, per-Case `days` honoured, and localhost fixture sites working end to end. Provide a five-Case sample set including the thin JD and the no-hiring-page company.

### Acceptance criteria

- [ ] Five sample Cases complete in under 15 minutes including forced rate-limit retries
- [ ] Each failure code fires in its scenario (`INVALID_INPUT`, `LLM_UNAVAILABLE`, `KIT_INVALID`, `TIMEOUT`, `MISSING_CREDENTIALS`) and one failure never stops the run
- [ ] A partially researched Case is `ok` with gaps recorded
- [ ] Each Case's Schedule length equals its own `days`
- [ ] The command works with no database, no optional keys and no telemetry endpoint
- [ ] Output validates against the batch contract in an automated test

---

## Phase 8: Auth and sessions

**User stories**: 1–7, 100

### What to build

Registration, login, logout and current-user with Argon2id, hashed opaque sessions with server-side expiry, secure cookies, origin checks on mutating requests, login throttling, ownership enforcement, and the uniform error envelope with a reference id. Health endpoint. Mongo repositories with in-memory equivalents.

### Acceptance criteria

- [ ] Unauthenticated requests to protected routes return 401 in the envelope
- [ ] Expired or revoked sessions return 401 with a distinguishable code
- [ ] Logout invalidates the session server-side
- [ ] Another user's resource is indistinguishable from a missing one (404)
- [ ] Repeated failed logins are throttled
- [ ] Mutating requests with a foreign Origin are rejected
- [ ] Auth and ownership tests pass

---

## Phase 9: Kits API and job queue

**User stories**: 8–16, 19, 20, 101, 102

### What to build

Creating a Kit returns 202 with a Kit id and job id (or the existing Kit for a duplicate); a Mongo-backed worker claims jobs, runs the pipeline, writes per-step progress and heartbeats, requeues stale jobs once, and fails them retryable thereafter. Only one active job per Kit; concurrency bounded. Dedupe on the normalised key (including days), `force_new`, failed Kits retried in place. List, get, delete and export (exact structure, metadata stripped).

### Acceptance criteria

- [ ] Creating the same Kit twice returns the existing one; different days creates a new Kit; `force_new` creates anew; a failed Kit is retried, not deduped
- [ ] Progress is observable step by step, including skipped-with-reason and failed
- [ ] Killing the worker mid-run leads to one automatic requeue, then a retryable failure
- [ ] A double trigger yields a single active job
- [ ] The exported Kit validates against the structure schema and contains no item metadata
- [ ] Deleting a Kit removes it and its job/practice data
- [ ] Queue, dedupe and export tests pass

---

## Phase 10: Web batch upload

**User stories**: 17, 18

### What to build

An endpoint accepting a JSON array in the same shape as the CLI cases file (ids optional, server-assigned), capped at 10 entries, that creates one Kit and job per valid entry and returns a per-entry accepted/rejected report.

### Acceptance criteria

- [ ] Valid entries create Kits/jobs; malformed entries are rejected individually with reasons
- [ ] More than 10 entries is rejected as a whole with a clear error
- [ ] Duplicates within the upload and against existing Kits follow the dedupe rules
- [ ] Concurrency stays within the global bound

---

## Phase 11: Editing

**User stories**: 60–63, 70, 72–75

### What to build

Item create/patch/delete for Questions, Flashcards, Requirements, the brief and Schedule days; per-item metadata (origin, edited, pinned, revision, order key); fractional ordering for reorder and cross-Category moves (a move counts as an edit); pinning; revision checks so rapid or concurrent edits never lose data; coverage recomputed after every change with Gaps surfaced (never blocking, never auto-generating); deleted Question ids stripped from the Schedule immediately; the Schedule marked stale when Questions or Requirements change while manual Schedule edits are preserved.

### Acceptance criteria

- [ ] Editing content sets edited; adding sets origin user; pin toggles; reorder within a Category changes only order
- [ ] Two rapid edits to one item both persist; a stale-revision write is rejected with a clear conflict error
- [ ] Deleting a Question removes it from the Schedule at once
- [ ] Deleting the only Question for a must yields a Gap in coverage and no automatic generation
- [ ] Editing a Requirement recomputes coverage and marks the Schedule stale
- [ ] Ordering-key and item-state tests pass

---

## Phase 12: Regeneration

**User stories**: 64–69, 71

### What to build

Section regeneration as jobs: the brief (a proposal when edited or pinned), one Category (replace only unprotected items via a single atomic update that also keeps any item whose revision changed since the job started; exclusion list prevents duplicates; coverage recomputed and gap-filled for that Category's Requirements), and the Schedule (rebuild with a warning that manual edits are replaced).

### Acceptance criteria

- [ ] Regenerating a Category keeps every protected item, including one moved in from another Category
- [ ] An edit made while a regeneration runs survives the commit
- [ ] Regenerated Questions do not duplicate retained ones
- [ ] Other Sections are byte-for-byte unchanged
- [ ] An edited brief yields a proposal that can be accepted or rejected; an untouched brief is replaced directly
- [ ] Rebuilding the Schedule clears the stale flag and reflects current Questions
- [ ] Merge-rule tests cover protected survival, in-flight edits and no-duplicate behaviour

---

## Phase 13: Practice and answer check

**User stories**: 76–81

### What to build

Practice queue ordering by the confidence-weighted prioritizer (unseen before mastered, recency decay, must boost), recording 1–3 confidence reviews, coverage summary overall/per Category/per Requirement, progress stored independently of Kit content so regeneration never wipes it, and the answer check: typed answer versus a Question's outline points, judged per point via Jev with a fallback, returning covered/missing points.

### Acceptance criteria

- [ ] Queue order follows the documented formula; unseen cards precede mastered ones
- [ ] Recording a review updates covered status and the summary
- [ ] Regenerating a Category leaves practice progress for surviving cards intact
- [ ] The answer check returns per-point verdicts, works without a Jev key via the fallback, and states its literal-match limits
- [ ] Prioritizer tests pass

---

## Phase 14: Observability

**User stories**: 103–105

### What to build

Optional tracing, metrics and structured logs: a root span per pipeline run with a child per step, spans for each fetch, LLM call and Jev call with token/latency/retry/rate-limit detail, background jobs linked to the originating request, no-op unless an endpoint is configured, and content-free by default. A local compose profile with a bundled backend for demos.

### Acceptance criteria

- [ ] With no endpoint configured, nothing is exported and behaviour is unchanged, including for the batch command
- [ ] With the local profile running, a batch run shows a trace per Case with steps, fetches, LLM and Jev calls, retries and coverage Passes
- [ ] Spans and logs contain sizes and hashes, never JD or page text, unless explicitly opted in
- [ ] An unreachable telemetry endpoint never slows or fails a run

---

## Phase 15: README and handoff

**User stories**: (brief's README requirements)

### What to build

The README sections the brief demands: overview and stack justification (Python deviation), local setup and the exact batch commands, LLM provider and model, architecture, retrieval approach and sources, step sequencing and responsibilities, generated/edited/pinned state, schedule allocation, the second-pass reasoning, the creative feature, edge-case handling, key decisions, trade-offs and known limitations. Ship the exported structure schema and sample batch input/output.

### Acceptance criteria

- [ ] A reader can go from clean clone to a successful batch run using only the README
- [ ] Every README section the brief lists is present
- [ ] `.env.example` documents every variable and marks which are required
- [ ] Sample cases and sample output are included and validate against the contracts
