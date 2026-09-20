"use client";
import Link from "next/link";
import { OverviewView } from "@/components/kit-views";

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

export function KitOverview({ kitId }: { kitId: string }) {
  return <OverviewView kitId={kitId} />;
}
