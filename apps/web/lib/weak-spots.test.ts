import { describe, expect, it } from "vitest";
import { rankWeakSpots } from "@/lib/weak-spots";

describe("weak spots ranking", () => {
  it("ranks a never-practised must with no Question above a practised nice", () => {
    const reqs = [
      { id: "r1", text: "Must know X", kind: "technical", priority: "must" },
      { id: "r2", text: "Nice Y", kind: "technical", priority: "nice" },
    ] as Parameters<typeof rankWeakSpots>[0];
    const questions = [{ id: "q1", requirement_ids: ["r2"], category: "technical", prompt: "p", answer_outline: "", difficulty: 1 }] as Parameters<typeof rankWeakSpots>[1];
    const cards = [{ id: "f2", front: "a", back: "b", requirement_ids: ["r2"] }] as Parameters<typeof rankWeakSpots>[2];
    const spots = rankWeakSpots(reqs, questions, cards, { f2: { last: 3, count: 2 } });
    expect(spots[0].requirement_id).toBe("r1");
    expect(spots[0].reasons).toContain("never practised");
    expect(spots[0].reasons).toContain("no Question");
  });

  it("states low Confidence as a reason", () => {
    const reqs = [{ id: "r1", text: "X", kind: "technical", priority: "must" }] as Parameters<typeof rankWeakSpots>[0];
    const cards = [{ id: "f1", front: "a", back: "b", requirement_ids: ["r1"] }] as Parameters<typeof rankWeakSpots>[2];
    const spots = rankWeakSpots(reqs, [], cards, { f1: { last: 1, count: 1 } });
    expect(spots[0].reasons).toContain("low Confidence");
  });
});
