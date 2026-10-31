import { StrictMode } from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { afterEach, expect, it, vi } from "vitest";
import { createApiQueryClient } from "../../shared/api/query/client";
import type { WorkspaceCapabilities } from "../../shared/api/generated/types.gen";
import { zTripStatus } from "../../shared/api/generated/zod.gen";
import { fixture } from "../../shared/api/test-fixtures";
import { PlannerPage } from "./PlannerPage";
import { JobProgress, POLLING_WINDOW_MS } from "./JobProgress";
import { AppRoutes } from "../../app/App";
import { completedResultSchema } from "./result";

const clients: ReturnType<typeof createApiQueryClient>[] = [];
afterEach(() => { clients.forEach((client) => client.clear()); clients.length = 0; vi.unstubAllGlobals(); vi.useRealTimers(); });
const job = zTripStatus.parse(fixture.job);
const completedResult = { ...completedResultSchema.parse(fixture.completed_result), viewer_url: `${window.location.origin}/trip/${"A".repeat(43)}` };

function network(capabilities: Partial<WorkspaceCapabilities> = {}) {
  let create = () => Promise.resolve(Response.json(fixture.accepted, { status: 202 }));
  let read = () => Promise.resolve(Response.json(job));
  const fetch = vi.fn((url: string, init: RequestInit) => {
    if (url === "/api/workspace/capabilities") return Promise.resolve(Response.json({ runtime_mode: "local", can_create_trip: true, planning_mode: "mock", ...capabilities }));
    if (url === "/api/demo/scenarios") return Promise.resolve(Response.json(fixture.scenarios));
    if (url === "/health") return Promise.resolve(Response.json(fixture.health));
    if (url === "/api/trips" && init.method === "POST") return create();
    if (url.startsWith("/api/trips/")) return read();
    throw new Error("Unexpected URL");
  });
  vi.stubGlobal("fetch", fetch);
  return { fetch, setCreate: (next: typeof create) => { create = next; }, setRead: (next: typeof read) => { read = next; }, posts: () => fetch.mock.calls.filter(([url]) => url === "/api/trips") };
}

function page(content = <PlannerPage />) {
  const client = createApiQueryClient(); clients.push(client);
  return { client, ...render(<StrictMode><QueryClientProvider client={client}><MemoryRouter initialEntries={["/planner"]}>{content}</MemoryRouter></QueryClientProvider></StrictMode>) };
}
async function ready() { await waitFor(() => expect(screen.getByRole("button", { name: "Przygotuj plan" })).toBeEnabled()); }
function fill(value = "  Syntetyczna podróż  ") { fireEvent.change(screen.getByLabelText("Opisz wycieczkę"), { target: { value } }); }
function submit() { fireEvent.click(screen.getByRole("button", { name: "Przygotuj plan" })); }

it("requires trusted capabilities before creation and does not infer mode from health", () => {
  const fetch = vi.fn(() => new Promise<Response>(() => undefined));
  vi.stubGlobal("fetch", fetch);
  page();
  expect(screen.getByRole("button", { name: "Przygotuj plan" })).toBeDisabled();
  expect(screen.getByText("Sprawdzanie trybu")).toBeVisible();
  fill(); submit();
  expect(fetch).not.toHaveBeenCalledWith("/health", expect.anything());
});

it.each([401, 403, 503, 200])("fails closed for unavailable or malformed capabilities %s", async (status) => {
  vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(Response.json({ runtime_mode: "guessed", can_create_trip: "true" }, { status }))));
  page();
  expect(await screen.findByRole("alert")).toHaveTextContent("Tworzenie planów jest wyłączone");
  expect(screen.getByRole("button", { name: "Przygotuj plan" })).toBeDisabled();
});

it("validates empty/whitespace/overlong input and counts Unicode like Pydantic", async () => {
  const api = network(); page(); await ready();
  fill(" \n "); submit();
  expect(screen.getByRole("alert")).toHaveTextContent("Wpisz od 1 do 10 000 znaków");
  expect(screen.getByLabelText("Opisz wycieczkę")).toHaveFocus();
  fill("x".repeat(10001)); submit();
  expect(api.posts()).toHaveLength(0);
  fill("🙂".repeat(10000));
  expect(screen.getByText("10 000 / 10 000 znaków")).toBeVisible();
  api.setCreate(() => new Promise<Response>(() => undefined));
  submit();
  await waitFor(() => expect(api.posts()).toHaveLength(1));
});

it("uses verified mock examples and supports labeled keyboard entry", async () => {
  const api = network(); page(); await ready();
  const example = await screen.findByRole("button", { name: "Ojców · 1 dzień" });
  const user = userEvent.setup();
  example.focus(); await user.keyboard("{Enter}");
  expect(screen.getByLabelText("Opisz wycieczkę")).toHaveFocus();
  expect(screen.getByLabelText<HTMLTextAreaElement>("Opisz wycieczkę").value).toContain("Kraków");
  expect(api.posts()).toHaveLength(0);
  expect(screen.getByText("DEMO / MOCK")).toBeVisible();
});

