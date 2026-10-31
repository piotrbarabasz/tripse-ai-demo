import "../../shared/api/client/validation-runtime";
import { zDocumentSummary } from "../../shared/api/generated/zod.gen";
import { legacyHref } from "../../shared/config/legacy";

export function validDocumentId(identifier: string): boolean {
  return zDocumentSummary.shape.document_id.safeParse(identifier).success &&
    !/^(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])$/i.test(identifier);
}

// All paths are constructed from identifiers, never from server-supplied URLs.
// The hash routes are implemented by legacy studio.js (not inferred from labels).
export function documentLinks(identifier: string, revision?: number) {
  if (!validDocumentId(identifier) || (revision !== undefined && (!Number.isSafeInteger(revision) || revision < 1))) return null;
  const id = encodeURIComponent(identifier);
  return {
    detail: `/documents/library/${id}`,
    reactEditor: `/documents/${id}/edit`,
    editor: `${legacyHref("/documents/demo")}#edit-draft/${id}`,
    history: `${legacyHref("/documents/demo")}#revisions/${id}`,
    preview: revision === undefined ? `/api/document-studio/drafts/${id}/preview` :
      `/api/document-studio/library/${id}/revisions/${revision}/preview`,
  };
}
