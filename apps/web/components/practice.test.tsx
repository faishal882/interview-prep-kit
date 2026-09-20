import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PracticeView } from "@/components/practice";

vi.mock("@/lib/kit-cache", () => ({
  useKit: () => ({
    data: {
      kit: {
        role: { requirements: [] },
        questions: [],
        flashcards: [{ id: "f1", front: "Q?", back: "A.", requirement_ids: [] }],
      },
    },
  }),
  kitKeys: { detail: (id: string) => ["kits", id], list: ["kits"] },
}));

vi.mock("@/lib/api-client", () => ({
  PracticeApi: {
    queue: vi.fn(async () => ({ queue: ["f1"] })),
    review: vi.fn(async () => ({ ok: true })),
    summary: vi.fn(async () => ({ total: 1, covered: 0, uncovered: 1 })),
  },
}));

vi.mock("@/components/kit-overview", () => ({ KitNav: () => <nav>nav</nav> }));

describe("practice Drill", () => {
  it("starts a Drill, reveals with Space and rates with 1", async () => {
    const qc = new QueryClient();
    render(
      <QueryClientProvider client={qc}>
        <PracticeView kitId="k" />
      </QueryClientProvider>,
    );
    await userEvent.click(await screen.findByRole("button", { name: /start drill/i }));
    expect(await screen.findByText(/card 1 of 1/i)).toBeInTheDocument();
    await userEvent.keyboard(" ");
    expect(await screen.findByText("A.")).toBeInTheDocument();
    await userEvent.keyboard("1");
    expect(await screen.findByText(/drill summary/i)).toBeInTheDocument();
  });
});
