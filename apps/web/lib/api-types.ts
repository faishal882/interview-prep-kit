// AUTO-GENERATED from apps/api/openapi.json — do not edit by hand.
// Run: npm run generate:types

export interface AcceptedEntry {
  id: string;
  kit_id: string;
  job_id?: (string) | null;
  duplicate?: boolean;
  [key: string]: unknown;
}
export interface BatchEntry {
  jd?: string;
  company_url?: string;
  days?: number;
  id?: string;
}
export interface BatchOut {
  accepted: Array<AcceptedEntry>;
  rejected: Array<RejectedEntry>;
}
export interface BriefMeta {
  origin?: string;
  edited?: boolean;
  pinned?: boolean;
  rev?: number;
}
export interface BriefOut {
  summary: string;
  what_they_do: string;
  hiring_process: string;
  sources: Array<string>;
  [key: string]: unknown;
}
export interface CheckBody {
  question_id: string;
  answer: string;
}
export interface CheckOut {
  results: Array<CheckPoint>;
  method: string;
  limits: string;
  [key: string]: unknown;
}
export interface CheckPoint {
  point: string;
  covered: boolean;
}
export interface CoverageOut {
  uncovered_requirement_ids: Array<string>;
  passes: number;
  [key: string]: unknown;
}
export interface CreateKit {
  jd?: string;
  company_url?: string;
  days?: number;
  force_new?: boolean;
}
export interface Creds {
  email: string;
  password: string;
}
export interface DeleteItemOut {
  ok?: boolean;
  flagged?: Array<string>;
}
export interface ErrorInfo {
  code?: string;
  message?: string;
  [key: string]: unknown;
}
export interface ExportOut {
  source?: SourceOut;
  research_log?: { [key: string]: unknown; };
  warnings?: Array<string>;
  company_brief?: BriefOut;
  role?: RoleOut;
  questions?: Array<QuestionOut>;
  flashcards?: Array<FlashcardOut>;
  schedule?: ScheduleOut;
  coverage?: CoverageOut;
  _brief_meta?: (BriefMeta) | null;
  [key: string]: unknown;
}
export interface FlashcardOut {
  id: string;
  front: string;
  back: string;
  requirement_ids: Array<string>;
  _meta?: (ItemMeta) | null;
  [key: string]: unknown;
}
export interface HTTPValidationError {
  detail?: Array<ValidationError>;
}
export interface HealthOut {
  ok?: boolean;
  problems?: (Array<string>) | null;
  [key: string]: unknown;
}
export interface ItemMeta {
  origin?: string;
  edited?: boolean;
  pinned?: boolean;
  rev?: number;
  order?: string;
  gen_run?: (string) | null;
}
export interface JobOut {
  id: string;
  kit_id: string;
  kind: string;
  status: "pending" | "running" | "done" | "failed";
  steps: Array<JobStepOut>;
  created_at?: (number) | null;
  deadline?: (number) | null;
  error?: (ErrorInfo) | null;
  retryable: boolean;
  [key: string]: unknown;
}
export interface JobStepOut {
  name: string;
  status: "pending" | "running" | "done" | "skipped" | "failed";
  message: string;
  started_at?: (string) | null;
  finished_at?: (string) | null;
  [key: string]: unknown;
}
export interface KitContentOut {
  source?: SourceOut;
  research_log?: { [key: string]: unknown; };
  warnings?: Array<string>;
  company_brief?: BriefOut;
  role?: RoleOut;
  questions?: Array<QuestionOut>;
  flashcards?: Array<FlashcardOut>;
  schedule?: ScheduleOut;
  coverage?: CoverageOut;
  _brief_meta?: (BriefMeta) | null;
  [key: string]: unknown;
}
export interface KitCreateOut {
  kit_id: string;
  job_id?: (string) | null;
  duplicate?: boolean;
}
export interface KitDocOut {
  id: string;
  status: "generating" | "ready" | "failed";
  input?: (KitInputOut) | null;
  kit?: (KitContentOut) | null;
  error?: (ErrorInfo) | null;
  schedule_stale?: boolean;
  proposals?: { [key: string]: ProposalOut; };
  created_at?: (number) | null;
  [key: string]: unknown;
}
export interface KitInputOut {
  jd?: string;
  company_url?: string;
  days?: number;
  [key: string]: unknown;
}
export interface KitListOut {
  kits: Array<KitSummaryOut>;
}
export interface KitSummaryOut {
  id: string;
  status: "generating" | "ready" | "failed";
  company: string;
  role: string;
  days: number;
  requirement_count: number;
  question_count: number;
  updated_at?: (number) | null;
  job_id?: (string) | null;
  [key: string]: unknown;
}
export interface MoveOut {
  ok?: boolean;
  day?: number;
}
export interface OkOut {
  ok?: boolean;
}
export interface PracticeSummaryOut {
  total: number;
  covered: number;
  uncovered: number;
}
export interface ProposalOut {
  summary?: string;
  status?: string;
  [key: string]: unknown;
}
export interface QuestionOut {
  id: string;
  requirement_ids: Array<string>;
  category: "technical" | "behavioural" | "system-design" | "company-fit";
  prompt: string;
  answer_outline: string;
  difficulty: number;
  outline_points: Array<string>;
  _meta?: (ItemMeta) | null;
  [key: string]: unknown;
}
export interface QueueOut {
  queue: Array<string>;
}
export interface RegenOut {
  job_id?: (string) | null;
  ok?: (boolean) | null;
  proposal?: ({ [key: string]: unknown; }) | null;
  warning?: (string) | null;
  [key: string]: unknown;
}
export interface RejectedEntry {
  id: string;
  reason: string;
}
export interface RequirementOut {
  id: string;
  text: string;
  kind: "technical" | "behavioural" | "domain";
  priority: "must" | "nice";
  _meta?: (ItemMeta) | null;
  [key: string]: unknown;
}
export interface Review {
  flashcard_id: string;
  confidence: number;
}
export interface RoleOut {
  title: string;
  seniority: string;
  responsibilities: Array<string>;
  requirements: Array<RequirementOut>;
  [key: string]: unknown;
}
export interface ScheduleDayOut {
  day: number;
  focus: string;
  question_ids: Array<string>;
  minutes: number;
  [key: string]: unknown;
}
export interface ScheduleOut {
  days_available: number;
  days: Array<ScheduleDayOut>;
  [key: string]: unknown;
}
export interface SourceOut {
  company?: string;
  company_url?: string;
  role?: string;
  location?: string;
  jd_chars?: number;
  researched_at?: string;
  pages_used?: Array<string>;
  [key: string]: unknown;
}
export interface UserOut {
  id: string;
  email: string;
}
export interface ValidationError {
  loc: Array<string | number>;
  msg: string;
  type: string;
  input?: unknown;
  ctx?: {  };
}
export interface WeakSpotEntry {
  requirement_id: string;
  reasons: Array<string>;
  score: number;
  question_ids: Array<string>;
  flashcard_ids: Array<string>;
  [key: string]: unknown;
}
export interface WeakSpotsOut {
  spots: Array<WeakSpotEntry>;
}
