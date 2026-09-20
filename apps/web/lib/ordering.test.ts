import { describe, expect, it } from "vitest";
import { keyBetween, reorderWithin, moveToCategory } from "@/lib/ordering";

describe("ordering", () => {
  it("generates keys between neighbours", () => {
    expect(keyBetween(null, null)).toBe("a0");
    const k = keyBetween("a0", null);
    expect(k > "a0").toBe(true);
    const mid = keyBetween("a0", "a1");
    expect(mid > "a0" && mid < "a1").toBe(true);
  });

  it("reorders within a Category and matches server semantics", () => {
    const items = [
      { id: "q1", category: "technical", order: "a0" },
      { id: "q2", category: "technical", order: "a1" },
      { id: "q3", category: "technical", order: "a2" },
    ];
    const next = reorderWithin(items, "technical", "q3", null);
    const order = [...next].sort((a, b) => (a.order < b.order ? -1 : 1)).map((q) => q.id);
    expect(order[0]).toBe("q3");
  });

  it("moves to another Category", () => {
    const items = [
      { id: "q1", category: "technical", order: "a0" },
      { id: "q2", category: "behavioural", order: "a0" },
    ];
    const next = moveToCategory(items, "q1", "behavioural");
    expect(next.find((q) => q.id === "q1")?.category).toBe("behavioural");
  });

  it("moving after an id places it right after", () => {
    const items = [
      { id: "q1", category: "technical", order: "a0" },
      { id: "q2", category: "technical", order: "a1" },
      { id: "q3", category: "technical", order: "a2" },
    ];
    const next = reorderWithin(items, "technical", "q1", "q2");
    const order = [...next].sort((a, b) => (a.order < b.order ? -1 : 1)).map((q) => q.id);
    expect(order).toEqual(["q2", "q1", "q3"]);
  });
});
