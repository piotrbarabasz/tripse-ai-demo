import { Link } from "react-router-dom";
import { Button } from "../../shared/ui/button";
import { Badge } from "../../shared/ui/badge";
import { ApiError } from "../../shared/api/client/errors";
import type { DocumentSummary } from "../../shared/api/generated/types.gen";
import { documentLinks } from "./links";
import { documentError, statuses } from "./labels";

const confidentiality = { public: "Publiczna", client: "Klientowska", internal: "Wewnętrzna", internal_restricted: "Wewnętrzna / ograniczona" };

export function ReadError({ error, retry }: { error: unknown; retry: () => void }) {
  const blocked = error instanceof ApiError && (error.status === 401 || error.status === 403);
  return <div className="documents-notice" role="alert"><p>{documentError(error)}</p>
    {!blocked && <Button type="button" variant="outline" onClick={retry}>Spróbuj ponownie</Button>}
  </div>;
}

export function DocumentMetadata({ row, templateName }: { row: DocumentSummary; templateName?: string | undefined }) {
  return <>
    <div className="documents-badges"><Badge>{templateName || row.template_id}</Badge><Badge>{statuses[row.document_status]}</Badge>
      {(row.archived_at !== null || row.document_status === "archived") && <Badge>W archiwum</Badge>}</div>
    <dl className="document-metadata">
      <dt>Źródło</dt><dd>{row.source_type === "trip" ? "Wycieczka" : "Kampania"}: {row.source_title}</dd>
      <dt>Szablon</dt><dd>{row.template_id}</dd>
      <dt>Rewizja</dt><dd>{row.revision}</dd>
      <dt>Zmodyfikowano</dt><dd><time dateTime={row.updated_at}>{new Date(row.updated_at).toLocaleString("pl-PL")}</time></dd>
      <dt>Poufność</dt><dd>{confidentiality[row.confidentiality]}</dd>
    </dl>
  </>;
}

export function DocumentActions({ row, canEdit, detail = true }: { row: DocumentSummary; canEdit: boolean; detail?: boolean }) {
  const links = documentLinks(row.document_id);
  if (!links) return <p role="alert">Nieprawidłowy identyfikator dokumentu.</p>;
  return <div className="documents-actions">
    {detail && <Link className="text-link" to={links.detail}>Szczegóły i historia<span className="sr-only">: {row.title}</span></Link>}
    <a className="text-link" href={links.preview} target="_blank" rel="noopener noreferrer">Podgląd A4 (nowa karta)<span className="sr-only">: {row.title}</span></a>
    <a className="text-link" href={links.history}>Historia w dotychczasowym Studio<span className="sr-only">: {row.title}</span></a>
    {canEdit && row.document_status !== "archived" && row.archived_at === null &&
      <a className="text-link" href={links.editor}>Edytuj w dotychczasowym Studio<span className="sr-only">: {row.title}</span></a>}
  </div>;
}
