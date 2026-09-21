# Plan: Interview Prep Kit — Production Readiness

> Source PRD: `docs/prd-production-readiness.md` (user stories are numbered there). Earlier plans (`plans/backend.md`, `plans/frontend.md`) built the prototype; this plan hardens it. Vocabulary: `CONTEXT.md`.

## Sequencing

Order is by grading impact, then dependency. Phases 1–6 fix what the automated batch run and the builder review will hit. Phases 7–10 make state durable and regeneration real (regeneration needs the repository layer and the model gateway). Phases 11–13 are security and contract. Phases 14–16 are operations, delivery and honest documentation.

**Minimum viable set if time is short:** phases 1, 3, 5, 6, 9, 10 and 16. Phase 10 then runs on the in-memory repository implementation (the interface from phase 7 is still needed), which delivers real regeneration but not durability — say so in the README.

Every phase updates the README and any decision record it touches; phase 16 is the final reconciliation, not the first time documentation is corrected.

## Architectural decisions

Durable decisions that apply across all phases:

- **Repository layer**: one interface per store — users, sessions, Kits, jobs, practice progress, page cache — each with an in-memory and a MongoDB implementation, both run against one shared behavioural contract suite. The batch command and unit tests use in-memory only; the server uses MongoDB.
- **Database guarantees**: expiring indexes on sessions and the page cache; a partial unique index enforcing one active job per Kit; every Kit query filtered by owner; atomic Section merge as a single-document pipeline update.
- **Job model**: jobs are documents `{id, kit_id, user_id, kind, status pending|running|done|failed, steps[], attempts, heartbeat, error, retryable, deadline}`; kinds include generation and each regeneration Section. A worker claims atomically; stale jobs are requeued once, then fail retryable; a recovery loop runs continuously.
- **Settings**: one validated settings object loaded at startup. Production refuses to start without a reachable database, a model key, and an allowed-origin list; the scripted fake model is only reachable through an explicit setting; the unused signing secret is removed.
- **Error envelope** (unchanged shape): `{error: {code, message, details, trace_id}}`; `trace_id` equals the request id that appears in logs; unexpected errors return a generic message with no exception type.
- **Fetch semantics**: every URL and every redirect hop validated before it is requested (strict by default; the batch command opts out explicitly); refuse anything not globally routable; production allows ports 80 and 443 only; robots per RFC 9309 (missing = allow, server error or unreachable = disallow) with crawl delay; streamed size cap 2 MB; content-type allowlist; per-host rate limit safe under concurrency; page cache bounded and expiring.
- **Crawl scope**: public-suffix-aware registrable domain plus an exact-domain allowlist of hiring platforms, one hop; normalised URLs; budget counts pages retrieved; bounded links per page.
- **Ordering**: one correct fractional-index algorithm implemented in Python and TypeScript from shared test vectors; keys are always unique, strictly between neighbours, and rebalanced when they grow long.
- **Item schemas**: typed create and patch schemas per collection, unknown fields rejected, ids assigned by the server only, references validated; revision conflicts always enforced; the Schedule is marked stale only for changes that can affect it.
- **Auth**: registration closed by default; users created by an operator command; reopening is an explicit setting; secure cookie flags by environment; per-user quotas (defaults: 10 Kits/day, 50 stored Kits, 1 concurrent generation — adjustable settings); throttle keyed on client address plus account with a bounded store; Argon2id only, off the request loop, password length bounded.
- **Limits** (adjustable settings): JD 30,000 characters; request body 1 MB; batch entries 10; days 1–60 everywhere.
- **Deadlines** (adjustable settings): per-Step 60 s, overall generation 180 s — below the batch's 240 s per-case budget; on expiry return a valid partial Kit where possible.
- **Model gateway**: one shared pooled client, key in a header, a request and token rate limiter shared by all concurrent runs, retries only for provider conditions (429, 5xx, network) honouring hints, truncated output detected and retried smaller, deep schema validation, repair attempt under the same retry protection, usage and latency recorded.
- **Observability**: structured JSON logs always on with request id, job id and trace id; every unexpected error logged with stack trace; liveness and readiness endpoints (readiness checks database and model key); OpenTelemetry optional, off by default, content-free by default.
- **Delivery topology** (from `docs/ARCHITECTURE.md`): Vercel web → CloudFront (HTTPS only) → one EC2 running the API and MongoDB on a durable volume with daily snapshots; Terraform with local state; `.env` on the instance; manual deploy and rollback commands; no hosted CI, a single local `verify` command instead.
- **Contract**: every endpoint declares a typed response; one committed OpenAPI document is the single source; generated frontend types are used throughout; a test enumerates operations and fails on any untyped response or drift.
- **Unchanged**: the Kit structure (Appendix A), the batch command and its output shape, the unreachable-company-is-`ok` rule, and the batch command needing no database.

