// Item mutation queue: optimistic apply, debounce, per-item serialisation,
// rollback, retry, conflict with draft preserved.
export type ItemState = "idle" | "saving" | "saved" | "failed" | "conflict";

export interface QueueEntry {
  key: string;
  state: ItemState;
  draft: unknown;
  serverRev?: number;
  error?: string;
}

type ApplyFn = (key: string, value: unknown) => void;
type WriteFn = (key: string, value: unknown, baseRev?: number) => Promise<{ rev?: number } | unknown>;
type Listener = (states: Record<string, QueueEntry>) => void;

const SAVE_DELAY_MS = 30; // short in tests; UI passes ~600 via scheduleSave caller

export class MutationQueue {
  private entries = new Map<string, QueueEntry>();
  private timers = new Map<string, ReturnType<typeof setTimeout>>();
  private chains = new Map<string, Promise<void>>();
  private listeners = new Set<Listener>();
  constructor(
    private apply: ApplyFn,
    private write: WriteFn,
  ) {}

  subscribe(fn: Listener): () => void {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  private emit(): void {
    const snap: Record<string, QueueEntry> = {};
    this.entries.forEach((v, k) => {
      snap[k] = { ...v };
    });
    this.listeners.forEach((fn) => fn(snap));
  }

  stateOf(key: string): ItemState {
    return this.entries.get(key)?.state ?? "idle";
  }

  entryOf(key: string): QueueEntry | undefined {
    return this.entries.get(key);
  }

  enqueue(key: string, value: unknown, opts: { immediate?: boolean; baseRev?: number } = {}): void {
    this.apply(key, value);
    const prev = this.entries.get(key);
    this.entries.set(key, {
      key,
      state: "saving",
      draft: value,
      serverRev: opts.baseRev ?? prev?.serverRev,
    });
    this.emit();
    if (opts.immediate) {
      this.flush(key);
      return;
    }
    if (this.timers.has(key)) clearTimeout(this.timers.get(key)!);
    this.timers.set(
      key,
      setTimeout(() => this.flush(key), SAVE_DELAY_MS),
    );
  }

  flush(key: string): Promise<void> {
    if (this.timers.has(key)) {
      clearTimeout(this.timers.get(key)!);
      this.timers.delete(key);
    }
    const entry = this.entries.get(key);
    if (!entry || entry.state === "saving" && this.chains.has(key) && entry.draft === undefined) return Promise.resolve();
    const prev = this.chains.get(key) ?? Promise.resolve();
    const next = prev.then(async () => {
      const cur = this.entries.get(key);
      if (!cur) return;
      this.entries.set(key, { ...cur, state: "saving" });
      this.emit();
      try {
        const res = (await this.write(key, cur.draft, cur.serverRev)) as { rev?: number };
        const latest = this.entries.get(key);
        // If a newer draft arrived while writing, keep saving (do not mark saved).
        if (latest && latest.draft !== cur.draft) return;
        this.entries.set(key, { key, state: "saved", draft: cur.draft, serverRev: res?.rev ?? cur.serverRev });
        this.emit();
      } catch (e: unknown) {
        const err = e as { code?: string; status?: number };
        const cur2 = this.entries.get(key);
        if (!cur2) return;
        if (err?.code === "CONFLICT" || err?.status === 409) {
          this.entries.set(key, { ...cur2, state: "conflict", error: "Changed elsewhere. Your draft is kept." });
        } else {
          this.entries.set(key, { ...cur2, state: "failed", error: e instanceof Error ? e.message : "Save failed" });
        }
        this.emit();
      }
    });
    this.chains.set(key, next);
    return next;
  }

  retry(key: string): Promise<void> {
    const cur = this.entries.get(key);
    if (!cur) return Promise.resolve();
    this.entries.set(key, { ...cur, state: "saving" });
    this.emit();
    // Force a fresh chain attempt with the preserved draft.
    this.chains.set(key, Promise.resolve());
    return this.flush(key);
  }

  /** Resolve a conflict: keepMine rewrites server with draft, useLatest drops draft. */
  async resolve(key: string, which: "mine" | "latest", fetchLatest?: () => Promise<{ value: unknown; rev?: number }>): Promise<void> {
    const cur = this.entries.get(key);
    if (!cur) return;
    if (which === "mine") {
      this.entries.set(key, { ...cur, state: "saving" });
      this.emit();
      this.chains.set(key, Promise.resolve());
      await this.flush(key);
      return;
    }
    if (fetchLatest) {
      const latest = await fetchLatest();
      this.apply(key, latest.value);
      this.entries.set(key, { key, state: "idle", draft: latest.value, serverRev: latest.rev });
      this.emit();
    } else {
      this.entries.set(key, { key, state: "idle", draft: cur.draft });
      this.emit();
    }
  }

  rollback(key: string, previous: unknown): void {
    this.apply(key, previous);
    this.entries.set(key, { key, state: "failed", draft: previous, error: "Rolled back" });
    this.emit();
  }
}
