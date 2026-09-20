// Regeneration controller: replaced/protected counts, replaceable tracking,
// new-item marking, brief Proposal, Schedule rebuild warning.
import { isProtectedMeta, type Category, type Question } from "./types";

export interface RegenPlan {
  section: string;
  replaceable: string[];
  protectedIds: string[];
  replacedCount: number;
  protectedCount: number;
  summary: string;
}

export function planRegeneration(section: string, questions: Question[], category?: Category): RegenPlan {
  if (section === "brief" || section === "schedule") {
    return { section, replaceable: [], protectedIds: [], replacedCount: 0, protectedCount: 0, summary: section };
  }
  const inScope = questions.filter((q) => q.category === category);
  const replaceable = inScope.filter((q) => !isProtectedMeta(q._meta)).map((q) => q.id);
  const protectedIds = inScope.filter((q) => isProtectedMeta(q._meta)).map((q) => q.id);
  const summary = `replaces ${replaceable.length} unprotected Question${replaceable.length === 1 ? "" : "s"}, keeps ${protectedIds.length} you edited`;
  return { section, replaceable, protectedIds, replacedCount: replaceable.length, protectedCount: protectedIds.length, summary };
}

export function markNewItems(before: Set<string>, after: Question[]): string[] {
  return after.filter((q) => !before.has(q.id)).map((q) => q.id);
}

export function briefNeedsProposal(briefMeta?: { edited?: boolean; pinned?: boolean }): boolean {
  return Boolean(briefMeta?.edited || briefMeta?.pinned);
}
