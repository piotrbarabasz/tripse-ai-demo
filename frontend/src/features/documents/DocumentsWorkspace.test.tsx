import { StrictMode } from "react";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { afterEach, expect, it, vi } from "vitest";
import { zLibraryPage } from "../../shared/api/generated/zod.gen";
import { createApiQueryClient } from "../../shared/api/query/client";
import { fixture } from "../../shared/api/test-fixtures";
import DocumentsWorkspace from "./DocumentsWorkspace";
import { documentLinks, validDocumentId } from "./links";

const library = zLibraryPage.parse(fixture.library);
const row = library.items.find((item) => item.document_id === "synthetic-draft")!;
const clients: ReturnType<typeof createApiQueryClient>[] = [];
afterEach(() => { clients.forEach((client) => client.clear()); clients.length = 0; vi.unstubAllGlobals(); });

function network(canEdit = true) {
  let access = () => Promise.resolve(Response.json({ can_edit: canEdit }));
  let templates = () => Promise.resolve(Response.json(fixture.templates));
  let list = (query: URLSearchParams): Promise<Response> => { void query; return Promise.resolve(Response.json(library)); };
  let revisions = () => Promise.resolve(Response.json(fixture.revisions));
  const fetch = vi.fn((path: string, init: RequestInit) => {
    if (init.method !== "GET") throw new Error("Document mutations forbidden");
    if (path.endsWith("/access")) return access();
    if (path.endsWith("/templates")) return templates();
    if (path.includes("/revisions")) return revisions();
    if (path.includes("/library?")) return list(new URL(path, "http://localhost").searchParams);
    throw new Error("Unexpected API path");
  });
  vi.stubGlobal("fetch", fetch);
  return { fetch, setAccess: (value: typeof access) => { access = value; }, setTemplates: (value: typeof templates) => { templates = value; },
    setList: (value: typeof list) => { list = value; }, setRevisions: (value: typeof revisions) => { revisions = value; },
    lists: () => fetch.mock.calls.filter(([path]) => path.includes("/library?")) };
}
function page(path = "/documents") {
  const client = createApiQueryClient(); clients.push(client);
  return { client, ...render(<StrictMode><QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}>
    <Routes><Route path="documents/*" element={<DocumentsWorkspace />} /><Route path="*" element={<p>Inny widok</p>} /></Routes>
  </MemoryRouter></QueryClientProvider></StrictMode>) };
}
async function loadedLibrary() { await screen.findByRole("heading", { name: row.title }); }

it("renders all eight fixture templates grouped by family, with descriptions and variants", async () => {
  const api = network(); page();
  await screen.findByRole("heading", { name: "Wyjazd indywidualny" });
  expect(within(screen.getByRole("region", { name: "Oferty" })).getAllByRole("article")).toHaveLength(4);
  expect(within(screen.getByRole("region", { name: "Materiały pilota" })).getAllByRole("article")).toHaveLength(3);
  expect(within(screen.getByRole("region", { name: "Marketing" })).getAllByRole("article")).toHaveLength(1);
  expect(screen.getAllByRole("article")).toHaveLength(8);
  expect(screen.getByText("new_trips, theme_collection")).toBeVisible();
  expect(screen.getByText("Wyjazd bez pilota; zakres wsparcia wymaga ustalenia.")).toBeVisible();
  expect(screen.getAllByRole("link", { name: /Tworzenie w dotychczasowym Studio/ })).toHaveLength(8);
  expect(api.fetch.mock.calls.every(([, init]) => init.method === "GET")).toBe(true);
});

it("keeps templates visible to readers without active creation links", async () => {
  network(false); page();
  await screen.findByRole("heading", { name: "Materiały merytoryczne" });
  expect(screen.getByText("Dostęp tylko do odczytu")).toBeVisible();
  expect(screen.queryByRole("link", { name: /Tworzenie w/ })).not.toBeInTheDocument();
});

it("shows access loading and makes no private resource reads before access is confirmed", () => {
  const api = network(); api.setAccess(() => new Promise<Response>(() => undefined)); page();
  expect(screen.getByRole("status")).toHaveTextContent("Sprawdzanie dostępu");
  expect(api.fetch.mock.calls.every(([path]) => path.endsWith("/access"))).toBe(true);
});

