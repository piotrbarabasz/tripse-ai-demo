import { StrictMode } from "react";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { afterEach, expect, it, vi } from "vitest";
import { z } from "zod";
import { fixture } from "../../shared/api/test-fixtures";
import { createApiQueryClient, apiKeys, sessionFailed } from "../../shared/api/query/client";
import { zDocumentDraftOutput, zDraftUpdate, zTripOutput } from "../../shared/api/generated/zod.gen";
import { customSection } from "./editing";
import type { Draft } from "./editing";
import DocumentsWorkspace from "./DocumentsWorkspace";

const base = zDocumentDraftOutput.parse(fixture.draft);
const clients: ReturnType<typeof createApiQueryClient>[] = [], routers: ReturnType<typeof createMemoryRouter>[] = [];
afterEach(() => { clients.splice(0).forEach((client) => client.clear()); routers.splice(0).forEach((router) => router.dispose()); vi.unstubAllGlobals(); });
function network(initial = base, canEdit = true) {
  let current = structuredClone(initial);
  let get = () => Promise.resolve(Response.json(current));
  let put = (value: unknown) => {
    zDraftUpdate.parse(value);
    const raw = z.record(z.string(), z.unknown()).parse(value);
    if (raw.revision !== current.revision) return Promise.resolve(new Response(null, { status: 409 }));
    current = zDocumentDraftOutput.parse({ ...current, ...raw, revision: current.revision + 1, updated_at: "2026-11-01T00:00:00Z", last_library_operation: null });
    return Promise.resolve(Response.json(current));
  };
  const fetch = vi.fn((path: string, init: RequestInit) => {
    if (path.endsWith("/access")) return Promise.resolve(Response.json({ can_edit: canEdit }));
    if (path.endsWith("/templates")) return Promise.resolve(Response.json(fixture.templates));
    if (path.includes("/drafts/")) return init.method === "PUT" ? put(JSON.parse(init.body as string)) : get();
    throw new Error("Unexpected request");
  });
  vi.stubGlobal("fetch", fetch);
  return { fetch, writes: () => fetch.mock.calls.filter(([, init]) => init.method === "PUT"),
    setPut: (value: typeof put) => { put = value; }, setGet: (value: typeof get) => { get = value; },
    current: () => current, replace: (draft: Draft) => { current = draft; } };
}
function page(path = `/documents/${base.document_id}/edit`) {
  const client = createApiQueryClient(); clients.push(client);
  const router = createMemoryRouter([{ path: "documents/*", element: <DocumentsWorkspace /> }, { path: "*", element: <p>Inny widok</p> }], { initialEntries: [path] }); routers.push(router);
  render(<StrictMode><QueryClientProvider client={client}><RouterProvider router={router} /></QueryClientProvider></StrictMode>);
  return { client, router };
}
async function editTitle(title = "Lokalny tytuł") { const input = await screen.findByLabelText("Tytuł dokumentu"); fireEvent.change(input, { target: { value: title } }); }
function draftWith(kind: Parameters<typeof customSection>[0]): Draft {
  const trip = zTripOutput.parse({ ...base.trip_snapshot, days: [{ day_id: "day-1", day_number: 1, title: "Dzień QA", stops: [{ stop_id: "stop-1", name: "Miejsce QA" }] }] });
  return zDocumentDraftOutput.parse({ ...base, template_id: kind === "knowledge" ? "pilot.knowledge" : kind === "logistics" ? "pilot.advanced" : base.template_id,
    confidentiality: kind === "knowledge" ? "internal" : kind === "logistics" ? "internal_restricted" : base.confidentiality,
    trip_snapshot: trip, sections: [customSection(kind, 0, "day-1")] });
}
it("loads persisted data with metadata, no write, and a saved-only safe preview", async () => {
  const api = network(); page(); await screen.findByLabelText("Tytuł dokumentu");
  expect(screen.getByRole("button", { name: "Zapisz zmiany" })).toBeDisabled(); expect(screen.getByText("Brak zmian.")).toBeVisible(); expect(api.writes()).toHaveLength(0);
  expect(screen.getByRole("link", { name: "Podgląd ostatniego zapisu (nowa karta)" })).toHaveAttribute("target", "_blank");
  expect(screen.getByRole("link", { name: "Edytuj w dotychczasowym Studio" })).toHaveAttribute("href", `/documents/demo#edit-draft/${base.document_id}`);
});
it("saves once under duplicate clicks, increments revision, invalidates library/history and preserves metadata", async () => {
  const api = network(); const { client } = page(); const invalidation = vi.spyOn(client, "invalidateQueries"); await editTitle();
  const button = screen.getByRole("button", { name: "Zapisz zmiany" }); act(() => { fireEvent.click(button); fireEvent.click(button); });
  await screen.findByText("Zapisano rewizję 2."); expect(api.writes()).toHaveLength(1);
  expect(z.record(z.string(), z.unknown()).parse(JSON.parse(api.writes()[0]![1].body as string))).toEqual({ revision: 1, title: "Lokalny tytuł" });
  expect(api.current().trip_snapshot).toEqual(base.trip_snapshot); expect(api.current().offer_data).toEqual(base.offer_data); expect(api.current().sections).toEqual(base.sections);
  expect(invalidation).toHaveBeenCalledWith({ queryKey: apiKeys.studio }); expect(screen.getByRole("button", { name: "Zapisz zmiany" })).toBeDisabled();
});
it("does not overwrite edited values or the loaded revision on a background refetch", async () => {
  const api = network(); const { client } = page(); await editTitle(); api.replace({ ...base, revision: 2, title: "Inny redaktor" });
  await act(async () => { await client.invalidateQueries({ queryKey: [...apiKeys.studio, "editor"] }); });
  expect(screen.getByLabelText("Tytuł dokumentu")).toHaveValue("Lokalny tytuł");
  fireEvent.click(screen.getByRole("button", { name: "Zapisz zmiany" })); await screen.findByText(/Konflikt —/);
  expect(zDraftUpdate.parse(JSON.parse(api.writes()[0]![1].body as string)).revision).toBe(1);
});
it("keeps a conflict local draft until explicit inspection and confirmed discard", async () => {
  const api = network(); page(); await editTitle(); api.replace({ ...base, revision: 2, title: "Inny redaktor" });
  fireEvent.click(screen.getByRole("button", { name: "Zapisz zmiany" })); await screen.findByText(/Konflikt —/);
  expect(screen.getByLabelText("Tytuł dokumentu")).toHaveValue("Lokalny tytuł"); expect(api.writes()).toHaveLength(1);
  fireEvent.click(screen.getByRole("button", { name: "Sprawdź wersję serwera" })); await screen.findByRole("heading", { name: "Wersja serwera: rewizja 2" });
  expect(screen.getByLabelText("Tytuł dokumentu")).toHaveValue("Lokalny tytuł");
  fireEvent.click(screen.getByRole("button", { name: "Wczytaj wersję serwera i odrzuć moje zmiany" }));
  fireEvent.click(screen.getByRole("button", { name: "Zachowaj moje zmiany" })); expect(screen.getByLabelText("Tytuł dokumentu")).toHaveValue("Lokalny tytuł");
  fireEvent.click(screen.getByRole("button", { name: "Wczytaj wersję serwera i odrzuć moje zmiany" })); fireEvent.click(screen.getByRole("button", { name: "Potwierdź odrzucenie" }));
  expect(screen.getByLabelText("Tytuł dokumentu")).toHaveValue("Inny redaktor"); expect(api.writes()).toHaveLength(1);
});
it("recovers a committed-but-lost save by explicit GET without a second PUT", async () => {
  const api = network(); api.setPut((value) => { const raw = z.record(z.string(), z.unknown()).parse(value); api.replace(zDocumentDraftOutput.parse({ ...base, ...raw, revision: 2, last_library_operation: null })); return Promise.reject(new TypeError("lost")); });
  page(); await editTitle(); fireEvent.click(screen.getByRole("button", { name: "Zapisz zmiany" })); await screen.findByText(/Niepewny wynik/);
  expect(screen.getByLabelText("Tytuł dokumentu")).toBeDisabled(); fireEvent.click(screen.getByRole("button", { name: "Sprawdź wersję serwera" }));
  await screen.findByText("Zapisano rewizję 2."); expect(api.writes()).toHaveLength(1); expect(screen.getByLabelText("Tytuł dokumentu")).toHaveValue("Lokalny tytuł");
});
it("allows a deliberate identical retry only after read-back confirms the old baseline", async () => {
  const api = network(); api.setPut(() => Promise.resolve(new Response(null, { status: 503 }))); page(); await editTitle();
  fireEvent.click(screen.getByRole("button", { name: "Zapisz zmiany" })); await screen.findByText(/Niepewny wynik/);
  expect(screen.queryByRole("button", { name: "Ponów ten sam zapis" })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Sprawdź wersję serwera" })); fireEvent.click(await screen.findByRole("button", { name: "Ponów ten sam zapis" }));
  await waitFor(() => expect(api.writes()).toHaveLength(2)); expect(api.writes()[0]![1].body).toBe(api.writes()[1]![1].body);
});
it.each([401, 403, 422])("handles PUT %i without replay or raw errors", async (status) => {
  const api = network(); api.setPut(() => Promise.resolve(new Response("confidential raw body", { status }))); const { client } = page(); await editTitle();
  fireEvent.click(screen.getByRole("button", { name: "Zapisz zmiany" })); await screen.findByRole("alert");
  expect(api.writes()).toHaveLength(1); expect(sessionFailed(client)).toBe(status === 401); expect(screen.queryByText(/confidential raw body/)).not.toBeInTheDocument();
  if (status === 401) expect(screen.queryByLabelText("Tytuł dokumentu")).not.toBeInTheDocument();
  else expect(screen.getByLabelText("Tytuł dokumentu")).toHaveValue("Lokalny tytuł");
});
it("denies direct reader URLs without fetching private drafts", async () => { const api = network(base, false); page(); await screen.findByText("Brak uprawnień do edycji dokumentu."); expect(api.fetch.mock.calls.some(([path]) => path.includes("/drafts/"))).toBe(false); });
it("denies archived documents", async () => { network({ ...base, document_status: "archived", archived_at: "2026-10-31T00:00:00Z" }); page(); await screen.findByText(/Dokument jest w archiwum/); expect(screen.queryByRole("button", { name: "Zapisz zmiany" })).not.toBeInTheDocument(); });
it("validates IDs before any draft request", async () => { const api = network(); page("/documents/CON/edit"); await screen.findByText("Nieprawidłowy identyfikator dokumentu."); expect(api.fetch.mock.calls.some(([path]) => path.includes("/drafts/"))).toBe(false); });
it("preserves null legacy sections without manufacturing a migration", async () => { const api = network({ ...base, sections: null }); page(); await editTitle(); expect(screen.getByText(/starszą strukturę/)).toBeVisible(); fireEvent.click(screen.getByRole("button", { name: "Zapisz zmiany" })); await screen.findByText("Zapisano rewizję 2."); expect(api.current().sections).toBeNull(); });
it("saves day overrides against original day IDs and preserves empty strings", async () => {
  const draft = draftWith("day"); const api = network(draft); page(); await screen.findByLabelText("Tytuł dokumentu");
  fireEvent.click(screen.getByText("Nadpisania dni w dokumencie"));
  fireEvent.change(screen.getByLabelText("Opis dnia 1"), { target: { value: "Opis w dokumencie" } });
  fireEvent.click(screen.getByRole("button", { name: "Zapisz zmiany" })); await screen.findByText("Zapisano rewizję 2.");
  expect(api.current().day_overrides).toEqual([{ day_id: "day-1", title: "", description: "Opis w dokumencie" }]);
  expect(api.current().trip_snapshot).toEqual(draft.trip_snapshot);
});
it("protects bound/required sections, reorders stable IDs and adds/removes custom sections only after confirmation", async () => {
  network(); page(); await screen.findByLabelText("Tytuł sekcji");
  expect(screen.getByRole("button", { name: "Usuń sekcję" })).toBeDisabled(); expect(screen.getByRole("checkbox", { name: /Widoczna w dokumencie/ })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Dodaj sekcję" })); fireEvent.change(screen.getByLabelText("Tytuł sekcji"), { target: { value: "Własna" } });
  fireEvent.click(screen.getByRole("button", { name: "Przesuń sekcję w górę" })); expect(screen.getByLabelText("Tytuł sekcji")).toHaveValue("Własna");
  fireEvent.click(screen.getByRole("button", { name: "Usuń sekcję" })); expect(screen.getByLabelText("Tytuł sekcji")).toHaveValue("Własna");
  fireEvent.click(screen.getByRole("button", { name: "Zachowaj sekcję" })); expect(screen.getByLabelText("Tytuł sekcji")).toHaveValue("Własna");
  fireEvent.click(screen.getByRole("button", { name: "Usuń sekcję" })); fireEvent.click(screen.getByRole("button", { name: "Potwierdź usunięcie sekcji" })); expect(screen.queryByLabelText("Tytuł sekcji")).not.toBeInTheDocument();
});
it("normalizes section order when adding to a document with noncontiguous stored indexes", async () => {
  const draft = { ...base, sections: base.sections?.map((section, i) => ({ ...section, order: i + 50 })) };
  const api = network(draft); page(); await screen.findByLabelText("Tytuł sekcji");
  fireEvent.click(screen.getByRole("button", { name: "Dodaj sekcję" })); fireEvent.click(screen.getByRole("button", { name: "Zapisz zmiany" }));
  await screen.findByText("Zapisano rewizję 2.");
  expect(api.current().sections?.map((section) => section.order)).toEqual(api.current().sections?.map((_, i) => i));
  expect(api.current().sections?.slice(0, -1).map((section) => section.section_id)).toEqual(base.sections?.map((section) => section.section_id));
});
it.each(["text", "list", "image", "gallery", "table", "callout", "day", "logistics", "knowledge"] as const)("renders and edits typed %s sections", async (kind) => {
  const draft = draftWith(kind); network(draft); page(); await screen.findByLabelText("Tytuł sekcji");
  fireEvent.change(screen.getByLabelText("Tytuł sekcji"), { target: { value: "Zmieniona sekcja" } });
  expect(screen.getByLabelText("Tytuł sekcji")).toHaveValue("Zmieniona sekcja");
  if (kind === "list") { fireEvent.click(screen.getByRole("button", { name: "Dodaj punkt" })); fireEvent.change(screen.getByLabelText("Punkt 1"), { target: { value: "Punkt QA" } }); }
  if (kind === "table") { fireEvent.click(screen.getByRole("button", { name: "Dodaj wiersz" })); fireEvent.change(screen.getByLabelText("Komórka 1, 1"), { target: { value: "Wartość" } }); fireEvent.click(screen.getByRole("button", { name: "Dodaj kolumnę" })); expect(screen.getByLabelText("Komórka 1, 3")).toHaveValue(""); }
  if (kind === "logistics") { expect(screen.getByLabelText("Dystans jazdy (km)")).toHaveValue(null); fireEvent.change(screen.getByLabelText("Dystans jazdy (km)"), { target: { value: "12" } }); fireEvent.change(screen.getByLabelText("Dystans jazdy (km)"), { target: { value: "" } }); fireEvent.change(screen.getByLabelText("Strefa IANA"), { target: { value: "bad-zone" } }); expect(screen.getByRole("button", { name: "Zapisz zmiany" })).toBeDisabled(); fireEvent.change(screen.getByLabelText("Strefa IANA"), { target: { value: "Europe/Warsaw" } }); }
  if (kind === "knowledge") { fireEvent.change(screen.getByLabelText("Status weryfikacji"), { target: { value: "verified" } }); expect(screen.getByRole("button", { name: "Zapisz zmiany" })).toBeDisabled(); fireEvent.click(screen.getByRole("button", { name: "Dodaj źródło" })); fireEvent.change(screen.getByLabelText("Dokładne odniesienie 1"), { target: { value: "Opracowanie QA" } }); fireEvent.change(screen.getByLabelText("Data sprawdzenia 1"), { target: { value: "2026-10-31" } }); }
  expect(screen.getByRole("button", { name: "Zapisz zmiany" })).toBeEnabled();
});
it("warns on dirty route/native unload and only discards after confirmation", async () => {
  network(); const { router } = page(); await editTitle(); const event = new Event("beforeunload", { cancelable: true }); window.dispatchEvent(event); expect(event.defaultPrevented).toBe(true);
  await act(async () => { await router.navigate("/other"); }); expect(screen.getByRole("alertdialog")).toBeVisible(); fireEvent.click(screen.getByRole("button", { name: "Zostań w formularzu" })); expect(screen.getByLabelText("Tytuł dokumentu")).toHaveValue("Lokalny tytuł");
  fireEvent.click(screen.getByRole("button", { name: "Odrzuć zmiany" })); const dialog = screen.getByRole("alertdialog"); fireEvent.click(within(dialog).getByRole("button", { name: "Potwierdź odrzucenie" })); expect(screen.getByLabelText("Tytuł dokumentu")).toHaveValue(base.title);
});
