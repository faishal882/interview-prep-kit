# Plan: Interview Prep Kit — Frontend

> Source PRD: `docs/prd-frontend.md` (user stories are numbered there). Backend: `docs/prd-backend.md` and `plans/backend.md`. Vocabulary: `CONTEXT.md`.

## Sequencing

Backend phases 1–7 (pipeline and batch command) are CLI-only and come first. Frontend phases then interleave with backend phases 8–13 so each backend slice ships with its UI, developed against the real backend running locally (the scripted fake LLM keeps it free and deterministic). The pairing is shown in each phase.

If time runs short, cut in this order and never touch the first three: generation progress → the builder (edit, reorder, regenerate) → practice → weak-spots report → web batch upload UI → drag-and-drop (fall back to Move menus) → print view.

## Architectural decisions

Durable decisions that apply across all phases:

- **Stack**: latest stable Next.js (App Router, strict TypeScript), Tailwind CSS v4, shadcn/ui (Radix primitives), TanStack Query for server state, dnd-kit for drag and drop, react-hook-form + zod for forms, npm.
- **Routes**: `/login`, `/register`, `/kits`, `/kits/new` (single | batch tabs), and per-Kit views `/kits/{id}` (Overview), `/kits/{id}/role`, `/kits/{id}/questions`, `/kits/{id}/flashcards`, `/kits/{id}/schedule`, `/kits/{id}/practice`, plus a print view `/kits/{id}/print`. While a Kit is generating, `/kits/{id}` shows the progress screen.
- **Data path**: all Kit data is fetched client-side through the query cache (one entry per Kit, one for the list); server rendering is used only for the app shell; middleware redirects signed-out visitors with a return-to address. The cache is the single source of truth; every mutation is optimistic with rollback.
- **Same-origin API**: the browser only talks to the web app; `/api/*` is proxied to the backend so cookies are first-party and no cross-origin setup exists. The only frontend environment variable is the API origin.
- **Contract**: TypeScript types are generated from the backend's committed OpenAPI document; a drift check runs inside the normal test command. The UI never hand-writes response types.
- **Error model**: the backend's uniform envelope (code, message, details, reference id) is decoded in one place into typed errors; every error surface shows a plain-language message plus the reference id; a 401 raises one "session expired" flow.
- **Item state in the UI**: items carry origin (generated | user), edited, pinned and revision from the API; badges (Generated, Edited, Yours, Pinned) derive from that; "protected" = user-written, edited or pinned.
- **Editing model**: autosave per field on blur or ~600 ms idle; writes serialised per item; per-item Saving / Saved / Failed with retry; revision conflicts resolved per item with Keep mine / Use latest.
- **Polling**: job progress polled with backoff (fast at first, slower later), paused while the tab is hidden.
- **Terms in the UI**: Kit, Requirement, Question, Flashcard, Schedule, Review day, Gap, Drill, Weak spot, Proposal, Step (per `CONTEXT.md`); "session" only ever means login session.
- **Accessibility baseline**: keyboard operable, visible focus, skip link, live-region announcements, WCAG AA contrast, light/dark following the system (no toggle), reduced motion respected.
- **Responsive baseline**: usable on phone and laptop; on phones, view navigation collapses and Category columns become an accordion.
- **Testing approach**: unit tests for the deep modules (mutation queue, ordering, regeneration controller, Drill engine, progress polling), component tests for states and dialogs, one end-to-end journey against the real backend in scripted fake-LLM mode.

---

## Phase 1: Foundation and auth

**User stories**: 1–5, 60–64  ·  **Pairs with**: backend Phase 8

### What to build

The application scaffold and the first end-to-end slice: an API client that sends credentials, decodes the error envelope and raises the session-expired event; generated types with the drift check; the same-origin proxy; route protection with return-to; register, login and logout screens with field-level errors; the app shell with navigation; and the shared feedback primitives (empty state, error state with reference id, skeletons, toasts, confirm dialog, live region, page-level error fallback and not-found).

### Acceptance criteria

- [ ] A visitor can register, log in, reach `/kits`, and log out; a signed-out visit to any protected route redirects to login and returns after signing in
- [ ] Wrong credentials, invalid input and throttled login show plain-language errors beside the fields
- [ ] Forcing a 401 shows "session expired" and redirects with return-to
- [ ] An unexpected render error shows the page-level fallback with a way back to `/kits`
- [ ] Generated types match the committed OpenAPI document; the test run fails on drift
- [ ] Keyboard-only use works for every auth screen; skip link and visible focus are present
- [ ] Unit and component tests for the client, error decoding and auth flows pass

---

## Phase 2: Create a Kit and watch it generate

**User stories**: 6–9, 11–17  ·  **Pairs with**: backend Phase 9

