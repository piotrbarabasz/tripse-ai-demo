import { useEffect, useState } from "react";
import { Link, NavLink, Route, Routes, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "../../shared/components/PageHeader";
import { Button } from "../../shared/ui/button";
import { Badge } from "../../shared/ui/badge";
import { legacyHref } from "../../shared/config/legacy";
import { readAccess, readTemplates } from "../../shared/api/adapters/studio";
import type { LibraryFilters } from "../../shared/api/adapters/studio";
import { zListLibraryApiDocumentStudioLibraryGetQuery } from "../../shared/api/generated/zod.gen";
import { apiKeys } from "../../shared/api/query/client";
import { useSessionFailure } from "../../shared/api/query/useSessionFailure";
import { documentLibraryQuery, initialFilters, revisionsQuery } from "./queries";
import { DocumentActions, DocumentMetadata, ReadError } from "./presentation";
import { families, statuses } from "./labels";
import { documentLinks, validDocumentId } from "./links";

type Templates = Awaited<ReturnType<typeof readTemplates>>;

function Catalog({ templates, pending, error, retry, canEdit }: {
  templates: Templates | undefined; pending: boolean; error: Error | null; retry: () => void; canEdit: boolean;
}) {
  return <section aria-labelledby="templates-title">
    <h2 id="templates-title" className="documents-section-title">Katalog szablonów</h2>
    {pending && <p role="status">Wczytywanie szablonów…</p>}
    {error ? <ReadError error={error} retry={retry} /> : !pending && !templates?.length ? <p role="status">Brak dostępnych szablonów.</p> :
      Object.entries(families).map(([family, label]) => <section key={family} aria-label={label} className="documents-family">
        <h3>{label}</h3><div className="documents-grid">{templates?.filter((template) => template.family === family).map((template) =>
          <article className="document-card" key={template.template_id}>
            <p className="eyebrow">{families[template.family]}</p><h4>{template.name}</h4>
            <p className="document-id">{template.template_id}</p><p>{template.description}</p>
            <dl className="document-metadata"><dt>Źródło</dt><dd>{template.source_type === "trip" ? "Wycieczka" : "Kampania"}</dd>
              <dt>Warianty</dt><dd>{template.layout_variants.join(", ")}</dd></dl>
            {canEdit && <a className="text-link" href={`${legacyHref("/documents/demo")}#templates`}>Tworzenie w dotychczasowym Studio<span className="sr-only">: {template.name}</span></a>}
          </article>)}</div>
      </section>)}
  </section>;
}

function Library({ templates, canEdit, filters, onFilters }: { templates: Templates | undefined; canEdit: boolean; filters: LibraryFilters; onFilters: (value: LibraryFilters) => void }) {
  const query = useQuery(documentLibraryQuery(filters));
  function filter(name: keyof LibraryFilters, value: string) {
    const next = { ...filters, [name]: value === "" && name !== "search" ? undefined : value, offset: 0 };
    const parsed = zListLibraryApiDocumentStudioLibraryGetQuery.parse(next);
    onFilters({ ...parsed, family: parsed.family ?? null, template_id: parsed.template_id ?? null, document_status: parsed.document_status ?? null });
  }
  return <section aria-labelledby="library-title">
    <h2 id="library-title" className="documents-section-title">Biblioteka dokumentów</h2>
    <form className="documents-filters" onSubmit={(event) => event.preventDefault()} aria-label="Filtry biblioteki">
      <label>Szukaj po tytule<input type="search" maxLength={200} value={filters.search ?? ""} onChange={(event) => filter("search", event.target.value)} /></label>
      <label>Rodzina<select value={filters.family ?? ""} onChange={(event) => filter("family", event.target.value)}><option value="">Wszystkie rodziny</option>{Object.entries(families).map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>
      <label>Szablon<select value={filters.template_id ?? ""} onChange={(event) => filter("template_id", event.target.value)}><option value="">Wszystkie szablony</option>{templates?.map((template) => <option key={template.template_id} value={template.template_id}>{template.name}</option>)}</select></label>
      <label>Status dokumentu<select value={filters.document_status ?? ""} onChange={(event) => filter("document_status", event.target.value)}><option value="">Wszystkie statusy</option>{Object.entries(statuses).map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label>
      <label>Archiwum<select value={filters.archived} onChange={(event) => filter("archived", event.target.value)}><option value="exclude">Bez archiwum</option><option value="include">Aktywne i archiwalne</option><option value="only">Tylko archiwum</option></select></label>
      <label>Sortuj według<select value={filters.sort} onChange={(event) => filter("sort", event.target.value)}><option value="updated_at">Ostatnia modyfikacja</option><option value="created_at">Data utworzenia</option><option value="title">Tytuł</option></select></label>
      <label>Kierunek<select value={filters.direction} onChange={(event) => filter("direction", event.target.value)}><option value="desc">Malejąco</option><option value="asc">Rosnąco</option></select></label>
      <Button type="button" variant="outline" onClick={() => onFilters(initialFilters)}>Wyczyść filtry</Button>
    </form>
    {query.isPending && <p role="status">Wczytywanie biblioteki…</p>}
    {query.isError && <ReadError error={query.error} retry={() => { void query.refetch(); }} />}
    {query.isSuccess && <>
      <p role="status">{query.data.items.length ? `Dokumenty: ${query.data.total}` : "Brak dokumentów pasujących do filtrów."}</p>
      <div className="documents-grid">{query.data.items.map((row) => <article className="document-card" key={row.document_id}>
        <h3>{row.title}</h3><DocumentMetadata row={row} templateName={templates?.find((template) => template.template_id === row.template_id)?.name} />
        <DocumentActions row={row} canEdit={canEdit} />
      </article>)}</div>
      <nav className="documents-pagination" aria-label="Strony biblioteki">
        <Button type="button" variant="outline" disabled={query.data.offset === 0} onClick={() => onFilters({ ...filters, offset: Math.max(0, query.data.offset - query.data.limit) })}>Poprzednia strona</Button>
        <p>{query.data.items.length ? `${query.data.offset + 1}–${query.data.offset + query.data.items.length} z ${query.data.total}` : `0 z ${query.data.total}`}</p>
        <Button type="button" variant="outline" disabled={!query.data.has_more} onClick={() => onFilters({ ...filters, offset: query.data.offset + query.data.limit })}>Następna strona</Button>
      </nav>
    </>}
  </section>;
}

function Details({ templates, canEdit }: { templates: Templates | undefined; canEdit: boolean }) {
  const { documentId = "" } = useParams();
  const valid = validDocumentId(documentId);
  const query = useQuery({ ...revisionsQuery(documentId), enabled: valid });
  const row = query.data?.[0]; // Repository lists head + preserved revisions, newest first.
  return <section aria-labelledby="document-title">
    <Link className="text-link" to="/documents/library">Wróć do biblioteki</Link>
    <h2 id="document-title" className="documents-section-title">{row?.title ?? "Szczegóły dokumentu"}</h2>
    {!valid ? <p role="alert">Nieprawidłowy identyfikator dokumentu.</p> : query.isPending ? <p role="status">Wczytywanie historii dokumentu…</p> :
      query.isError ? <ReadError error={query.error} retry={() => { void query.refetch(); }} /> : !row ? <p role="status">Brak zapisanych rewizji dokumentu.</p> : <>
        <article className="document-card"><DocumentMetadata row={row} templateName={templates?.find((template) => template.template_id === row.template_id)?.name} />
          <p className="document-id">Identyfikator: {row.document_id}</p><DocumentActions row={row} canEdit={canEdit} detail={false} />
        </article>
        <h3 className="documents-section-title">Historia rewizji</h3>
        <p>Historia obejmuje zachowane zapisy. Nie odtwarzamy brakujących wcześniejszych rewizji. Podglądy otwierają się w osobnej karcie.</p>
        <ol className="documents-history">{query.data?.map((revision) => {
          const links = documentLinks(revision.document_id, revision.revision);
          return <li className="document-card" key={revision.revision}>
            <h4>Rewizja {revision.revision}</h4><p>{revision.title} · {statuses[revision.document_status]}</p>
            <p><time dateTime={revision.updated_at}>{new Date(revision.updated_at).toLocaleString("pl-PL")}</time></p>
            {links && <a className="text-link" href={links.preview} target="_blank" rel="noopener noreferrer">Podgląd rewizji {revision.revision} (nowa karta)</a>}
          </li>;
        })}</ol>
      </>}
  </section>;
}

export default function DocumentsWorkspace() {
  const expired = useSessionFailure();
  const access = useQuery({ queryKey: [...apiKeys.studio, "access"], queryFn: ({ signal }) => readAccess(signal), enabled: !expired, gcTime: 0 });
  const templates = useQuery({ queryKey: [...apiKeys.studio, "templates"], queryFn: ({ signal }) => readTemplates(signal), enabled: !expired && access.isSuccess, gcTime: 0 });
  const [filters, setFilters] = useState<LibraryFilters>(initialFilters);
  useEffect(() => { document.getElementById("page-title")?.focus(); }, []);
  const canEdit = access.data?.can_edit === true;
  return <>
    <PageHeader eyebrow="Dokumenty TRIPSE" title="Document Studio">Katalog szablonów i zapisane dokumenty. Tworzenie i edycja pozostają w dotychczasowym Studio.</PageHeader>
    <nav className="documents-tabs" aria-label="Widoki Document Studio">
      <NavLink to="/documents" end>Katalog szablonów</NavLink><NavLink to="/documents/library">Biblioteka dokumentów</NavLink>
    </nav>
    <a className="text-link" href={legacyHref("/documents/demo")}>Otwórz obecne studio</a>
    {expired ? <p role="alert">Sesja wygasła. Zaloguj się ponownie i odśwież stronę.</p> : access.isError ? <ReadError error={access.error} retry={() => { void access.refetch(); }} /> : access.isPending ? <p role="status">Sprawdzanie dostępu do dokumentów…</p> : <>
      <div className="documents-notice"><Badge>{canEdit ? "Sesja z uprawnieniami edytora" : "Dostęp tylko do odczytu"}</Badge>
        <p>Ten widok służy do przeglądania. Status „Gotowy” i klasyfikacja poufności nie oznaczają zgody na publikację.</p>
        <a className="text-link" href={`${legacyHref("/documents/demo")}#drafts`}>Otwórz dotychczasową bibliotekę</a>
      </div>
      <Routes>
        <Route index element={<Catalog templates={templates.data} pending={templates.isPending} error={templates.error} retry={() => { void templates.refetch(); }} canEdit={canEdit} />} />
        <Route path="library" element={<Library templates={templates.data} canEdit={canEdit} filters={filters} onFilters={setFilters} />} />
        <Route path="library/:documentId" element={<Details templates={templates.data} canEdit={canEdit} />} />
        <Route path="*" element={<p role="alert">Nie znaleziono widoku dokumentów. Wybierz katalog lub bibliotekę.</p>} />
      </Routes>
    </>}
  </>;
}
