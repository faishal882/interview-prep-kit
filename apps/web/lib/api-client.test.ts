import { afterEach, describe, expect, it, vi } from "vitest";
import { api, sessionExpiredEvent } from "./api-client";

function respondUnauthorized() {
  global.fetch = vi.fn(
    async () => new Response(JSON.stringify({ error: { code: "UNAUTHORIZED", message: "not signed in", trace_id: "t1" } }), { status: 401 }),
  ) as unknown as typeof fetch;
}

describe("401 handling", () => {
  afterEach(() => vi.restoreAllMocks());

  it.each(["/api/me", "/api/auth/login", "/api/auth/register"])("does not signal session expiry for %s", async (path) => {
    respondUnauthorized();
    const expired = vi.fn();
    window.addEventListener(sessionExpiredEvent, expired);
    await expect(api.get(path)).rejects.toMatchObject({ status: 401 });
    window.removeEventListener(sessionExpiredEvent, expired);
    expect(expired).not.toHaveBeenCalled();
  });

  it("signals session expiry when an ordinary call is unauthorized", async () => {
    respondUnauthorized();
    const expired = vi.fn();
    window.addEventListener(sessionExpiredEvent, expired);
    await expect(api.get("/api/kits")).rejects.toMatchObject({ status: 401 });
    window.removeEventListener(sessionExpiredEvent, expired);
    expect(expired).toHaveBeenCalledTimes(1);
  });
});
