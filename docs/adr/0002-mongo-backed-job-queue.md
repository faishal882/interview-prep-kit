# Generation jobs are Mongo documents claimed by a worker loop

Generation takes ~90 seconds, can fail halfway and can be triggered twice, so it
cannot live inside a request. Jobs are documents
`{id, kit_id, user_id, kind, status pending|running|done|failed, steps[], attempts,
heartbeat, error, retryable, deadline}` with kinds for generation and each
regeneration Section. An in-process worker claims them atomically
(`find_one_and_update` / equivalent in-memory claim), heartbeats while running,
enforces `MAX_CONCURRENT_RUNS` and per-user limits, and a recovery loop requeues
a stale job once then fails it retryable. A partial unique index enforces one
active job per Kit. Retry reuses the page cache. Plain in-process fire-and-forget
tasks were rejected because a restart would silently lose work; a broker
(Redis/SQS) was rejected as needless infrastructure for a single instance. The
batch CLI bypasses the queue and calls the pipeline directly. Consequence: we
assume a single API instance and progress is read by polling `GET /api/jobs/{id}`.
