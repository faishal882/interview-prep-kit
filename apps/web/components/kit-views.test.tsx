import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { QuestionsView, RoleView, ScheduleView } from "@/components/kit-views";

vi.mock("@/lib/kit-cache", async (orig) => {
  const actual = (await orig()) as Record<string, unknown>;
  return {
    ...(actual as object),
    useKit: () => ({
      data: {
        kit: {
          company_brief: { summary: "Hi" },
          role: {
            title: "Eng",
            responsibilities: ["ship"],
            requirements: [{ id: "r1", text: "React", kind: "technical", priority: "must" }],
          },
          questions: [],
          flashcards: [],
          schedule: { days: [] },
          coverage: { uncovered_requirement_ids: ["r1"] },
          warnings: [],
        },
      },
    }),
  };
});

vi.mock("@/components/kit-overview", () => ({
  KitNav: () => <nav>nav</nav>,
}));

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient();
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("read views", () => {
  it("Role shows Gap for uncovered Requirement", () => {
    wrap(<RoleView kitId="k" />);
    expect(screen.getByText("Gap")).toBeInTheDocument();
  });

  it("Questions explains empty Category", () => {
    wrap(<QuestionsView kitId="k" />);
    expect(screen.getAllByText(/no Requirements routed here/i).length).toBeGreaterThan(0);
  });

  it("Schedule has an empty state", () => {
    wrap(<ScheduleView kitId="k" />);
    expect(screen.getAllByText(/no schedule/i).length).toBeGreaterThan(0);
  });
});
