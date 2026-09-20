# PRD: Interview Prep Kit — Backend

Scope: the FastAPI backend and the batch entry point. The frontend, and infrastructure/deployment, are separate efforts (see Out of Scope). Vocabulary follows `CONTEXT.md`; decisions follow `docs/adr/`; the wider design is in `docs/ARCHITECTURE.md`.

## Problem Statement

A candidate with an interview coming up has a job description, a company website and a limited number of days. Preparing well means working out what the role really demands, learning how this particular company hires, guessing the questions likely to be asked, and turning all that into a day-by-day plan. Doing this by hand is slow, and asking a chatbot for "an interview prep kit" in one prompt produces generic, partly invented material that ignores what the company actually publishes about its hiring process and silently skips requirements from the posting.

Separately, the assessors who will evaluate this system need to run it, unattended, over job descriptions and company sites it has never seen — including a near-empty description and a company with no hiring page — and get a well-formed result for every case, honest about what could not be found.

## Solution

A backend that turns a job description, a company website and a number of days into a structured Kit through a sequence of deliberate research and generation steps: it extracts the Requirements (never inventing any), crawls the company site to find what the company does and how it hires, looks for public discussion of its interviews, writes a brief from only what was found, generates Questions per Category shaped by the hiring signals discovered, and then checks — in plain code — which Requirements have no Question, generating targeted Questions for the Gaps before shipping. The schedule is computed by code, not a model, across exactly the days requested.

The candidate can then reshape any part of the Kit; regenerating one Section never destroys work they have done elsewhere or by hand. They can practise Flashcards with confidence tracking, and an ordering that surfaces what they know least.

The same pipeline is exposed through a command-line batch entry point that reads Cases from a file and writes Kits (or recorded failures) to a file, continuing past individual failures.

## User Stories

### Account and access
1. As a candidate, I want to register with an email and password, so that my Kits are mine.
2. As a candidate, I want to log in and log out, so that I control access to my account on shared devices.
3. As a candidate, I want a signed-out visitor to be unable to read any of my Kits or call any protected endpoint, so that my preparation stays private.
4. As a candidate, I want to be able to read and change only my own Kits, so that other users cannot see or alter them.
5. As a candidate, I want a request for someone else's Kit to look identical to a request for a Kit that doesn't exist, so that Kit ids reveal nothing.
6. As a candidate, I want an expired or invalid session to produce a clear "sign in again" response, so that the app can send me to log in rather than fail mysteriously.
7. As a candidate, I want repeated failed logins to be slowed down, so that my account is harder to guess into.

### Creating a Kit
8. As a candidate, I want to submit a job description, a company website and a number of days, so that a Kit is prepared for me.
9. As a candidate, I want submission to return immediately with a handle I can follow, so that a 90-second generation doesn't hang my request.
10. As a candidate, I want to see which step the generation is on (pending, running, done, skipped with a reason, failed), so that I know it is working and where it is stuck.
11. As a candidate, I want a failed generation to say what failed and let me retry it, so that one bad step doesn't waste my attempt.
12. As a candidate, I want a partly researched Kit to still be delivered with the gaps clearly recorded, so that a dead page doesn't cost me the whole Kit.
13. As a candidate, I want submitting the same description, company and days twice to return my existing Kit rather than burn another generation, so that duplicates don't waste time or quota.
14. As a candidate, I want to override that and create a new Kit anyway, so that I can regenerate from scratch on purpose.
15. As a candidate, I want a previously failed Kit to be retried rather than treated as a duplicate, so that a failure doesn't block me.
16. As a candidate, I want different numbers of days to produce a different Kit, so that my plan matches my actual time.
17. As a candidate, I want to upload a file of several description-and-company pairs (up to 10), so that I can prepare for multiple roles at once.
18. As a candidate, I want a batch upload to report which entries were accepted and which were rejected and why, so that one malformed entry doesn't discard the rest.
19. As a candidate, I want to see and reopen all my Kits later, so that I can continue preparing.
20. As a candidate, I want to delete a Kit, so that I can clean up.

