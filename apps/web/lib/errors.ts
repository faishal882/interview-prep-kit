// Decodes the backend uniform envelope {error:{code,message,details,trace_id}}
// into typed errors. Every surface shows message + reference id.

export type ErrorCode =
  | "UNAUTHORIZED"
  | "SESSION_EXPIRED"
  | "FORBIDDEN"
  | "NOT_FOUND"
  | "CONFLICT"
  | "RATE_LIMITED"
  | "INVALID_INPUT"
  | "INTERNAL"
  | string;

export class ApiError extends Error {
  code: ErrorCode;
  details: Record<string, unknown>;
  referenceId: string;
  status: number;
  constructor(code: ErrorCode, message: string, referenceId: string, status: number, details: Record<string, unknown> = {}) {
    super(message);
    this.code = code;
    this.referenceId = referenceId;
    this.status = status;
    this.details = details;
  }
  get isSessionExpired(): boolean {
    return this.status === 401;
  }
}

export function decodeError(status: number, body: unknown): ApiError {
  const fallback = new ApiError("INTERNAL", "Something went wrong.", "n/a", status);
  if (!body || typeof body !== "object") return fallback;
  const err = (body as { error?: { code?: string; message?: string; details?: Record<string, unknown>; trace_id?: string } }).error;
  if (!err) return fallback;
  return new ApiError(
    err.code ?? "INTERNAL",
    plainMessage(err.code ?? "INTERNAL", err.message ?? "Something went wrong."),
    err.trace_id ?? "n/a",
    status,
    err.details ?? {},
  );
}

const PLAIN: Record<string, string> = {
  UNAUTHORIZED: "Wrong email or password. Try again.",
  SESSION_EXPIRED: "Your login session expired. Sign in again.",
  FORBIDDEN: "Not allowed.",
  NOT_FOUND: "Not found.",
  CONFLICT: "That already exists or changed elsewhere.",
  RATE_LIMITED: "Too many attempts. Wait a little and try again.",
  INVALID_INPUT: "Check the highlighted fields and try again.",
};

export function plainMessage(code: string, backendMessage: string): string {
  if (code === "INVALID_INPUT" || code === "CONFLICT" || code === "RATE_LIMITED") {
    // Prefer backend detail when it is plain language, else generic.
    if (backendMessage && backendMessage.length < 160) return backendMessage;
  }
  return PLAIN[code] ?? backendMessage ?? "Something went wrong.";
}

export function formatWithRef(e: unknown): string {
  if (e instanceof ApiError) return `${e.message} (ref ${e.referenceId})`;
  if (e instanceof Error) return e.message;
  return "Something went wrong.";
}
