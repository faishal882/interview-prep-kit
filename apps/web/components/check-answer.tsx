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
      <button onClick={() => setOpen(true)} className="mt-1 rounded border px-2 py-0.5 text-xs no-print">
        Self-check my answer
      </button>
    );
  }
  return (
    <div className="mt-2 rounded border p-2 no-print">
      <p className="text-xs font-medium">Self-check (keyword match only)</p>
      <label htmlFor={`answer-${questionId}`} className="sr-only">
        Type your answer
      </label>
      <textarea id={`answer-${questionId}`} value={answer} onChange={(e) => setAnswer(e.target.value)} rows={3} placeholder="Type your answer…" className="mt-1 w-full rounded border px-2 py-1 text-sm" />
      <button onClick={() => void check()} disabled={busy || !answer.trim()} className="mt-1 rounded border px-2 py-0.5 text-xs disabled:opacity-50">
        {busy ? "Checking…" : "Check coverage"}
      </button>
      {results ? (
        <ul className="mt-1 space-y-1 text-xs">
          {results.map((r, i) => (
            <li key={i}>
              {r.covered ? "✓" : "✗"} {r.point}
            </li>
          ))}
        </ul>
      ) : null}
      {limits ? <p className="mt-1 text-xs text-neutral-500">{limits}</p> : null}
    </div>
  );
}
