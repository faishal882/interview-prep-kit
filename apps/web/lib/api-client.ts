// One place for all server calls: sends credentials (cookies), decodes the
// uniform error envelope, turns 401 into a single "session expired" event.
//
// Response types are the generated API contract (lib/api-types.ts); the only
// local shapes are request bodies.
import type {
  BatchOut,
  BriefOut,
  CheckOut,
  DeleteItemOut,
  ExportOut,
  FlashcardOut,
  JobOut,
  KitCreateOut,
  KitDocOut,
  KitListOut,
  MoveOut,
  OkOut,
  PracticeSummaryOut,
  ProposalOut,
  QuestionOut,
  QueueOut,
  RegenOut,
  RejectedEntry,
  RequirementOut,
  ScheduleDayOut,
  UserOut,
  WeakSpotsOut,
} from "./api-types";
import { ApiError, decodeError } from "./errors";

export const sessionExpiredEvent = "trao:session-expired";

let warned = false;
export function notifySessionExpired(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(sessionExpiredEvent));
  if (!warned) {
    warned = true;
    setTimeout(() => (warned = false), 5000);
  }
}

// A 401 from these means "not signed in" or "wrong password", not an expired session.
const AUTH_PATHS = new Set(["/api/me", "/api/auth/login", "/api/auth/register"]);

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(path, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
  });
  if (res.status === 401) {
    let body: unknown = null;
    try {
      body = await res.json();
    } catch {
      body = null;
    }
    if (!AUTH_PATHS.has(path)) notifySessionExpired();
    throw decodeError(401, body);
  }
  if (!res.ok) {
    let body: unknown = null;
    try {
      body = await res.json();
    } catch {
      body = null;
    }
    throw decodeError(res.status, body);
  }
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  if (!text) return undefined as T;
  return JSON.parse(text) as T;
}

export const api = {
  get<T>(path: string): Promise<T> {
    return request<T>(path);
  },
  post<T>(path: string, body?: unknown): Promise<T> {
    return request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
  },
  patch<T>(path: string, body?: unknown): Promise<T> {
    return request<T>(path, { method: "PATCH", body: body === undefined ? undefined : JSON.stringify(body) });
  },
  del<T>(path: string): Promise<T> {
    return request<T>(path, { method: "DELETE" });
  },
};

export const AuthApi = {
  register(email: string, password: string) {
    return api.post<UserOut>("/api/auth/register", { email, password });
  },
  login(email: string, password: string) {
    return api.post<UserOut>("/api/auth/login", { email, password });
  },
  logout() {
    return api.post<OkOut>("/api/auth/logout");
  },
  me() {
    return api.get<UserOut>("/api/me");
  },
};

export const KitsApi = {
  create(jd: string, company_url: string, days: number, force_new = false) {
    return api.post<KitCreateOut>("/api/kits", {
      jd,
      company_url,
      days,
      force_new,
    });
  },
  list() {
    return api.get<KitListOut>("/api/kits");
  },
  get(kitId: string) {
    return api.get<KitDocOut>(`/api/kits/${kitId}`);
  },
  remove(kitId: string) {
    return api.del<OkOut>(`/api/kits/${kitId}`);
  },
  exportJson(kitId: string) {
    return api.get<ExportOut>(`/api/kits/${kitId}/export`);
  },
  batch(entries: Array<{ id?: string; jd: string; company_url?: string; days: number }>) {
    return api.post<BatchOut>("/api/kits/batch", entries);
  },
};

export const JobsApi = {
  get(jobId: string) {
    return api.get<JobOut>(`/api/jobs/${jobId}`);
  },
};

export type ItemResult = QuestionOut | FlashcardOut | RequirementOut;
export type BriefPatchResult = BriefOut & { _rev?: number };

export const ItemsApi = {
  create(kitId: string, collection: "questions" | "flashcards" | "requirements", body: Record<string, unknown>) {
    return api.post<ItemResult>(`/api/kits/${kitId}/${collection}`, body);
  },
  patch(kitId: string, collection: string, itemId: string, body: Record<string, unknown>) {
    return api.patch<ItemResult | BriefPatchResult>(`/api/kits/${kitId}/${collection}/${itemId}`, body);
  },
  remove(kitId: string, collection: string, itemId: string) {
    return api.del<DeleteItemOut>(`/api/kits/${kitId}/${collection}/${itemId}`);
  },
  reorder(kitId: string, body: { id: string; category?: string; after_id?: string | null }) {
    return api.post<QuestionOut>(`/api/kits/${kitId}/questions/reorder`, body);
  },
};

export const SectionsApi = {
  regenerate(kitId: string, section: string) {
    return api.post<RegenOut>(`/api/kits/${kitId}/sections/${section}/regenerate`);
  },
  generateForRequirement(kitId: string, requirementId: string) {
    return api.post<RegenOut>(`/api/kits/${kitId}/requirements/${requirementId}/generate`);
  },
  acceptBrief(kitId: string) {
    return api.post<OkOut>(`/api/kits/${kitId}/sections/brief/accept`);
  },
  rejectBrief(kitId: string) {
    return api.post<OkOut>(`/api/kits/${kitId}/sections/brief/reject`);
  },
  patchScheduleDay(kitId: string, day: number, body: Record<string, unknown>) {
    return api.patch<ScheduleDayOut>(`/api/kits/${kitId}/schedule/days/${day}`, body);
  },
  moveScheduleQuestion(kitId: string, body: { question_id: string; to_day: number }) {
    return api.post<MoveOut>(`/api/kits/${kitId}/schedule/move`, body);
  },
};

export const PracticeApi = {
  queue(kitId: string) {
    return api.get<QueueOut>(`/api/kits/${kitId}/practice/queue`);
  },
  review(kitId: string, flashcard_id: string, confidence: number) {
    return api.post<OkOut>(`/api/kits/${kitId}/practice/reviews`, { flashcard_id, confidence });
  },
  summary(kitId: string) {
    return api.get<PracticeSummaryOut>(`/api/kits/${kitId}/practice/summary`);
  },
  weakSpots(kitId: string) {
    return api.get<WeakSpotsOut>(`/api/kits/${kitId}/practice/weak-spots`);
  },
  check(kitId: string, question_id: string, answer: string) {
    return api.post<CheckOut>(
      `/api/kits/${kitId}/practice/check`,
      { question_id, answer },
    );
  },
};

export type {
  BriefOut,
  CheckOut,
  KitCreateOut,
  KitDocOut,
  KitListOut,
  MoveOut,
  ProposalOut,
  QuestionOut,
  QueueOut,
  RegenOut,
  RejectedEntry,
  UserOut,
  WeakSpotsOut,
};
export { ApiError };
