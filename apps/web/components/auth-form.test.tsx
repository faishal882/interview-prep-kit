import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/lib/auth";
import { LoginForm } from "@/components/auth-form";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

function ui() {
  const qc = new QueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <LoginForm />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("auth screens", () => {
  it("shows field-level errors for bad input", async () => {
    ui();
    await userEvent.click(screen.getByRole("button", { name: /log in/i }));
    expect(await screen.findByText(/valid email/i)).toBeInTheDocument();
  });

  it("shows plain-language server error with ref on wrong credentials", async () => {
    global.fetch = vi.fn(async () => new Response(JSON.stringify({ error: { code: "UNAUTHORIZED", message: "bad", trace_id: "ref9" } }), { status: 401 })) as unknown as typeof fetch;
    ui();
    await userEvent.type(screen.getByLabelText(/email/i), "a@b.co");
    await userEvent.type(screen.getByLabelText(/password/i), "password123");
    await userEvent.click(screen.getByRole("button", { name: /log in/i }));
    expect(await screen.findByText(/ref9/)).toBeInTheDocument();
  });
});
