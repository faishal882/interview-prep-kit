# PRD: Interview Prep Kit — Production Readiness

Scope: hardening the existing backend and frontend so the system is durable, honest about what it does, safe to expose to the internet, observable, and deployable. Vocabulary follows `CONTEXT.md`. This PRD does not add product features; it makes the features described in `docs/prd-backend.md` and `docs/prd-frontend.md` actually true in production. Findings come from a full audit of the repository (see Further Notes for the evidence base).

## Problem Statement

The system works as a demonstration but not as a service. Everything the server knows — users, sessions, Kits, jobs, practice progress — lives in process memory, so a restart erases all of it and a second worker would see none of it. Several features present themselves as working but are not: regenerating a Section does not call the model and instead inserts placeholder text; the crawler claims to respect `robots.txt` but never reads it, and fails to follow ordinary redirects, so many real company sites yield no content at all. Drag-reordering can silently corrupt ordering because the ordering algorithm produces invalid keys. The API accepts arbitrary data for edits, so a single request can corrupt a Kit and the export will serve it anyway.

On the security side, the session cookie is never marked secure, registration is open to anyone with no quotas (so anyone can burn the model quota and use the crawler as a proxy), the login redirect can be pointed at another site, the fetcher validates redirects only after the request has already been made, and a missing model key silently switches the production server to a fake model. There is no logging at all, no readiness signal, no telemetry beyond a stub, no container image, no deployment definition, no quality gates, and the README describes a database-backed, fully working system that the code does not implement.

For a candidate this means lost work and a "regenerate" that produces nonsense. For an assessor it means a submission whose behaviour and documentation disagree. For an operator it means a service that cannot be deployed, watched, or trusted with the open internet.

## Solution

A hardening programme in five workstreams, in priority order:

1. **Correctness.** Regeneration really regenerates (with the protected-item guarantees already specified). The crawler follows redirects, honours `robots.txt`, validates every hop before requesting it, caps downloads as they stream, and stays within the company's own scope. Ordering is replaced with a correct algorithm shared by backend and frontend. Every edit is validated against a typed schema, references stay consistent, and exports are validated before they are served.
2. **Durability.** A real database backs users, sessions, Kits, jobs and practice progress. Generation runs through a durable job queue with enforced concurrency, deadlines, heartbeats and restart recovery.
3. **Security.** Secure cookies, closed registration with a documented way to provision users, per-user quotas, fail-closed origin checks, validated redirects, security headers, bounded inputs, and fail-fast configuration so misconfiguration can never silently degrade to something unsafe.
4. **Operations.** Structured logging with correlation ids, real (optional) telemetry, liveness and readiness checks, container images, an infrastructure definition, backups, quality gates, and a runbook.
5. **Contract and honesty.** Every endpoint has a typed response so the generated frontend types are real; the README, ADRs and architecture document describe exactly what is built.

## User Stories

### Durability and restart safety
1. As a candidate, I want my account, Kits, edits and practice progress to survive a server restart, so that a deploy never costs me work.
2. As a candidate, I want to stay signed in across a server restart until my session expires, so that a deploy does not log me out.
3. As an operator, I want all state stored in a real database, so that the service can be restarted, redeployed and inspected without data loss.
4. As an operator, I want the server to refuse to start in production when the database is unreachable or unconfigured, so that it never quietly runs on memory.
5. As an operator, I want expired sessions and stale cache entries removed automatically, so that storage and memory do not grow without bound.
6. As a developer, I want the same behavioural test suite to run against the in-memory and the database implementations of every store, so that the two cannot diverge.
7. As an assessor, I want the batch command to keep running with no database and no setup beyond the documented install step, so that evaluation stays simple.

### Generation jobs
8. As a candidate, I want a generation interrupted by a restart to resume by being requeued once, and then fail as retryable, so that a deploy does not strand my Kit in "generating" forever.
9. As an operator, I want the number of concurrent generations enforced, not merely reported, so that a burst cannot exhaust the model quota.
10. As an operator, I want a per-Step and an overall deadline on every generation, so that a hung provider or site cannot hold a worker indefinitely.
11. As a candidate, I want a generation that hits its deadline to keep whatever valid partial result exists and say so, so that slowness does not cost me everything.
12. As an operator, I want at most one active generation per Kit and per-user limits on concurrent generations, so that one user cannot monopolise capacity.
13. As a candidate, I want a generation that failed halfway to be retryable without re-fetching pages it already retrieved, so that a retry is fast.
14. As an operator, I want stuck or lost jobs detected and recovered continuously, not only at startup, so that a single lost worker does not need a restart to heal.

