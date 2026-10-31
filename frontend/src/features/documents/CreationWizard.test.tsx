import { StrictMode } from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { afterEach, expect, it, vi } from "vitest";
import { fixture } from "../../shared/api/test-fixtures";
import { createApiQueryClient, apiKeys, sessionFailed } from "../../shared/api/query/client";
import { zDraftRequest, zDocumentDraftOutput, zTripOutput, zCampaignOutput } from "../../shared/api/generated/zod.gen";
import { templatesSchema } from "../../shared/api/adapters/guards";
import DocumentsWorkspace from "./DocumentsWorkspace";

const templates = templatesSchema.parse(fixture.templates);
const trip = zTripOutput.parse(fixture.trip);
const campaign = zCampaignOutput.parse(fixture.campaign);
const base = zDocumentDraftOutput.parse(fixture.draft);
const clients: ReturnType<typeof createApiQueryClient>[] = [];
const routers: ReturnType<typeof createMemoryRouter>[] = [];
afterEach(() => { clients.splice(0).forEach((client) => client.clear()); routers.splice(0).forEach((router) => router.dispose()); vi.unstubAllGlobals(); });
function network(canEdit = true) {
  let catalog = () => Promise.resolve(Response.json(templates));
  let trips = () => Promise.resolve(Response.json([trip]));
  let campaigns = () => Promise.resolve(Response.json([campaign]));
  let stored: unknown;
  let post = (value: unknown) => {
    const p = zDraftRequest.parse(value); const template = templates.find((item) => item.template_id === p.template_id)!;
    stored = { ...base, ...p, confidentiality: template.confidentiality, trip_snapshot: p.source_type === "trip" ? trip : null, campaign_snapshot: p.source_type === "campaign" ? campaign : null };
    return Promise.resolve(Response.json(stored, { status: 201 }));
  };
  let get = () => Promise.resolve(Response.json(stored));
  const fetch = vi.fn((path: string, init: RequestInit) => {
    if (path.endsWith("/access")) return Promise.resolve(Response.json({ can_edit: canEdit }));
    if (path.endsWith("/templates")) return catalog();
    if (path.endsWith("/trips")) return trips();
    if (path.endsWith("/campaigns")) return campaigns();
    if (path.endsWith("/drafts")) return post(JSON.parse(init.body as string));
    if (path.includes("/drafts/")) return get();
    throw new Error("Unexpected request");
  });
  vi.stubGlobal("fetch", fetch);
  return { fetch, posts: () => fetch.mock.calls.filter(([, init]) => init.method === "POST"),
    setCatalog: (value: typeof catalog) => { catalog = value; },
    setTrips: (value: typeof trips) => { trips = value; }, setCampaigns: (value: typeof campaigns) => { campaigns = value; },
    setPost: (value: typeof post) => { post = value; }, setGet: (value: typeof get) => { get = value; } };
}
function page(path = "/documents/new") {
  const client = createApiQueryClient(); clients.push(client);
  const router = createMemoryRouter([{ path: "documents/*", element: <DocumentsWorkspace /> }, { path: "*", element: <p>Inny widok</p> }], { initialEntries: [path] }); routers.push(router);
  render(<StrictMode><QueryClientProvider client={client}><RouterProvider router={router} /></QueryClientProvider></StrictMode>);
  return { client, router };
}
async function confirm(templateId = "offer.private") {
  const template = templates.find((item) => item.template_id === templateId)!;
  fireEvent.click(await screen.findByRole("radio", { name: new RegExp(template.name) }));
  fireEvent.click(screen.getByRole("button", { name: "Dalej: źródło" }));
  fireEvent.click(await screen.findByRole("radio", { name: new RegExp(template.source_type === "trip" ? trip.title : campaign.title) }));
  fireEvent.click(screen.getByRole("button", { name: "Dalej: potwierdzenie" }));
  return screen.getByRole("button", { name: "Utwórz i zapisz dokument" });
}
it("presents eight server templates and preserves title, source and variant across steps without POST", async () => {
  const api = network(); page(); await confirm();
  fireEvent.change(screen.getByLabelText("Tytuł dokumentu"), { target: { value: "Moja oferta" } });
  fireEvent.click(screen.getByRole("button", { name: "Wstecz: źródło" }));
  expect(screen.getByRole("radio", { name: /Synthetic source/ })).toBeChecked();
  fireEvent.click(screen.getByRole("button", { name: "Wstecz: typ dokumentu" }));
  expect(screen.getAllByRole("radio")).toHaveLength(8);
  fireEvent.click(screen.getByRole("button", { name: "Dalej: źródło" })); fireEvent.click(screen.getByRole("button", { name: "Dalej: potwierdzenie" }));
  expect(screen.getByLabelText("Tytuł dokumentu")).toHaveValue("Moja oferta"); expect(api.posts()).toHaveLength(0);
});
it("uses campaign sources and server variants, clearing an incompatible trip selection", async () => {
  const api = network(); page(); await confirm();
  fireEvent.click(screen.getByRole("button", { name: "Wstecz: źródło" })); fireEvent.click(screen.getByRole("button", { name: "Wstecz: typ dokumentu" }));
  fireEvent.click(screen.getByRole("radio", { name: /Nowości \/ kolekcje/ }));
  expect(screen.getByLabelText("Wariant układu")).toHaveValue("new_trips");
  fireEvent.change(screen.getByLabelText("Wariant układu"), { target: { value: "theme_collection" } });
  fireEvent.click(screen.getByRole("button", { name: "Dalej: źródło" }));
  expect(await screen.findByRole("radio", { name: /Synthetic campaign/ })).not.toBeChecked();
  expect(screen.queryByRole("radio", { name: /Synthetic source/ })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("radio", { name: /Synthetic campaign/ })); fireEvent.click(screen.getByRole("button", { name: "Dalej: potwierdzenie" }));
  expect(screen.getByText("theme_collection", { exact: true })).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Utwórz i zapisz dokument" }));
  await screen.findByRole("heading", { name: "Dokument został zapisany" });
  expect(JSON.parse(api.posts()[0]![1].body as string)).toMatchObject({ source_type: "campaign", source_id: campaign.campaign_id, layout_variant: "theme_collection" });
});
it("sends one POST under duplicate clicks, verifies GET, invalidates library and links to the real editor", async () => {
  const api = network(); const { client } = page();
  client.setQueryData(apiKeys.library({}), fixture.library); const invalidate = vi.spyOn(client, "invalidateQueries");
  const create = await confirm(); act(() => { fireEvent.click(create); fireEvent.click(create); });
  await screen.findByRole("heading", { name: "Dokument został zapisany" });
  expect(api.posts()).toHaveLength(1); expect(invalidate).toHaveBeenCalledWith({ queryKey: apiKeys.studio });
  const p = zDraftRequest.parse(JSON.parse(api.posts()[0]![1].body as string));
  expect(screen.getByRole("link", { name: "Otwórz dokument w edytorze" })).toHaveAttribute("href", `/documents/demo#edit-draft/${p.document_id}`);
  expect(screen.getByRole("link", { name: "Wróć do biblioteki" })).toHaveAttribute("href", "/documents/library");
  expect(api.fetch.mock.calls.some(([path, init]) => path.endsWith(`/drafts/${p.document_id}`) && init.method === "GET")).toBe(true);
});
it.each([401, 403, 503])("handles source-list %i without creating a draft", async (status) => {
  const api = network(); api.setTrips(() => Promise.resolve(new Response(null, { status }))); const { client } = page();
  fireEvent.click(await screen.findByRole("radio", { name: /Wyjazd indywidualny/ })); fireEvent.click(screen.getByRole("button", { name: "Dalej: źródło" }));
  await screen.findByRole("alert"); expect(api.posts()).toHaveLength(0); expect(sessionFailed(client)).toBe(status === 401);
  if (status === 401) { expect(client.getQueryCache().getAll().every((query) => query.state.data === undefined)).toBe(true); expect(screen.queryByRole("radio")).not.toBeInTheDocument(); }
});
it("shows empty, search-miss and unavailable source states with the verified legacy management route", async () => {
  const api = network(); api.setTrips(() => Promise.resolve(Response.json([]))); page("/documents/new?template=offer.private");
  fireEvent.click(await screen.findByRole("button", { name: "Dalej: źródło" })); await screen.findByText("Brak zapisanych źródeł tego typu.");
  expect(screen.getByRole("button", { name: "Dalej: potwierdzenie" })).toBeDisabled();
  expect(screen.getByRole("link", { name: "Zarządzaj źródłami w dotychczasowym Studio" })).toHaveAttribute("href", "/documents/demo#trips");
  api.setTrips(() => Promise.resolve(Response.json([trip]))); fireEvent.click(screen.getByRole("button", { name: "Odśwież źródła" })); await screen.findByRole("radio");
  fireEvent.change(screen.getByLabelText("Szukaj źródła"), { target: { value: "nie istnieje" } }); await screen.findByText("Brak źródeł pasujących do wyszukiwania.");
});
it("requires selection of a new revision after a source refresh", async () => {
  const api = network(); page(); await confirm(); fireEvent.click(screen.getByRole("button", { name: "Wstecz: źródło" }));
  api.setTrips(() => Promise.resolve(Response.json([{ ...trip, revision: 2 }]))); fireEvent.click(screen.getByRole("button", { name: "Odśwież źródła" }));
  await screen.findByText("Źródło zmieniło się. Wybierz ponownie jego aktualną rewizję."); expect(screen.getByRole("button", { name: "Dalej: potwierdzenie" })).toBeDisabled();
  fireEvent.click(screen.getByRole("radio", { name: /Rewizja 2/ })); expect(screen.getByRole("button", { name: "Dalej: potwierdzenie" })).toBeEnabled(); expect(api.posts()).toHaveLength(0);
});
it.each([409, 422])("requires a fresh explicit review after POST %i", async (status) => {
  const api = network(); api.setPost(() => Promise.resolve(new Response(null, { status }))); page(); fireEvent.click(await confirm());
  const review = await screen.findByRole("button", { name: "Sprawdź aktualne źródła" }); expect(api.posts()).toHaveLength(1);
  expect(screen.queryByRole("button", { name: "Ponów tę samą próbę" })).not.toBeInTheDocument();
  fireEvent.click(review); await waitFor(() => expect(screen.getByRole("button", { name: "Dalej: potwierdzenie" })).toBeDisabled()); expect(screen.getByRole("radio")).not.toBeChecked();
});
it.each([401, 403])("handles POST %i without replay or leaking private data", async (status) => {
  const api = network(); api.setPost(() => Promise.resolve(new Response("raw private source", { status }))); const { client } = page(); fireEvent.click(await confirm());
  await screen.findByRole("alert"); expect(api.posts()).toHaveLength(1); expect(sessionFailed(client)).toBe(status === 401);
  expect(screen.queryByText(/raw private/)).not.toBeInTheDocument(); expect(screen.queryByRole("button", { name: "Ponów tę samą próbę" })).not.toBeInTheDocument();
});
it("allows only GET recovery during uncertainty and repeats the identical payload after a verified 404", async () => {
  const api = network(); api.setPost(() => Promise.reject(new TypeError("offline"))); api.setGet(() => Promise.resolve(new Response(null, { status: 503 })));
  page(); fireEvent.click(await confirm()); await screen.findByText(/Nie można potwierdzić wyniku zapisu/);
  expect(api.posts()).toHaveLength(1); expect(screen.queryByRole("button", { name: "Ponów tę samą próbę" })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Sprawdź zapis ponownie" })); await waitFor(() => expect(api.fetch.mock.calls.filter(([path]) => path.includes("/drafts/")).length).toBe(2)); expect(api.posts()).toHaveLength(1);
  api.setGet(() => Promise.resolve(new Response(null, { status: 404 }))); fireEvent.click(screen.getByRole("button", { name: "Sprawdź zapis ponownie" }));
  fireEvent.click(await screen.findByRole("button", { name: "Ponów tę samą próbę" })); await waitFor(() => expect(api.posts()).toHaveLength(2));
  expect(api.posts()[0]![1].body).toBe(api.posts()[1]![1].body);
});
it("blocks leaving dirty input, preserves state on stay, and warns on native unload", async () => {
  network(); const { router } = page(); await confirm();
  const event = new Event("beforeunload", { cancelable: true }); window.dispatchEvent(event); expect(event.defaultPrevented).toBe(true);
  await act(async () => { await router.navigate("/other"); }); expect(screen.getByRole("alertdialog")).toBeVisible(); expect(router.state.location.pathname).toBe("/documents/new");
  fireEvent.click(screen.getByRole("button", { name: "Zostań w formularzu" })); expect(screen.getByLabelText("Tytuł dokumentu")).toHaveValue(trip.title);
  await act(async () => { await router.navigate("/other"); }); fireEvent.click(screen.getByRole("button", { name: "Opuść formularz" })); await screen.findByText("Inny widok");
});
it("warns when only a preselected template's layout was changed", async () => {
  network(); const { router } = page("/documents/new?template=marketing.collection");
  fireEvent.change(await screen.findByLabelText("Wariant układu"), { target: { value: "theme_collection" } });
  await act(async () => { await router.navigate("/other"); }); expect(screen.getByRole("alertdialog")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Zostań w formularzu" })); expect(screen.getByLabelText("Wariant układu")).toHaveValue("theme_collection");
});
it("requires a new reviewed intent after an explicit retry gets 409", async () => {
  const api = network(); api.setPost(() => Promise.reject(new TypeError())); api.setGet(() => Promise.resolve(new Response(null, { status: 404 })));
  page(); fireEvent.click(await confirm());
  const retry = await screen.findByRole("button", { name: "Ponów tę samą próbę" });
  api.setPost(() => Promise.resolve(new Response(null, { status: 409 }))); fireEvent.click(retry);
  const review = await screen.findByRole("button", { name: "Sprawdź aktualne źródła" });
  expect(screen.queryByRole("button", { name: "Ponów tę samą próbę" })).not.toBeInTheDocument(); expect(api.posts()).toHaveLength(2);
  fireEvent.click(review); const radio = await screen.findByRole("radio", { name: /Synthetic source/ }); fireEvent.click(radio);
  fireEvent.click(screen.getByRole("button", { name: "Dalej: potwierdzenie" })); fireEvent.click(screen.getByRole("button", { name: "Utwórz i zapisz dokument" }));
  await waitFor(() => expect(api.posts()).toHaveLength(3));
  expect(zDraftRequest.parse(JSON.parse(api.posts()[0]![1].body as string)).document_id).not.toBe(zDraftRequest.parse(JSON.parse(api.posts()[2]![1].body as string)).document_id);
});
it("supports keyboard-only template selection and step progression", async () => {
  network(); page(); const user = userEvent.setup(); const radio = await screen.findByRole("radio", { name: /Wyjazd indywidualny/ });
  radio.focus(); await user.keyboard(" "); expect(radio).toBeChecked(); screen.getByRole("button", { name: "Dalej: źródło" }).focus(); await user.keyboard("{Enter}"); await screen.findByRole("radio", { name: /Synthetic source/ });
  expect(screen.getByRole("heading", { name: "Utwórz dokument" })).toHaveFocus();
});
it("rejects invalid direct template URLs", async () => { network(); page("/documents/new?template=invalid"); expect(await screen.findByRole("alert")).toHaveTextContent("Nieprawidłowy szablon"); });
it("shows a failed template read and supports safe explicit retry", async () => {
  const api = network(); api.setCatalog(() => Promise.resolve(new Response(null, { status: 503 }))); page();
  expect(await screen.findByRole("alert")).toHaveTextContent("niedostępna");
  api.setCatalog(() => Promise.resolve(Response.json(templates))); fireEvent.click(screen.getByRole("button", { name: "Spróbuj ponownie" }));
  await screen.findByRole("radio", { name: /Wyjazd indywidualny/ }); expect(api.posts()).toHaveLength(0);
});
it("shows an empty catalog without actionable creation controls", async () => {
  const api = network(); api.setCatalog(() => Promise.resolve(Response.json([]))); page(); await screen.findByText("Brak dostępnych szablonów.");
  expect(screen.queryByRole("radio")).not.toBeInTheDocument(); expect(screen.queryByRole("button", { name: "Dalej: źródło" })).not.toBeInTheDocument(); expect(api.posts()).toHaveLength(0);
});
it("keeps a direct reader URL non-actionable with no source reads", async () => {
  const api = network(false); page("/documents/new?template=offer.private"); expect(await screen.findByRole("alert")).toHaveTextContent("Brak uprawnień");
  expect(screen.queryByRole("radio")).not.toBeInTheDocument(); expect(api.posts()).toHaveLength(0); expect(api.fetch.mock.calls.some(([path]) => path.endsWith("/trips"))).toBe(false);
});
