"use client";
import { use } from "react";
import { useKit } from "@/lib/kit-cache";
import { ErrorState, Skeleton } from "@/components/feedback";
import { formatWithRef } from "@/lib/errors";

// Print view: clean one-page summary (brief, Requirements with weak spots, Schedule).
export default function PrintPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data, isLoading, isError, error, refetch } = useKit(id);
  if (isLoading) return <Skeleton label="Loading print view" />;
  if (isError)
    return <ErrorState message={formatWithRef(error)} referenceId={(error as { referenceId?: string })?.referenceId} onRetry={() => void refetch()} />;
  const kit = data?.kit;
  const reqs = kit?.role?.requirements ?? [];
  const uncovered = new Set(kit?.coverage?.uncovered_requirement_ids ?? []);
  const days = kit?.schedule?.days ?? [];
  return (
    <div className="section" style={{ color: "var(--ink)" }}>
      <button onClick={() => window.print()} className="button button-secondary no-print">
        Print / save
      </button>
      <span className="eyebrow no-print" style={{ marginLeft: 12 }}>One page</span>
      <h1 className="kit-display" style={{ fontSize: "clamp(28px, 3vw, 40px)", marginTop: 16 }}>Interview prep — one page</h1>
      <section aria-label="Brief" className="neu-card" style={{ marginTop: 20 }}>
        <h2 className="kit-display" style={{ fontSize: 17 }}>Brief</h2>
        <p style={{ marginTop: 8 }}>{kit?.company_brief?.summary || "—"}</p>
      </section>
      <section aria-label="Requirements" className="neu-card" style={{ marginTop: 16 }}>
        <h2 className="kit-display" style={{ fontSize: 17 }}>Requirements and weak spots</h2>
        <ul style={{ paddingLeft: 20, marginTop: 8 }}>
          {reqs.map((r) => (
            <li key={r.id}>
              {r.text} [{r.priority}]{uncovered.has(r.id) ? " — Gap: no Question" : ""}
            </li>
          ))}
        </ul>
      </section>
      <section aria-label="Schedule" className="neu-card" style={{ marginTop: 16 }}>
        <h2 className="kit-display" style={{ fontSize: 17 }}>Schedule</h2>
        <ol style={{ paddingLeft: 20, marginTop: 8 }}>
          {days.map((d) => (
            <li key={d.day}>
              Day {d.day}: {d.focus} ({d.minutes} min)
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