### Regeneration that is real
15. As a candidate, I want regenerating the brief to produce a genuinely new brief written from the retrieved company pages, so that "regenerate" means something.
16. As a candidate, I want regenerating a Category to produce new Questions from the model, using the Category's own instructions, the hiring signals and the Requirements routed to it, so that it is as good as the original generation.
17. As a candidate, I want regenerated Questions not to duplicate ones I kept, so that the Category stays coherent.
18. As a candidate, I want anything I wrote, edited, moved or pinned to survive a Category regeneration, and an edit I make while it runs to survive its completion, so that timing never costs me work.
19. As a candidate, I want an edited or pinned brief to yield a genuine Proposal I can accept or reject, so that I keep control of single blocks.
20. As a candidate, I want "Generate a Question for this" on a Gap to produce a real Question that covers exactly that Requirement, so that I can close Gaps individually.
21. As a candidate, I want a regeneration that fails to leave my Kit exactly as it was, with a clear message, so that failure is safe.
22. As a candidate, I want every regeneration to report honest job progress and outcome, so that the interface reflects what actually happened.

### Company research
23. As a candidate, I want the crawler to follow redirects (for example from an http address to https, or to a www host), so that ordinary company sites yield content.
24. As a candidate, I want the crawler to fetch and obey each site's `robots.txt` (allowing everything on a missing file, treating an unreachable or erroring file as disallowed), and to honour its crawl delay, so that the crawler is a good citizen.
25. As an operator, I want every URL, including each redirect hop, validated before it is requested, so that the service cannot be tricked into contacting internal systems.
26. As an operator, I want downloads cut off as they stream once they exceed the size limit, so that a hostile page cannot exhaust memory.
27. As an operator, I want addresses in non-public ranges (including shared-address and IPv4-mapped forms) refused in production, and only standard web ports allowed, so that the guard has no obvious gaps.
28. As a candidate, I want the crawl to stay on the company's own domain, using a proper public-suffix rule, so that a `.co.uk` company does not lead the crawler to unrelated companies.
29. As an operator, I want third-party hiring platforms recognised by their exact domain (never a substring match), so that a look-alike domain cannot pass the allowlist.
30. As a candidate, I want the crawl budget to count pages retrieved, and duplicate or trivially different addresses treated as one, so that the budget is spent on distinct pages.
31. As an operator, I want the number of links taken from any single page bounded, so that a hostile page cannot flood the crawl queue.
32. As an operator, I want per-host rate limiting to hold even when several generations run at once, so that concurrency cannot turn the crawler into a flood.
33. As an operator, I want cached pages to expire and the cache to be bounded, so that stale content is never served forever and memory stays flat.
34. As a candidate, I want the company name taken from the description or, failing that, from the company's own site, so that the Kit and the discussion search use the real name rather than a hostname.
35. As a candidate, I want hiring-process signals derived only from pages that actually describe hiring, using stricter patterns, so that an ordinary "about" page does not falsely claim a take-home or coding round.
36. As a candidate, I want the research log to record which page was identified as the hiring page, or that none was, so that the reasoning is visible.

### Pipeline robustness
37. As an assessor, I want the number of days validated everywhere the pipeline runs (1 to 60) with a clear error, so that `0` is not silently changed to 5 and a negative number does not produce an invalid Kit.
38. As an assessor, I want duplicate case ids in a batch file rejected or made unique with a note, so that results stay keyed unambiguously.
39. As a candidate, I want model output sanitised uniformly — out-of-range difficulty clamped, items without an outline or Requirement reference dropped — so that one bad value never fails an otherwise good Kit.
40. As a candidate, I want a description longer than the model can take to be handled explicitly (chunked or clearly warned), so that Requirements at the end are never silently ignored.
41. As an operator, I want every prompt to frame fetched and pasted text as delimited data, and page text checked for instruction-style content more thoroughly, so that hostile text has less influence.
42. As a candidate, I want the Schedule to balance minutes across days as well as ordering by priority, and Review days to space repeats at expanding intervals as specified, so that it matches its documented behaviour.
43. As a candidate, I want the Schedule's minutes to stay correct after I delete a Question or move one between days, so that the totals never lie.

