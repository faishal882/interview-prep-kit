"use client";
import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/lib/auth";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <div>
      <a href="#main" className="sr-only">
        Skip to content
      </a>
      <header className="site-header">
        <div className="nav-shell">
          <Link href="/kits" className="brand-lockup" aria-label="Interview Prep Kit home">
            <span className="brand-mark" aria-hidden="true">
              ✦
            </span>
            Interview Prep Kit
          </Link>
          <nav aria-label="Main" className="desktop-nav">
            <Link href="/kits">Kits</Link>
            <Link href="/kits/new">New Kit</Link>
          </nav>
          {user ? <span className="nav-user">{user.email}</span> : null}
          <span className="desktop-cta">
            {user ? (
              <button onClick={() => void logout()} className="button button-secondary button-small">
                Log out
              </button>
            ) : (
              <Link href="/login" className="button button-small">
                Log in
              </Link>
            )}
          </span>
          <button
            className="menu-button"
            aria-expanded={menuOpen}
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            onClick={() => setMenuOpen((o) => !o)}
          >
            <span />
            <span />
            <span />
          </button>
          {menuOpen ? (
            <nav aria-label="Mobile" className="mobile-nav">
              <Link href="/kits" onClick={() => setMenuOpen(false)}>
                Kits
              </Link>
              <Link href="/kits/new" onClick={() => setMenuOpen(false)}>
                New Kit
              </Link>
              {user ? (
                <button
                  onClick={() => {
                    setMenuOpen(false);
                    void logout();
                  }}
                  className="button button-secondary button-small"
                >
                  Log out ({user.email})
                </button>
              ) : (
                <Link href="/login" className="button button-small" onClick={() => setMenuOpen(false)}>
                  Log in
                </Link>
              )}
            </nav>
          ) : null}
        </div>
      </header>
      <main id="main">
        <div className="frame">{children}</div>
      </main>
      <footer className="kit-footer">
        <div>
          <span className="brand-lockup" style={{ color: "#fff" }}>
            <span className="brand-mark" aria-hidden="true">
              ✦
            </span>
            Interview Prep Kit
          </span>
          <p>Turn a job description into evidence-backed interview preparation.</p>
        </div>
        <nav aria-label="Footer">
          <Link href="/kits">Kits</Link>
          <Link href="/kits/new">New Kit</Link>
        </nav>
      </footer>
    </div>
  );
}