---

## Phase 1: Trustworthy crawler

**User stories**: 23–33

### What to build

Rebuild the fetcher and crawler so they behave as the brief and the PRD require. Redirects are followed manually up to a small limit with each hop validated before it is requested; the body is streamed and cut off at the size limit; `robots.txt` is actually fetched per host (cached with expiry) with the specified semantics and crawl delay; the URL guard refuses anything not globally routable and, in production, non-standard ports; the per-host limiter holds under concurrency; the page cache is bounded and expiring. The crawler scopes by public-suffix domain and an exact-domain hiring-platform allowlist, normalises and de-duplicates URLs, counts retrieved pages against the budget and bounds links per page. The fixture sites are extended with redirect, robots, oversize and look-alike-domain cases.

### Acceptance criteria

- [x] A URL that redirects (http→https, host→www, path→path/) returns the final page's content
- [x] A redirect to a private or loopback address is refused before any request to it is made
- [x] A disallowed path is not fetched; a missing `robots.txt` allows crawling; a server-error `robots.txt` disallows it; crawl delay is honoured
- [x] A body larger than the limit is aborted mid-stream, not after full download
- [x] `greenhouse.io.evil.example` is not treated as a hiring platform; a `.co.uk` company does not lead the crawl to other `.co.uk` sites
- [x] Non-globally-routable addresses (private, loopback, link-local, shared-address, IPv4-mapped) are refused; production refuses non-standard ports
- [x] Two concurrent callers to one host still respect the per-host rate limit
- [x] Trivially different URLs are fetched once; a page with thousands of links adds a bounded number to the queue
- [x] Cached pages expire and the cache never exceeds its bound
- [x] Fetcher, robots, guard and crawler tests pass; the batch command still completes on the fixture sites

---

## Phase 2: Research enrichment

**User stories**: 34, 35, 36

### What to build

Make the research use what it finds. The company name comes from the description, then the company's site (declared site name or title), then the domain; the discussion search uses it. Hiring signals are computed only from pages typed as hiring-related, using stricter patterns, so an ordinary page cannot trigger a false take-home or coding round. The research log records which page was judged to be the hiring page, or that none was.

### Acceptance criteria

- [x] A description with no company name yields the site's declared name in the Kit and in the discussion query
- [x] A fixture "about" page mentioning "coding" or "values" does not set a hiring signal; a fixture hiring page describing a take-home does
- [x] The research log names the hiring page found, or records that none exists
- [x] The no-hiring-page fixture site produces an honest Kit with no hiring-specific Questions
- [x] Enrichment tests pass

---

## Phase 3: Pipeline and batch robustness

**User stories**: 10, 11, 37, 38, 39, 40, 41

### What to build

Harden the pipeline boundary and the batch command. Days validated to 1–60 with a clear error (0 is no longer silently 5; negatives no longer yield an invalid Kit); duplicate or missing case ids in a batch file handled explicitly; all model output sanitised uniformly (out-of-range difficulty clamped, items lacking an outline or Requirement reference dropped) so one bad value never fails the Kit; over-long descriptions chunked or clearly warned; every prompt frames pasted and fetched text as delimited data and page text gets a broader instruction-style check; per-Step and overall deadlines with a valid partial Kit returned as `ok` with warnings where possible; the batch file validated up front and output written atomically.

### Acceptance criteria

- [x] `days` of 0, −3 and 61 fail that Case with `INVALID_INPUT`; 1 and 60 succeed
- [x] Duplicate case ids are rejected or made unique with a recorded note; the output stays keyed one-to-one
- [x] A model item with difficulty 99 or no outline is clamped or dropped and the Kit still validates
- [x] A description beyond the model's limit is handled with no silently ignored tail
- [x] A hung provider triggers the per-Step deadline; the Case returns a valid partial Kit (`ok` with warnings) or `TIMEOUT` when none is possible
- [x] A malformed cases file fails cleanly before any work; an interrupted run never leaves a half-written output file
- [x] Sanitisation, deadline and batch tests pass; five sample Cases still finish within fifteen minutes

