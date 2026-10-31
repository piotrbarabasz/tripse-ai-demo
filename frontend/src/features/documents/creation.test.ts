import { afterEach, expect, it, vi } from "vitest";
import { fixture } from "../../shared/api/test-fixtures";
import { templatesSchema } from "../../shared/api/adapters/guards";
import { zCampaignOutput, zDocumentDraftOutput, zTripOutput } from "../../shared/api/generated/zod.gen";
import { ApiError } from "../../shared/api/client/errors";
import { readSources } from "../../shared/api/adapters/studio";
import { creationIntent, matchesIntent, submitCreation, verifyCreation } from "./creation";
import type { Intent, Source } from "./creation";

const templates = templatesSchema.parse(fixture.templates);
const trip = zTripOutput.parse(fixture.trip);
const campaign = zCampaignOutput.parse(fixture.campaign);
const base = zDocumentDraftOutput.parse(fixture.draft);
const source: Source = { source_id: trip.trip_id!, source_type: "trip", title: trip.title, revision: trip.revision, summary: "", incomplete: true, data_origin: trip.data_origin };
function saved(intent: Intent) {
  return { ...base, document_id: intent.payload.document_id, title: intent.payload.title, template_id: intent.payload.template_id,
    layout_variant: intent.payload.layout_variant, confidentiality: intent.confidentiality, editorial_notes: "", demo_example: false,
    trip_snapshot: intent.payload.source_type === "trip" ? trip : null, campaign_snapshot: intent.payload.source_type === "campaign" ? campaign : null };
}
function attempt() { return creationIntent(templates[0]!, "standard", source, "Nowy dokument"); }
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });
it.each(["trip", "campaign"] as const)("validates the actual %s wire list and retains only selector metadata", async (kind) => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json(fixture[kind === "trip" ? "trips" : "campaigns"])));
  const rows = await readSources(kind); expect(rows).toHaveLength(1);
  expect(rows[0]).toMatchObject({ source_type: kind, revision: 1 });
  expect(Object.keys(rows[0]!)).toEqual(["source_type", "source_id", "revision", "title", "summary", "incomplete", "data_origin"]);
});
it("rejects missing persisted source IDs as safe invalid-response errors", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json([{ ...trip, trip_id: undefined }])));
  await expect(readSources("trip")).rejects.toMatchObject({ kind: "invalid-response" });
});

