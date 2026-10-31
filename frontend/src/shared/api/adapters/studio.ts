import "../client/validation-runtime";
import type { DraftRequest, DraftUpdate, LibraryMutation, StatusMutation, ListLibraryApiDocumentStudioLibraryGetData } from "../generated/types.gen";
import { zDraftRequest, zTripOutput, zCampaignOutput, zDocumentDraftOutput, zLibraryPage, zDocumentSummary } from "../generated/zod.gen";
import { z } from "zod";
import { request } from "../client/transport";
import { accessSchema, assetSchema, templatesSchema } from "./guards";

const base = "/api/document-studio";
const id = encodeURIComponent;
export async function readAccess(signal?: AbortSignal) {
  return (await request(`${base}/access`, { json: (value) => accessSchema.parse(value) }, { signal })).data;
}
export async function readTemplates(signal?: AbortSignal) {
  return (await request(`${base}/templates`, { json: (value) => templatesSchema.parse(value) }, { signal })).data;
}
// Validate complete source contracts, then retain only selector metadata. Private
// program/pilot fields are not needed in the selector or its query cache.
export async function readSources(kind: "trip" | "campaign", signal?: AbortSignal) {
  if (kind === "trip") {
    return (await request(`${base}/trips`, { json: (value) => z.array(zTripOutput).parse(value).map((row) => ({ source_type: kind, source_id: zDocumentSummary.shape.document_id.parse(row.trip_id), revision: row.revision, title: row.title,
      summary: `${row.duration_days} dni · ${row.days?.length ?? 0} dni programu · ${row.destinations?.join(", ") || "brak kierunku"}`,
      incomplete: !row.days?.length, data_origin: row.data_origin })) }, { signal })).data;
  }
  return (await request(`${base}/campaigns`, { json: (value) => z.array(zCampaignOutput).parse(value).map((row) => ({ source_type: kind, source_id: zDocumentSummary.shape.document_id.parse(row.campaign_id), revision: row.revision, title: row.title,
    summary: `${row.items.length} pozycji · ${row.season || "brak sezonu"}`, incomplete: !row.items.length, data_origin: row.data_origin })) }, { signal })).data;
}
export async function createDraft(value: DraftRequest, signal?: AbortSignal) {
  const body = zDraftRequest.parse(value);
  return (await request(`${base}/drafts`, { json: (response) => zDocumentDraftOutput.parse(response) }, { method: "POST", body: { json: body }, signal })).data;
}
export async function readDraft(identifier: string, signal?: AbortSignal) {
  const validId = zDocumentSummary.shape.document_id.parse(identifier);
  return (await request(`${base}/drafts/${id(validId)}`, { json: (value) => zDocumentDraftOutput.parse(value) }, { signal })).data;
}
export type LibraryFilters = NonNullable<ListLibraryApiDocumentStudioLibraryGetData["query"]>;
export async function readLibrary(filters: LibraryFilters = {}, signal?: AbortSignal) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) if (value != null) query.set(key, String(value));
  return (await request(`${base}/library?${query}`, { json: (value) => zLibraryPage.parse(value) }, { signal })).data;
}

export async function readRevisions(identifier: string, signal?: AbortSignal) {
  const validId = zDocumentSummary.shape.document_id.parse(identifier);
  const schema = z.array(zDocumentSummary).refine((rows) => rows.every((row) => row.document_id === validId));
  return (await request(`${base}/library/${id(validId)}/revisions`, { json: (value) => schema.parse(value) }, { signal })).data;
}
// Revision is the last loaded revision. Never refresh it silently to force a save.
export async function saveDraft(identifier: string, value: DraftUpdate, signal?: AbortSignal) {
  return (await request(`${base}/drafts/${id(identifier)}`, { json: (body) => zDocumentDraftOutput.parse(body) }, { method: "PUT", body: { json: value }, signal })).data;
}
// Keep the operation UUID stable for one user intent. A conflict must be reviewed.
export async function setDocumentStatus(identifier: string, value: StatusMutation, signal?: AbortSignal) {
  return (await request(`${base}/library/${id(identifier)}/status`, { json: (body) => zDocumentDraftOutput.parse(body) }, { method: "POST", body: { json: value }, signal })).data;
}
export async function duplicateDocument(identifier: string, value: LibraryMutation, signal?: AbortSignal) {
  return (await request(`${base}/library/${id(identifier)}/duplicate`, { json: (body) => zDocumentDraftOutput.parse(body) }, { method: "POST", body: { json: value }, signal })).data;
}
export async function previewDraft(identifier: string, outputFormat: "a4" | "social" = "a4", signal?: AbortSignal) {
  return (await request(`${base}/drafts/${id(identifier)}/preview?output_format=${outputFormat}`, { html: true }, { signal })).data;
}
export async function uploadImage(filename: string, rightsConfirmed: boolean, bytes: Blob, signal?: AbortSignal) {
  const query = new URLSearchParams({ filename, rights_confirmed: String(rightsConfirmed) });
  return (await request(`${base}/assets?${query}`, { json: (body) => assetSchema.parse(body) }, { method: "POST", body: { bytes, contentType: bytes.type }, signal })).data;
}
export async function downloadImage(identifier: string, signal?: AbortSignal) {
  return (await request(`${base}/assets/${id(identifier)}/content`, { binary: true }, { signal })).data;
}
