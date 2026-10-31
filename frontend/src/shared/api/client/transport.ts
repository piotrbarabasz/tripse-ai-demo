import { ApiError, httpKind, validationIssues } from "./errors";

export type RequestOptions = {
  method?: "GET" | "POST" | "PUT";
  signal?: AbortSignal | undefined;
  timeoutMs?: number;
  headers?: Record<string, string>;
  body?: { json: unknown } | { bytes: Blob | ArrayBuffer | Uint8Array<ArrayBuffer>; contentType: string };
};
export type ApiResponse<T> = { data: T; status: number; headers: Headers };
type ResponseMode<T> = { json: (value: unknown) => T } | { html: true } | { binary: true };

function isJson(media: string): boolean {
  return media === "application/json" || /^application\/[a-z0-9!#$&^_.+-]+\+json$/.test(media);
}

export async function request<T>(path: string, mode: { json: (value: unknown) => T }, options?: RequestOptions): Promise<ApiResponse<T>>;
export async function request(path: string, mode: { html: true }, options?: RequestOptions): Promise<ApiResponse<string>>;
export async function request(path: string, mode: { binary: true }, options?: RequestOptions): Promise<ApiResponse<Blob>>;
export async function request<T>(path: string, mode: ResponseMode<T>, options: RequestOptions = {}): Promise<ApiResponse<T | string | Blob>> {
  if (!/^\/(?:api\/|health(?:\?|$))/.test(path) || /[\\#]/.test(path) || [...path].some((char) => char.charCodeAt(0) <= 32)) throw new ApiError("bad-request");
  const timeout = options.timeoutMs ?? 5000;
  if (!Number.isFinite(timeout) || timeout <= 0 || timeout > 60000) throw new ApiError("bad-request");
  const controller = new AbortController();
  let timedOut = false;
  let rejectAbort: (error: ApiError) => void = () => undefined;
  const aborted = new Promise<never>((_resolve, reject) => { rejectAbort = reject; });
  const cancel = () => {
    controller.abort();
    rejectAbort(new ApiError(timedOut ? "timeout" : "cancelled"));
  };
  options.signal?.addEventListener("abort", cancel, { once: true });
  const timer = setTimeout(() => { timedOut = true; cancel(); }, timeout);
  const run = async (): Promise<ApiResponse<T | string | Blob>> => {
    if (options.signal?.aborted) throw new ApiError("cancelled");
    const headers = new Headers(options.headers);
    headers.set("Accept", "json" in mode ? "application/json" : "html" in mode ? "text/html" : "image/jpeg, image/png, image/webp, application/octet-stream");
    let body: BodyInit | undefined;
    if (options.body) {
      if ("json" in options.body) {
        headers.set("Content-Type", "application/json");
        body = JSON.stringify(options.body.json);
      } else {
        headers.set("Content-Type", options.body.contentType);
        body = options.body.bytes;
      }
    }
    const response = await fetch(path, {
      method: options.method ?? "GET", credentials: "same-origin", cache: "no-store",
      redirect: "error", signal: controller.signal, headers,
      ...(body === undefined ? {} : { body }),
    });
    if (controller.signal.aborted) throw new ApiError(timedOut ? "timeout" : "cancelled");
    if (response.redirected || response.type === "opaque" || response.status === 0 || (response.status >= 300 && response.status < 400)) throw new ApiError("invalid-response");
    const media = response.headers.get("content-type")?.split(";")[0]?.trim().toLowerCase() ?? "";
    if (!response.ok) {
      let issues;
      if (response.status === 422 && isJson(media)) {
        try { const value: unknown = await response.json(); issues = validationIssues(value); } catch { /* retain HTTP failure */ }
      }
      throw new ApiError(httpKind(response.status), response.status, issues);
    }
    let data: T | string | Blob;
    try {
      if ("json" in mode) {
        if (!isJson(media)) throw new ApiError("invalid-response");
        const value: unknown = await response.json();
        data = mode.json(value);
      } else if ("html" in mode) {
        if (media !== "text/html") throw new ApiError("invalid-response");
        data = await response.text();
      } else {
        if (!["image/jpeg", "image/png", "image/webp", "application/octet-stream"].includes(media)) throw new ApiError("invalid-response");
        data = await response.blob();
      }
    } catch { throw new ApiError("invalid-response"); }
    return { data, status: response.status, headers: response.headers };
  };
  try { return await Promise.race([run(), aborted]); }
  catch (error) {
    if (error instanceof ApiError) throw error;
    if (controller.signal.aborted) throw new ApiError(timedOut ? "timeout" : "cancelled");
    throw new ApiError("network");
  } finally {
    clearTimeout(timer);
    options.signal?.removeEventListener("abort", cancel);
  }
}