it("shows library loading and a real empty state", async () => {
  const api = network(); api.setList(() => new Promise<Response>(() => undefined)); page("/documents/library");
  expect(await screen.findByText("Wczytywanie biblioteki…")).toBeVisible();
  api.setList(() => Promise.resolve(Response.json({ items: [], total: 0, offset: 0, limit: 25, has_more: false })));
  fireEvent.change(screen.getByLabelText("Archiwum"), { target: { value: "include" } });
  expect(await screen.findByText("Brak dokumentów pasujących do filtrów.")).toBeVisible();
  expect(screen.getByRole("button", { name: "Następna strona" })).toBeDisabled();
});

it("sends every filter and sort to the backend, with pagination reset", async () => {
  const api = network(); page("/documents/library"); await loadedLibrary();
  await screen.findByRole("option", { name: "Self-Guide" });
  for (const [label, value] of [["Rodzina", "pilot"], ["Szablon", "pilot.basic"], ["Status dokumentu", "archived"], ["Archiwum", "only"], ["Sortuj według", "title"], ["Kierunek", "asc"]]) {
    fireEvent.change(screen.getByLabelText(label!), { target: { value } });
  }
  await waitFor(() => {
    const url = api.lists().at(-1)?.[0];
    expect(url).toContain("family=pilot"); expect(url).toContain("template_id=pilot.basic");
    expect(url).toContain("document_status=archived"); expect(url).toContain("archived=only");
    expect(url).toContain("sort=title"); expect(url).toContain("direction=asc");
    expect(url).toContain("offset=0"); expect(url).toContain("limit=25");
  });
});

it("debounces search, cancels the old read and ignores a late response", async () => {
  const api = network();
  let resolveOld: ((value: Response) => void) | undefined;
  api.setList(() => new Promise<Response>((resolve) => { resolveOld = resolve; }));
  page("/documents/library"); await screen.findByText("Wczytywanie biblioteki…");
  await waitFor(() => expect(api.lists().length).toBeGreaterThan(0));
  const oldSignal = api.lists().at(-1)?.[1].signal;
  api.setList((query) => Promise.resolve(Response.json({ ...library, items: [{ ...row, title: "Nowy wynik" }], total: 1, has_more: false, search: query.get("search") })));
  const input = screen.getByLabelText("Szukaj po tytule");
  fireEvent.change(input, { target: { value: "No" } });
  fireEvent.change(input, { target: { value: "Nowy" } });
  expect(oldSignal?.aborted).toBe(true);
  expect(await screen.findByRole("heading", { name: "Nowy wynik" })).toBeVisible();
  expect(api.lists().filter(([url]) => url.includes("search=No&"))).toHaveLength(0);
  resolveOld?.(Response.json({ ...library, items: [{ ...row, title: "Stary wynik" }] }));
  await waitFor(() => expect(screen.queryByRole("heading", { name: "Stary wynik" })).not.toBeInTheDocument());
});

it("uses server offsets/limit/has_more and never paginates an all-documents download", async () => {
  const api = network();
  api.setList((query) => {
    const offset = Number(query.get("offset"));
    return Promise.resolve(Response.json({ items: Array.from({ length: offset === 0 ? 25 : 1 }, (_, index) => ({ ...row, document_id: `synthetic-${offset + index}`, title: `Dokument ${offset + index}` })), total: 26, offset, limit: 25, has_more: offset === 0 }));
  });
  page("/documents/library"); await screen.findByRole("heading", { name: "Dokument 0" });
  expect(screen.getAllByRole("article")).toHaveLength(25);
  fireEvent.click(screen.getByRole("button", { name: "Następna strona" }));
  await screen.findByRole("heading", { name: "Dokument 25" });
  expect(screen.getAllByRole("article")).toHaveLength(1);
  expect(api.lists().at(-1)?.[0]).toContain("offset=25");
  expect(screen.getByText("26–26 z 26")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Poprzednia strona" }));
  expect(await screen.findByRole("heading", { name: "Dokument 0" })).toBeVisible();
});

it("displays archived metadata and hides editing links even for editors", async () => {
  const api = network(); api.setList(() => Promise.resolve(Response.json({ ...library, items: [{ ...row, document_status: "archived", archived_at: "2026-10-31T00:00:00Z" }] })));
  page("/documents/library"); await loadedLibrary();
  expect(screen.getByText("W archiwum")).toBeVisible();
  expect(screen.queryByRole("link", { name: /Edytuj w/ })).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Podgląd A4/ })).toBeVisible();
});

