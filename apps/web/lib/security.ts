// Post-login redirect allowlist: only in-app paths. Absolute URLs,
// protocol-relative URLs and backslash tricks land on the default page.
export const DEFAULT_RETURN_TO = "/kits";

export function safeReturnTo(raw: string | null): string {
  if (!raw) return DEFAULT_RETURN_TO;
  let path = raw;
  // block backslash escapes and control characters
  if (/[\\\x00-\x1f\x7f]/.test(path)) return DEFAULT_RETURN_TO;
  if (!path.startsWith("/")) return DEFAULT_RETURN_TO;
  if (path.startsWith("//")) return DEFAULT_RETURN_TO;
  try {
    const parsed = new URL(path, "http://app.local");
    if (parsed.origin !== "http://app.local") return DEFAULT_RETURN_TO;
    if (!parsed.pathname.startsWith("/")) return DEFAULT_RETURN_TO;
    return parsed.pathname + parsed.search + parsed.hash;
  } catch {
    return DEFAULT_RETURN_TO;
  }
}

// Security headers applied to every response by middleware.
export const SECURITY_HEADERS: Record<string, string> = {
  // Next.js flight data and Tailwind need inline scripts/styles; framing,
  // exfiltration and sniffing protections stay strict.
  "Content-Security-Policy":
    "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; " +
    "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
  "X-Frame-Options": "DENY",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "X-Content-Type-Options": "nosniff",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
};
