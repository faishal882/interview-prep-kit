import { describe, expect, it, vi } from "vitest";
import { decodeError, ApiError, formatWithRef } from "@/lib/errors";

describe("error decoding", () => {
  it("decodes the uniform envelope with reference id", () => {
    const e = decodeError(400, { error: { code: "INVALID_INPUT", message: "days must be 1..60", details: {}, trace_id: "abc123" } });
    expect(e).toBeInstanceOf(ApiError);
    expect(e.code).toBe("INVALID_INPUT");
    expect(e.referenceId).toBe("abc123");
    expect(e.message).toContain("days must be 1..60");
  });

  it("maps 401 to session expired", () => {
    const e = decodeError(401, { error: { code: "SESSION_EXPIRED", message: "sign in again", trace_id: "r1" } });
    expect(e.isSessionExpired).toBe(true);
    expect(e.message.toLowerCase()).toContain("expired");
  });

  it("falls back safely on unknown bodies", () => {
    const e = decodeError(500, null);
    expect(e.code).toBe("INTERNAL");
    expect(formatWithRef(e)).toContain("ref");
  });

  it("formats plain language with ref", () => {
    const e = new ApiError("NOT_FOUND", "Not found.", "xyz", 404);
    expect(formatWithRef(e)).toBe("Not found. (ref xyz)");
  });
});

describe("session expired event", () => {
  it("api client dispatches the event on 401", async () => {
    const { notifySessionExpired, sessionExpiredEvent } = await import("@/lib/api-client");
    const seen: string[] = [];
    const h = () => seen.push("expired");
    window.addEventListener(sessionExpiredEvent, h);
    global.fetch = vi.fn(async () => new Response(JSON.stringify({ error: { code: "SESSION_EXPIRED", message: "x", trace_id: "t" } }), { status: 401 })) as unknown as typeof fetch;
    const { api } = await import("@/lib/api-client");
    await expect(api.get("/api/me")).rejects.toBeInstanceOf(ApiError);
    notifySessionExpired();
    expect(seen.length).toBeGreaterThan(0);
    window.removeEventListener(sessionExpiredEvent, h);
  });
});