### Data integrity in editing
44. As a candidate, I want every create and edit validated against a typed schema for that item, with unknown fields rejected and values checked (Category, difficulty range, Requirement priority and kind, existing Requirement references), so that a malformed request cannot corrupt my Kit.
45. As a candidate, I want item ids assigned only by the server, so that a request cannot collide with or overwrite another item.
46. As a candidate, I want deleting a Requirement to remove it from every Question, Flashcard and Gap list that referenced it, and to flag any Question left with no Requirement, so that references never dangle.
47. As a candidate, I want the stale-Schedule banner to appear only when a change can actually affect the Schedule (Questions or Requirements added, removed or materially changed), not when I pin an item, reorder, or edit a Flashcard.
48. As a candidate, I want a request with an out-of-date revision to be rejected with a clear conflict, so that concurrent edits never silently overwrite each other.
49. As a candidate, I want the export to be validated before it is served, to contain only the agreed structure plus documented extensions, and never internal metadata, so that what I download is exactly what was promised.
50. As a candidate, I want reordering and moving Questions to always produce valid, unique, correctly sorted order keys no matter how many times I insert at the front, the back or between two neighbours, so that drag-and-drop never scrambles my list.
51. As a candidate, I want the backend and frontend to compute identical order keys, so that an instant local reorder matches what the server stores.

### Authentication and abuse resistance
52. As an operator, I want the session cookie marked secure in production and its flags driven by environment, so that sessions cannot travel over plain connections.
53. As an operator, I want registration closed by default, with a documented command to create a user, so that only intended people can use the service and I can still onboard someone.
54. As an operator, I want per-user limits on Kits created per day, stored Kits, and concurrent generations, so that no single account can exhaust the model quota or the crawler.
55. As an operator, I want login throttling keyed on the client address and account together, with a bounded store, so that an attacker cannot lock a real user out by guessing their email, and the throttle store cannot be used to exhaust memory.
56. As an operator, I want password hashing performed off the request loop and password length bounded, so that login and registration cannot stall the server or be used for resource exhaustion.
57. As an operator, I want a single strong password-hashing scheme with no silent weaker fallback, so that a missing library can never downgrade security.
58. As an operator, I want mutating requests in production to be rejected unless they carry an allowed origin, and the server to refuse to start in production without the allowed-origin setting, so that cross-site requests fail closed.
59. As a candidate, I want the post-login redirect to accept only paths within the app, so that a crafted link cannot send me to another site after I sign in.
60. As an operator, I want security headers (content security policy, framing protection, referrer policy, content-type sniffing protection) on every web response, so that common browser attacks are mitigated.
61. As an operator, I want request bodies, job descriptions, batch entries, URLs and answer text bounded, so that no single request can consume unbounded memory or model tokens.
62. As an operator, I want unexpected errors to return a generic message with a reference id and never the exception type or internals, so that failures do not leak implementation details.
63. As an operator, I want API responses to omit internal fields (owner id, dedupe hash, worker heartbeat), so that clients see only what they need.
64. As an operator, I want a missing or invalid model key in production to stop the server at startup, and the scripted fake model to be available only through an explicit setting, so that production can never quietly serve fake Kits.
65. As an operator, I want the frontend and backend dependency trees free of known high-severity advisories at release time, so that shipped software is not knowingly vulnerable.

### Model gateway
66. As an operator, I want a single shared connection pool and the model key sent in a request header rather than the address, so that the key never appears in logs and connections are reused.
67. As an operator, I want a request-rate and token-rate limiter shared across all concurrent generations, so that the free-tier quota is respected by construction rather than by retry storms.
68. As an operator, I want retries only for genuine provider conditions (rate limit, server error, network failure), honouring the provider's retry hints, so that programming errors fail fast instead of sleeping and retrying.
69. As a candidate, I want a response cut off by the output limit to be detected and retried with a smaller request, so that truncated JSON does not fail my Kit.
70. As an operator, I want model output validated deeply against its schema (types, not only top-level keys), and the repair attempt to enjoy the same retry protection as the first call, so that malformed output is handled uniformly.
71. As an operator, I want token usage and latency recorded per call, so that quota consumption is visible.

