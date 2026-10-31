import { afterEach, expect, it, vi } from "vitest";
import { fixture } from "../../shared/api/test-fixtures";
import { zDocumentDraftOutput } from "../../shared/api/generated/zod.gen";
import { templatesSchema } from "../../shared/api/adapters/guards";
import { customSection, formFrom, inspectSave, matchesSave, saveIntent, savePayload, submitSave, validationMessages } from "./editing";
import { saveDraft } from "../../shared/api/adapters/studio";

const base = zDocumentDraftOutput.parse(fixture.draft);
const templates = templatesSchema.parse(fixture.templates);
function attempt() { return saveIntent(base, { ...formFrom(base), title: "Nowy tytuł" }); }
function saved() { return { ...base, title: "Nowy tytuł", revision: base.revision + 1, updated_at: "2026-11-01T00:00:00Z", updated_by: "editor", last_library_operation: null }; }
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });

it.each(templates)("omits unrelated fields/defaults for $template_id", (template) => {
  const draft = { ...base, template_id: template.template_id };
  expect(savePayload(draft, { ...formFrom(draft), title: " Zmiana " })).toEqual({ revision: 1, title: "Zmiana" });
});
it("validates without serializing generated optional defaults", async () => {
  const fetch = vi.fn().mockImplementation(() => Promise.resolve(Response.json(saved()))); vi.stubGlobal("fetch", fetch);
  await saveDraft(base.document_id!, { revision: 1, title: "Nowy tytuł" });
  expect(JSON.parse((fetch.mock.calls[0]![1] as RequestInit).body as string)).toEqual({ revision: 1, title: "Nowy tytuł" });
});
it("keeps null versus empty sections and empty arrays distinct", () => {
  const legacy = { ...base, sections: null };
  expect(savePayload(legacy, formFrom(legacy))).not.toHaveProperty("sections");
  expect(savePayload(legacy, { ...formFrom(legacy), sections: [] }).sections).toEqual([]);
  const withOverrides = { ...base, day_overrides: [{ day_id: "day-1", title: "Dzień", description: "Opis" }] };
  expect(savePayload(withOverrides, { ...formFrom(withOverrides), day_overrides: [] }).day_overrides).toEqual([]);
});
it("freezes a separate intent and preserves full section attachments and opaque properties", () => {
  const section = { ...customSection("gallery", 0), images: [{ asset_id: "asset-1", caption: "Podpis", position: { x: 10, y: 20, zoom: 1.5 } }] };
  const draft = { ...base, sections: [section] };
  const form = formFrom(draft); form.sections![0]!.body = "Zmiana";
  const intent = saveIntent(draft, form);
  expect(intent.payload.sections?.[0]?.images).toEqual(section.images);
  expect(intent.baseline.sections?.[0]?.body).toBe(""); expect(Object.isFrozen(intent.payload.sections)).toBe(true);
  form.sections![0]!.images![0]!.caption = "Kolejna zmiana";
  expect(intent.payload.sections?.[0]?.images?.[0]?.caption).toBe("Podpis");
});
it.each(["text", "list", "image", "gallery", "table", "callout", "day", "logistics", "knowledge"] as const)("creates a stable custom %s section with correct typed defaults", (kind) => {
  const section = customSection(kind, 4, "day-1");
  expect(section.section_id).toMatch(/^[a-f0-9]{32}$/); expect(section.order).toBe(4); expect(section.role).toBeNull();
  if (kind === "table") expect(section.columns).toHaveLength(2);
  if (kind === "logistics") expect(section.logistics?.drive_km).toBeNull();
  if (kind === "knowledge") expect(section.knowledge?.sources).toEqual([]);
});
it("refuses arbitrary source bindings", () => { expect(() => customSection("source", 0)).toThrow(); });
it("compares all unchanged data, not just the title/revision", () => {
  const intent = attempt(); expect(matchesSave(zDocumentDraftOutput.parse(saved()), intent)).toBe(true);
  for (const patch of [{ revision: 3 }, { document_id: "other" }, { confidentiality: "internal" }, { date_label: "lost data" }, { offer_data: null }, { trip_snapshot: { ...base.trip_snapshot, title: "changed source" } }, { sections: [] }]) {
    expect(matchesSave(zDocumentDraftOutput.parse({ ...saved(), ...patch }), intent)).toBe(false);
  }
});
it("writes exactly once and verifies the persisted revision", async () => {
  const fetch = vi.fn().mockImplementation(() => Promise.resolve(Response.json(saved()))); vi.stubGlobal("fetch", fetch);
  expect((await submitSave(attempt())).kind).toBe("saved");
  expect(fetch.mock.calls.map(([, init]) => (init as RequestInit).method)).toEqual(["PUT", "GET"]);
});
it.each([401, 403, 409, 422])("propagates definitive %i failures without retry", async (status) => {
  const fetch = vi.fn().mockResolvedValue(new Response("private body", { status })); vi.stubGlobal("fetch", fetch);
  await expect(submitSave(attempt())).rejects.toMatchObject({ status }); expect(fetch).toHaveBeenCalledTimes(1);
});
it.each(["network", "503", "500", "invalid"])("keeps an ambiguous %s dirty until explicit inspection", async (kind) => {
  const fetch = vi.fn().mockImplementation(() => kind === "network" ? Promise.reject(new TypeError("private")) : Promise.resolve(kind === "invalid" ? Response.json({}) : new Response(null, { status: Number(kind) })));
  vi.stubGlobal("fetch", fetch); expect((await submitSave(attempt())).kind).toBe("uncertain"); expect(fetch).toHaveBeenCalledTimes(1);
  fetch.mockResolvedValue(Response.json(saved())); expect((await inspectSave(attempt())).kind).toBe("saved"); expect(fetch).toHaveBeenCalledTimes(2);
});
it("treats a genuine transport timeout as uncertain without automatic replay", async () => {
  vi.useFakeTimers(); const fetch = vi.fn().mockImplementation((_path: string, init: RequestInit) => new Promise((_resolve, reject) => init.signal?.addEventListener("abort", () => reject(new DOMException("abort", "AbortError")))));
  vi.stubGlobal("fetch", fetch); const result = submitSave(attempt()); await vi.advanceTimersByTimeAsync(5001);
  expect((await result).kind).toBe("uncertain"); expect(fetch).toHaveBeenCalledTimes(1);
});
it("permits deliberate same-revision retry only after confirming unchanged baseline", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json(base)));
  expect((await inspectSave(attempt())).kind).toBe("not-saved");
});
it("does not accept a later revision or inconclusive read as saved", async () => {
  const fetch = vi.fn().mockResolvedValueOnce(Response.json({ ...saved(), revision: 8 })).mockResolvedValueOnce(new Response(null, { status: 503 })); vi.stubGlobal("fetch", fetch);
  expect((await inspectSave(attempt())).kind).toBe("conflict"); expect((await inspectSave(attempt())).kind).toBe("uncertain");
});
it("never offers to adopt data for another document or template", async () => {
  vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(Response.json({ ...saved(), document_id: "another-document" }))));
  expect(await inspectSave(attempt())).toEqual({ kind: "uncertain" });
});
it("validates table width, blank titles, time zones and verification evidence", () => {
  const table = { ...customSection("table", 0), rows: [["wrong width"]] };
  const logistics = customSection("logistics", 1, "day-1"); logistics.logistics!.time_zone = "invalid-zone"; logistics.logistics!.verification_status = "verified";
  const knowledge = customSection("knowledge", 2, "day-1"); knowledge.knowledge!.verification_status = "verified";
  const issues = validationMessages(base, { ...formFrom(base), sections: [table, logistics, knowledge] });
  expect(issues.join(" ")).toMatch(/Tabela/); expect(issues.join(" ")).toMatch(/IANA/); expect(issues.join(" ")).toMatch(/źródeł i dat/);
});