### Requirement extraction
21. As a candidate, I want every Requirement to come from text actually in the job description, so that I'm not preparing for things the employer never asked for.
22. As a candidate, I want each Requirement to be a single claim with one priority, so that a bullet like "React, TypeScript and Node.js; PostgreSQL a plus" becomes separate, correctly-prioritised items.
23. As a candidate, I want "X or Y" alternatives kept as one Requirement, so that I'm not asked to master both.
24. As a candidate, I want wording like "required" and "must" treated as `must`, and "plus", "bonus", "preferred" as `nice`, so that priorities reflect what the posting says.
25. As a candidate, I want lines with no signal to default to `must`, so that nothing important is silently demoted.
26. As a candidate, I want responsibility lines that state a competency I must demonstrate (such as mentoring junior engineers) to become Requirements, and pure task descriptions to remain in the responsibilities list.
27. As a candidate, I want no requirement inferred that the description doesn't state, so that a thin posting yields a thin Kit.
28. As a candidate, I want a near-empty description to produce a small Kit that says the description was thin, rather than padding, so that I can trust what is there.
29. As a candidate, I want company name, role title, seniority and location captured without guessing, so that unknown values are empty or "unspecified" rather than fabricated.

### Company research
30. As a candidate, I want the company's site crawled to find what they do, so that the brief reflects reality.
31. As a candidate, I want the crawler to find the hiring-process page wherever the company put it (careers, jobs, a handbook, an engineering blog), so that it doesn't depend on guessing URLs.
32. As a candidate, I want links ranked by how likely they are to describe hiring or the business, so that the limited crawl budget is spent on the right pages.
33. As a candidate, I want the crawler to follow relative links and work against any host, including local ones, so that it works on test sites.
34. As a candidate, I want the crawler to respect `robots.txt` and rate limits and to back off on failures, so that it is a good citizen.
35. As a candidate, I want a page that cannot be fetched, is disallowed, is too large or is the wrong type to be skipped and recorded, so that one bad source never fails the run.
36. As a candidate, I want public discussion of the company's interview process searched, so that I benefit from what others report.
37. As a candidate, I want "nothing found" recorded honestly, so that the brief doesn't invent a reputation.
38. As a candidate, I want the brief written only from pages that were actually retrieved, so that every claim traces to a source.
39. As a candidate, I want the brief to say plainly when nothing could be retrieved about the company, so that I know to research it myself.
40. As a candidate, I want the list of pages used and the brief's sources shown, so that I can check them.
41. As a candidate, I want an unreachable, invalid or 404 company site to still produce a Kit from the description alone, so that a bad URL doesn't block my preparation.

### Question generation and coverage
42. As a candidate, I want Questions generated separately per Category with instructions suited to that Category, so that a technical requirement and a behavioural one are not treated alike.
43. As a candidate, I want the questions to change when the company publishes a take-home or a system-design round, so that the Kit reflects how that company really interviews.
44. As a candidate, I want every Question to reference the Requirements it covers, so that coverage is checkable rather than a matter of opinion.
45. As a candidate, I want a Category with nothing to ask about to be omitted rather than filled with generic questions.
46. As a candidate, I want each Question to have a difficulty and an answer outline, so that I know how hard it is and what a good answer contains.
47. As a candidate, I want the system to find Requirements no Question covers and then generate Questions for exactly those, so that nothing important is left unprepared.
48. As a candidate, I want the coverage decision made by code, not by the model, so that it is reliable.
49. As a candidate, I want questions whose claimed coverage is dubious to be discounted, so that a mislabelled question doesn't hide a Gap.
50. As a candidate, I want the second pass to stop after a bounded number of attempts or when it stops making progress, and to list whatever remains uncovered, so that the result is honest and generation terminates.
51. As a candidate, I want Kit size bounded (at most 30 Questions, 20 Flashcards), so that it stays usable and within provider limits.