it("shows read-only metadata/history and verified legacy/preview links without loading a full draft", async () => {
  const api = network(); page("/documents/library/synthetic-draft");
  expect(await screen.findByRole("heading", { name: "Rewizja 2" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "Rewizja 1" })).toBeVisible();
  expect(screen.getByRole("link", { name: /Edytuj w dotychczasowym/ })).toHaveAttribute("href", "/documents/demo#edit-draft/synthetic-draft");
  expect(screen.getByRole("link", { name: /Edytuj w React/ })).toHaveAttribute("href", "/documents/synthetic-draft/edit");
  expect(screen.getByRole("link", { name: /Historia w dotychczasowym/ })).toHaveAttribute("href", "/documents/demo#revisions/synthetic-draft");
  const preview = screen.getByRole("link", { name: "Podgląd rewizji 1 (nowa karta)" });
  expect(preview).toHaveAttribute("href", "/api/document-studio/library/synthetic-draft/revisions/1/preview");
  expect(preview).toHaveAttribute("rel", "noopener noreferrer");
  expect(api.fetch.mock.calls.some(([path]) => path.includes("/drafts/"))).toBe(false);
  expect(document.querySelector("iframe")).toBeNull();
});

it("keeps filtering state in memory across detail navigation and supports keyboard catalog/library navigation", async () => {
  network(false); page("/documents/library"); await loadedLibrary();
  fireEvent.change(screen.getByLabelText("Rodzina"), { target: { value: "offer" } });
  const user = userEvent.setup();
  await user.click(await screen.findByRole("link", { name: new RegExp(`^Szczegóły i historia: ${row.title}$`) }));
  await screen.findByRole("heading", { name: "Rewizja 1" });
  expect(screen.queryByRole("link", { name: /Edytuj w/ })).not.toBeInTheDocument();
  await user.click(screen.getByRole("link", { name: "Wróć do biblioteki" }));
  expect(await screen.findByLabelText("Rodzina")).toHaveValue("offer");
  const catalog = within(screen.getByRole("navigation", { name: "Widoki Document Studio" })).getByRole("link", { name: "Katalog szablonów" });
  catalog.focus(); await user.keyboard("{Enter}");
  expect(await screen.findByRole("heading", { name: "Wyjazd indywidualny" })).toBeVisible();
});

it.each([401, 403])("blocks resources after access HTTP %s and never exposes raw details", async (status) => {
  const api = network(); api.setAccess(() => Promise.resolve(Response.json({ detail: "private identity" }, { status })));
  const { client } = page("/documents/library");
  expect(await screen.findByRole("alert")).not.toHaveTextContent("private identity");
  expect(api.fetch.mock.calls.every(([path]) => path.endsWith("/access"))).toBe(true);
  expect(client.getQueryCache().getAll().every((query) => query.state.data === undefined)).toBe(true);
});

it.each([401, 403, 404, 503, 200])("handles library HTTP %s or malformed data safely", async (status) => {
  const api = network(); api.setList(() => Promise.resolve(Response.json({ detail: "private pilot data" }, { status })));
  page("/documents/library");
  expect(await screen.findByRole("alert")).not.toHaveTextContent("private pilot data");
  expect(screen.queryByRole("article")).not.toBeInTheDocument();
  expect(api.fetch.mock.calls.every(([, init]) => init.method === "GET")).toBe(true);
});

it("rejects a malformed template response rather than making up registry entries", async () => {
  const api = network(); api.setTemplates(() => Promise.resolve(Response.json([{ template_id: "invented" }])));
  page(); expect(await screen.findByRole("alert")).toHaveTextContent("nieprawidłowe dane");
  expect(screen.queryByRole("article")).not.toBeInTheDocument();
});

it("rejects history belonging to another document and supports safe read retry", async () => {
  const api = network(); api.setRevisions(() => Promise.resolve(Response.json([{ ...row, document_id: "another-document" }])));
  page("/documents/library/synthetic-draft");
  expect(await screen.findByRole("alert")).toHaveTextContent("nieprawidłowe dane");
  api.setRevisions(() => Promise.resolve(Response.json(fixture.revisions)));
  fireEvent.click(screen.getByRole("button", { name: "Spróbuj ponownie" }));
  expect(await screen.findByRole("heading", { name: "Rewizja 1" })).toBeVisible();
});

it.each(["../x", "x/y", "x?write=1", "x#bad", "x%2fsecret", "CON", "", "<script>", "https://evil.example"])("blocks unsafe identifiers in all legacy and preview links: %s", (id) => {
  expect(validDocumentId(id)).toBe(false); expect(documentLinks(id)).toBeNull();
});
it.each([0, -1, 1.5, Infinity, NaN])("blocks unsafe historical revision %s", (revision) => {
  expect(documentLinks("synthetic-draft", revision)).toBeNull();
});
