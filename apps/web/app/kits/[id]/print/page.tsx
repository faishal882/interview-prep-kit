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
    <div className="space-y-4 text-black">
      <button onClick={() => window.print()} className="no-print rounded border px-3 py-1.5 text-sm">
        Print / save
      </button>
      <h1 className="text-xl font-bold">Interview prep — one page</h1>
      <section aria-label="Brief">
        <h2 className="font-semibold">Brief</h2>
        <p className="text-sm">{kit?.company_brief?.summary || "—"}</p>
      </section>
      <section aria-label="Requirements">
        <h2 className="font-semibold">Requirements and weak spots</h2>
        <ul className="list-disc pl-5 text-sm">
          {reqs.map((r) => (
            <li key={r.id}>
              {r.text} [{r.priority}]{uncovered.has(r.id) ? " — Gap: no Question" : ""}
            </li>
          ))}
        </ul>
      </section>
      <section aria-label="Schedule">
        <h2 className="font-semibold">Schedule</h2>
        <ol className="list-decimal pl-5 text-sm">
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