it("sends trimmed local text exactly once even on double submit, including StrictMode", async () => {
  const api = network(); api.setCreate(() => new Promise<Response>(() => undefined));
  page(); await ready(); fill();
  const form = screen.getByLabelText("Opisz wycieczkę").closest("form");
  if (!form) throw new Error("Missing form");
  fireEvent.submit(form); fireEvent.submit(form);
  await waitFor(() => expect(api.posts()).toHaveLength(1));
  const init = api.posts()[0]?.[1];
  expect(init?.body).toBe('{"text":"Syntetyczna podróż"}');
  expect(new Headers(init?.headers).has("Idempotency-Key")).toBe(false);
  await waitFor(() => expect(screen.getByRole("button", { name: "Wysyłanie prośby…" })).toBeDisabled());
});

it.each(["local", "cloud_demo"] as const)("requires explicit retry after ambiguous %s create", async (runtime_mode) => {
  const api = network({ runtime_mode }); api.setCreate(() => Promise.reject(new TypeError("private network diagnostics")));
  page(); await ready(); fill(); submit();
  expect(await screen.findByRole("alert")).toHaveTextContent("Zadanie mogło już powstać");
  expect(screen.queryByText("private network diagnostics")).not.toBeInTheDocument();
  expect(api.posts()).toHaveLength(1);
  expect(screen.getByRole("button", { name: "Przygotuj plan" })).toBeDisabled();
  const retry = screen.getByRole("button", { name: runtime_mode === "local" ? "Wyślij ponownie mimo ryzyka duplikatu" : "Ponów tę samą prośbę" });
  api.setCreate(() => Promise.resolve(Response.json(fixture.accepted, { status: 202 })));
  fireEvent.click(retry);
  await screen.findByText(/Numer zadania:/);
  expect(api.posts()).toHaveLength(2);
  const headers = api.posts().map(([, init]) => new Headers(init.headers));
  if (runtime_mode === "cloud_demo") {
    expect(headers[0]?.get("Idempotency-Key")).toMatch(/^[0-9a-f-]{36}$/);
    expect(headers[1]?.get("Idempotency-Key")).toBe(headers[0]?.get("Idempotency-Key"));
  } else expect(headers.every((value) => !value.has("Idempotency-Key"))).toBe(true);
});

it("uses a new cloud UUID for a deliberately new operation", async () => {
  const api = network({ runtime_mode: "cloud_demo" }); api.setCreate(() => Promise.reject(new TypeError("network")));
  page(); await ready(); fill(); submit();
  await screen.findByText(/Zadanie mogło już powstać/);
  fireEvent.click(screen.getByRole("button", { name: "Rozpocznij nową prośbę" }));
  fill("Nowa prośba"); submit();
  await waitFor(() => expect(api.posts()).toHaveLength(2));
  expect(new Headers(api.posts()[0]?.[1].headers).get("Idempotency-Key")).not.toBe(new Headers(api.posts()[1]?.[1].headers).get("Idempotency-Key"));
});

it.each([401, 403])("blocks creation after HTTP %s without rendering private errors", async (status) => {
  const api = network(); api.setCreate(() => Promise.resolve(Response.json({ detail: "private identity" }, { status })));
  page(); await ready(); fill(); submit();
  expect(await screen.findByRole("alert")).not.toHaveTextContent("private identity");
  expect(screen.getByRole("button", { name: "Przygotuj plan" })).toBeDisabled();
  expect(api.posts()).toHaveLength(1);
});

it("disables editor actions for a reader and never POSTs", async () => {
  const api = network({ runtime_mode: "cloud_demo", can_create_trip: false }); page();
  await screen.findByText(/Dostęp tylko do odczytu/);
  fill(); submit();
  expect(screen.getByRole("button", { name: "Przygotuj plan" })).toBeDisabled();
  expect(api.posts()).toHaveLength(0);
});

it("shows LIVE only from capabilities and never fetches demo examples in live mode", async () => {
  const api = network({ planning_mode: "live" }); page(); await ready();
  expect(screen.getByText("LIVE")).toBeVisible();
  expect(screen.getByText(/Sugestie wymagają sprawdzenia/)).toBeVisible();
  expect(api.fetch.mock.calls.some(([url]) => url === "/api/demo/scenarios")).toBe(false);
});

it("tracks queued → running → completed and opens only the validated viewer path", async () => {
  const api = network();
  let status = "queued";
  api.setRead(() => Promise.resolve(Response.json({ ...job, status, result: completedResult })));
  page(); await ready(); fill(); submit();
  expect(await screen.findByText("W kolejce")).toBeVisible();
  status = "running";
  expect(await screen.findByText("Przygotowanie planu", {}, { timeout: 4000 })).toBeVisible();
  status = "completed";
  const link = await screen.findByRole("link", { name: "Otwórz plan i mapę" }, { timeout: 4000 });
  expect(link).toHaveAttribute("href", `/trip/${"A".repeat(43)}`);
  expect(screen.getByText(/miejsca, czasy i trasa są przykładowe/)).toBeVisible();
  expect(api.posts()).toHaveLength(1);
}, 12000);

