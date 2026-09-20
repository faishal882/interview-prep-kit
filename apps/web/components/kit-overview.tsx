"use client";
import Link from "next/link";
import { useKit } from "@/lib/kit-cache";

export function KitNav({ kitId }: { kitId: string }) {
  const views = ["role", "questions", "flashcards", "schedule", "practice"];
  return (
    <nav aria-label="Kit views" className="flex flex-wrap gap-2">
      <Link href={`/kits/${kitId}`} className="rounded border px-2 py-1 text-sm underline">
        Overview
      </Link>
      {views.map((v) => (
        <Link key={v} href={`/kits/${kitId}/${v}`} className="rounded border px-2 py-1 text-sm underline">
          {v[0].toUpperCase() + v.slice(1)}
        </Link>
      ))}
      <Link href={`/kits/${kitId}/print`} className="rounded border px-2 py-1 text-sm underline">
        Print
      </Link>
    </nav>
  );
}

// Phase 3 replaces this placeholder with the full Overview view.
export function KitOverview({ kitId }: { kitId: string }) {
  const { data } = useKit(kitId);
  const warnings = data?.kit?.warnings ?? [];
  const uncovered = data?.kit?.coverage?.uncovered_requirement_ids ?? [];
  return (
    <div className="space-y-4">
      <KitNav kitId={kitId} />
      <h1 className="text-xl font-semibold">Kit overview</h1>
      {warnings.length > 0 ? (
        <div role="alert" className="rounded border border-amber-300 bg-amber-50 p-3 text-sm dark:bg-amber-950">
          Partial research: {warnings.join("; ")}
        </div>
      ) : null}
      {uncovered.length > 0 ? (
        <p className="text-sm">Uncovered Requirements: {uncovered.join(", ")}</p>
      ) : null}
      <p className="text-sm text-neutral-500">Full read-only views land in Phase 3.</p>
    </div>
  );
}
