# PRD: Interview Prep Kit — Frontend

Scope: the Next.js web application that talks to the backend described in `docs/prd-backend.md`. Vocabulary follows `CONTEXT.md`. Deployment is a separate final effort.

## Problem Statement

A candidate preparing for an interview needs more than a generated document. Generation takes about a minute and a half and can partly fail; the result is a draft they must be able to reshape — edit, reorder, add, delete, regenerate one Section — without ever losing work they've done; and it only becomes useful when they can practise against it and see where they are weakest. An interface that blocks on every keystroke, hides what the generator is doing, silently discards edits when something is regenerated, or works only on a laptop with a mouse fails at exactly the interactions the product is about.

## Solution

A responsive, keyboard-navigable web application where a candidate signs in, submits a job description, company website and number of days, watches the Kit being generated step by step (including what was skipped and why), and then reads and reshapes it. Editing is immediate: changes appear at once, save in the background per item, and never block typing. Regenerating a Section tells the candidate exactly what will be replaced and what is protected, leaves their own work untouched and editable throughout, and marks what is new. The candidate can practise Flashcards in short Drills, see what they have and haven't covered, and get a weak-spots report that says what to study next, with a printable one-page export.

## User Stories

### Access
1. As a candidate, I want to register and log in with an email and password, so that I have my own Kits.
2. As a candidate, I want form errors (invalid email, short password, wrong credentials, throttled login) shown next to the fields in plain language, so that I can fix them.
3. As a candidate, I want to log out from anywhere in the app, so that I can protect my account on a shared device.
4. As a signed-out visitor, I want any protected page to send me to the login screen and bring me back to where I was afterwards, so that a link I follow still works once I sign in.
5. As a candidate whose session expired mid-use, I want to be told it expired and be sent to log in, so that I understand what happened rather than see errors.

### Kit list and creation
6. As a candidate, I want a list of my Kits showing company, role, days, status, how many Requirements and Questions each has, and when it was last updated, so that I can resume the right one.
7. As a candidate with no Kits, I want an empty state that explains what a Kit is and offers to create one, so that I know what to do first.
8. As a candidate, I want a form with a job description box, a company website field and a number of days, with validation before submitting, so that I don't waste a generation on bad input.
9. As a candidate, I want to be told when I'm submitting something I already have, and choose between opening the existing Kit and creating a new one anyway, so that I don't create duplicates by accident.
10. As a candidate, I want to upload a file of several description-and-company pairs (up to 10) and see which were accepted and which were rejected and why, so that one bad entry doesn't discard the rest.
11. As a candidate, I want Kits that are still generating to show a live status in the list, so that I can start several and come back.
12. As a candidate, I want to delete a Kit after confirming, so that I can clean up without deleting by accident.

### Watching generation
13. As a candidate, I want to see each generation Step with its status (pending, running, done, skipped with a reason, failed) and elapsed time, so that I know it is working and where it is.
14. As a candidate, I want to leave the page and come back to find generation continuing, so that I'm not tied to the screen.
15. As a candidate, I want the progress screen to turn into the Kit as soon as it is ready, so that I don't have to refresh.
16. As a candidate, I want a Kit that finished with problems to open with a clear warning listing sources that couldn't be retrieved, a thin-description notice and any uncovered Requirements, so that I can judge how much to trust it.
17. As a candidate whose generation failed, I want to see what failed, a reference id, and a Retry button that resubmits the same input, so that one failure doesn't cost me my inputs.

### Reading the Kit
18. As a candidate, I want to move between the Kit's views — Overview, Role, Questions, Flashcards, Schedule, Practice — with addresses I can bookmark and share with myself, so that I can return to exactly where I was.
19. As a candidate, I want the Overview to show the company brief, what they do, how they hire, the sources used, coverage status and any warnings, so that I get the picture at a glance.
20. As a candidate, I want the Role view to list responsibilities and Requirements with their kind and priority, and for each Requirement how many Questions cover it and whether it is a Gap, so that I can see coverage.
21. As a candidate, I want Questions grouped by Category, each showing its difficulty, the Requirements it covers and its answer outline, so that I can study it.
22. As a candidate, I want every item to show whether it was generated, edited, written by me or pinned, so that I know what regeneration would replace.
23. As a candidate, I want the Schedule shown day by day with focus, Questions and minutes, Review days labelled, and any overload warning, so that I can follow it.
24. As a candidate, I want to download the Kit as JSON, so that I can keep or reuse it.
25. As a candidate, I want purposeful empty states (a Category with no Questions and why, no Flashcards yet), so that empty never looks broken.

