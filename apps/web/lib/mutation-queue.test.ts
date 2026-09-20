import { describe, expect, it, vi } from "vitest";
import { MutationQueue } from "@/lib/mutation-queue";

function setup(write: (key: string, value: unknown) => Promise<unknown>) {
  const applied: Array<{ key: string; value: unknown }> = [];
  const q = new MutationQueue(
    (k, v) => applied.push({ key: k, value: v }),
    write,
  );
  return { q, applied };
}

describe("mutation queue", () => {
  it("applies optimistically at once", () => {
    const { q, applied } = setup(async () => ({}));
    q.enqueue("a", "hello");
    expect(applied).toEqual([{ key: "a", value: "hello" }]);
    expect(q.stateOf("a")).toBe("saving");
  });

  it("debounces then saves and marks saved", async () => {
    const { q } = setup(async () => ({ rev: 2 }));
    q.enqueue("a", "v1");
    await q.flush("a");
    expect(q.stateOf("a")).toBe("saved");
    expect(q.entryOf("a")?.serverRev).toBe(2);
  });

  it("serialises two rapid edits so no update is lost (last draft wins, containing both)", async () => {
    const seen: unknown[] = [];
    const { q } = setup(async (_k, v) => {
      seen.push(v);
      await new Promise((r) => setTimeout(r, 10));
      return {};
    });
    // Same field edited twice fast: the second draft contains the first edit's text.
    q.enqueue("a", "v1", { immediate: true });
    q.enqueue("a", "v1+v2", { immediate: true });
    await q.flush("a");
    await new Promise((r) => setTimeout(r, 50));
    expect(seen[seen.length - 1]).toBe("v1+v2");
    expect(q.stateOf("a")).toBe("saved");
  });

  it("rolls back state on failure and retries", async () => {
    let fail = true;
    const { q } = setup(async () => {
      if (fail) throw Object.assign(new Error("boom"), { code: "INTERNAL" });
      return {};
    });
    q.enqueue("a", "v1", { immediate: true });
    await q.flush("a");
    expect(q.stateOf("a")).toBe("failed");
    fail = false;
    await q.retry("a");
    expect(q.stateOf("a")).toBe("saved");
  });

  it("surfaces revision conflict with draft preserved", async () => {
    const { q } = setup(async () => {
      throw Object.assign(new Error("stale"), { code: "CONFLICT", status: 409 });
    });
    q.enqueue("a", "mine", { immediate: true });
    await q.flush("a");
    expect(q.stateOf("a")).toBe("conflict");
    expect(q.entryOf("a")?.draft).toBe("mine");
  });

  it("rollback restores the previous value", () => {
    const { q, applied } = setup(async () => ({}));
    q.enqueue("a", "new");
    q.rollback("a", "old");
    expect(applied[applied.length - 1]).toEqual({ key: "a", value: "old" });
    expect(q.stateOf("a")).toBe("failed");
  });
});
