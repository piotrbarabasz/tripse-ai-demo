export type ErrorKind =
  | "bad-request" | "unauthenticated" | "forbidden" | "not-found"
  | "conflict" | "too-large" | "validation" | "unavailable" | "http"
  | "network" | "timeout" | "cancelled" | "invalid-response";

export type ValidationIssue = { path: (string | number)[]; code: string };

const messages: Record<ErrorKind, string> = {
  "bad-request": "Request rejected. Check the request and origin.",
  unauthenticated: "Your session has expired. Sign in again.",
  forbidden: "You do not have permission for this operation.",
  "not-found": "The requested resource was not found.",
  conflict: "This resource has changed. Reload and review your changes before saving.",
  "too-large": "The uploaded file is too large.",
  validation: "Some request fields are invalid.",
  unavailable: "The service is temporarily unavailable.",
  http: "The request failed.", network: "Could not connect to the service.",
  timeout: "The service took too long to respond.", cancelled: "Request cancelled.",
  "invalid-response": "The service returned an unexpected response.",
};

export class ApiError extends Error {
  constructor(
    public readonly kind: ErrorKind,
    public readonly status?: number,
    public readonly issues: ValidationIssue[] = [],
  ) {
    super(messages[kind]);
    this.name = "ApiError";
  }
}

export function httpKind(status: number): ErrorKind {
  switch (status) {
    case 400: return "bad-request";
    case 401: return "unauthenticated";
    case 403: return "forbidden";
    case 404: return "not-found";
    case 409: return "conflict";
    case 413: return "too-large";
    case 422: return "validation";
    case 503: return "unavailable";
    default: return "http";
  }
}

// Keep structural field locations and machine codes, never input, ctx or server
// messages (Pydantic/domain exceptions may include private submitted values).
export function validationIssues(value: unknown): ValidationIssue[] {
  if (!value || typeof value !== "object" || !("detail" in value) || !Array.isArray(value.detail)) return [];
  const issues: ValidationIssue[] = [];
  for (const detail of value.detail.slice(0, 50) as unknown[]) {
    if (!detail || typeof detail !== "object" || !("loc" in detail) || !Array.isArray(detail.loc)) continue;
    const path = (detail.loc as unknown[]).filter((part): part is string | number =>
      (typeof part === "string" && /^[a-zA-Z_][a-zA-Z0-9_]{0,63}$/.test(part)) ||
      (typeof part === "number" && Number.isSafeInteger(part) && part >= 0));
    const code = "type" in detail && typeof detail.type === "string" && /^[a-z_]{1,64}$/.test(detail.type) ? detail.type : "invalid";
    issues.push({ path, code });
  }
  return issues;
}
