import { describe, expect, it } from "vitest";
import { parseBatchFile } from "@/components/batch-upload";

describe("batch upload parsing", () => {
  it("accepts a valid file and previews the count", () => {
    const { entries } = parseBatchFile(JSON.stringify([{ jd: "x".repeat(30), days: 5 }]));
    expect(entries).toHaveLength(1);
  });

  it("rejects invalid JSON clearly", () => {
    expect(parseBatchFile("not json").error).toMatch(/invalid json/i);
  });

  it("rejects more than 10 entries as a whole", () => {
    const big = JSON.stringify(Array.from({ length: 11 }, (_, i) => ({ id: `e${i}`, jd: "x".repeat(30), days: 5 })));
    expect(parseBatchFile(big).error).toMatch(/at most 10/i);
  });

  it("rejects a non-array shape", () => {
    expect(parseBatchFile(JSON.stringify({ jd: "x" })).error).toMatch(/array/i);
  });
});