### Observability and operations
72. As an operator, I want structured logs for every request and every generation Step, carrying a request id, job id and (when telemetry is on) trace id, so that one failure can be followed end to end.
73. As an operator, I want every unexpected error logged with its stack trace, so that failures are never invisible.
74. As a candidate, I want the reference id shown in an error to match the id in the server's logs, so that a report can be traced.
75. As an operator, I want a liveness check and a readiness check that verifies the database is reachable and the model key present, so that a load balancer and a deploy script can trust them.
76. As a developer, I want real optional telemetry — a trace per generation with spans for Steps, fetches and model calls, and metrics for jobs, tokens, rate-limit hits and crawl outcomes — that is off unless configured and never slows or fails a run, so that I can see how the pipeline behaves.
77. As a developer, I want telemetry to record sizes and hashes rather than description or page text unless explicitly enabled locally, so that user content is not leaked.
78. As an operator, I want configuration loaded and validated once at startup with a clear error naming every missing or invalid setting, so that a bad deploy fails immediately and explains itself.

### Deployment and delivery
79. As an operator, I want a container image for the API and a production composition of the API and database, so that deployment is repeatable.
80. As an operator, I want the infrastructure defined as code (network, instance, address, HTTPS front door, budget alarm) and reproducible from a clean checkout, so that the environment can be rebuilt.
81. As an operator, I want the database on durable storage with automated daily backups and a documented restore procedure, so that data can be recovered.
82. As an operator, I want a one-command deploy and a one-command rollback to the previous release, so that a bad release is cheap to undo.
83. As an operator, I want secrets kept out of the repository, out of infrastructure state and out of images, and documented, so that leaking the repository leaks nothing sensitive.
84. As a developer, I want a single verification command that runs formatting/lint, type checks, all tests, the OpenAPI drift check and dependency audits, so that quality is enforced before every release.
85. As a developer, I want Python dependencies locked and pinned, so that a clean install is reproducible.
86. As an operator, I want a short runbook covering deploy, rollback, backup and restore, rotating the model key, creating a user, and reading logs, so that operating the service does not depend on tribal knowledge.

### Contract and documentation
87. As a frontend developer, I want every endpoint to declare a typed response, so that the generated types describe the real shapes.
88. As a frontend developer, I want the UI to use the generated types instead of hand-written duplicates, and a single committed OpenAPI document as the source, so that drift is impossible to miss.
89. As a reviewer, I want the README, architecture document and decision records to describe exactly what is built — including any remaining limitation — so that documentation can be trusted.
90. As a reviewer, I want unused or misleading code (placeholder generators, dead proxy handlers, unused settings, disabled logic) removed, so that what remains is what runs.

## Implementation Decisions

### Modules (deep modules with small, stable interfaces)

