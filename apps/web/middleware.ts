import { NextRequest, NextResponse } from "next/server";
import { DEFAULT_RETURN_TO, safeReturnTo, SECURITY_HEADERS } from "@/lib/security";

// Route protection with return-to: signed-out visits to protected routes
// redirect to login and return after signing in (validated in-app path only).
// Auth state lives in the httpOnly session cookie, so middleware treats
// "no session cookie" as signed out. Security headers ride every response.
const PROTECTED = [/^\/kits(\/.*)?$/];

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const headers = new Headers(SECURITY_HEADERS);
  if (!PROTECTED.some((re) => re.test(pathname))) return NextResponse.next({ headers });
  const session = req.cookies.get("session");
  if (session?.value) return NextResponse.next({ headers });
  const url = req.nextUrl.clone();
  url.pathname = "/login";
  url.searchParams.set("returnTo", safeReturnTo(pathname));
  const redirect = NextResponse.redirect(url);
  for (const [key, value] of headers) redirect.headers.set(key, value);
  return redirect;
}

export function validatedReturnTo(raw: string | null): string {
  return safeReturnTo(raw ?? DEFAULT_RETURN_TO);
}

export const config = { matcher: ["/:path*"] };
