# Interview Prep Kit

Turns a job description and a company website into a personalised, editable interview preparation kit.

## Language

### Inputs

**Job description (JD)**:
The pasted text of a role that a candidate is preparing for.
_Avoid_: posting, listing, ad

**Case**:
One batch input: an id, a job description, a company website and a number of days.
_Avoid_: job, run, row

**Requirement**:
One independently interviewable claim from a job description, carrying exactly one priority (`must` or `nice`). Alternatives such as "Go or Rust" stay together as one claim; qualifiers such as "5+ years" stay attached.
_Avoid_: skill, criterion, bullet, qualification

### Deliverable

**Kit**:
The generated preparation deliverable for one job description, company website and number of days.
_Avoid_: prep pack, plan, report

**Question**:
An interview question in one category, with an answer outline, that addresses at least one Requirement.
_Avoid_: prompt

**Category**:
The kind of a Question: technical, behavioural, system-design or company-fit.

**Flashcard**:
A front/back recall card tied to one or more Requirements, used in practice.
_Avoid_: card deck entry

**Schedule**:
The distribution of a Kit's Questions across exactly the number of days the candidate has.

**Review day**:
A day in a Schedule that repeats earlier Questions because there are more days than Questions.

**Hiring signal**:
A finding from the company's site or public discussion about how it interviews, such as a take-home or a system-design round.

**Research log**:
The honest record of what was retrieved, what was skipped and why, and what could not be found.

### Generation

**Step**:
One stage of generating a Kit, with its own status shown to the candidate: pending, running, done, skipped (with a reason) or failed.
_Avoid_: stage, phase

### Quality and editing

**Coverage**:
The relation between a Kit's Requirements and the Questions that address them.

**Gap**:
A Requirement that no verified Question addresses.
_Avoid_: hole, miss

**Pass**:
One coverage check, optionally followed by generation aimed at the Gaps it found.
_Avoid_: iteration, round

**Section**:
The unit of regeneration: the company brief, one Category of Questions, or the Schedule.
_Avoid_: tab, part

**Protected item**:
A Kit item that is user-written, edited, or pinned, and which regeneration never removes or overwrites.
_Avoid_: locked item, frozen item

**Proposal**:
A regenerated version of an edited or pinned single-block Section (the company brief) held for the candidate to accept or reject instead of replacing the current text.
_Avoid_: suggestion, draft

### Practice

**Confidence**:
The candidate's self-rating (1–3) of how well they recalled a Flashcard.

**Drill**:
One sitting of practice: a fixed set of Flashcards drawn, in order of least confidence first, from the practice queue.
_Avoid_: session, study session

**Weak spot**:
A Requirement the candidate is least ready on, judged from practice Confidence, Coverage and priority.
_Avoid_: weakness, problem area