it.each(templates.flatMap((template) => template.layout_variants.map((variant) => ({ template, variant }))))("freezes a generated request for $template.template_id / $variant", ({ template, variant }) => {
  const selected = template.source_type === "trip" ? source : { ...source, source_type: "campaign" as const, source_id: campaign.campaign_id! };
  const intent = creationIntent(template, variant, selected, " Test ");
  expect(intent.payload.title).toBe("Test"); expect(intent.payload.source_revision).toBe(1);
  expect(intent.payload.document_id).toMatch(/^[a-f0-9]{32}$/); expect(Object.isFrozen(intent.payload)).toBe(true);
  expect(matchesIntent(zDocumentDraftOutput.parse(saved(intent)), intent)).toBe(true);
  expect(() => creationIntent(template, "invalid", selected, "Test")).toThrow(ApiError);
  expect(() => creationIntent(template, variant, { ...selected, source_type: selected.source_type === "trip" ? "campaign" : "trip" }, "Test")).toThrow(ApiError);
});
it("validates response and reads back the persisted document after exactly one POST", async () => {
  const intent = attempt(); const fetch = vi.fn().mockImplementation(() => Promise.resolve(Response.json(saved(intent)))); vi.stubGlobal("fetch", fetch);
  expect((await submitCreation(intent)).kind).toBe("saved");
  expect(fetch.mock.calls.map(([, init]) => (init as RequestInit).method)).toEqual(["POST", "GET"]);
  const options = fetch.mock.calls[0]![1] as RequestInit;
  expect(JSON.parse(options.body as string)).toEqual(intent.payload); expect(options.credentials).toBe("same-origin");
  expect(new Headers(options.headers).has("Idempotency-Key")).toBe(false);
});
it.each(["network", "timeout", "503", "500", "invalid"])("recovers a committed draft after ambiguous %s without another POST", async (kind) => {
  const intent = attempt(); const fetch = vi.fn().mockImplementationOnce(() => kind === "network" ? Promise.reject(new TypeError("private raw body")) : kind === "timeout" ? Promise.reject(new DOMException("timeout", "TimeoutError")) : Promise.resolve(kind === "invalid" ? Response.json({}) : new Response("private", { status: Number(kind) })))
    .mockResolvedValueOnce(Response.json(saved(intent))); vi.stubGlobal("fetch", fetch);
  expect((await submitCreation(intent)).kind).toBe("saved"); expect(fetch).toHaveBeenCalledTimes(2);
});
it("times out the actual transport and verifies the same ID", async () => {
  vi.useFakeTimers(); const intent = attempt();
  const fetch = vi.fn().mockImplementationOnce((_path: string, init: RequestInit) => new Promise((_resolve, reject) => init.signal?.addEventListener("abort", () => reject(new DOMException("abort", "AbortError")))))
    .mockResolvedValueOnce(Response.json(saved(intent))); vi.stubGlobal("fetch", fetch);
  const result = submitCreation(intent); await vi.advanceTimersByTimeAsync(5001);
  expect((await result).kind).toBe("saved"); expect(fetch.mock.calls[1]![0]).toContain(intent.payload.document_id);
});
it.each([401, 403, 409, 422])("does not retry definitive %i errors", async (status) => {
  const fetch = vi.fn().mockResolvedValue(new Response("private", { status })); vi.stubGlobal("fetch", fetch);
  await expect(submitCreation(attempt())).rejects.toMatchObject({ status }); expect(fetch).toHaveBeenCalledTimes(1);
});
it("offers a stable-payload repeat only after a definite missing read", async () => {
  const intent = attempt(); const fetch = vi.fn().mockRejectedValueOnce(new TypeError()).mockResolvedValueOnce(new Response(null, { status: 404 }))
    .mockResolvedValueOnce(Response.json(saved(intent))).mockResolvedValueOnce(Response.json(saved(intent))); vi.stubGlobal("fetch", fetch);
  expect((await submitCreation(intent)).kind).toBe("missing"); expect((await submitCreation(intent)).kind).toBe("saved");
  expect((fetch.mock.calls[0]![1] as RequestInit).body).toBe((fetch.mock.calls[2]![1] as RequestInit).body);
});
it.each([503, 500, 200])("preserves uncertainty when verification is inconclusive (%i)", async (status) => {
  const fetch = vi.fn().mockResolvedValue(Response.json({}, { status })); vi.stubGlobal("fetch", fetch);
  expect((await verifyCreation(attempt())).kind).toBe("uncertain"); expect(fetch).toHaveBeenCalledTimes(1);
});
it.each([401, 403])("propagates verification %i into the shared session/permission handling", async (status) => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status })));
  await expect(verifyCreation(attempt())).rejects.toMatchObject({ status });
});
it.each(["document_id", "template_id", "layout_variant", "title", "editorial_notes", "demo_example", "confidentiality", "source_id", "source_revision", "both_snapshots"])("rejects a mismatched stored %s", async (field) => {
  const intent = attempt(); const row = saved(intent);
  const changed = field === "source_id" ? { trip_snapshot: { ...trip, trip_id: "other" } } : field === "source_revision" ? { trip_snapshot: { ...trip, revision: 2 } } : field === "both_snapshots" ? { campaign_snapshot: campaign } : { [field]: field === "demo_example" ? true : field === "confidentiality" ? "internal" : "other" };
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({ ...row, ...changed })));
  expect((await verifyCreation(intent)).kind).toBe("mismatch");
});
