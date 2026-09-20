"use client";
import Link from "next/link";
import { useAuth } from "@/lib/auth";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  return (
    <div className="min-h-screen">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:rounded focus:bg-white focus:px-2 focus:py-1">
        Skip to content
      </a>
      <header className="border-b">
        <nav aria-label="Main" className="mx-auto flex max-w-5xl items-center gap-4 p-4">
          <Link href="/kits" className="font-semibold">
            Interview Prep Kit
          </Link>
          <Link href="/kits" className="text-sm underline">
            Kits
          </Link>
          <Link href="/kits/new" className="text-sm underline">
            New Kit
          </Link>
          <span className="ml-auto text-sm">{user ? user.email : ""}</span>
          {user ? (
            <button onClick={() => void logout()} className="rounded border px-2 py-1 text-sm">
              Log out
            </button>
          ) : (
            <Link href="/login" className="text-sm underline">
              Log in
            </Link>
          )}
        </nav>
      </header>
      <main id="main" className="mx-auto max-w-5xl p-4">
        {children}
      </main>
    </div>
  );
}
