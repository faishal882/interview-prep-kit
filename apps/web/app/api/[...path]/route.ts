import { NextResponse } from "next/server";

// Same-origin API: the browser only talks to the web app; /api/* is proxied
// to the backend so cookies stay first-party. Next rewrites (next.config.mjs)
// handle the proxy in production; this route documents the contract for tests.
export async function GET() {
  return NextResponse.json({ ok: true, proxy: "/api/:path* -> API_ORIGIN/api/:path*" });
}
