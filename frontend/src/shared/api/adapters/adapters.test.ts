import { afterEach, expect, it, vi } from "vitest";
import { z } from "zod";
import { zDocumentDraftOutput, zLibraryPage, zTripAccepted, zTripStatus, zTripOutput, zDocumentSummary, zWorkspaceCapabilities } from "../generated/zod.gen";
import { accessSchema, assetSchema, templatesSchema } from "./guards";
import { createTrip, readJob, scenariosSchema } from "./planner";
import { readAccess, readTemplates, readLibrary, saveDraft, setDocumentStatus, duplicateDocument, previewDraft, uploadImage, downloadImage } from "./studio";
import { parseHealth } from "../../../features/hub/health";
import { fixture } from "../test-fixtures";

// Captured by scripts.export_api_fixtures from real isolated FastAPI routes;
// Python tests detect wire drift, these tests validate the consuming TS guards.
afterEach(() => vi.unstubAllGlobals());

it("validates generated and supplemental contracts against synthetic FastAPI fixtures", () => {
  expect(zTripAccepted.parse(fixture.accepted).status).toBe("queued");
  expect(zTripStatus.parse(fixture.job).result).toBeNull();
  expect(zTripOutput.parse(fixture.trip).trip_id).toBe("synthetic-trip");
  for (const key of ["draft", "historical", "status", "duplicate"]) expect(zDocumentDraftOutput.safeParse(fixture[key]).success).toBe(true);
  expect(z.array(zDocumentSummary).parse(fixture.revisions)).toHaveLength(2);
  expect(zLibraryPage.parse(fixture.library).items).toHaveLength(2);
  expect(accessSchema.parse(fixture.access)).toEqual({ can_edit: true });
  expect(templatesSchema.parse(fixture.templates)).toHaveLength(8);
  expect(assetSchema.parse(fixture.asset).media_type).toBe("image/png");
  expect(parseHealth(fixture.health)).toEqual({ status: "ok", generation_mode: "mock" });
  expect(zWorkspaceCapabilities.parse(fixture.capabilities)).toEqual({ runtime_mode: "local", planning_mode: "mock", can_create_trip: true });
  expect(scenariosSchema.parse(fixture.scenarios).scenarios).toHaveLength(3);
});

it("preserves nullable versus empty sections and rejects missing/untyped wire values", () => {
  const draft = zDocumentDraftOutput.parse(fixture.draft);
  expect(zDocumentDraftOutput.parse({ ...draft, sections: null }).sections).toBeNull();
  expect(zDocumentDraftOutput.parse({ ...draft, sections: [] }).sections).toEqual([]);
  for (const value of [null, {}, { can_edit: "true" }]) expect(accessSchema.safeParse(value).success).toBe(false);
  expect(templatesSchema.safeParse([{}]).success).toBe(false);
  expect(assetSchema.safeParse({ asset_id: "x", media_type: "text/html" }).success).toBe(false);
  expect(zTripStatus.safeParse({ ...zTripStatus.parse(fixture.job), status: "success" }).success).toBe(false);
});

it("preserves local versus cloud create idempotency without any automatic replay", async () => {
  const fetch = vi.fn().mockImplementation(() => Promise.resolve(Response.json(fixture.accepted, { status: 202, headers: { Location: "/api/trips/synthetic" } })));
  vi.stubGlobal("fetch", fetch);
  expect((await createTrip({ text: "test" }, { mode: "local" })).headers.get("Location")).toBe("/api/trips/synthetic");
  await createTrip({ text: "test" }, { mode: "cloud_demo", idempotencyKey: "stable-operation-uuid" });
  const headers = fetch.mock.calls.map((call) => new Headers((call[1] as RequestInit).headers));
  expect(headers[0]?.has("Idempotency-Key")).toBe(false);
  expect(headers[1]?.get("Idempotency-Key")).toBe("stable-operation-uuid");
  expect(fetch).toHaveBeenCalledTimes(2);
});

it("returns opaque planner results without inventing a Studio trip or exposing a viewer adapter", async () => {
  const job = zTripStatus.parse(fixture.job);
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({ ...job, status: "completed", result: { future_field: [null, "opaque"] } })));
  expect((await readJob(job.trip_id)).result).toEqual({ future_field: [null, "opaque"] });
});

it("reads access/templates/library metadata with encoded filters", async () => {
  const fetch = vi.fn().mockResolvedValueOnce(Response.json(fixture.access)).mockResolvedValueOnce(Response.json(fixture.templates)).mockResolvedValueOnce(Response.json(fixture.library));
  vi.stubGlobal("fetch", fetch);
  expect((await readAccess()).can_edit).toBe(true);
  expect(await readTemplates()).toHaveLength(8);
  expect((await readLibrary({ search: "a & b", limit: 20 })).items).toHaveLength(2);
  expect(fetch.mock.calls[2]?.[0]).toContain("search=a+%26+b&limit=20");
});

it("sends exact revisions/operation IDs and leaves conflicts visible", async () => {
  const fetch = vi.fn().mockResolvedValueOnce(Response.json(fixture.draft)).mockResolvedValueOnce(Response.json(fixture.status)).mockResolvedValueOnce(Response.json(fixture.duplicate)).mockResolvedValueOnce(Response.json({ detail: "private conflict" }, { status: 409 }));
  vi.stubGlobal("fetch", fetch);
  const operation = { revision: 1, operation_id: "00000000-0000-4000-8000-000000000002" };
  await saveDraft("synthetic-draft", { revision: 1, title: "Synthetic edit" });
  await setDocumentStatus("synthetic-draft", { ...operation, document_status: "in_review" });
  await duplicateDocument("synthetic-draft", operation);
  await expect(saveDraft("synthetic-draft", { revision: 1, title: "Stale" })).rejects.toMatchObject({ kind: "conflict" });
  expect(fetch.mock.calls[1]?.[1]).toMatchObject({ body: JSON.stringify({ ...operation, document_status: "in_review" }) });
  expect(fetch).toHaveBeenCalledTimes(4);
});

it("handles previews/raw uploads/downloads without JSON conversion", async () => {
  const fetch = vi.fn().mockResolvedValueOnce(new Response("<html>synthetic</html>", { headers: { "content-type": "text/html" } })).mockResolvedValueOnce(Response.json(fixture.asset, { status: 201 })).mockResolvedValueOnce(new Response(new Uint8Array([1, 2]), { headers: { "content-type": "image/png" } }));
  vi.stubGlobal("fetch", fetch);
  expect(await previewDraft("synthetic-draft", "social")).toContain("synthetic");
  const bytes = new Blob([new Uint8Array([1, 2])], { type: "image/png" });
  expect((await uploadImage("a & b.png", true, bytes)).asset_id).toBe("synthetic-asset");
  expect(fetch.mock.calls[1]?.[0]).toContain("filename=a+%26+b.png&rights_confirmed=true");
  expect(fetch.mock.calls[1]?.[1]).toMatchObject({ body: bytes });
  expect((await downloadImage("synthetic-asset")).size).toBe(2);
});