- **Persistence layer.** One repository interface per store — users, sessions, Kits, jobs, practice progress, page cache — each with an in-memory and a database implementation. Interface changes are small and stable: get/put/update by id, plus a few purpose-built operations (claim next job, atomically merge a Section, list Kits for a user). Database-level guarantees carry the correctness: expiring sessions and cache entries, uniqueness for "one active job per Kit", ownership filters on every Kit query. The startup routine creates indexes and verifies connectivity. The batch command uses only in-memory repositories.
- **Session store.** Sessions live in the database, keyed by a hash of an opaque random token, with server-side expiry. The unused signing secret is removed.
- **Job queue and worker.** Jobs are documents claimed atomically; a worker loop with a configured concurrency limit executes them, records per-Step progress and a heartbeat, enforces per-Step and overall deadlines, and cancels cleanly. A recovery loop (not only startup) requeues a stale job once, then fails it as retryable. Per-user concurrency and daily limits are checked before enqueueing. This replaces the current fire-and-forget background execution and realises the earlier decision to use a database-backed queue.
- **Regeneration service.** Reuses the pipeline's own steps (brief writer, per-Category question generator, targeted generation, scheduler) rather than separate placeholder logic. Commits Category regeneration as a single atomic document update that keeps protected items and any item whose revision changed since the job began. Brief regeneration on an edited or pinned brief stores a Proposal. Every regeneration is a real job with real progress and a real outcome; a failure leaves the Kit untouched.
- **Safe fetcher.** Follows redirects manually up to a small limit, validating each hop before requesting it; streams the body and aborts at the size limit; fetches `robots.txt` per host with the standard semantics (missing = allow, server error or unreachable = disallow), caching the result with expiry and honouring crawl delay; applies a per-host rate limit that is safe under concurrency; keeps a bounded, expiring page cache; enforces content type and time limits. Fetch outcomes always come back as either a page or a recorded skip reason.
- **URL guard.** Refuses any address that is not globally routable (covering private, loopback, link-local, shared-address, reserved and IPv4-mapped forms) after resolving every address a name maps to; allows only standard web ports in production; strict by default, with the explicit opt-out used by the batch command for local fixture sites. The residual DNS-rebinding window is documented rather than closed.
- **Crawler.** Scope by public-suffix-aware registrable domain plus an exact-domain allowlist of hiring platforms (one hop); normalises and de-duplicates addresses; counts retrieved pages against the budget; bounds links taken per page; records which page it judged to be the hiring page.
- **Research enrichment.** Derives the company name from the description, then from the company's site (its declared site name or title), then from the domain; uses it for the discussion search; computes hiring signals only from pages typed as hiring-related, with stricter patterns.
- **Ordering.** Replaces the current key algorithm with a correct fractional-indexing algorithm (proper midpoint and prefix handling, no degenerate keys, safe rebalancing when keys grow), implemented once in each language from shared test vectors so backend and frontend agree exactly.
- **Item schemas and edit service.** Typed create and patch schemas per collection with unknown fields rejected and values validated; server-assigned ids; reference-integrity rules (deleting a Requirement prunes references and flags Questions left uncovered); revision conflicts always enforced; the Schedule marked stale only for changes that can affect it; Schedule minutes recomputed on every Schedule mutation.
- **Export service.** Validates the Kit before serving; refuses to serve an invalid one with a clear error; strips all internal metadata (including brief metadata); output is identical in shape to batch output.
- **Kit validator.** Extended to cover consistency of Schedule minutes with Question minutes, and referential integrity after edits; used on every save path, not only at generation.
- **LLM gateway.** A shared client with connection pooling and the key in a header; a request/token rate limiter shared by all concurrent runs; retries limited to genuine provider conditions honouring provider hints; detection of truncated output with a smaller retry; deep schema validation with the repair attempt under the same retry protection; usage and latency recorded per call. The scripted fake model is selectable only through an explicit setting.
- **Pipeline hardening.** Days validated (1–60) at the pipeline boundary; uniform sanitisation of model output (clamp or drop, never fail the whole Kit for one bad value); explicit handling of over-long descriptions; consistent data-framing of every prompt; a per-Step and overall deadline with a valid partial Kit on expiry where possible; the batch command validates the cases file and case ids up front and writes its output atomically.
- **Scheduler.** Aligned with its specification: balance minutes across days as well as ordering by weight; spaced repeats for Review days; dead logic removed.
- **Auth and abuse controls.** Cookie flags by environment (secure in production); closed registration by default with an operator command to create a user (and an explicit setting to reopen it); per-user quotas; login throttle keyed on client address plus account, bounded and expiring; password hashing off the request loop with length bounds; one hashing scheme, no fallback; origin required on mutating requests in production and startup refused without the allowed-origin setting; generic error responses; internal fields removed from API responses.
- **Frontend hardening.** Post-login redirect accepts only in-app paths; security headers on every response; dead proxy handler removed; framework and CSS dependencies upgraded to patched versions; types generated from the OpenAPI document and used throughout.
- **API contract.** Every endpoint declares a typed response; the OpenAPI document is the single committed source; a test enumerates all operations and fails if any has an untyped response or if the generated types drift.
- **Configuration.** A single validated settings object; production startup validates required secrets, database, allowed origins and model key and refuses fake models; unused settings removed; the example environment file documents every variable and marks required ones.
- **Observability.** Structured logging on by default, with request, job and trace ids; every unexpected error logged with stack trace; the error envelope's reference id equals the request id in logs; liveness and readiness endpoints; optional OpenTelemetry (off unless configured, content-free by default) covering runs, Steps, fetches and model calls, with metrics for jobs, tokens, rate-limit hits and crawl outcomes.
- **Delivery.** A container image for the API; a production composition of API and database; infrastructure as code for the environment described in the architecture document (static frontend host, HTTPS front door, one instance, durable database volume, budget alarm, daily volume snapshots); a deploy command and a rollback command; secrets on the instance only; a single verification command (lint, type check, tests, drift check, dependency audits); locked Python dependencies; a runbook.
- **Documentation.** README, architecture document and decision records updated to match the built system; a new decision record for closed registration with operator-provisioned users; the earlier database-queue and regeneration records reconciled with the implementation.

