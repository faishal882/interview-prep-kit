import { describe, expect, it } from "vitest";
import { safeReturnTo, SECURITY_HEADERS } from "@/lib/security";
import { middleware } from "@/middleware";
import { NextRequest } from "next/server";

describe("post-login redirect validation", () => {
  it("accepts in-app paths with query and hash", () => {
    expect(safeReturnTo("/kits/abc")).toBe("/kits/abc");
    expect(safeReturnTo("/kits/abc?x=1#y")).toBe("/kits/abc?x=1#y");
  });

  it("rejects absolute and protocol-relative URLs", () => {
    expect(safeReturnTo("https://evil.test/x")).toBe("/kits");
    expect(safeReturnTo("//evil.test/x")).toBe("/kits");
    expect(safeReturnTo("javascript:alert(1)")).toBe("/kits");
    expect(safeReturnTo("")).toBe("/kits");
    expect(safeReturnTo(null)).toBe("/kits");
  });

  it("rejects backslash and control-character tricks", () => {
    expect(safeReturnTo("/\\evil.test")).toBe("/kits");
    expect(safeReturnTo("/kits\n")).toBe("/kits");
  });
});

describe("security headers", () => {
  it("defines framing, referrer, sniffing, permissions and CSP headers", () => {
    expect(SECURITY_HEADERS["X-Frame-Options"]).toBe("DENY");
    expect(SECURITY_HEADERS["X-Content-Type-Options"]).toBe("nosniff");
    expect(SECURITY_HEADERS["Referrer-Policy"]).toContain("strict-origin");
    expect(SECURITY_HEADERS["Permissions-Policy"]).toContain("camera=()");
    expect(SECURITY_HEADERS["Content-Security-Policy"]).toContain("frame-ancestors 'none'");
  });

  it("middleware attaches headers and guards returnTo", () => {
    const res = middleware(new NextRequest("http://app.test/kits/abc") as never);
    expect(res.headers.get("X-Frame-Options")).toBe("DENY");
    expect(res.headers.get("Content-Security-Policy")).toContain("frame-ancestors");
    const location = res.headers.get("location") ?? "";
    expect(location).toContain("/login?returnTo=%2Fkits%2Fabc");
  });

  it("middleware lets signed-in users through with headers", () => {
    const req = new NextRequest("http://app.test/kits/abc", {
      headers: { cookie: "session=tok" },
    }) as never;
    const res = middleware(req);
    expect(res.headers.get("X-Content-Type-Options")).toBe("nosniff");
  });
});
