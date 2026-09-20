"use client";
import { originBadge, type ItemMeta } from "@/lib/types";

export function OriginBadge({ meta }: { meta?: ItemMeta }) {
  const label = originBadge(meta);
  const cls = label === "Pinned" ? "pill" : label === "Yours" ? "pill pill-teal" : label === "Edited" ? "pill" : "pill pill-neutral";
  return (
    <span aria-label={`Origin: ${label}`} className={cls}>
      {label}
    </span>
  );
}

export function CoverageChip({ count, isGap }: { count: number; isGap: boolean }) {
  return isGap ? (
    <span role="status" aria-label="Gap: no Question covers this Requirement" className="pill pill-red">
      Gap
    </span>
  ) : (
    <span aria-label={`${count} Questions cover this Requirement`} className="pill pill-teal">
      {count} covered
    </span>
  );
}
