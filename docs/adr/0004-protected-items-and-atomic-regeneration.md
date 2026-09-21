# Regeneration preserves edits via per-item state and one atomic array update

Each Kit item carries metadata (origin, edited, pinned, revision, order key); a
Protected item is user-written, edited or pinned. Regenerating a Section calls
the real pipeline steps (brief writer, per-Category question generator, or
targeted generation for one Requirement) — never placeholder text. Category
regeneration replaces only unprotected items, committed as a single-document
pipeline update (`$filter` + `$concatArrays`) that also keeps any item whose
revision changed while the job ran — so an in-flight edit survives. Kept prompts
are passed as an exclusion list so regenerated Questions do not duplicate them.
Coverage is recomputed after every regeneration. An edited or pinned brief
yields a Proposal; an untouched brief is replaced directly. Every regeneration
is a durable job with progress and outcome; provider failure leaves the Kit
byte-for-byte unchanged. Moving a Question to another Category counts as an
edit; reordering within a Category does not. Metadata (including brief metadata)
is stripped on export so the kit matches the brief's structure. Rejected: one
document per item (needs transactions, which standalone Mongo lacks),
snapshot/diff merging (heavy, hard to explain), and pin-only protection (users
would have to pin everything they touch).
