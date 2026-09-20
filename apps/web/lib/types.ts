// Vocabulary per CONTEXT.md: Kit, Requirement, Question, Flashcard, Schedule,
// Review day, Gap, Drill, Weak spot, Proposal, Step, Category, Coverage, Pass,
// Section, Protected item, Confidence, Hiring signal, Research log.

export type Priority = "must" | "nice";
export type Kind = "technical" | "behavioural" | "domain";
export type Category = "technical" | "behavioural" | "system-design" | "company-fit";
export type StepStatus = "pending" | "running" | "done" | "skipped" | "failed";
export type JobStatus = "pending" | "running" | "done" | "failed";
export type ItemOrigin = "generated" | "user";

export interface ItemMeta {
  origin: ItemOrigin;
  edited: boolean;
  pinned: boolean;
  rev: number;
  order: string;
  gen_run?: string | null;
}

export interface Requirement {
  id: string;
  text: string;
  kind: Kind;
  priority: Priority;
  _meta?: ItemMeta;
}

export interface Question {
  id: string;
  requirement_ids: string[];
  category: Category;
  prompt: string;
  answer_outline: string;
  difficulty: number;
  outline_points?: string[];
  _meta?: ItemMeta;
}

export interface Flashcard {
  id: string;
  front: string;
  back: string;
  requirement_ids?: string[];
  _meta?: ItemMeta;
}

export interface ScheduleDay {
  day: number;
  focus: string;
  question_ids: string[];
  minutes: number;
  is_review_day?: boolean;
}

export interface KitDoc {
  id: string;
  status: "generating" | "ready" | "failed";
  input?: { jd: string; company_url: string; days: number };
  kit?: {
    source?: { company?: string; role?: string; pages_used?: string[] };
    company_brief?: { summary?: string; what_they_do?: string; hiring_process?: string; sources?: string[] };
    role?: { title?: string; seniority?: string; responsibilities?: string[]; requirements?: Requirement[] };
    questions?: Question[];
    flashcards?: Flashcard[];
    schedule?: { days_available?: number; days?: ScheduleDay[] };
    coverage?: { uncovered_requirement_ids?: string[]; passes?: number };
    research_log?: Record<string, unknown>;
    warnings?: string[];
  } | null;
  schedule_stale?: boolean;
  proposals?: { brief?: { summary: string; status: string } };
  error?: { code?: string; message?: string };
  updated_at?: string;
}

export interface KitSummary {
  id: string;
  company?: string;
  role?: string;
  days?: number;
  status: string;
  requirement_count?: number;
  question_count?: number;
  updated_at?: string;
  job_id?: string | null;
}

export interface JobStep {
  name: string;
  status: StepStatus;
  message?: string;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface Job {
  id: string;
  kit_id: string;
  status: JobStatus;
  steps: JobStep[];
  error?: { code?: string; message?: string } | null;
  retryable?: boolean;
}

export const CATEGORIES: Category[] = ["technical", "behavioural", "system-design", "company-fit"];

export function isProtectedMeta(m?: ItemMeta): boolean {
  if (!m) return false;
  return m.origin === "user" || m.edited || m.pinned;
}

export function originBadge(m?: ItemMeta): "Generated" | "Edited" | "Yours" | "Pinned" {
  if (!m) return "Generated";
  if (m.pinned) return "Pinned";
  if (m.origin === "user") return "Yours";
  if (m.edited) return "Edited";
  return "Generated";
}
