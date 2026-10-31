import "../client/validation-runtime";
import type { DraftUpdate, LibraryMutation, StatusMutation, ListLibraryApiDocumentStudioLibraryGetData } from "../generated/types.gen";
import { zDocumentDraftOutput, zLibraryPage } from "../generated/zod.gen";
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
export type LibraryFilters = NonNullable<ListLibraryApiDocumentStudioLibraryGetData["query"]>;
export async function readLibrary(filters: LibraryFilters = {}, signal?: AbortSignal) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) if (value != null) query.set(key, String(value));
  return (await request(`${base}/library?${query}`, { json: (value) => zLibraryPage.parse(value) }, { signal })).data;
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