### Editing
26. As a candidate, I want to edit any Question, answer outline, Flashcard, Requirement or the brief in place, so that the Kit reflects my judgment.
27. As a candidate, I want typing never to wait on the network, and changes to save automatically after I pause or leave the field, so that editing feels immediate.
28. As a candidate, I want each item to show Saving, Saved or Failed with a retry, so that I always know whether my edit is safe.
29. As a candidate, I want two quick edits to the same item never to lose either, so that fast typing is safe.
30. As a candidate, I want, when an item changed elsewhere while I was editing it, to keep my version or take the latest without losing my draft, so that conflicts don't silently destroy work.
31. As a candidate, I want to add a Question or Flashcard by hand, choosing its Category and the Requirements it covers, so that I can fill what the generator missed.
32. As a candidate, I want to delete any item after confirming, so that I don't lose one by a slip.
33. As a candidate, I want to pin an item so that regeneration can't touch it, so that I can protect things I haven't edited.
34. As a candidate, I want to edit, add and delete Requirements and change their priority and kind, and see coverage and Gaps update immediately, so that the Kit follows my understanding of the role.
35. As a candidate, I want a banner when Questions or Requirements changed after the Schedule was built, so that I know it may be out of date.
36. As a candidate, I want to edit a day's focus text and move a Question to another day, so that I can adjust my plan.

### Reordering and moving
37. As a candidate, I want to drag a Question to reorder it within its Category with mouse, touch or keyboard, so that I can organise my study.
38. As a candidate, I want every Question to have a Move menu (up, down, to another Category), so that reordering and recategorising never depend on dragging, especially on a phone or with a keyboard.
39. As a candidate, I want a reorder or move to appear instantly and roll back with a message if the server refuses it, so that it feels immediate without risking a wrong state.
40. As a candidate, I want moving a Question to another Category to count as my edit, so that it survives regeneration.

### Regeneration
41. As a candidate, I want to regenerate the brief, one Category or the Schedule on its own, so that I can refresh one part.
42. As a candidate, I want a confirmation that says exactly what will be replaced and what is protected ("replaces 6 unprotected Questions, keeps 2 you edited"), so that I decide with full information.
43. As a candidate, I want only the replaceable items to dim and show progress during regeneration while my own items stay visible and editable, so that I can keep working.
44. As a candidate, I want new items marked as new after regeneration, so that I can find what changed.
45. As a candidate, I want regenerating an edited brief to show my current text and the proposal together with Accept and Reject, so that I never lose my wording by accident.
46. As a candidate, I want to rebuild the Schedule with a warning that my manual Schedule edits will be replaced, so that I choose it knowingly.
47. As a candidate, I want an uncovered Requirement to offer "Generate a Question for this", so that I can close a Gap without regenerating a whole Category.
48. As a candidate, I want regeneration failures to say what happened and leave my Kit exactly as it was, so that failure is safe.

### Practice
49. As a candidate, I want to start a Drill of Flashcards ordered by what I'm least sure of, so that my time goes where it helps.
50. As a candidate, I want the Drill's order fixed when it starts, so that cards don't shuffle under me.
51. As a candidate, I want to reveal an answer and rate my Confidence 1–3, with the next card appearing automatically, so that I can move quickly.
52. As a candidate, I want keyboard shortcuts (space to reveal, 1/2/3 to rate, Backspace to undo the last rating), so that I never need the mouse.
53. As a candidate, I want to see progress through the Drill and, at the end, a summary with an option to drill the weak cards again, so that I can keep going.
54. As a candidate, I want to see what I have covered and what I haven't, overall and per Requirement and Category, so that I know what's left.
55. As a candidate, I want my practice progress to survive regenerating the Kit, so that regeneration doesn't reset me.

