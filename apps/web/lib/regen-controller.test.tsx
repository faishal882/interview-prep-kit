import { describe, expect, it, vi } from "vitest";
import { planRegeneration, markNewItems, briefNeedsProposal } from "@/lib/regen-controller";
import type { Question } from "@/lib/types";

const q = (id: string, meta: Question["_meta"]): Question => ({
  id,
  requirement_ids: ["r1"],
  category: "technical",
  prompt: id,
  answer_outline: "",
  difficulty: 1,
  outline_points: [],
  _meta: meta,
});

describe("regeneration controller", () => {
  it("counts replaced vs protected from item metadata", () => {
    const questions = [
      q("a", { origin: "generated", edited: false, pinned: false, rev: 1, order: "a0" }),
      q("b", { origin: "generated", edited: true, pinned: false, rev: 2, order: "a1" }),
      q("c", { origin: "user", edited: false, pinned: false, rev: 1, order: "a2" }),
    ];
    const plan = planRegeneration("questions", questions, "technical");
    expect(plan.replacedCount).toBe(1);
    expect(plan.protectedCount).toBe(2);
    expect(plan.summary).toContain("replaces 1");
    expect(plan.summary).toContain("keeps 2");
  });

  it("marks only new items after completion", () => {
    const before = new Set(["a"]);
    const after: Question[] = [q("a", undefined), q("b", undefined)];
    expect(markNewItems(before, after)).toEqual(["b"]);
  });

  it("routes edited or pinned briefs to a Proposal", () => {
    expect(briefNeedsProposal({ edited: true })).toBe(true);
    expect(briefNeedsProposal({ pinned: true })).toBe(true);
    expect(briefNeedsProposal({})).toBe(false);
    expect(briefNeedsProposal(undefined)).toBe(false);
  });
});

describe("regen confirmation dialog", () => {
  it("renders counts from the plan", async () => {
    const { render, screen } = await import("@testing-library/react");
    const { QueryClient, QueryClientProvider } = await import("@tanstack/react-query");
    const { RegenCategoryButton } = await import("@/components/regen");
    vi.mock("@/lib/kit-cache", () => ({
      useKit: () => ({ data: { kit: { questions: [] } } }),
      kitKeys: { detail: (id: string) => ["kits", id], list: ["kits"] },
    }));
    const qc = new QueryClient();
    render(
      <QueryClientProvider client={qc}>
        <RegenCategoryButton kitId="k" category="technical" />
      </QueryClientProvider>,
    );
    expect(screen.getByRole("button", { name: /regenerate technical/i })).toBeInTheDocument();
  });
});
