import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { readDraft } from "../../shared/api/adapters/studio";
import { ApiError } from "../../shared/api/client/errors";
import { apiKeys } from "../../shared/api/query/client";
import { Button } from "../../shared/ui/button";
import { ReadError } from "./presentation";
import { documentLinks, validDocumentId } from "./links";
import { statuses } from "./labels";
import type { Template } from "./creation";
import { SectionForm } from "./SectionForm";
import { UnsavedWarning } from "./UnsavedWarning";
import { customSection, equal, formFrom, freeze, inspectSave, saveIntent, sectionKinds, submitSave, validationMessages } from "./editing";
import type { Draft, Form, SaveIntent, SaveOutcome, Section } from "./editing";

const confidentialityLabels = { public: "Publiczna", client: "Klientowska", internal: "Wewnętrzna", internal_restricted: "Wewnętrzna — ograniczony dostęp" };

export default function DocumentEditor({ canEdit, templates }: { canEdit: boolean; templates: Template[] | undefined }) {
  const { documentId = "" } = useParams();
  const valid = validDocumentId(documentId);
  const query = useQuery({ queryKey: [...apiKeys.studio, "editor", documentId], gcTime: 0, staleTime: Infinity,
    enabled: canEdit && valid && !!templates,
    queryFn: async ({ signal }) => {
      const draft = await readDraft(documentId, signal);
      if (draft.document_id !== documentId || draft.sections?.some((s) => !s.section_id || !validDocumentId(s.section_id)) || new Set(draft.sections?.map((s) => s.section_id)).size !== (draft.sections?.length ?? 0)) throw new ApiError("invalid-response");
      return draft;
    } });
  if (!canEdit) return <p role="alert">Brak uprawnień do edycji dokumentu.</p>;
  if (!valid) return <p role="alert">Nieprawidłowy identyfikator dokumentu.</p>;
  if (query.isError) return <ReadError error={query.error} retry={() => { void query.refetch(); }} />;
  if (!query.data || !templates) return <p role="status">Wczytywanie dokumentu…</p>;
  const template = templates.find((item) => item.template_id === query.data.template_id);
  if (!template) return <p role="alert">Nieobsługiwany szablon dokumentu. Otwórz dotychczasowe Studio.</p>;
  if (query.data.document_status === "archived" || query.data.archived_at) return <p role="alert">Dokument jest w archiwum. Przywrócenie odbywa się w dotychczasowym Studio.</p>;
  // Revision is deliberately NOT part of the key: query refetches cannot reset
  // an edited form. Only a verified save or explicit discard adopts a baseline.
  return <Editor key={documentId} initial={query.data} template={template} />;
}

