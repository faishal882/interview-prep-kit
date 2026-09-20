import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { EditingProvider } from "@/lib/editing";
import { EditableField } from "@/components/editable";

vi.mock("@/lib/api-client", () => ({
  ItemsApi: { patch: vi.fn(async () => ({})), remove: vi.fn(async () => ({ ok: true })), create: vi.fn(async () => ({})) },
  SectionsApi: { patchScheduleDay: vi.fn(async () => ({})) },
}));

function wrap() {
  const qc = new QueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <EditingProvider kitId="k1">
        <EditableField collection="questions" itemId="q1" field="prompt" value="orig" label="Prompt" />
      </EditingProvider>
    </QueryClientProvider>,
  );
}

describe("editor states", () => {
  it("shows Saved after an edit pauses", async () => {
    wrap();
    const input = screen.getByLabelText(/prompt/i);
    await userEvent.clear(input);
    await userEvent.type(input, "new prompt");
    expect((await screen.findAllByText(/saving|saved/i)).length).toBeGreaterThan(0);
  });

  it("idle editor has no failure text", () => {
    wrap();
    expect(screen.queryByText(/failed/i)).toBeNull();
  });
});
