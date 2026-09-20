// AUTO-GENERATED from apps/api/openapi.json — do not edit by hand.
// Run: npm run generate:types
export const OPENAPI_PATHS = [
  "/api/auth/login",
  "/api/auth/logout",
  "/api/auth/register",
  "/api/health",
  "/api/jobs/{job_id}",
  "/api/kits",
  "/api/kits/batch",
  "/api/kits/{kit_id}",
  "/api/kits/{kit_id}/export",
  "/api/kits/{kit_id}/practice/check",
  "/api/kits/{kit_id}/practice/queue",
  "/api/kits/{kit_id}/practice/reviews",
  "/api/kits/{kit_id}/practice/summary",
  "/api/kits/{kit_id}/practice/weak-spots",
  "/api/kits/{kit_id}/questions/reorder",
  "/api/kits/{kit_id}/requirements/{requirement_id}/generate",
  "/api/kits/{kit_id}/schedule/days/{day}",
  "/api/kits/{kit_id}/schedule/move",
  "/api/kits/{kit_id}/sections/brief/accept",
  "/api/kits/{kit_id}/sections/brief/reject",
  "/api/kits/{kit_id}/sections/{section}/regenerate",
  "/api/kits/{kit_id}/{collection}",
  "/api/kits/{kit_id}/{collection}/{item_id}",
  "/api/me"
] as const;
export type ApiPath = (typeof OPENAPI_PATHS)[number];
export const OPENAPI_TITLE = "trao interview prep kit";