function Editor({ initial, template }: { initial: Draft; template: Template }) {
  const client = useQueryClient();
  const [baseline, setBaseline] = useState(() => freeze(structuredClone(initial)));
  const [form, setForm] = useState(() => formFrom(initial));
  const [selection, setSelection] = useState(initial.sections?.[0]?.section_id);
  const [newKind, setNewKind] = useState<Section["kind"]>("text");
  const [intent, setIntent] = useState<SaveIntent>();
  const [state, setState] = useState<"clean" | "saving" | "saved" | "conflict" | "validation" | "uncertain" | "not-saved" | "denied">("clean");
  const [error, setError] = useState<Error>();
  const [server, setServer] = useState<Draft>();
  const [remove, setRemove] = useState<string>();
  const [discard, setDiscard] = useState(false);
  const [panelsOpen, setPanelsOpen] = useState(() => typeof window.matchMedia === "function" ? window.matchMedia("(min-width: 768px)").matches : true);
  const lock = useRef(false);
  const abort = useRef<AbortController | null>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  useEffect(() => { titleRef.current?.focus(); return () => abort.current?.abort(); }, []);
  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const media = window.matchMedia("(min-width: 768px)");
    const changed = () => setPanelsOpen(media.matches);
    media.addEventListener("change", changed);
    return () => media.removeEventListener("change", changed);
  }, []);
  const dirty = !equal(form, formFrom(baseline));
  const busy = state === "saving";
  const locked = busy || state === "uncertain" || state === "conflict" || state === "denied" || state === "not-saved";
  const messages = validationMessages(baseline, form);
  const sections = form.sections;
  const selected = sections?.find((s) => s.section_id === selection);
  const links = documentLinks(baseline.document_id!)!;
  const required = (s: Section) => !!s.role && (s.kind === "knowledge" || s.kind === "logistics" || template.default_sections.some((spec) => spec.role === s.role && spec.required));
  const mutation = useMutation({ mutationFn: ({ attempt, check }: { attempt: SaveIntent; check: boolean }) => (check ? inspectSave : submitSave)(attempt, abort.current?.signal), retry: false, networkMode: "always", gcTime: 0 });
  const inspection = useMutation({ mutationFn: () => readDraft(baseline.document_id!, abort.current?.signal), retry: false, networkMode: "always", gcTime: 0 });
  function change(value: Form) { setForm(value); setError(undefined); if (!locked) setState("clean"); }
  function updateSection(value: Section) { change({ ...form, sections: sections?.map((s) => s.section_id === value.section_id ? value : s) }); }
  function move(offset: number) {
    const index = sections?.findIndex((s) => s.section_id === selection) ?? -1;
    if (!sections || index < 0 || index + offset < 0 || index + offset >= sections.length) return;
    const next = [...sections]; [next[index], next[index + offset]] = [next[index + offset]!, next[index]!];
    change({ ...form, sections: next.map((s, order) => ({ ...s, order })) });
  }
  async function accept(result: SaveOutcome) {
    if (result.kind === "saved") {
      setBaseline(freeze(structuredClone(result.draft))); setForm(formFrom(result.draft)); setIntent(undefined); setServer(undefined); setState("saved");
      await client.invalidateQueries({ queryKey: apiKeys.studio });
    } else { setState(result.kind); if (result.kind !== "uncertain") setServer(result.draft); }
  }
  async function save(check = false) {
    if (lock.current || state === "denied" || (!check && (state === "conflict" || state === "uncertain")) || (check && !intent)) return;
    if (!check && (messages.length || !dirty)) { setState(messages.length ? "validation" : "clean"); return; }
    lock.current = true; setState("saving"); setError(undefined); abort.current = new AbortController();
    try {
      const attempt = intent ?? saveIntent(baseline, form); setIntent(attempt);
      const result = await mutation.mutateAsync({ attempt, check });
      if (!abort.current.signal.aborted) await accept(result);
    } catch (failure) {
      if (!abort.current.signal.aborted) {
        setError(failure instanceof Error ? failure : new ApiError("invalid-response"));
        if (failure instanceof ApiError && failure.kind === "conflict") setState("conflict");
        else if (failure instanceof ApiError && ["forbidden", "unauthenticated"].includes(failure.kind)) setState("denied");
        else { setState("validation"); setIntent(undefined); }
      }
    } finally { lock.current = false; }
  }
  async function inspect() {
    if (lock.current) return;
    lock.current = true; abort.current = new AbortController(); setError(undefined);
    try {
      const draft = await inspection.mutateAsync();
      if (draft.document_id !== baseline.document_id || draft.template_id !== baseline.template_id || draft.confidentiality !== baseline.confidentiality) throw new ApiError("invalid-response");
      if (!abort.current.signal.aborted) setServer(draft);
    } catch (failure) { if (!abort.current.signal.aborted) { setError(failure instanceof Error ? failure : new ApiError("invalid-response")); if (failure instanceof ApiError && ["forbidden", "unauthenticated"].includes(failure.kind)) setState("denied"); } }
    finally { lock.current = false; }
  }
  function discardChanges() {
    const draft = server ?? baseline;
    setBaseline(freeze(structuredClone(draft))); setForm(formFrom(draft)); setSelection(draft.sections?.[0]?.section_id);
    setState("clean"); setIntent(undefined); setError(undefined); setServer(undefined); setDiscard(false);
  }
  const missing = template.default_sections.filter((spec) => spec.required && sections != null && !sections.some((s) => s.role === spec.role && s.visible));
  return <section className="document-editor" aria-labelledby="editor-title">
    <UnsavedWarning dirty={dirty || !!intent} title="Opuścić edycję dokumentu?" description="Niezapisane zmiany i próba zapisu są tylko w pamięci tej strony. Wyjście je odrzuci. Przy niepewnym wyniku najpierw sprawdź zapis." />
    <h2 id="editor-title" tabIndex={-1} ref={titleRef}>Edytuj dokument</h2>
    <div className="editor-toolbar"><Button disabled={!dirty || locked || !!messages.length} onClick={() => { void save(); }}>Zapisz zmiany</Button>
      <Button variant="outline" disabled={!dirty || busy || state === "denied" || state === "uncertain"} onClick={() => setDiscard(true)}>Odrzuć zmiany</Button>
      <Link className="text-link" to="/documents/library">Wróć do biblioteki</Link></div>
    <p role="status">{state === "saving" ? "Zapisywanie i weryfikacja…" : state === "saved" ? `Zapisano rewizję ${baseline.revision}.` : state === "conflict" ? "Konflikt — dokument zmienił się na serwerze. Twoje zmiany pozostają w formularzu." : state === "uncertain" ? "Niepewny wynik zapisu. Nie ponawiaj zapisu przed sprawdzeniem." : state === "not-saved" ? "Sprawdzono: serwer nadal ma wersję bazową. Możesz świadomie ponowić ten sam zapis." : state === "denied" ? "Brak uprawnień. Zapis nie został potwierdzony." : state === "validation" ? "Błąd walidacji. Sprawdź dane; serwer nie potwierdził zapisu." : dirty ? "Niezapisane zmiany." : "Brak zmian."}</p>
    {error && <p role="alert">{error instanceof ApiError && error.kind === "conflict" ? "Nie nadpisujemy nowszej rewizji. Sprawdź wersję serwera." : error instanceof ApiError && error.kind === "forbidden" ? "Serwer odmówił dostępu do tej operacji." : "Nie udało się potwierdzić operacji. Sprawdź dane lub odczytaj wersję serwera."}</p>}
    {!!messages.length && <ul role="alert">{messages.map((message) => <li key={message}>{message}</li>)}</ul>}
    {!!missing.length && <p role="note">Brakuje wymaganych sekcji: {missing.map((spec) => spec.title).join(", ")}. Serwer może zachować niepełny dokument; to nie potwierdza gotowości do eksportu. Przywrócenie struktury w dotychczasowym Studio.</p>}
    {["conflict", "uncertain", "not-saved"].includes(state) && <div className="documents-notice"><p>Bez automatycznego ponawiania lub podmiany rewizji.</p>
      <Button variant="outline" disabled={inspection.isPending} onClick={() => { if (state === "conflict") void inspect(); else void save(true); }}>Sprawdź wersję serwera</Button>
      {state === "not-saved" && <Button onClick={() => { void save(); }}>Ponów ten sam zapis</Button>}
      {server && <section aria-label="Wersja serwera"><h3>Wersja serwera: rewizja {server.revision}</h3><p>{server.title} · {statuses[server.document_status]}</p><p>Twoje lokalne pola pozostają powyżej i poniżej. Odczyt nie zmienił formularza.</p><ul>{server.sections?.map((s) => <li key={s.section_id}>{s.title} · {sectionKinds[s.kind]} · {s.body}</li>)}</ul><Button variant="outline" onClick={() => setDiscard(true)}>Wczytaj wersję serwera i odrzuć moje zmiany</Button></section>}
    </div>}
    {discard && <section role="alertdialog" aria-label="Potwierdź odrzucenie zmian" className="documents-notice"><p>Odrzucić lokalne zmiany{server ? ` i wczytać rewizję ${server.revision}` : " i wrócić do wersji bazowej"}? Tej czynności nie można cofnąć.</p><Button variant="outline" onClick={() => setDiscard(false)}>Zachowaj moje zmiany</Button><Button onClick={discardChanges}>Potwierdź odrzucenie</Button></section>}
    <fieldset disabled={locked || baseline.document_status === "archived"} className="editor-content"><legend className="sr-only">Pola dokumentu</legend><div className="editor-grid">
      <details className="editor-structure" open={panelsOpen}><summary>Struktura dokumentu</summary><h3>{form.title}</h3><nav aria-label="Sekcje dokumentu">{sections?.map((s) => <Button variant="outline" key={s.section_id} aria-current={selection === s.section_id ? "true" : undefined} onClick={() => setSelection(s.section_id)}>{s.title} · {sectionKinds[s.kind]} · {s.visible ? "widoczna" : "ukryta"}</Button>)}</nav>
        {sections == null ? <p>Dokument ma starszą strukturę sekcji. Zachowujemy ją; migracja pozostaje w dotychczasowym Studio.</p> : <><label>Nowa sekcja<select value={newKind} onChange={(e) => { const kind = Object.keys(sectionKinds).find((key) => key === e.target.value); if (kind) setNewKind(kind as Section["kind"]); }}>{Object.entries(sectionKinds).filter(([kind]) => kind !== "source" && (kind !== "logistics" || baseline.template_id === "pilot.advanced") && (kind !== "knowledge" || baseline.template_id === "pilot.knowledge")).map(([kind, label]) => <option key={kind} value={kind}>{label}</option>)}</select></label><Button variant="outline" disabled={sections.length >= 500 || (["knowledge", "logistics"].includes(newKind) && !baseline.trip_snapshot?.days?.length)} onClick={() => { const added = customSection(newKind, sections.length, ["knowledge", "logistics"].includes(newKind) ? baseline.trip_snapshot?.days?.[0]?.day_id : undefined); change({ ...form, sections: [...sections, added].map((s, order) => ({ ...s, order })) }); setSelection(added.section_id); }}>Dodaj sekcję</Button></>}
      </details>
      <div className="editor-workspace"><section><h3>Dane dokumentu</h3><label>Tytuł dokumentu<input required maxLength={200} value={form.title} onChange={(e) => change({ ...form, title: e.target.value })} /></label><label>Etykieta terminu<input maxLength={200} value={form.date_label} onChange={(e) => change({ ...form, date_label: e.target.value })} /></label><label>Notatki redakcyjne<textarea maxLength={20000} value={form.editorial_notes} onChange={(e) => change({ ...form, editorial_notes: e.target.value })} /></label></section>
        {!!baseline.trip_snapshot?.days?.length && <details><summary>Nadpisania dni w dokumencie</summary><p>Identyfikatory i program źródłowy pozostają bez zmian. Usunięcie nadpisania przywraca treść migawki.</p>{baseline.trip_snapshot.days.map((day) => { const override = form.day_overrides?.find((item) => item.day_id === day.day_id); const update = (key: "title" | "description", value: string) => { const next = { day_id: day.day_id!, title: override?.title ?? "", description: override?.description ?? "", [key]: value }; change({ ...form, day_overrides: override ? form.day_overrides?.map((item) => item.day_id === day.day_id ? next : item) : [...form.day_overrides ?? [], next] }); }; return <fieldset key={day.day_id}><legend>Dzień {day.day_number}: {day.title}</legend><label>Tytuł dnia {day.day_number}<input maxLength={200} value={override?.title ?? ""} onChange={(e) => update("title", e.target.value)} /></label><label>Opis dnia {day.day_number}<textarea maxLength={20000} value={override?.description ?? ""} onChange={(e) => update("description", e.target.value)} /></label><Button variant="outline" disabled={!override} onClick={() => change({ ...form, day_overrides: form.day_overrides?.filter((item) => item.day_id !== day.day_id) })}>Usuń nadpisanie dnia {day.day_number}</Button></fieldset>; })}</details>}
        {selected && <section aria-label="Wybrana sekcja"><h3>{sectionKinds[selected.kind]}</h3><div className="creation-actions"><Button variant="outline" disabled={sections?.[0]?.section_id === selection} onClick={() => move(-1)}>Przesuń sekcję w górę</Button><Button variant="outline" disabled={sections?.at(-1)?.section_id === selection} onClick={() => move(1)}>Przesuń sekcję w dół</Button><Button variant="outline" disabled={!!selected.role} onClick={() => setRemove(selected.section_id)}>Usuń sekcję</Button></div>
          {remove === selected.section_id && <div role="alertdialog" aria-label="Potwierdź usunięcie sekcji"><p>Usunąć tę własną sekcję? Zmiana zostanie zapisana dopiero po zapisie dokumentu.</p><Button variant="outline" onClick={() => setRemove(undefined)}>Zachowaj sekcję</Button><Button onClick={() => { change({ ...form, sections: sections?.filter((s) => s.section_id !== remove).map((s, order) => ({ ...s, order })) }); setSelection(undefined); setRemove(undefined); }}>Potwierdź usunięcie sekcji</Button></div>}
          <SectionForm section={selected} draft={baseline} required={required(selected)} onChange={updateSection} />
        </section>}
      </div>
      <details className="editor-information" open={panelsOpen}><summary>Informacje o dokumencie</summary><dl className="document-metadata"><dt>Szablon</dt><dd>{template.name} · {baseline.template_id}</dd><dt>Rewizja</dt><dd>{baseline.revision}</dd><dt>Status</dt><dd>{statuses[baseline.document_status]}</dd><dt>Poufność</dt><dd>{confidentialityLabels[baseline.confidentiality]}</dd><dt>Źródło</dt><dd>{baseline.trip_snapshot?.title ?? baseline.campaign_snapshot?.title} · rewizja {baseline.trip_snapshot?.revision ?? baseline.campaign_snapshot?.revision}</dd><dt>Ostatni zapis</dt><dd><time dateTime={baseline.updated_at}>{baseline.updated_at ? new Date(baseline.updated_at).toLocaleString("pl-PL") : "Brak daty"}</time></dd></dl>
        <p>Zaawansowane pola {template.family === "offer" ? "oferty, ceny, hotelu i zakresu świadczeń" : template.family === "marketing" ? "kampanii, kolejności kierunków i ich zdjęć" : "operacyjne, rezerwacje, kontakty i wspólna logistyka"} są zachowane. Edytuj je w dotychczasowym Studio. Status jest tylko informacją, bez procesu zatwierdzania.</p>
      </details>
    </div></fieldset>
    <div className="creation-actions"><a className="text-link" href={links.preview} target="_blank" rel="noopener noreferrer">Podgląd ostatniego zapisu (nowa karta)</a><a className="text-link" href={links.editor}>Edytuj w dotychczasowym Studio</a><Link className="text-link" to={links.detail}>Szczegóły i historia</Link></div><p>Podgląd przedstawia ostatnią zapisaną wersję, bez zmian z formularza. Zapis nie oznacza gotowości do publikacji.</p>
  </section>;
}
