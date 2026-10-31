import { MutationObserver, QueryObserver } from "@tanstack/react-query";
import { afterEach, expect, it, vi } from "vitest";
import { createApiQueryClient, apiKeys, jobQuery, libraryQuery, saveDraftMutation, createTripMutation } from "./client";
import { fixture } from "../test-fixtures";
import { zTripStatus } from "../generated/zod.gen";

afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });

it("cancels an active fetch and consumes the query AbortSignal", async () => {
  const client = createApiQueryClient();
  let signal: AbortSignal | null | undefined;
  vi.stubGlobal("fetch", vi.fn((_path: string, init: RequestInit) => { signal = init.signal; return new Promise<Response>(() => undefined); }));
  const pending = client.fetchQuery(jobQuery("synthetic"));
  const rejected = expect(pending).rejects.toThrow();
  await client.cancelQueries({ queryKey: apiKeys.job("synthetic") });
  await rejected;
  expect(signal?.aborted).toBe(true);
  client.clear();
});

it("aborts an observed job read when the last observer unmounts", () => {
  const client = createApiQueryClient();
  let signal: AbortSignal | null | undefined;
  vi.stubGlobal("fetch", vi.fn((_path: string, init: RequestInit) => { signal = init.signal; return new Promise<Response>(() => undefined); }));
  const observer = new QueryObserver(client, jobQuery("synthetic"));
  const unsubscribe = observer.subscribe(() => undefined);
  unsubscribe();
  expect(signal?.aborted).toBe(true);
  client.clear();
});

it.each(["completed", "failed"])("polls queued/running and stops at %s", async (terminal) => {
  vi.useFakeTimers();
  const client = createApiQueryClient();
  const job = zTripStatus.parse(fixture.job);
  let index = 0;
  const states = ["queued", "running", terminal];
  const fetch = vi.fn().mockImplementation(() => Promise.resolve(Response.json({ ...job, status: states[index++] ?? terminal })));
  vi.stubGlobal("fetch", fetch);
  const observer = new QueryObserver(client, jobQuery(job.trip_id));
  const unsubscribe = observer.subscribe(() => undefined);
  await vi.advanceTimersByTimeAsync(0);
  expect(observer.getCurrentResult().data?.status).toBe("queued");
  await vi.advanceTimersByTimeAsync(1500);
  expect(observer.getCurrentResult().data?.status).toBe("running");
  await vi.advanceTimersByTimeAsync(1500);
  expect(observer.getCurrentResult().data?.status).toBe(terminal);
  await vi.advanceTimersByTimeAsync(6000);
  expect(fetch).toHaveBeenCalledTimes(3);
  unsubscribe(); client.clear();
});

it("clears private cache, aborts other reads and stops polling on session failure", async () => {
  vi.useFakeTimers();
  const session = vi.fn();
  const client = createApiQueryClient(session);
  client.setQueryData(apiKeys.library({}), fixture.library);
  let otherSignal: AbortSignal | null | undefined;
  const fetch = vi.fn((path: string, init: RequestInit) => {
    if (path.includes("other")) { otherSignal = init.signal; return new Promise<Response>(() => undefined); }
    return Promise.resolve(Response.json({ detail: "private" }, { status: 401 }));
  });
  vi.stubGlobal("fetch", fetch);
  const other = client.fetchQuery(jobQuery("other"));
  const rejected = expect(other).rejects.toThrow();
  const observer = new QueryObserver(client, jobQuery("expired"));
  const unsubscribe = observer.subscribe(() => undefined);
  await vi.advanceTimersByTimeAsync(0);
  await rejected;
  expect(client.getQueryCache().getAll()).toHaveLength(0);
  expect(otherSignal?.aborted).toBe(true);
  expect(session).toHaveBeenCalledOnce();
  await vi.advanceTimersByTimeAsync(6000);
  expect(fetch).toHaveBeenCalledTimes(2);
  unsubscribe(); client.clear();
});