### Weak spots and export
56. As a candidate, I want a weak-spots report ranking Requirements by how ready I am, with the reasons (never practised, low Confidence, no Question, no Flashcard) and links to the relevant items, so that I know what to study next.
57. As a candidate, I want to print or save a one-page summary of the Kit (brief, Requirements with weak spots, Schedule), so that I can carry it into the interview prep.
58. As a candidate, I want (stretch) a keyword self-check of my typed answer against a Question's outline, clearly labelled as keyword match only, so that I get a rough signal.

### Quality, accessibility and errors
59. As a candidate, I want the whole app usable on a phone and a laptop, so that I can prepare anywhere.
60. As a candidate, I want everything operable by keyboard with visible focus, a skip link and announced status changes (saving, regenerating, errors), so that the app is accessible.
61. As a candidate, I want light and dark appearance to follow my system, with readable contrast, and reduced motion respected.
62. As a candidate, I want every error to say what went wrong in plain language with a reference id, and never to show a blank page, so that I can recover or report it.
63. As a candidate, I want skeletons while data loads, so that the layout doesn't jump.
64. As a candidate, I want a page-level fallback when something unexpected breaks, with a way back to my Kits, so that a bug in one view doesn't strand me.

## Implementation Decisions

### Modules (deep modules with small, stable interfaces)

- **API client.** One place for all server calls: sends credentials, decodes the uniform error envelope into typed errors (including the reference id), and turns a 401 into a single "session expired" event. Types come from the backend's committed OpenAPI document; the UI never hand-writes response types. A drift check fails the test run if the generated types are stale.
- **Kit cache.** Server state lives in a client-side query cache, one entry per Kit and one per list. Every view reads from it; every mutation updates it optimistically and rolls back on failure. There is no second source of truth.
- **Item mutation queue.** The heart of "editing feels immediate". Interface: enqueue an edit for an item; it applies to the cache at once, debounces text changes, serialises writes per item so two edits never race, tracks each item's Saving/Saved/Failed state, retries on request, and surfaces a revision conflict with the user's draft preserved so the UI can offer Keep mine / Use latest.
- **Ordering.** Mirrors the backend's fractional ordering so a reorder or move can be computed locally and shown instantly, then confirmed by the server.
- **Generation progress.** Polls a job with backoff (fast at first, slower later, paused while the tab is hidden), maps the fixed per-Step shape to a display, and resolves to success, success-with-warnings or failure. Also drives the list's live status for Kits that are still generating.
- **Regeneration controller.** Given a Section, computes from item metadata what would be replaced and what is protected (for the confirmation), starts the job, tracks which items are replaceable while it runs, and marks new items when it finishes. Handles the brief's Proposal and the Schedule rebuild warning.
- **Drill engine.** Fixes the queue at Drill start, tracks position, reveals and rating, undo of the last rating, and the end-of-Drill summary; records reviews through the optimistic path.
- **Weak-spots view model.** Presents the server's ranked report with reasons and links.
- **Auth shell.** Route protection for signed-out visitors (with return-to), the session-expired flow, and logout.
- **Feedback primitives.** Shared empty states, error states with reference ids, skeletons, toasts, confirmation dialogs and a live region for status announcements — used everywhere so states are consistent.

### Key decisions