### Flashcards and schedule
52. As a candidate, I want Flashcards for the key concepts behind my must-have Requirements, so that I can drill them.
53. As a candidate, I want a Schedule that spans exactly the number of days I said I have, so that it fits my time.
54. As a candidate, I want every day to have a focus, a set of Questions and a duration in whole minutes, so that I know what to do and how long it takes.
55. As a candidate, I want harder and higher-priority material earlier, so that the night before is light.
56. As a candidate, I want every covered must-have Requirement to appear somewhere in the Schedule, so that nothing is skipped.
57. As a candidate, I want a 1-day Schedule to work (with honest minutes) and a 60-day Schedule to work (using Review days), so that extreme requests are handled.
58. As a candidate, I want a warning when my Schedule averages an unrealistic daily load, so that I can choose more days.
59. As a candidate, I want the Schedule computed by arithmetic that gives the same answer every time for the same inputs, so that it is predictable.

### Editing and regeneration
60. As a candidate, I want to edit any Question, answer outline, Flashcard, Requirement or the brief, so that the Kit reflects my judgment.
61. As a candidate, I want to add a Question or Flashcard by hand and delete any item, so that I control the content.
62. As a candidate, I want to reorder Questions and move one to another Category, so that I can organise them my way.
63. As a candidate, I want to pin an item, so that it is safe from regeneration even if I haven't edited it.
64. As a candidate, I want to regenerate only the company brief, or one Category, or the Schedule, so that I can refresh one part.
65. As a candidate, I want regeneration of one Section to leave every other Section untouched.
66. As a candidate, I want anything I wrote, edited, moved or pinned to survive regenerating its Category, so that my work is never lost.
67. As a candidate, I want an edit I make while a regeneration is running not to be overwritten when it finishes, so that timing doesn't cost me work.
68. As a candidate, I want regenerating an edited brief to give me a proposal to accept or reject rather than overwrite it, so that I keep control of single blocks.
69. As a candidate, I want regenerated Questions not to duplicate ones I kept, so that the Category stays coherent.
70. As a candidate, I want to be told when my Questions or Requirements changed after the Schedule was built, so that I can rebuild it deliberately.
71. As a candidate, I want manual Schedule edits preserved until I choose to rebuild, and a warning before rebuild replaces them.
72. As a candidate, I want deleting a Question to remove it from the Schedule immediately, so that the Schedule never points at something that doesn't exist.
73. As a candidate, I want deleting the only Question for a must-have, or editing a Requirement, to be allowed and to show the resulting Gap with an offer to generate a Question for it, without any automatic generation.
74. As a candidate, I want to export the Kit in the exact agreed structure, so that I can use it elsewhere.
75. As a candidate, I want two edits to the same item in quick succession not to lose either, so that fast typing is safe.

### Practice
76. As a candidate, I want to be served Flashcards to work through, so that I can practise.
77. As a candidate, I want to record how confident I felt on each card (1–3), so that the system learns what I know.
78. As a candidate, I want to see what I have covered and what I haven't, overall and per Requirement, so that I know where to focus.
79. As a candidate, I want the next session ordered by what I'm least sure of, with unseen cards before mastered ones and a slight boost for cards on must-have Requirements, so that my time goes where it helps most.
80. As a candidate, I want my practice progress to survive regenerating the Kit's content.
81. As a candidate, I want to type an answer to a Question and see which points of the outline I covered and which I missed, so that I know whether my practice answer is any good.

