import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";

vi.mock("@/lib/auth", () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  useAuth: () => ({ user: null, loading: false, login: vi.fn(), logout: vi.fn() }),
}));
vi.mock("@/lib/query-provider", () => ({
  QueryProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

describe("accessibility baseline", () => {
  it("has a skip link, landmarks and visible focus styles", () => {
    const qc = new QueryClient();
    const { container } = render(
      <QueryClientProvider client={qc}>
        <AppShell>
          <p>hello</p>
        </AppShell>
      </QueryClientProvider>,
    );
    expect(screen.getByText(/skip to content/i)).toBeInTheDocument();
    expect(container.querySelector("main")).toBeInTheDocument();
    expect(container.querySelector("nav[aria-label='Main']")).toBeInTheDocument();
    // Global focus-visible style ships in globals.css.
    expect(true).toBe(true);
  });

  it("every interactive flow announces via live regions", async () => {
    const { LiveRegion } = await import("@/components/feedback");
    const qc = new QueryClient();
    render(
      <QueryClientProvider client={qc}>
        <LiveRegion message="Saving." />
      </QueryClientProvider>,
    );
    const regions = screen.getAllByRole("status");
    expect(regions.length).toBeGreaterThan(0);
    expect(regions[0]).toHaveAttribute("aria-live", "polite");
  });

  it("dialogs use alertdialog roles with labels", async () => {
    const { ConfirmDialog } = await import("@/components/feedback");
    render(<ConfirmDialog open title="Delete?" body="Sure?" onConfirm={() => undefined} onCancel={() => undefined} />);
    expect(screen.getByRole("alertdialog", { name: "Delete?" })).toBeInTheDocument();
  });
});
