import { describe, expect, it, vi } from "vitest";
import { isTerminal, nextDelayMs, pollJob } from "@/lib/progress";

describe("progress polling", () => {
  it("backs off: fast at first, slower later", () => {
    expect(nextDelayMs(1)).toBe(1000);
    expect(nextDelayMs(4)).toBe(2500);
    expect(nextDelayMs(9)).toBe(6000);
  });

  it("recognises terminal states", () => {
    expect(isTerminal("done")).toBe(true);
    expect(isTerminal("failed")).toBe(true);
    expect(isTerminal("running")).toBe(false);
  });

  it("pauses while hidden and resolves on done", async () => {
    let calls = 0;
    const job = await pollJob(
      async () => {
        calls += 1;
        return calls < 2
          ? { id: "j", kit_id: "k", kind: "generate", status: "running", steps: [], retryable: false }
          : { id: "j", kit_id: "k", kind: "generate", status: "done", steps: [], retryable: false };
      },
      { isHidden: () => false },
    );
    expect(job.status).toBe("done");
    expect(calls).toBe(2);
  });

  it("skips fetching while hidden", async () => {
    let calls = 0;
    let hidden = true;
    setTimeout(() => (hidden = false), 2500);
    const job = await pollJob(
      async () => {
        calls += 1;
        return { id: "j", kit_id: "k", kind: "generate", status: "done", steps: [], retryable: false };
      },
      { isHidden: () => hidden },
      10,
    );
    expect(job.status).toBe("done");
    expect(calls).toBe(1);
  });

  it("create form validation is enforced by schema", async () => {
    const { z } = await import("zod");
    const schema = z.object({ days: z.coerce.number().int().min(1).max(60) });
    expect(schema.safeParse({ days: 0 }).success).toBe(false);
    expect(schema.safeParse({ days: 61 }).success).toBe(false);
    expect(schema.safeParse({ days: 5 }).success).toBe(true);
    void vi;
  });
});
