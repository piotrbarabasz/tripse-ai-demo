import type { DraftRequest } from "../../shared/api/generated/types.gen";
import { zDraftRequest } from "../../shared/api/generated/zod.gen";
import { createDraft, readDraft, readSources, readTemplates } from "../../shared/api/adapters/studio";
import { ApiError } from "../../shared/api/client/errors";

export type Template = Awaited<ReturnType<typeof readTemplates>>[number];
export type Source = Awaited<ReturnType<typeof readSources>>[number];
type Draft = Awaited<ReturnType<typeof readDraft>>;
export type Intent = Readonly<{ payload: Readonly<DraftRequest & { document_id: string; source_revision: number; title: string }>; confidentiality: Template["confidentiality"] }>;
export function creationIntent(template: Template, variant: string, source: Source, title: string): Intent {
  if (source.source_type !== template.source_type || !template.layout_variants.includes(variant)) throw new ApiError("validation");
  const payload: Intent["payload"] = { document_id: crypto.randomUUID().replaceAll("-", ""), source_revision: source.revision,
    template_id: template.template_id, source_type: source.source_type, source_id: source.source_id, layout_variant: variant,
    title: title.trim(), editorial_notes: "", demo_example: false };
  zDraftRequest.parse(payload);
  return Object.freeze({ payload: Object.freeze(payload), confidentiality: template.confidentiality });
}
export function matchesIntent(draft: Draft, intent: Intent): boolean {
  const p = intent.payload;
  const source = p.source_type === "trip" ? draft.trip_snapshot : draft.campaign_snapshot;
  const sourceId = p.source_type === "trip" ? draft.trip_snapshot?.trip_id : draft.campaign_snapshot?.campaign_id;
  return draft.document_id === p.document_id && draft.template_id === p.template_id && draft.layout_variant === p.layout_variant
    && sourceId === p.source_id && source?.revision === p.source_revision
    && (p.source_type === "trip" ? !draft.campaign_snapshot : !draft.trip_snapshot)
    && draft.title === p.title && draft.editorial_notes === p.editorial_notes && draft.demo_example === p.demo_example
    && draft.confidentiality === intent.confidentiality;
}
export type Outcome = { kind: "saved"; draft: Draft } | { kind: "missing" | "uncertain" | "mismatch" };
// Only a definite 404 permits an explicit repeat of the frozen payload/ID.
// Recovery never POSTs and never manufactures a fresh ID.
export async function verifyCreation(intent: Intent, signal?: AbortSignal): Promise<Outcome> {
  try {
    const draft = await readDraft(intent.payload.document_id, signal);
    return matchesIntent(draft, intent) ? { kind: "saved", draft } : { kind: "mismatch" };
  } catch (error) {
    if (error instanceof ApiError && ["unauthenticated", "forbidden"].includes(error.kind)) throw error;
    return { kind: error instanceof ApiError && error.kind === "not-found" ? "missing" : "uncertain" };
  }
}
export async function submitCreation(intent: Intent, signal?: AbortSignal): Promise<Outcome> {
  try {
    const response = await createDraft(intent.payload, signal);
    if (!matchesIntent(response, intent)) return { kind: "mismatch" };
  } catch (error) {
    if (error instanceof ApiError && error.status && error.status < 500) throw error;
    // Invalid responses, interrupted requests and 5xx can all follow a commit.
  }
  return verifyCreation(intent, signal);
}
