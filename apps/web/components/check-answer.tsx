"use client";
import { useState } from "react";
import { PracticeApi } from "@/lib/api-client";

// Stretch: keyword self-check of a typed answer against a Question's outline,
// clearly labelled as keyword match only.
export function CheckAnswer({ kitId, questionId }: { kitId: string; questionId: string }) {
  const [open, setOpen] = useState(false);
  const [answer, setAnswer] = useState("");
  const [results, setResults] = useState<Array<{ point: string; covered: boolean }> | null>(null);
  const [limits, setLimits] = useState("");
  const [busy, setBusy] = useState(false);

  const check = async () => {
    setBusy(true);
    try {
      const res = await PracticeApi.check(kitId, questionId, answer);
      setResults(res.results);
      setLimits(res.limits);
    } finally {
      setBusy(false);
    }
  };

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="button button-secondary button-small no-print" style={{ marginTop: 8 }}>
        Self-check my answer
      </button>
    );
  }
  return (
    <div className="neu-card-flat no-print" style={{ marginTop: 8 }}>
      <span className="eyebrow">Self-check (keyword match only)</span>
      <label htmlFor={`answer-${questionId}`} className="sr-only">
        Type your answer
      </label>
      <textarea id={`answer-${questionId}`} value={answer} onChange={(e) => setAnswer(e.target.value)} rows={3} placeholder="Type your answer…" className="inset-textarea" style={{ marginTop: 8 }} />
      <button onClick={() => void check()} disabled={busy || !answer.trim()} className="button button-small" style={{ marginTop: 8 }}>
        {busy ? "Checking…" : "Check coverage"}
      </button>
      {results ? (
        <ul className="ruled-list" style={{ marginTop: 8 }}>
          {results.map((r, i) => (
            <li key={i} style={{ padding: "8px 4px", fontSize: 14 }}>
              {r.covered ? "✓" : "✗"} {r.point}
            </li>
          ))}
        </ul>
      ) : null}
      {limits ? <p style={{ marginTop: 8, fontSize: 13, color: "var(--copy)" }}>{limits}</p> : null}
    </div>
  );
}