### Batch entry point
82. As an assessor, I want one command that reads a file of Cases and writes a file of results, so that I can evaluate the pipeline without the interface.
83. As an assessor, I want each Case to use its own days value, so that schedules match the request.
84. As an assessor, I want the batch to run the same pipeline the application uses, so that what I test is what ships.
85. As an assessor, I want one entry per input Case, keyed by its id, with a status and either a Kit or an error, so that results are machine-checkable.
86. As an assessor, I want a Case that fails to be recorded and the run to continue, so that one failure doesn't abort the rest.
87. As an assessor, I want `failed` reserved for Cases where no valid Kit could be produced, and partly researched Cases to be `ok` with gaps recorded, so that status is meaningful.
88. As an assessor, I want five Cases to complete within fifteen minutes even when the LLM provider rate-limits, so that runs are practical.
89. As an assessor, I want the command to work from a clean clone after one documented install step, needing only environment variables documented in the example file.
90. As an assessor, I want the batch to work against company sites served from a local address, so that I can use fixture sites.
91. As an assessor, I want a missing required credential to fail immediately with a clear message, so that I don't wait on a doomed run.
92. As an assessor, I want the pipeline to need only one LLM key, so that I don't need extra accounts.

### Robustness and safety
93. As a candidate, I want a rate-limited or briefly failing LLM provider to be retried with backoff and, if configured, failed over to another, so that a transient problem doesn't fail my Kit.
94. As a candidate, I want invalid or incomplete model output repaired or regenerated and validated against the Kit structure before it is saved, so that I never receive a malformed Kit.
95. As a candidate, I want a Kit that cannot be validly assembled to fail with a clear error rather than be saved broken.
96. As an operator, I want fetched URLs validated and private, loopback and link-local addresses rejected by default, so that the service cannot be used to reach internal systems.
97. As an operator, I want only expected content types and bounded sizes fetched, so that hostile pages can't exhaust resources.
98. As an operator, I want text in a pasted description or crawled page treated strictly as content, never as instructions, so that hostile text cannot steer generation.
99. As an operator, I want a page that appears to address an AI or issue instructions to be dropped and logged.
100. As an operator, I want every error returned in one structured shape with a reference id, so that a failure can be traced.
101. As an operator, I want a job interrupted by a restart to resume by being requeued once, so that a deploy doesn't strand work.
102. As an operator, I want at most one active generation per Kit and a bounded number of concurrent generations, so that a double-click or a burst cannot overrun quotas.

### Observability
103. As a developer, I want each pipeline run, step, fetch and LLM call traced with token, latency, retry and rate-limit detail, so that I can see how a run behaved.
104. As a developer, I want that telemetry to be off unless an endpoint is configured and never to slow or fail a run, so that the batch command needs no extra setup.
105. As a developer, I want job description and page text never recorded in telemetry, so that user content isn't leaked.

## Implementation Decisions

### Modules (deep modules with small, stable interfaces)