### Key behavioural decisions

- **Order of work:** correctness → durability → security → operations → contract/documentation. If time is short, the correctness workstream plus documentation honesty are the minimum, because they affect graded behaviour and reviewer trust.
- **Registration:** closed by default; users are created by an operator command; reopening is an explicit setting. The web app remains login-only.
- **Database for the server, memory for the batch:** the batch command never requires a database.
- **Production refuses to degrade:** missing database, missing allowed origins, or a missing model key stop startup; the fake model requires an explicit flag.
- **Robots semantics:** a missing `robots.txt` allows crawling; a server error or unreachable file disallows it.
- **Ports:** production fetches allow only standard web ports.
- **Unreachable company remains `ok`** with the failure recorded (unchanged from the backend PRD).
- **Quota defaults** (adjustable by setting): a small number of Kits per user per day, a cap on stored Kits per user, and one concurrent generation per user.
- **Deadline defaults** (adjustable): a per-Step deadline and an overall generation deadline well below the batch's per-case budget.
- **Telemetry remains optional and off by default;** structured logs are always on.

### API contracts

No new user-facing routes are required. Changes to existing contracts: every response is typed; item create/patch bodies become strict typed schemas and reject unknown fields; error responses stay in the uniform envelope with the reference id matching logs; kit and job responses omit internal fields; the export refuses to serve an invalid Kit; two health endpoints exist (liveness and readiness). One operator command is added for creating users. Existing behaviour that graders exercise — the batch command and its output shape, the Kit structure — is unchanged.

### Data shape (high level)

Collections as previously specified: users, sessions (expiring), Kits, jobs, practice progress, page cache (expiring). New database guarantees: expiry indexes, one active job per Kit, and ownership-scoped lookups. Kit documents keep per-item metadata and section revision counters; brief metadata moves into the same structure as other items' metadata so that export can strip it uniformly.

## Testing Decisions

- **What makes a good test:** exercise external behaviour through public interfaces — a request in, a response and stored state out; a URL in, a page or skip reason out — never internals, prompt wording or call order. No test depends on a live model or the public internet.
- **Repository contract suite:** one behavioural suite run against both the in-memory and the database implementations of every store (ownership filtering, expiry, atomic Section merge, single active job per Kit, claim semantics). The database run uses the composition's database and is skipped when unavailable.
- **Fetcher and crawler:** redirect chains (followed, too long, redirect to a private address rejected before requesting), robots (allowed, disallowed, missing, server error, crawl delay), streamed size cap, content-type rejection, ATS look-alike rejection, public-suffix cases, URL normalisation and budget accounting, per-host rate limit under concurrent callers, bounded links per page, cache expiry. Uses the existing local fixture-site approach extended with these cases.
- **Regeneration:** with the scripted fake model — protected items survive, in-flight edits survive (a concurrent edit during the run), no duplicates, brief Proposal on edited/pinned brief, targeted generation covers exactly one Requirement and changes nothing else, failure leaves the Kit untouched, coverage recomputed.
- **Jobs:** concurrency limit enforced, per-user limits, stale requeue once then retryable failure, deadline yields partial or failure as specified, recovery after a simulated restart against the real database.
- **Editing and integrity:** mass-assignment attempts rejected, unknown fields rejected, enum and range validation, server-assigned ids, reference pruning on Requirement delete, stale-flag only when relevant, Schedule minutes correct after mutations, export refuses an invalid Kit and never leaks metadata.
- **Ordering:** property-based tests over random sequences of inserts (front, back, between) checking strict ordering and uniqueness, plus shared test vectors executed by both the backend and the frontend implementations.
- **Security:** cookie flags per environment; registration closed by default and the operator command works; quotas and throttling (including that a wrong-email guess cannot lock out a real account); origin fail-closed in production and startup refusal without configuration; open-redirect rejection on the login redirect; security headers present; oversized inputs rejected; error responses free of internals; production refuses fake model and missing key.
- **Pipeline:** days bounds (0, negative, 61), duplicate case ids, sanitisation (a single out-of-range value does not fail the Kit), over-long description handling, company-name fallback and its use in discussion search, hiring signals not triggered by unrelated pages, deadline behaviour, atomic batch output.
- **Model gateway:** retries only on provider conditions, shared limiter under concurrency, truncated-output retry, deep schema validation, repair under retry protection, key not present in any logged address.
- **Observability:** the reference id in an error response appears in a log line for the same request; unexpected errors are logged with a stack trace; readiness reflects database and key state; telemetry off produces no export and no behaviour change.
- **Contract:** a test enumerates every operation and fails on an untyped response or on generated-type drift; the frontend type check runs against the generated types.
- **Frontend:** the existing unit, component, accessibility and end-to-end tests continue to pass; new tests for the redirect validation and header presence.
- **Verification command:** runs lint, type checks, all tests, the drift check and dependency audits, and must pass from a clean checkout.
- **Prior art:** the existing backend (45) and frontend (47) test suites, the local fixture sites, the scripted fake model and the property-based scheduler tests are the base to extend.
- **Not tested:** live-provider output quality, visual styling, third-party service uptime.

