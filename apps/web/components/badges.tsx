"use client";
import { originBadge, type ItemMeta } from "@/lib/types";

export function OriginBadge({ meta }: { meta?: ItemMeta }) {
  const label = originBadge(meta);
  return (
    <span aria-label={`Origin: ${label}`} className="rounded bg-neutral-100 px-1.5 py-0.5 text-xs dark:bg-neutral-800">
      {label}
    </span>
  );
}

export function CoverageChip({ count, isGap }: { count: number; isGap: boolean }) {
  return isGap ? (
    <span role="status" aria-label="Gap: no Question covers this Requirement" className="rounded bg-red-100 px-1.5 py-0.5 text-xs dark:bg-red-900">
      Gap
    </span>
  ) : (
    <span aria-label={`${count} Questions cover this Requirement`} className="rounded bg-green-100 px-1.5 py-0.5 text-xs dark:bg-green-900">
      {count} covered
    </span>
  );
}
