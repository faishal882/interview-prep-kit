import { notFound } from "next/navigation";

export default function NotFound() {
  return (
    <div className="section">
      <span className="eyebrow">404</span>
      <h1 className="kit-display" style={{ fontSize: "clamp(28px, 3vw, 40px)", marginTop: 16 }}>Not found</h1>
      <p style={{ marginTop: 8, color: "var(--copy)" }}>That page does not exist.</p>
      <a href="/kits" className="button button-secondary button-small" style={{ marginTop: 20 }}>
        Back to Kits
      </a>
    </div>
  );
}

export function KitNotFound() {
  notFound();
}