- **Kit model and validator.** The canonical structure (Appendix A) as strict types plus a semantic validator: unique ids, all references resolve, schedule length equals days requested, integer minutes, difficulty within 1–3, no must Requirement missing from both coverage and the uncovered list. Interface: build/validate a Kit; export the exact-structure projection.
- **Item state and merge.** Per-item metadata (origin, edited, pinned, revision, order key). Interface: "given current items, freshly generated items and a job-start snapshot, produce the merged items", encoding the protected-item rules of ADR-0004. Also fractional ordering keys.
- **Requirement extractor.** Interface: JD → atomic Requirements + role metadata. Guarantees every Requirement carries verbatim evidence verified against the JD, assigns stable ids, dedupes, caps at ~25, and never guesses metadata.
- **Requirement classifier.** Interface: Requirement (+ its section heading) → kind, priority; seniority. LLM-proposed values checked by deterministic heuristics; default priority is `must`.
- **Safe fetcher.** URL validation (strict by default, redirect re-validation), robots handling (RFC 9309 semantics), content-type/size/time limits, per-host rate limiting, backoff, and a fetch cache. Interface: fetch(url) → cleaned page or a recorded skip reason.
- **Crawler.** Interface: (company URL, budget) → ranked, retrieved pages + a record of skips. Priority-queue traversal driven by link ranking; same registrable domain plus an ATS allowlist one hop; relative links; static HTML only.
- **Discussion researcher.** Interface: company name → discussion excerpts or an explicit "not found / not queried, reason".
- **Hiring-signal analyzer.** Interface: retrieved text → flags (take-home, system-design round, coding round, behavioural round) each true/false/unknown.
- **Brief writer.** Interface: retrieved pages → brief; when nothing was retrieved it returns a fixed honest statement without calling the model.
- **Question generator.** Interface: (Category, Requirement subset, hiring signals, existing questions to avoid) → Questions with difficulty, requirement ids, answer outline and outline points. One instance per Category with its own instructions; routing from Requirement kind to Category; empty Categories skipped.
- **Coverage checker.** Pure. Interface: (Requirements, Questions, optional verified links) → Gaps. Set arithmetic only.
- **Coverage loop.** Interface: (Kit draft) → Kit with Gaps filled or honestly listed. Maximum three Passes; stops on no gaps, on the cap, or on no progress; the last Pass targets `must` Gaps only.
- **Scheduler.** Pure and deterministic. Interface: (Questions, Requirements, days) → Schedule with exactly `days` days. Weights by difficulty and priority; front-loaded triangular allocation when Questions ≥ days; Review days when fewer; integer-minute estimates by Category and difficulty; overload warning above 180 minutes/day average.
- **Practice prioritizer.** Pure. Interface: (cards, review history, now) → ordered queue. Confidence-weighted with recency decay, unseen-before-mastered, must-boost.
- **LLM gateway.** Interface: structured generation against a schema. Single Gemini model, rate-limit and token budgeting, backoff honouring provider hints, one repair attempt on invalid output. Only Gemini is required.
- **Pipeline orchestrator.** Interface: (Case, dependencies, progress callback) → Kit + research log. Pure orchestration with no persistence; JD analysis runs concurrently with retrieval; question generation waits for both. Also provides Section regeneration.
- **Job queue.** Mongo-backed claim/heartbeat/requeue-once (ADR-0002); one active job per Kit; bounded concurrency; step-level progress records.
- **Auth and sessions.** Argon2id passwords; opaque random session tokens stored only as hashes with server-side expiry; httpOnly, secure, same-site cookies; origin check on mutating requests; login throttling; ownership enforced on every Kit query.
- **Persistence repositories.** Users, sessions, Kits, jobs, practice progress, fetch cache. In-memory implementations exist so the pipeline and batch need no database.
- **Batch runner.** Interface: cases file → results file. Two Cases concurrently, per-Case deadline (240 s), continue on failure; opts out of the private-URL block explicitly.
- **API layer.** Thin: validation, auth, error envelope, delegating to the above.
- **Observability.** Optional tracing/metrics/logging that is a no-op unless configured; content-free by default.

### Key behavioural decisions

- Requirement = atomic claim (see `CONTEXT.md`); responsibilities become Requirements only when they state a competency the candidate must demonstrate; no implied Requirements.
- The single LLM writes and proposes classifications; code arbitrates; no AI orchestration framework (ADR-0003).
- Protected items and atomic regeneration (ADR-0004). Brief regeneration on an edited brief returns a proposal. The Schedule is derived: it is marked stale when Questions change, user edits are kept until an explicit rebuild, and deleted question ids are removed immediately.
- Coverage: all Requirements are subject to Gap reporting; retries prioritise `must`; three Passes maximum. Deleting a covering Question or editing a Requirement never blocks and never triggers automatic generation.
- Unreachable/invalid/404 company site → `ok` with recorded failure and a deterministic honest brief. `failed` is reserved for: empty description, no LLM available and nothing generated, Kit could not be validly assembled, deadline hit before a valid Kit existed, missing required credentials.
- Caps: 30 Questions, 20 Flashcards, ~25 Requirements, 12 crawled pages, depth 2, 10 cases per web batch upload.
- Duplicate key = user + normalised JD + normalised URL + days; only ready/generating Kits dedupe; `force_new` overrides.
- Security: URL guard strict by default (CLI opts out explicitly); allowlisted content types; size and time limits; untrusted text framed as data; keyword markers flag instruction-style pages for dropping.
- Required config: only the Gemini key; search API and telemetry endpoint are optional.

### API contracts (routes)

