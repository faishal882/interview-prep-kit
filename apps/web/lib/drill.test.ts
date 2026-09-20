import { describe, expect, it } from "vitest";
import { startDrill, reveal, rate, undoLast, isFinished, weakCardIds, coverageOf } from "@/lib/drill";

const cards = [
  { id: "f1", front: "a", back: "b" },
  { id: "f2", front: "c", back: "d" },
  { id: "f3", front: "e", back: "f" },
];

describe("drill engine", () => {
  it("fixes the queue at Drill start", () => {
    const s = startDrill(cards, ["f3", "f1", "f2"], 10);
    expect(s.cards.map((c) => c.id)).toEqual(["f3", "f1", "f2"]);
  });

  it("reveals, rates 1-3 and auto-advances", () => {
    let s = startDrill(cards, ["f1", "f2"], 10);
    s = reveal(s);
    expect(s.revealed).toBe(true);
    s = rate(s, 2);
    expect(s.position).toBe(1);
    expect(s.revealed).toBe(false);
    expect(s.ratings).toEqual([{ id: "f1", confidence: 2 }]);
  });

  it("undoes the last rating with Backspace semantics", () => {
    let s = startDrill(cards, ["f1", "f2"], 10);
    s = rate(s, 1);
    s = rate(s, 3);
    s = undoLast(s);
    expect(s.position).toBe(1);
    expect(s.ratings).toEqual([{ id: "f1", confidence: 1 }]);
  });

  it("finishes and summarises weak cards for re-drill", () => {
    let s = startDrill(cards, ["f1", "f2"], 10);
    s = rate(s, 1);
    s = rate(s, 3);
    expect(isFinished(s)).toBe(true);
    expect(weakCardIds(s)).toEqual(["f1"]);
  });

  it("reports coverage", () => {
    expect(coverageOf(10, 4)).toEqual({ rated: 4, total: 10, pct: 40 });
  });
});