### What to build

The Kit list with per-Kit summary and a live status for Kits still generating; the create form with validation; the duplicate notice (Open existing / Create anyway); and the generation progress screen at the Kit's address showing each Step with status, message and elapsed time, resolving into the Kit view, into a warnings state for partial research, or into a failure state with reference id and a Retry that resubmits the same input. Delete a Kit with a confirmation.

### Acceptance criteria

- [ ] The list shows company, role, days, status, counts and last-updated; an empty state explains what a Kit is
- [ ] Invalid input is rejected before submission; a valid submission navigates to the progress screen
- [ ] Steps show pending, running, done, skipped (with reason) and failed; elapsed time updates
- [ ] Leaving and returning mid-generation resumes the display; the list shows live status for generating Kits
- [ ] Completion transitions to the Kit without a manual refresh; partial research opens with a warnings banner
- [ ] A failed generation shows the message, reference id and Retry, which resubmits the same input
- [ ] Submitting a duplicate offers Open existing / Create anyway
- [ ] Deleting a Kit requires confirmation and removes it from the list
- [ ] Progress-polling tests (backoff, paused when hidden, terminal states) and component tests pass

---

## Phase 3: Read the Kit

**User stories**: 18–25  ·  **Pairs with**: backend Phase 9

### What to build

Read-only views for the whole Kit as addressable routes: Overview (brief, what they do, how they hire, sources, coverage, warnings), Role (responsibilities and Requirements with kind, priority, covering-Question counts and Gap indication), Questions grouped by Category (difficulty, covered Requirements, answer outline), Flashcards, and the Schedule (days with focus, Questions, minutes, Review days, overload warning). Origin badges on every item, purposeful empty states, responsive layouts (columns on laptop, accordion on phone), and JSON export download.

### Acceptance criteria

- [ ] Each view has its own address and survives reload and bookmarking
- [ ] Requirements show coverage chips; an uncovered Requirement is visibly a Gap
- [ ] Questions are grouped by Category; an empty Category explains why it is empty
- [ ] Origin badges reflect generated, edited, user-written and pinned items
- [ ] A Kit with no hiring information shows the honest brief and a warnings banner
- [ ] Layout is usable at phone and laptop widths; every view is keyboard navigable
- [ ] The exported file downloads and matches the export endpoint's output
- [ ] Component tests for empty, loading and error states pass

---

## Phase 4: Web batch upload

**User stories**: 10  ·  **Pairs with**: backend Phase 10

### What to build

The batch tab on the new-Kit screen: choose a JSON file in the agreed shape, preview the number of entries, submit, and see a per-entry accepted/rejected report with reasons, with links to the new Kits.

### Acceptance criteria

- [ ] A valid file creates one Kit per accepted entry and links to each
- [ ] Malformed entries are listed individually with reasons while valid ones proceed
- [ ] A file with more than 10 entries or invalid JSON is rejected with a clear message
- [ ] The tab is keyboard operable and its states (idle, uploading, report, error) are announced

---

## Phase 5: Inline editing

**User stories**: 26–35  ·  **Pairs with**: backend Phase 11

### What to build

The mutation queue and every inline edit built on it: Questions, answer outlines, Flashcards, Requirements and the brief edited in place with autosave and per-item Saving / Saved / Failed with retry; per-item serialisation; per-item conflict handling with Keep mine / Use latest; add a Question or Flashcard by hand (Category and covered Requirements chosen); delete with confirmation; pin; Requirement add, edit, delete and priority/kind change with coverage and Gaps updating at once; the Gap banner; the stale-Schedule banner; and editing a day's focus text.

### Acceptance criteria

- [ ] Typing never waits on the network; the edit appears instantly and saves after a pause or on leaving the field
- [ ] Two rapid edits to one item both persist; the item shows Saving then Saved
- [ ] A failed save shows Failed with a working retry and never loses the draft
- [ ] A revision conflict on one item offers Keep mine / Use latest without touching other items
- [ ] Added items appear at once with origin "Yours"; deleted items disappear only after confirmation
- [ ] Pinning toggles the badge and persists
- [ ] Editing a Requirement updates coverage chips and Gaps immediately; deleting a Question's only cover shows the Gap banner without triggering generation
- [ ] Changing Questions or Requirements shows the stale-Schedule banner
- [ ] Mutation-queue unit tests (optimistic apply, debounce, serialisation, rollback, retry, conflict) and editor component tests pass

---

## Phase 6: Reorder and move

**User stories**: 36–40  ·  **Pairs with**: backend Phase 11

### What to build

