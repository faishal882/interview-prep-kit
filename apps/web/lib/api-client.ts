// One place for all server calls: sends credentials (cookies), decodes the
// uniform error envelope, turns 401 into a single "session expired" event.
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
    notifySessionExpired();
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

// Typed endpoint helpers (shapes mirror backend routers; see openapi.json).
export const AuthApi = {
  register(email: string, password: string) {
    return api.post<{ id: string; email: string }>("/api/auth/register", { email, password });
  },
  login(email: string, password: string) {
    return api.post<{ id: string; email: string }>("/api/auth/login", { email, password });
  },
  logout() {
    return api.post<{ ok: boolean }>("/api/auth/logout");
  },
  me() {
    return api.get<{ id: string; email: string }>("/api/me");
  },
};

export const KitsApi = {
  create(jd: string, company_url: string, days: number, force_new = false) {
    return api.post<{ kit_id: string; job_id: string | null; duplicate?: boolean }>("/api/kits", {
      jd,
      company_url,
      days,
      force_new,
    });
  },
  list() {
    return api.get<{ kits: Array<Record<string, unknown>> }>("/api/kits");
  },
  get(kitId: string) {
    return api.get<import("./types").KitDoc>(`/api/kits/${kitId}`);
  },
  remove(kitId: string) {
    return api.del<{ ok: boolean }>(`/api/kits/${kitId}`);
  },
  exportJson(kitId: string) {
    return api.get<Record<string, unknown>>(`/api/kits/${kitId}/export`);
  },
  batch(entries: Array<{ id?: string; jd: string; company_url?: string; days: number }>) {
    return api.post<{ accepted: Array<{ id: string; kit_id: string; job_id?: string; duplicate?: boolean }>; rejected: Array<{ id: string; reason: string }> }>(
      "/api/kits/batch",
      entries,
    );
  },
};

export const JobsApi = {
  get(jobId: string) {
    return api.get<import("./types").Job>(`/api/jobs/${jobId}`);
  },
};

export const ItemsApi = {
  create(kitId: string, collection: "questions" | "flashcards" | "requirements", body: Record<string, unknown>) {
    return api.post<Record<string, unknown>>(`/api/kits/${kitId}/${collection}`, body);
  },
  patch(kitId: string, collection: string, itemId: string, body: Record<string, unknown>) {
    return api.patch<Record<string, unknown>>(`/api/kits/${kitId}/${collection}/${itemId}`, body);
  },
  remove(kitId: string, collection: string, itemId: string) {
    return api.del<{ ok: boolean }>(`/api/kits/${kitId}/${collection}/${itemId}`);
  },
  reorder(kitId: string, body: { id: string; category?: string; after_id?: string | null }) {
    return api.post<Record<string, unknown>>(`/api/kits/${kitId}/questions/reorder`, body);
  },
};

export const SectionsApi = {
  regenerate(kitId: string, section: string) {
    return api.post<Record<string, unknown>>(`/api/kits/${kitId}/sections/${section}/regenerate`);
  },
  generateForRequirement(kitId: string, requirementId: string) {
    return api.post<Record<string, unknown>>(`/api/kits/${kitId}/requirements/${requirementId}/generate`);
  },
  acceptBrief(kitId: string) {
    return api.post<Record<string, unknown>>(`/api/kits/${kitId}/sections/brief/accept`);
  },
  rejectBrief(kitId: string) {
    return api.post<Record<string, unknown>>(`/api/kits/${kitId}/sections/brief/reject`);
  },
  patchScheduleDay(kitId: string, day: number, body: Record<string, unknown>) {
    return api.patch<Record<string, unknown>>(`/api/kits/${kitId}/schedule/days/${day}`, body);
  },
};

export const PracticeApi = {
  queue(kitId: string) {
    return api.get<{ queue: string[] }>(`/api/kits/${kitId}/practice/queue`);
  },
  review(kitId: string, flashcard_id: string, confidence: number) {
    return api.post<{ ok: boolean }>(`/api/kits/${kitId}/practice/reviews`, { flashcard_id, confidence });
  },
  summary(kitId: string) {
    return api.get<{ total: number; covered: number; uncovered: number }>(`/api/kits/${kitId}/practice/summary`);
  },
  weakSpots(kitId: string) {
    return api.get<{ spots: Array<{ requirement_id: string; reasons: string[]; score: number }> }>(
      `/api/kits/${kitId}/practice/weak-spots`,
    );
  },
  check(kitId: string, question_id: string, answer: string) {
    return api.post<{ results: Array<{ point: string; covered: boolean }>; method: string; limits: string }>(
      `/api/kits/${kitId}/practice/check`,
      { question_id, answer },
    );
  },
};

export { ApiError };
