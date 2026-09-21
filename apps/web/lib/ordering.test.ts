import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { keyBetween, moveToCategory, needsRebalance, rebalanceKeys, reorderWithin } from "@/lib/ordering";

const here = dirname(fileURLToPath(import.meta.url));
const vectors = JSON.parse(readFileSync(resolve(here, "../../../fixtures/ordering-vectors.json"), "utf8"));

describe("ordering", () => {
  it("generates keys between neighbours", () => {
    expect(keyBetween(null, null)).toBe("h");
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

  it("produces identical keys to the backend for the shared vectors", () => {
    for (const group of vectors) {
      if (group.name === "back-inserts") {
        let prev: string | null = null;
        for (const op of group.ops) {
          expect(keyBetween(prev, null)).toBe(op.key);
          prev = op.key;
        }
      } else if (group.name === "front-inserts") {
        let head: string | null = null;
        for (const op of group.ops) {
          expect(keyBetween(null, head)).toBe(op.key);
          head = op.key;
        }
      } else if (group.name === "bisections" || group.name === "legacy-neighbours") {
        for (const op of group.ops) {
          expect(keyBetween(op.a ?? null, op.b ?? null)).toBe(op.key);
        }
      } else if (group.name.startsWith("rebalance-")) {
        expect(rebalanceKeys(group.count)).toEqual(group.keys);
      }
    }
  });

  it("keeps strict order and uniqueness over random insert sequences", () => {
    let seed = 42;
    const rand = () => {
      seed = (seed * 1103515245 + 12345) % 2147483648;
      return seed / 2147483648;
    };
    for (let trial = 0; trial < 60; trial++) {
      const keys: string[] = [];
      for (let i = 0; i < 25; i++) {
        const ordered = [...keys].sort();
        const r = rand();
        let k: string;
        if (ordered.length === 0 || r < 0.3) k = keyBetween(ordered[ordered.length - 1] ?? null, null);
        else if (r < 0.6) k = keyBetween(null, ordered[0]);
        else {
          const at = Math.floor(rand() * (ordered.length - 1));
          k = keyBetween(ordered[at], ordered[at + 1]);
        }
        keys.push(k);
        const sorted = [...keys].sort();
        // insertion position must match sorted position semantics
        expect(new Set(keys).size).toBe(keys.length);
        for (let j = 1; j < sorted.length; j++) expect(sorted[j - 1] < sorted[j]).toBe(true);
        if (k.length > 32) {
          const fresh = rebalanceKeys(keys.length);
          expect(new Set(fresh).size).toBe(fresh.length);
          keys.length = 0;
          keys.push(...fresh);
        }
      }
    }
  });

  it("rebalances long keys into short ones", () => {
    expect(needsRebalance("h".padEnd(40, "0"))).toBe(true);
    expect(needsRebalance("h")).toBe(false);
  });
});
