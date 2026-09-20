import { NextRequest, NextResponse } from "next/server";

// Route protection with return-to: signed-out visits to protected routes
// redirect to login and return after signing in. Auth state lives in the
// httpOnly session cookie, so middleware treats "no session cookie" as signed out.
const PROTECTED = [/^\/kits(\/.*)?$/];

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  if (!PROTECTED.some((re) => re.test(pathname))) return NextResponse.next();
  const session = req.cookies.get("session");
  if (session?.value) return NextResponse.next();
  const url = req.nextUrl.clone();
  url.pathname = "/login";
  url.searchParams.set("returnTo", pathname);
  return NextResponse.redirect(url);
}

export const config = { matcher: ["/kits/:path*"] };