- **Stack:** latest stable Next.js (App Router, strict TypeScript), Tailwind CSS v4, shadcn/ui components (Radix, for accessible primitives), TanStack Query for server state, dnd-kit for drag and drop, react-hook-form with zod for forms, npm.
- **Data fetching:** all Kit data is fetched client-side through the query cache. Server rendering is used only for the app shell; middleware redirects signed-out visitors. One data path keeps optimistic updates simple and avoids forwarding cookies server-side.
- **Same-origin API:** the browser only ever talks to the web app; requests to the API are proxied by the web app so cookies are first-party and no cross-origin setup exists. The only frontend environment variable is the API origin.
- **Navigation:** login, register, Kit list, new Kit (single | batch upload), and per-Kit views (Overview, Role, Questions, Flashcards, Schedule, Practice) as separate addressable routes; a print view for the one-pager. On phones the Kit's view navigation collapses into a compact control and the Category columns become an accordion.
- **Editing:** autosave per field on leaving the field or after ~600 ms idle; writes serialised per item; per-item Saving/Saved/Failed with retry. On a revision conflict the item alone shows Keep mine / Use latest; the user's draft is never silently discarded.
- **Reorder and move:** drag within a Category with pointer, touch (long-press) and keyboard sensors; a Move menu (up, down, to Category) on every Question and a "Move to day" menu on the Schedule are always available and are the primary path on phones. Cross-Category dragging between columns is a stretch goal.
- **Delete:** a confirmation dialog, no undo (an undo would require a restore endpoint and deferred commits).
- **Regeneration UX:** confirmation with counts of replaced vs protected items; only replaceable items dim with progress; new items badged after; an edited or pinned brief yields a stacked current/proposed view with Accept/Reject; the Schedule rebuild warns first.
- **Gaps:** each Requirement shows a coverage chip; a Gap shows a banner with "Generate a Question for this", which calls the targeted-generation endpoint rather than regenerating a Category.
- **Generation progress:** a dedicated screen at the Kit's address while generating (step list, elapsed time, skip reasons), which becomes the Kit view on completion, with a warnings banner if research was partial. Failure shows the message, reference id and a Retry that resubmits the same input. A duplicate submission shows Open existing / Create anyway.
- **Practice:** Drills of 10 Flashcards from a queue snapshot taken at the start; space reveals, 1/2/3 rate and auto-advance, Backspace undoes; the end screen offers "Drill weak cards again"; a separate view shows coverage per Requirement and Category.
- **Creative feature:** the weak-spots report (deterministic, from practice Confidence, coverage and priority), plus a print/save one-page export via a print stylesheet. The keyword answer check is a stretch goal and must be labelled "keyword match only".
- **Session expiry:** any 401 shows "session expired" and redirects to login with a return-to address.
- **Accessibility:** keyboard operability throughout, visible focus, a skip link, live-region announcements for saving/regenerating/errors, WCAG AA contrast, light/dark following the system with no toggle, reduced motion respected.
- **Cut order if time runs short** (never cut the first three): generation progress → the builder (edit, reorder, regenerate) → practice → weak-spots report → web batch upload UI → drag-and-drop (fall back to Move menus) → print view.

### Backend dependencies (already folded into the backend PRD and plan)

The list summary fields, item metadata in responses, a fixed per-Step job shape, a duplicate flag on create, the reference id on errors, targeted generation for one Requirement, the weak-spots report, a committed OpenAPI document, and a scripted fake-LLM server mode for end-to-end tests.

## Testing Decisions

- **What makes a good test:** exercise what the user sees and does — text appears, a keyboard sequence produces a result, an error is announced — not component internals, hook call order or CSS. No test depends on a live model or the public internet.
- **Unit tests (behaviour of the deep modules):** the item mutation queue (optimistic apply, debounce, per-item serialisation, rollback, retry, conflict with draft preserved), ordering (moves and reorders produce the same order the server would), the regeneration controller's replaced/protected counts, the Drill engine (fixed queue, rating, undo, summary), generation-progress polling (backoff, pause when hidden, terminal states).
- **Component tests:** the question editor states (idle, editing, saving, saved, failed, conflict), the Move menu, the confirmation dialogs, error and empty states, form validation messages.
- **Contract:** the generated API types match the committed OpenAPI document; the test run fails on drift.
- **End-to-end (one journey):** register → create a Kit → watch progress → edit a Question → regenerate its Category → the edit survives — run against the real backend in scripted fake-LLM mode, so it needs no key or quota.
- **Accessibility checks:** automated checks on the main views plus a manual keyboard pass through edit, move, regenerate and Drill.
- **Prior art:** none — greenfield.
- **Not tested:** visual styling, animation, live-provider output.

## Out of Scope

- Deployment and hosting configuration (a separate final effort).
- Email verification, password reset, roles, sharing, team features, payments, CV features, job search, audio/video.
- Undo for deletes; a theme toggle; internationalisation; offline support.
- Cross-Category drag between columns (stretch only); word-level diffs in the brief Proposal.
- Real-time collaboration and multi-tab live sync beyond conflict handling on save.

## Further Notes

- The hard interaction problems are the mutation queue and regeneration without clobbering; they carry the most weight in review and get the most test coverage.
- The hard submission deadline has not been confirmed; the cut order above is the plan if time runs short.
- The keyword answer check is honest but weak (it misses paraphrases); the weak-spots report is the intended creative feature because it is deterministic and explains itself.
- The video should demonstrate: create-and-watch, an edit surviving a regeneration, reorder/move, a Drill, and the weak-spots report.
