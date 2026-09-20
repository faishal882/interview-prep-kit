import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MoveMenu } from "@/components/move-menu";

vi.mock("@/lib/kit-cache", () => ({
  useKit: () => ({ data: undefined }),
  kitKeys: { detail: (id: string) => ["kits", id], list: ["kits"] },
}));
vi.mock("@/lib/api-client", () => ({
  ItemsApi: { reorder: vi.fn(async () => ({})) },
}));

describe("Move menu", () => {
  it("offers up, down and cross-Category moves", () => {
    const qc = new QueryClient();
    const siblings = [
      { id: "q1", requirement_ids: [], category: "technical", prompt: "a", answer_outline: "", difficulty: 1 },
      { id: "q2", requirement_ids: [], category: "technical", prompt: "b", answer_outline: "", difficulty: 1 },
    ] as never as Parameters<typeof MoveMenu>[0]["siblings"];
    render(
      <QueryClientProvider client={qc}>
        <MoveMenu kitId="k" question={siblings[1] as never} siblings={siblings} />
      </QueryClientProvider>,
    );
    expect(screen.getByRole("button", { name: /move q2 up/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/move q2 to category/i)).toBeInTheDocument();
  });
});
