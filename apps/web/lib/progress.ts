// Generation progress polling: backoff (fast at first, slower later), paused
// while the tab is hidden, resolves to terminal states.
import type { Job } from "./types";

export function nextDelayMs(attempt: number): number {
  if (attempt <= 2) return 1000;
  if (attempt <= 5) return 2500;
  return 6000;
}

export function isTerminal(status: string): boolean {
  return status === "done" || status === "failed";
}

export interface PollOptions {
  isHidden?: () => boolean;
  onJob?: (job: Job) => void;
}

export async function pollJob(
  fetchJob: () => Promise<Job>,
  opts: PollOptions = {},
  maxAttempts = 120,
): Promise<Job> {
  let attempt = 0;
  for (;;) {
    attempt += 1;
    if (!opts.isHidden?.()) {
      const job = await fetchJob();
      opts.onJob?.(job);
      if (isTerminal(job.status)) return job;
    }
    if (attempt >= maxAttempts) throw new Error("Timed out waiting for generation.");
    const d = nextDelayMs(attempt);
    await new Promise((r) => setTimeout(r, d));
  }
}

export function elapsedMs(startedAt?: string | null, finishedAt?: string | null): number | null {
  if (!startedAt) return null;
  const s = Date.parse(startedAt);
  if (Number.isNaN(s)) return null;
  const e = finishedAt ? Date.parse(finishedAt) : Date.now();
  return Math.max(0, e - s);
}
