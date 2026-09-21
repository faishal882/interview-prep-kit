// Vocabulary per CONTEXT.md: Kit, Requirement, Question, Flashcard, Schedule,
// Review day, Gap, Drill, Weak spot, Proposal, Step, Category, Coverage, Pass,
// Section, Protected item, Confidence, Hiring signal, Research log.
//
// Response shapes come from the generated API contract (lib/api-types.ts,
// produced from the single committed OpenAPI document). This module adds the
// metadata extension the API carries alongside items, UI conveniences, and
// the domain vocabulary. There are no hand-written response duplicates.

import type {
  CoverageOut,
  FlashcardOut,
  ItemMeta,
  JobOut,
  JobStepOut,
  KitInputOut,
  KitSummaryOut,
  ProposalOut,
  QuestionOut,
  RequirementOut,
  ScheduleDayOut,
  ErrorInfo,
} from "./api-types";

export type Priority = "must" | "nice";
export type Kind = "technical" | "behavioural" | "domain";
export type Category = "technical" | "behavioural" | "system-design" | "company-fit";
export type StepStatus = "pending" | "running" | "done" | "skipped" | "failed";
export type JobStatus = "pending" | "running" | "done" | "failed";
export type ItemOrigin = "generated" | "user";

export type { ItemMeta };
export type Proposal = ProposalOut;
export type KitInput = KitInputOut;
export type KitErrorInfo = ErrorInfo;

export interface Requirement extends RequirementOut {
  kind: Kind;
  priority: Priority;
  _meta?: ItemMeta | null;
}

export interface Question extends QuestionOut {
  category: Category;
  _meta?: ItemMeta | null;
}

export interface Flashcard extends FlashcardOut {
  _meta?: ItemMeta | null;
}

export interface ScheduleDay extends ScheduleDayOut {
  is_review_day?: boolean;
}

export interface KitDoc {
  id: string;
  status: "generating" | "ready" | "failed";
  input?: KitInputOut | null;
  kit?: {
    source?: { company?: string; role?: string; pages_used?: string[] };
    company_brief?: { summary?: string; what_they_do?: string; hiring_process?: string; sources?: string[] };
    role?: { title?: string; seniority?: string; responsibilities?: string[]; requirements?: Requirement[] };
    questions?: Question[];
    flashcards?: Flashcard[];
    schedule?: { days_available?: number; days?: ScheduleDay[] };
    coverage?: CoverageOut;
    research_log?: Record<string, unknown>;
    warnings?: string[];
    _brief_meta?: import("./api-types").BriefMeta | null;
  } | null;
  schedule_stale?: boolean;
  proposals?: { [key: string]: ProposalOut } | null;
  error?: ErrorInfo | null;
  created_at?: number | null;
}

export type KitSummary = KitSummaryOut;
export type JobStep = JobStepOut;
export type Job = JobOut;

export const CATEGORIES: Category[] = ["technical", "behavioural", "system-design", "company-fit"];

export function isProtectedMeta(m?: ItemMeta | null): boolean {
  if (!m) return false;
  return m.origin === "user" || !!m.edited || !!m.pinned;
}

export function originBadge(m?: ItemMeta | null): "Generated" | "Edited" | "Yours" | "Pinned" {
  if (!m) return "Generated";
  if (m.pinned) return "Pinned";
  if (m.origin === "user") return "Yours";
  if (m.edited) return "Edited";
  return "Generated";
}