- Auth: register, login, logout, current user.
- Kits: create (accepted with kit id and job id, or existing Kit for duplicates), batch create, list, get, delete, export.
- Jobs: get by id (status + per-step progress).
- Items: create/patch/delete for Questions, Flashcards, Requirements, brief and Schedule days; reorder/move for Questions with target Category and predecessor.
- Sections: regenerate brief / one Category / Schedule (returns a job; brief on an edited brief returns a proposal).
- Practice: next queue, record review, summary, and the answer check for a Question.
- Health.

All errors share one envelope: code, message, details, reference id.

### Data shape (high level)

Collections: users, sessions (expiring), Kits, jobs, practice progress, fetch cache (expiring). A Kit is one document containing the input, the Kit content with per-item metadata, the research log, and section revision counters. The research log holds pages tried and skipped with reasons, the discussion outcome, the thin-description flag and warnings. Extensions beyond the exact structure are optional and additive: research log, the brief's hiring-process text, and each Question's outline points.

### Batch contract

Input: array of Cases. Output: version, generated-at, and one entry per Case with id, status (`ok` | `failed`), Kit or null, error (code, message) or null. Five Cases within fifteen minutes; two concurrently; shared provider limiter; per-Case deadline returns a valid partial Kit as `ok` with warnings when possible.

## Testing Decisions

- **What makes a good test:** exercise external behaviour through a module's public interface — inputs in, outputs out — never internal helpers, prompt wording or call order. Tests must not depend on a live model or the open internet.
- **Required by the brief and prioritised:** Scheduler (including property-based tests: exactly `days` days, integer minutes, valid ids, every Question scheduled, harder/priority material never later than lighter when Questions ≥ days, Review days when fewer, zero Questions), Coverage checker, Kit validator.
- **Also tested:** item merge rules (protected survival, in-flight edit survival, moved-Category protection, no duplicates), fractional ordering, Requirement evidence grounding (paraphrase rejected, whitespace differences tolerated, injected text not in the JD dropped), URL guard (private/loopback/link-local/metadata, redirects to private, strict default), robots semantics, practice prioritizer, dedupe key normalisation, job claim/requeue semantics, auth ownership (other user's Kit is indistinguishable from missing).
- **Integration:** the full pipeline with a scripted fake LLM against fixture company sites on an ephemeral local server — a site with a buried hiring page, a site with none, a 404 site, a timing-out site — plus a two-line description, invalid model output, a provider rate-limit storm, and a first draft that misses a must so the second Pass demonstrably closes the Gap.
- **Contract:** every produced Kit validates against the exported structure schema; batch output matches the agreed output shape; the batch command runs end-to-end with no database and no optional keys.
- **Prior art:** none — the repository is greenfield. The fixture sites and cases become the shared test assets.
- **Not tested:** live-provider quality, prompt text, telemetry output.

## Out of Scope

- Frontend (separate PRD): UI, optimistic editing, drag-and-drop, generation-progress screens.
- Infrastructure and deployment (Terraform, Vercel, CloudFront, EC2) — a separate final phase.
- Email verification, password reset, roles, sharing, payments, CV features, job search, audio/video.
- Headless-browser rendering of JS-only pages; scraping login-walled review sites.
- CSV batch upload; DNS-rebinding defence; multi-instance job coordination.
- Confirmation from the assessors on the Python choice (accepted risk, ADR-0001).

## Further Notes

- **Risks:** Python backend versus the brief's JS/TS wording (ADR-0001); single-provider LLM limits are volatile (backoff, limiter, verify at build time); the Appendix B example shows an unreachable company as a failure while this design records it as `ok` — a one-line change if needed.
- **Ambiguity resolved by judgment:** thin descriptions and unknown companies yield honest, small output rather than padded output; this is a deliberate reading of the brief's "invent nothing" rule.
- **Time budget:** the brief expects 2–3 days of focused work; the backend is the bulk of the automated score (55 points), so it is built first and the batch command is a first-class deliverable, not an afterthought.