Reordering within a Category by drag with pointer, touch (long-press) and keyboard; a Move menu on every Question (up, down, to another Category) that is always available and primary on phones; a "Move to day" menu on the Schedule; local ordering computed instantly and confirmed by the server, rolling back with a message on refusal. Moving to another Category counts as an edit.

### Acceptance criteria

- [ ] A Question can be reordered within its Category by mouse, touch and keyboard, and by the Move menu alone
- [ ] A Question can be moved to another Category via the Move menu and then shows as Edited
- [ ] A Question can be moved to another day on the Schedule via the menu
- [ ] The new order appears instantly; a server refusal restores the previous order with a message
- [ ] Order persists across reload and matches the server
- [ ] Reorder moves are announced to assistive technology
- [ ] Ordering unit tests and menu component tests pass

---

## Phase 7: Regeneration

**User stories**: 41–48  ·  **Pairs with**: backend Phase 12

### What to build

Regenerating a Section from the UI: the brief, one Category, or the Schedule. A confirmation states what will be replaced and what is protected ("replaces 6 unprotected Questions, keeps 2 you edited"); only replaceable items dim and show progress while protected items stay editable; new items are badged after completion; an edited or pinned brief yields a stacked current/proposed view with Accept and Reject; the Schedule rebuild warns first; an uncovered Requirement offers "Generate a Question for this"; a failed regeneration leaves the Kit unchanged with a clear message.

### Acceptance criteria

- [ ] The confirmation counts replaced and protected items correctly from item metadata
- [ ] During regeneration, protected items remain editable and unaffected; an edit made mid-run survives completion
- [ ] Regenerated items are badged as new; other Sections are unchanged
- [ ] An edited brief shows a Proposal that can be accepted or rejected; an untouched brief is replaced directly
- [ ] Rebuilding the Schedule warns first and clears the stale banner
- [ ] "Generate a Question for this" closes the Gap without touching other Questions
- [ ] A failed regeneration shows what happened and leaves everything as it was
- [ ] Regeneration-controller unit tests and dialog component tests pass

---

## Phase 8: Practice

**User stories**: 49–55  ·  **Pairs with**: backend Phase 13

### What to build

The Drill: start a Drill of 10 Flashcards from a queue snapshot taken at the start; reveal with space; rate Confidence with 1/2/3 and auto-advance; Backspace undoes the last rating; progress through the Drill; an end summary with "Drill weak cards again"; and a coverage view showing what has and hasn't been covered per Requirement and Category. Reviews save optimistically.

### Acceptance criteria

- [ ] A Drill's order is fixed at the start and does not change as ratings are recorded
- [ ] Space reveals; 1/2/3 rate and advance; Backspace undoes the last rating
- [ ] The whole Drill is operable by keyboard alone and announces position and result
- [ ] The end summary offers to drill the weak cards again, and doing so serves low-Confidence cards first
- [ ] The coverage view reflects reviews immediately and per Requirement and Category
- [ ] Progress survives regenerating a Category
- [ ] Drill-engine unit tests and component tests pass

---

## Phase 9: Weak spots and print one-pager

**User stories**: 56, 57  ·  **Pairs with**: backend Phase 13

### What to build

The weak-spots report (the creative feature): Requirements ranked by readiness with the reasons for each rank and links to the relevant Questions and Flashcards; and a print view that produces a clean one-page summary (brief, Requirements with weak spots, Schedule) via a print stylesheet.

### Acceptance criteria

- [ ] The report lists Requirements in the server's order with reasons (never practised, low Confidence, no Question, no Flashcard) and working links
- [ ] Practising a weak spot's cards changes its rank in the report
- [ ] The print view fits a single page for a typical Kit and is legible in black and white
- [ ] The report and print view are keyboard accessible and have empty states (nothing practised yet)

---

## Phase 10: Polish and proof

**User stories**: 59–64 (quality sweep); optionally 58 if the backend stretch exists  ·  **Pairs with**: backend Phases 14–15

### What to build

The quality pass: a responsive audit of every view at phone and laptop widths; a manual keyboard pass through edit, move, regenerate and Drill; an empty/loading/error sweep for every view; automated accessibility checks on the main views; the end-to-end journey against the real backend in scripted fake-LLM mode; and the frontend sections of the README (setup, architecture, state model for edits and regeneration, design decisions, limitations). If time remains, the keyword answer check UI, labelled "keyword match only".

### Acceptance criteria

- [ ] Every view is usable at phone and laptop widths with no horizontal scrolling
- [ ] Every interactive flow is completable by keyboard alone with visible focus
- [ ] Every view has a designed loading, empty and error state
- [ ] The end-to-end journey passes: register → create → watch → edit a Question → regenerate its Category → the edit survives
- [ ] Automated accessibility checks pass on the main views
- [ ] The frontend README sections exist and let a reader run the app locally
