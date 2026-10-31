import { afterEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";
import { request } from "./transport";
import { ApiError } from "./errors";

afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });
const schema = z.object({ value: z.string().nullable() });
const json = { json: (value: unknown) => schema.parse(value) };
const respond = (response: Response) => {
  const mock = vi.fn().mockResolvedValue(response);
  vi.stubGlobal("fetch", mock);
  return mock;
};

describe("same-origin transport", () => {
  it("decodes typed JSON, retains null/status/headers and sends explicit JSON", async () => {
    const fetch = respond(Response.json({ value: null }, { status: 202, headers: { Location: "/api/trips/id" } }));
    const result = await request("/api/trips", json, { method: "POST", body: { json: { text: "Synthetic" } } });
    expect(result.data.value).toBeNull();
    expect(result.status).toBe(202);
    expect(result.headers.get("Location")).toBe("/api/trips/id");
    const init = fetch.mock.calls[0]?.[1] as RequestInit;
    expect(init).toMatchObject({ method: "POST", credentials: "same-origin", cache: "no-store", redirect: "error", body: '{"text":"Synthetic"}' });
    expect(new Headers(init.headers).get("Content-Type")).toBe("application/json");
  });
  it.each([undefined, "text/html", "text/json", "application/jsonp", "application/json, text/html"])("rejects missing/malformed JSON MIME %s", async (type) => {
    respond(new Response('{"value":"ok"}', { headers: type ? { "content-type": type } : {} }));
    await expect(request("/health", json)).rejects.toMatchObject({ kind: "invalid-response" });
  });
  it("accepts application problem+json with charset", async () => {
    respond(new Response('{"value":"ok"}', { headers: { "content-type": "application/problem+json; charset=utf-8" } }));
    expect((await request("/health", json)).data).toEqual({ value: "ok" });
  });
  it.each(["{bad", '{"value":5}', "null"])("rejects invalid JSON or schema %s", async (body) => {
    respond(new Response(body, { headers: { "content-type": "application/json" } }));
    await expect(request("/health", json)).rejects.toMatchObject({ kind: "invalid-response" });
  });
  it("returns preview HTML as inert text", async () => {
    respond(new Response("<html>preview</html>", { headers: { "content-type": "text/html; charset=utf-8" } }));
    expect((await request("/api/document-studio/drafts/id/preview", { html: true })).data).toBe("<html>preview</html>");
  });
  it("rejects JSON disguised as preview HTML and login HTML disguised as binary", async () => {
    respond(Response.json({}));
    await expect(request("/api/document-studio/drafts/id/preview", { html: true })).rejects.toMatchObject({ kind: "invalid-response" });
    respond(new Response("login", { headers: { "content-type": "text/html" } }));
    await expect(request("/api/document-studio/assets/id/content", { binary: true })).rejects.toMatchObject({ kind: "invalid-response" });
  });
  it("uploads exact bytes with image MIME and downloads private bytes", async () => {
    const bytes = new Uint8Array([1, 2, 3]);
    const fetch = respond(new Response(bytes, { headers: { "content-type": "image/png" } }));
    const result = await request("/api/document-studio/assets", { binary: true }, { method: "POST", body: { bytes, contentType: "image/png" } });
    expect(fetch.mock.calls[0]?.[1]).toMatchObject({ body: bytes });
    expect(new Headers((fetch.mock.calls[0]?.[1] as RequestInit).headers).get("Content-Type")).toBe("image/png");
    expect(result.data.type).toBe("image/png");
    expect(result.data.size).toBe(3);
  });
  it.each([[400, "bad-request"], [401, "unauthenticated"], [403, "forbidden"], [404, "not-found"], [409, "conflict"], [413, "too-large"], [422, "validation"], [503, "unavailable"], [500, "http"]])("distinguishes HTTP %s without exposing internal bodies", async (status, kind) => {
    respond(Response.json({ detail: "secret-provider-token" }, { status: Number(status) }));
    try { await request("/api/trips", json); expect.fail("must throw"); }
    catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      expect(error).toMatchObject({ status, kind });
      expect(JSON.stringify(error)).not.toContain("secret-provider-token");
      expect(String(error)).not.toContain("secret-provider-token");
    }
  });
  it("retains validation locations/codes while excluding input, ctx and messages", async () => {
    respond(Response.json({ detail: [{ loc: ["body", "text", 0], type: "string_too_long", msg: "secret", input: "secret", ctx: { error: "secret" } }] }, { status: 422 }));
    await expect(request("/api/trips", json)).rejects.toMatchObject({ issues: [{ path: ["body", "text", 0], code: "string_too_long" }] });
  });
  it("retains HTTP classification for malformed error bodies", async () => {
    respond(new Response("bad JSON secret", { status: 422, headers: { "content-type": "application/json" } }));
    await expect(request("/api/trips", json)).rejects.toMatchObject({ kind: "validation", issues: [] });
  });
  it.each(["https://example.com/api/trips", "//example.com/api/trips", "/api\\evil", "/api/trips#fragment", "/api/trips\n"])("blocks invalid destination %s before fetch", async (path) => {
    const fetch = respond(Response.json({}));
    await expect(request(path, json)).rejects.toMatchObject({ kind: "bad-request" });
    expect(fetch).not.toHaveBeenCalled();
  });
  it("rejects redirects and followed auth redirects", async () => {
    respond(new Response(null, { status: 302, headers: { Location: "/login" } }));
    await expect(request("/health", json)).rejects.toMatchObject({ kind: "invalid-response" });
    const followed = Response.json({ value: "login" });
    Object.defineProperty(followed, "redirected", { value: true });
    respond(followed);
    await expect(request("/health", json)).rejects.toMatchObject({ kind: "invalid-response" });
  });
  it("distinguishes network failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("private host")));
    await expect(request("/health", json)).rejects.toMatchObject({ kind: "network" });
  });
  it("bounds even an uncooperative pending fetch and aborts it", async () => {
    vi.useFakeTimers();
    let signal: AbortSignal | null | undefined;
    vi.stubGlobal("fetch", vi.fn((_path: string, init: RequestInit) => { signal = init.signal; return new Promise<Response>(() => undefined); }));
    const pending = request("/health", json, { timeoutMs: 50 });
    const rejected = expect(pending).rejects.toMatchObject({ kind: "timeout" });
    await vi.advanceTimersByTimeAsync(50);
    await rejected;
    expect(signal?.aborted).toBe(true);
    expect(vi.getTimerCount()).toBe(0);
  });
  it("also bounds response body decoding", async () => {
    vi.useFakeTimers();
    const response = Response.json({});
    vi.spyOn(response, "json").mockImplementation(() => new Promise(() => undefined));
    respond(response);
    const pending = request("/health", json, { timeoutMs: 50 });
    const rejected = expect(pending).rejects.toMatchObject({ kind: "timeout" });
    await vi.advanceTimersByTimeAsync(50);
    await rejected;
  });
  it("cancels pending and pre-aborted requests", async () => {
    const controller = new AbortController();
    const fetch = vi.fn(() => new Promise<Response>(() => undefined));
    vi.stubGlobal("fetch", fetch);
    const pending = request("/health", json, { signal: controller.signal });
    controller.abort();
    await expect(pending).rejects.toMatchObject({ kind: "cancelled" });
    await expect(request("/health", json, { signal: controller.signal })).rejects.toMatchObject({ kind: "cancelled" });
    expect(fetch).toHaveBeenCalledOnce();
  });
  it.each([0, -1, Infinity, 60001])("rejects unbounded timeout %s", async (timeoutMs) => {
    await expect(request("/health", json, { timeoutMs })).rejects.toMatchObject({ kind: "bad-request" });
  });
});