it("stops network polling on explicit cancellation even between reads", async () => {
  vi.useFakeTimers();
  const client = createApiQueryClient();
  const controller = new AbortController();
  const fetch = vi.fn().mockImplementation(() => Promise.resolve(Response.json(fixture.job)));
  vi.stubGlobal("fetch", fetch);
  const observer = new QueryObserver(client, jobQuery("synthetic", controller.signal));
  const unsubscribe = observer.subscribe(() => undefined);
  await vi.advanceTimersByTimeAsync(0);
  controller.abort();
  await vi.advanceTimersByTimeAsync(6000);
  expect(fetch).toHaveBeenCalledOnce();
  unsubscribe(); client.clear();
});

it.each([403, 409, 503])("does not retry HTTP %s reads or silently replace private state", async (status) => {
  const client = createApiQueryClient();
  client.setQueryData(apiKeys.library({}), fixture.library);
  const fetch = vi.fn().mockResolvedValue(Response.json({ detail: "private" }, { status }));
  vi.stubGlobal("fetch", fetch);
  await expect(client.fetchQuery(jobQuery("synthetic"))).rejects.toMatchObject({ status });
  expect(fetch).toHaveBeenCalledOnce();
  expect(client.getQueryData(apiKeys.library({}))).toEqual(fixture.library);
  client.clear();
});

it.each(["local", "cloud_demo"] as const)("never retries %s creates after ambiguous network failure", async (mode) => {
  const client = createApiQueryClient();
  const fetch = vi.fn().mockRejectedValue(new TypeError("network"));
  vi.stubGlobal("fetch", fetch);
  const target = mode === "local" ? { mode } : { mode, idempotencyKey: "same-operation" };
  const observer = new MutationObserver(client, createTripMutation(target));
  await expect(observer.mutate({ text: "Synthetic trip" })).rejects.toMatchObject({ kind: "network" });
  expect(fetch).toHaveBeenCalledOnce();
  expect(client.getDefaultOptions().mutations?.retry).toBe(false);
  client.clear();
});

it("invalidates Studio reads only after a successful revision-aware save", async () => {
  const client = createApiQueryClient();
  client.setQueryData(apiKeys.library({}), fixture.library);
  const fetch = vi.fn().mockResolvedValueOnce(Response.json({ detail: "conflict" }, { status: 409 })).mockResolvedValueOnce(Response.json(fixture.draft));
  vi.stubGlobal("fetch", fetch);
  const observer = new MutationObserver(client, saveDraftMutation(client, "synthetic-draft"));
  const form = { revision: 1, title: "Unsaved user title" };
  await expect(observer.mutate(form)).rejects.toMatchObject({ kind: "conflict" });
  expect(client.getQueryState(apiKeys.library({}))?.isInvalidated).toBe(false);
  expect(form).toEqual({ revision: 1, title: "Unsaved user title" });
  await observer.mutate(form);
  expect(client.getQueryState(apiKeys.library({}))?.isInvalidated).toBe(true);
  expect(fetch).toHaveBeenCalledTimes(2);
  client.clear();
});

it("clears session cache on mutation 401 as well as read failure", async () => {
  const session = vi.fn();
  const client = createApiQueryClient(session);
  client.setQueryData(apiKeys.library({}), fixture.library);
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({}, { status: 401 })));
  const observer = new MutationObserver(client, createTripMutation({ mode: "local" }));
  await expect(observer.mutate({ text: "Synthetic" })).rejects.toMatchObject({ kind: "unauthenticated" });
  expect(client.getQueryCache().getAll()).toHaveLength(0);
  expect(session).toHaveBeenCalledOnce();
  client.clear();
});

it("keys library filters independently and forwards read cancellation", async () => {
  const client = createApiQueryClient();
  const fetch = vi.fn().mockImplementation(() => Promise.resolve(Response.json(fixture.library)));
  vi.stubGlobal("fetch", fetch);
  await client.fetchQuery(libraryQuery({ family: "offer" }));
  await client.fetchQuery(libraryQuery({ family: "pilot" }));
  expect(client.getQueryCache().getAll()).toHaveLength(2);
  expect(fetch).toHaveBeenCalledTimes(2);
  client.clear();
});