## Out of Scope

- Multi-instance or high-availability operation, distributed job coordination, and horizontal scaling.
- A secret-management service, a web application firewall, and TLS on the hop between the HTTPS front door and the instance.
- Closing the DNS-rebinding window (documented as a residual risk).
- Headless-browser rendering of JavaScript-only pages; scraping login-walled sites.
- Email verification, password reset, roles, single sign-on, sharing, payments.
- Hosted continuous integration (a local verification command is provided instead, per the earlier decision to avoid it).
- Exporting telemetry to a hosted backend from production.
- New product features beyond those already specified; the keyword answer check remains a stretch item.
- Internationalisation and offline support.

## Further Notes

**Evidence base (from the audit of the current repository):**
- Persistence is a process-global in-memory store used by every router; the database configuration setting is unused and no database repository exists.
- Section regeneration performs no model call: the brief gains a suffix, and Category/targeted regeneration inserts fixed placeholder Questions; the associated "jobs" are fabricated completed records.
- Empirical: a fetch of a URL that redirects returned an empty page; a page disallowed by `robots.txt` was fetched and the site's `robots.txt` was never requested.
- Empirical: the ordering function returned a key not strictly between its bounds in 348 of 20,000 random trials, and repeated front-insertions produced duplicate, unsorted keys. The frontend mirrors the same algorithm.
- All 27 OpenAPI operations have untyped responses; the generated frontend "types" are only a list of paths.
- The session cookie is hard-coded non-secure; registration is open; the origin check is skipped when no origin is sent or when the setting is empty; the login redirect target is passed to the router unvalidated; the concurrency limit is computed but not enforced; stale-job recovery exists but is never invoked; a missing model key silently selects the fake model.
- No logging exists anywhere; the observability module is a no-op; health returns a constant.
- No container image, infrastructure definition, deploy script, quality gate or lockfile exists. Dependency audit reports one high-severity CSS-tooling advisory reachable through the frontend framework.
- Passing: 45 backend tests, 47 frontend tests, clean type check, successful production build.

**Decisions to confirm before build:**
1. Closed registration with an operator-created user (recommended) versus invite tokens versus keeping registration open behind rate limits.
2. Daily volume snapshots for backups (recommended, cheap) versus a scheduled dump to object storage.
3. Whether to accept the plaintext hop from the HTTPS front door to the instance (current design) or terminate TLS on the instance.
4. Whether hosted CI is wanted after all; the PRD assumes a single local verification command.
5. Default quotas (Kits per day, stored Kits, concurrent generations) and deadlines.

**Risks:** the scope is large relative to the assessment's submission window. Workstream 1 and the documentation-honesty story (89) are the minimum viable set: they change graded behaviour and reviewer trust. Durability and security follow because a deployed instance without them is unsafe; operations and delivery close the loop.