---

## Phase 4: Scheduler alignment

**User stories**: 42

### What to build

Bring the scheduler in line with its specification: balance minutes across days as well as ordering by weight, space Review-day repeats at expanding intervals, and remove the dead logic. Behaviour required by the brief stays: exactly the requested number of days, integer minutes, valid ids, harder and higher-priority material earlier, every Question scheduled.

### Acceptance criteria

- [x] Day totals differ by no more than the largest single Question's minutes where the Question count allows
- [x] Review days repeat the highest-weight Questions at expanding intervals
- [x] All existing scheduler property tests still pass; new properties cover minute balance and review spacing
- [x] 1-day, 60-day and zero-Question cases still produce valid Schedules

---

## Phase 5: Correct ordering

**User stories**: 50, 51

### What to build

Replace the fractional-index algorithm with a correct one, implemented in Python and TypeScript from shared test vectors: keys always unique and strictly between neighbours for inserts at the front, back and between; rebalancing when keys grow beyond a length limit; existing stored keys migrated or accepted.

### Acceptance criteria

- [x] Property tests over random insert sequences (front, back, between) show strict ordering and uniqueness in both languages
- [x] Both languages produce identical keys for the shared vectors
- [x] 1,000 repeated front-inserts and 1,000 repeated bisections stay valid and bounded in length
- [x] Existing kits with old keys still sort and can be reordered
- [x] Drag-reorder, the Move menu and cross-Category moves keep order across reload

---

## Phase 6: Model gateway

**User stories**: 64, 66, 67, 68, 69, 70, 71

### What to build

A production model gateway: one pooled client with the key in a header; a request and token rate limiter shared by every concurrent run; retries only for genuine provider conditions (429, 5xx, network) honouring hints; truncated output detected and retried smaller; deep schema validation with the repair attempt under the same retry protection; usage and latency recorded per call. The scripted fake model becomes available only through an explicit setting and never as an implicit fallback.

### Acceptance criteria

- [x] Programming errors fail immediately with no sleeping or retry
- [x] Rate-limit responses are retried with the provider's hint; server errors with backoff; both bounded
- [x] Two concurrent runs together stay within the configured request and token rates
- [x] A truncated response triggers one smaller retry; a schema-invalid response gets a repair attempt that is itself protected by retry
- [x] The key never appears in any logged address or error
- [x] With no key and no explicit fake setting, startup (server) and the batch command fail fast with `MISSING_CREDENTIALS`
- [x] Gateway tests pass with the scripted provider

---

## Phase 7: Durable state

**User stories**: 1, 2, 3, 4, 5, 6, 7, 78

### What to build

Introduce the repository layer and move the server onto MongoDB: users, sessions, Kits, jobs and practice progress behind repository interfaces with in-memory and MongoDB implementations, one shared contract suite, index creation at startup, expiring sessions and page cache, connectivity verification, and a single validated settings object whose production checks refuse to start on missing or invalid configuration (database, model key, allowed origins) naming every problem. The batch command keeps using in-memory only. This is the largest phase; if needed, deliver users and sessions first, then Kits and practice.

### Acceptance criteria

- [x] Restarting the server preserves accounts, sessions, Kits, edits and practice progress
- [x] The same repository contract suite passes against both in-memory and MongoDB implementations
- [x] Expired sessions and cache entries are removed automatically
- [x] Production startup fails with one message listing every missing or invalid setting; an unreachable database also fails startup
- [x] `npm run evaluate` still works with no database and no extra setup
- [x] The local composition provides the database; the README states how to run against it

---

## Phase 8: Durable job queue

**User stories**: 8, 9, 12, 13, 14

### What to build

Replace fire-and-forget background execution with the database-backed queue from the decision record: atomic claim, heartbeat, worker loop with enforced concurrency, per-Step and overall deadlines, cancellation, a recovery loop that requeues a stale job once then fails it retryable, one active job per Kit, and per-user concurrency limits. Retry reuses cached pages.

### Acceptance criteria

- [x] With the limit at 2, a third simultaneous generation waits rather than running
- [x] Killing the worker mid-run leads to one automatic requeue, then a retryable failure — verified against the real database and without a server restart
- [x] A hung job is stopped by its deadline and marked accordingly
- [x] A double trigger for one Kit yields one active job; a second concurrent generation by one user is queued or refused per the per-user limit
- [x] A retried generation does not re-fetch pages already cached
- [x] Queue tests pass

