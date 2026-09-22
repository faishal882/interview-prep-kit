# Walkthrough video script (target 3:30, hard limit 4:00)

The brief asks for 3–4 minutes covering five things, in this order: (1) create a Kit end to end, (2) research and generation steps plus the second pass closing a coverage gap, (3) editing, reordering and a regeneration that keeps your edits, (4) practice mode and the schedule, (5) your custom feature and one design decision you would defend. "Clarity matters more than production value."

Narration below is about 480 words, which is roughly 3:30 at a relaxed pace. Read it aloud once with a timer before recording.

## Before you hit record

- [ ] Backend, frontend and MongoDB are running. Sign in first so the recording starts inside the app.
- [ ] Use a clean browser profile or incognito with extensions off (Grammarly injected attributes and caused a hydration warning in the console earlier). Zoom the page to 125% so text is readable at 1080p.
- [ ] Pick a real posting whose company site has a hiring or careers page, and paste that posting. Use 5 days.
- [ ] Generation takes about 90 seconds. Record it live, then speed up the waiting part 4x in the edit. Do not narrate over dead air.
- [ ] Generate a backup Kit the day before with the same posting. If the live run fails on camera, cut to the backup.
- [ ] The coverage gap is not guaranteed on any single run. Before recording, open the job or research log of your backup Kit and check whether the second pass actually closed a gap. If none did, use the fallback in section 2 below.
- [ ] Do a full dry run with the backup Kit: edit a question, pin one, add one by hand, then regenerate that category, so you know what survives.
- [ ] The brief also requires a deployment link with frontend and backend both reachable. If you have deployed by recording time, record against the live URL. Otherwise localhost is fine for the video, but the form still needs a live URL.

## Script

| Time | On screen | Say |
|---|---|---|
| 0:00 to 0:12 | Kits page, then click New Kit | "Hi, I'm Faishal. This is Interview Prep Kit. You give it a job description and a company website, and it researches the company, builds a prep kit, and schedules your study days. Let me create one." |
| 0:12 to 0:57 | Paste description, paste company URL, set 5 days, click Generate. Show the progress screen with each step turning done. (Sped up in the edit.) | "I paste the posting, add the company site and choose five days. Generation runs as a background job, so I can watch each step. It extracts the requirements, crawls the company's own site, respecting robots.txt, looks for a hiring page, searches public discussion, and then generates each question category separately. Then comes the second pass. Coverage is checked in code, not by asking the model: every must-have requirement needs at least one question. Any gap gets a targeted extra round, up to three passes in total. Here it found gaps and closed them." |
| 0:57 to 1:22 | Kit overview: company brief, hiring process, research log, Coverage card reading "All Requirements covered." | "Here is the result: a company brief, the hiring process we found, and the research log showing which pages were actually read. Coverage says every requirement is covered. If a site had no hiring page, the Kit says so plainly instead of inventing one." |
| 1:22 to 2:12 | Questions tab. Edit an answer outline inline. Pin one question. Drag one question up, then use the Move menu to move another into a different category. Add a question by hand. Click Regenerate on that category and confirm. | "Everything is editable inline. I rewrite this answer outline, pin this question, drag this one up, and use the Move menu to put another into a different category. I add my own question by hand. Now I regenerate this category. The model writes fresh questions, but everything I wrote, edited, pinned or moved is still here, and only the untouched ones were replaced. Each item carries its origin, an edited flag, a pinned flag and a revision. Regeneration swaps only unprotected items in one atomic update, and it keeps anything whose revision changed while it was running, so an edit made mid-generation is never lost." |
| 2:12 to 2:47 | Practice tab: start a Drill, reveal a card, rate confidence with Space, 1, 2, 3. Show the coverage panel. Switch to the Schedule tab and scroll the days. | "In practice mode I step through flashcards, reveal the answer and record my confidence from the keyboard. The next drill puts the cards I was least sure about first. I chose a confidence-weighted sort because it is simple and easy to explain. The coverage panel shows what I have not touched yet. The schedule spans exactly the five days I asked for, in whole minutes, with harder and higher-priority material earlier, and every must-have appears somewhere." |
| 2:47 to 3:22 | Weak spots report. Then a question's answer check: type a short answer and show the covered and missing outline points. | "Two extras. A weak-spots report ranks requirements by confidence, coverage and priority, with the reason for each. And an answer check: I type my answer and it marks which outline points I covered. It is literal keyword matching with no extra model calls, and the interface says it is not a quality judgment. The design decision I would defend: coverage and edit protection live in code, not in prompts. Coverage is set arithmetic. Edits are protected by revisions and one atomic write. I rejected one document per item because it needs transactions, and pin-only protection because users would have to pin everything they touch." |
| 3:22 to 3:30 | Repo page or the Kit overview | "The code, README, decision records and tests are in the repo. Thanks for watching." |

## Section 2 fallback (if no gap was closed on your run)

Do not claim a gap was closed if it was not. Say instead: "On this run the first pass already covered everything. When it does not, the uncovered requirements are listed as Gaps, and this button generates a question for exactly that requirement." Then show an existing Gap and click "Generate a Question for this", or open a Kit from the same posting where the second pass did close one.

## If you finish under 3:20

Add one of these, 10 seconds each, in this order: the honest "We could not retrieve hiring information for this company" banner on a Kit whose site has no hiring page; the Print tab one-page view; the batch command (`npm run evaluate`) finishing five cases with one recorded failure.

## If you run over 4:00

Cut, in this order: the drag reorder (keep the Move menu), the answer check, the Print mention. Never cut the regeneration-keeps-edits demo. The brief says reviewers will look most closely at it.