it.each(["queued", "running"] as const)("shows %s → failed without displaying raw job.error", async (initial) => {
  const api = network(); let index = 0;
  api.setRead(() => Promise.resolve(Response.json({ ...job, status: index++ ? "failed" : initial, error: "secret provider body" })));
  page(); await ready(); fill(); submit();
  expect(await screen.findByRole("alert", {}, { timeout: 4000 })).toHaveTextContent("Nie udało się przygotować planu");
  expect(screen.queryByText("secret provider body")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Zaplanuj kolejną podróż" })).toBeEnabled();
});

it.each([404, 503])("allows manual status refresh after HTTP %s without creating another job", async (status) => {
  const api = network(); api.setRead(() => Promise.resolve(Response.json({ detail: "private" }, { status })));
  page(); await ready(); fill(); submit();
  const refresh = await screen.findByRole("button", { name: "Sprawdź status ponownie" });
  api.setRead(() => Promise.resolve(Response.json({ ...job, status: "completed", result: completedResult })));
  fireEvent.click(refresh);
  expect(await screen.findByRole("link", { name: "Otwórz plan i mapę" })).toBeVisible();
  expect(api.posts()).toHaveLength(1);
});

it.each([401, 403])("stops status polling on HTTP %s and offers no automatic/manual create replay", async (status) => {
  const api = network(); api.setRead(() => Promise.resolve(Response.json({}, { status })));
  page(); await ready(); fill(); submit();
  await screen.findByRole("alert");
  expect(screen.queryByRole("button", { name: "Sprawdź status ponownie" })).not.toBeInTheDocument();
  expect(api.posts()).toHaveLength(1);
});

it.each(["network", "timeout"])("reports a %s status failure safely and offers manual read refresh", async (failure) => {
  const api = network();
  if (failure === "network") api.setRead(() => Promise.reject(new TypeError("private internal host")));
  else api.setRead(() => new Promise<Response>(() => undefined));
  page(); await ready(); fill(); submit();
  expect(await screen.findByRole("button", { name: "Sprawdź status ponownie" }, { timeout: 7000 })).toBeEnabled();
  expect(screen.queryByText("private internal host")).not.toBeInTheDocument();
  expect(api.posts()).toHaveLength(1);
}, 10000);

it("shows verified LIVE output as a draft requiring review", async () => {
  const api = network({ planning_mode: "live" });
  api.setRead(() => Promise.resolve(Response.json({ ...job, status: "completed", result: { ...completedResult, is_mock: false, generation_mode: "live", verification_status: "verified" } })));
  page(); await ready(); fill(); submit();
  expect(await screen.findByText(/Dopasowania miejsc i trasy są oznaczone/)).toBeVisible();
  expect(screen.getByRole("link", { name: "Otwórz plan i mapę" })).toBeVisible();
});

it.each(["https://evil.example/trip/" + "A".repeat(43), null])("shows a safe fallback for unavailable completed viewer", async (viewer_url) => {
  const api = network(); api.setRead(() => Promise.resolve(Response.json({ ...job, status: "completed", result: { ...completedResult, viewer_url } })));
  page(); await ready(); fill(); submit();
  expect(await screen.findByRole("alert")).toHaveTextContent("Link do planu jest niedostępny");
  expect(screen.queryByRole("link", { name: "Otwórz plan i mapę" })).not.toBeInTheDocument();
});

it.each([null, {}, { viewer_url: "https://evil.example" }])("rejects malformed completed result", async (result) => {
  const api = network(); api.setRead(() => Promise.resolve(Response.json({ ...job, status: "completed", result })));
  page(); await ready(); fill(); submit();
  expect(await screen.findByRole("alert")).toHaveTextContent("wynik jest niekompletny");
  expect(screen.queryByRole("link", { name: "Otwórz plan i mapę" })).not.toBeInTheDocument();
});

it("bounds polling to two minutes and manual refresh remains GET-only", async () => {
  vi.useFakeTimers();
  const api = network(); page(<JobProgress tripId={job.trip_id} onNewRequest={() => undefined} />);
  await act(() => vi.advanceTimersByTimeAsync(POLLING_WINDOW_MS));
  expect(screen.getByText(/Wstrzymano automatyczne sprawdzanie/)).toBeVisible();
  const before = api.fetch.mock.calls.length;
  await act(() => vi.advanceTimersByTimeAsync(10000));
  expect(api.fetch).toHaveBeenCalledTimes(before);
  expect(api.posts()).toHaveLength(0);
});

it("aborts status requests on client-side navigation and makes no further POST", async () => {
  const api = network();
  let signal: AbortSignal | null | undefined;
  api.setRead(() => new Promise<Response>(() => undefined));
  const fetch = api.fetch.getMockImplementation();
  api.fetch.mockImplementation((url, init) => { if (url.startsWith("/api/trips/")) signal = init.signal; return fetch!(url, init); });
  page(<AppRoutes />); await ready(); fill(); submit();
  await screen.findByText(/Numer zadania:/);
  await waitFor(() => expect(signal).toBeDefined());
  await userEvent.setup().click(screen.getByRole("link", { name: "Wróć do pulpitu" }));
  expect(signal?.aborted).toBe(true);
  expect(api.posts()).toHaveLength(1);
});