---

## Phase 9: Validated editing and integrity

**User stories**: 43, 44, 45, 46, 47, 48, 49

### What to build

Make every write safe. Typed create and patch schemas per collection with unknown fields rejected and values validated (Category, difficulty range, priority and kind, existing Requirement references); server-assigned ids; revision conflicts always enforced; deleting a Requirement prunes it from every Question, Flashcard and gap list and flags Questions left without a Requirement; the stale-Schedule flag set only for changes that can affect the Schedule; Schedule minutes recomputed on every Schedule mutation; brief metadata unified with other item metadata. The export validates the Kit before serving, refuses an invalid one, and strips all internal metadata.

### Acceptance criteria

- [x] A patch that sets an unknown field, a bad Category, difficulty 999, a missing Requirement reference or a new `id` is rejected with a clear error and changes nothing
- [x] A request with an out-of-date revision is rejected with a conflict
- [x] Deleting a Requirement leaves no dangling reference anywhere and flags any Question left uncovered
- [x] Pinning, reordering or editing a Flashcard does not raise the stale-Schedule banner; adding, removing or materially changing a Question or Requirement does
- [x] After deleting a Question or moving one between days, each day's minutes equal the sum of its Questions' minutes
- [x] The export of a valid Kit contains no internal metadata; an invalid Kit yields a clear error, not a payload
- [x] Integrity, schema and export tests pass

---

## Phase 10: Real regeneration

**User stories**: 15–22

### What to build

Regeneration that actually regenerates, reusing the pipeline's own steps: the brief written from the retrieved pages (a Proposal when the current brief is edited or pinned), a Category regenerated by the per-Category question generator with hiring signals and an exclusion list of kept prompts, and targeted generation for one Requirement. Category regeneration commits as one atomic document update that keeps protected items and any item whose revision changed since the job started, then recomputes coverage. Each regeneration is a real job with real progress and outcome; failure leaves the Kit untouched. Placeholder generators are deleted.

### Acceptance criteria

- [x] Regenerating a Category calls the model, replaces only unprotected items, and every new Question has a genuine prompt and outline
- [x] A protected item (user-written, edited, pinned, or moved in) always survives; an edit made mid-run survives the commit (tested with a concurrent edit)
- [x] Regenerated Questions do not duplicate retained ones
- [x] An edited brief yields a genuine Proposal that can be accepted or rejected; an untouched brief is replaced directly
- [x] "Generate a Question for this" adds Question(s) covering exactly that Requirement and changes nothing else
- [x] A provider failure leaves the Kit byte-for-byte unchanged and the job `failed` with a message
- [x] Coverage and Gaps are recomputed after every regeneration
- [x] No placeholder text such as "(refreshed)" or "Regenerated … question" remains in the code
- [x] Regeneration tests pass with the scripted model

---

## Phase 11: Auth and abuse resistance

**User stories**: 52, 53, 54, 55, 56, 57, 58, 61, 62, 63

### What to build

Harden authentication and the API edge: cookie flags by environment (secure in production); registration closed by default with an operator command to create a user and an explicit setting to reopen; per-user quotas; login throttle keyed on client address plus account, bounded and expiring; Argon2id only, run off the request loop, with password length bounds; mutating requests in production require an allowed origin, and startup fails without the allowed-origin setting; request bodies, descriptions, batch entries, URLs and answers bounded; unexpected errors return a generic message with the reference id; internal fields (owner id, dedupe hash, heartbeat, attempts) removed from responses.

### Acceptance criteria

- [x] In production the session cookie is `Secure` and `HttpOnly`; in development it is not
- [x] Registration returns a clear "closed" response by default; the operator command creates a working user; the reopening setting works
- [x] The eleventh Kit created in a day, the 51st stored Kit, and a second concurrent generation are each refused with a clear error under the default quotas
- [x] Repeated wrong-password attempts for one account from one address are throttled; wrong-email guesses from elsewhere do not lock out the real user; the throttle store is bounded
- [x] A 1 MB password or an oversized body/description is rejected without heavy work
- [x] A mutating request without an allowed origin is rejected in production
- [x] A forced server error returns the generic message and reference id, with no exception type
- [x] Kit and job responses contain no internal fields
- [x] Security tests pass

---

## Phase 12: Frontend hardening

**User stories**: 59, 60, 65, 90 (frontend part)

### What to build

