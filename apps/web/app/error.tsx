"use client";
import Link from "next/link";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div role="alert" className="section">
      <span className="eyebrow">Something broke</span>
      <h1 className="kit-display" style={{ fontSize: "clamp(28px, 3vw, 40px)", marginTop: 16 }}>Something broke on this page</h1>
      <p style={{ marginTop: 8, color: "var(--copy)" }}>{error.message || "Unexpected error."}</p>
      <div style={{ marginTop: 20, display: "flex", gap: 12 }}>
        <button onClick={() => reset()} className="button button-secondary button-small">
          Try again
        </button>
        <Link href="/kits" className="button button-small">
          Back to Kits
        </Link>
      </div>
    </div>
  );
}