The frontend security pass: the post-login redirect accepts only in-app paths (rejecting absolute and protocol-relative URLs); security headers (content security policy, framing protection, referrer policy, content-type sniffing protection, permissions policy) on every response; the dead proxy handler removed; the framework and CSS tooling upgraded to versions without known high-severity advisories.

### Acceptance criteria

- [x] `returnTo` values such as an absolute URL or `//host` are ignored and the user lands on the default page
- [x] Every response carries the defined security headers, and the app still works under the content security policy
- [x] The dependency audit reports no high-severity advisory in production dependencies
- [x] No unused proxy handler remains; unauthenticated navigation and the e2e journey still pass
- [x] Redirect and header tests pass

---

## Phase 13: Typed API contract

**User stories**: 87, 88

### What to build

Give every endpoint a typed response model so the OpenAPI document describes real shapes; make it the single committed source (remove the duplicate copy); generate real frontend types from it; replace hand-written response types in the UI; keep the drift check, now comparing schemas rather than path lists.

### Acceptance criteria

- [x] A test enumerates every OpenAPI operation and fails if any response is untyped
- [x] Only one committed OpenAPI document exists; the frontend generates types from it
- [x] The UI compiles against generated types with no hand-written response duplicates
- [x] The drift check fails when a response shape changes without regenerating types
- [x] Frontend type check, tests and build pass

---

## Phase 14: Observability

**User stories**: 72, 73, 74, 75, 76, 77

### What to build

Structured JSON logging always on, with request, job and trace ids; every unexpected error logged with a stack trace; the error envelope's reference id equal to the request id in logs; liveness and readiness endpoints (readiness verifies the database and the model key); real, optional OpenTelemetry — a trace per generation with spans for Steps, fetches and model calls, plus metrics for jobs, tokens, rate-limit hits and crawl outcomes — off by default, content-free by default, never slowing or failing a run. The local composition keeps the demo backend.

### Acceptance criteria

- [x] The reference id in an error response appears in a log line for the same request
- [x] A forced 500 produces a logged stack trace and a generic response
- [x] Readiness fails when the database is down or the key is missing; liveness stays up
- [x] With telemetry off nothing is exported and behaviour is unchanged, including for the batch command
- [x] With the local profile on, a batch run shows a trace per Case with Steps, fetches and model calls, retries and rate-limit waits
- [x] Spans and logs contain sizes and hashes, never description or page text, unless explicitly enabled
- [x] An unreachable telemetry endpoint never slows or fails a run

---

## Phase 15: Delivery

**User stories**: 79–86, 65 (audit gate)

### What to build

Everything needed to ship: a container image for the API and a production composition of API and database; Terraform for the topology in the decisions (network, instance and address, HTTPS front door, database volume with daily snapshots, budget alarm); deploy and rollback commands; secrets kept on the instance only and documented; one `verify` command running lint, type checks, all tests, the drift check and dependency audits; locked and pinned Python dependencies; and a runbook covering deploy, rollback, backup, restore, rotating the model key, creating a user and reading logs.

### Acceptance criteria

- [ ] The image builds from a clean checkout and the production composition starts, passes readiness, and serves the API
- [ ] Terraform validates and plans from a clean checkout; state and secrets are not in the repository
- [ ] A deploy and a rollback each complete with one command; rollback restores the previous release
- [ ] A snapshot restore procedure is documented and has been exercised once
- [ ] `verify` passes from a clean checkout and fails on a lint, type, test, drift or high-severity audit problem
- [ ] A clean install from the lockfile reproduces the tested dependency set
- [ ] The runbook exists and each command in it has been run

---

## Phase 16: Honest documentation and cleanup

**User stories**: 89, 90

### What to build

Final reconciliation: the README, architecture document and decision records describe exactly what is built, including remaining limitations (single instance, plaintext hop from the HTTPS front door, DNS-rebinding window, no hosted CI). A new decision record covers closed registration with operator-provisioned users; the queue and regeneration records are reconciled with the implementation. Remaining dead or misleading code, unused settings and duplicate files are removed and ignore rules corrected.

### Acceptance criteria

- [ ] Every README claim about persistence, jobs, regeneration, security and observability is true of the code
- [ ] Known limitations are listed plainly
- [ ] The decision records match the implementation; the new registration record exists
- [ ] No unused settings, placeholder generators, dead handlers or duplicated contract files remain
- [ ] A reader can go from a clean clone to a running, verified system using only the README and the runbook
