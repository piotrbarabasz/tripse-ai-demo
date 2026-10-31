import { useEffect, useRef, useState } from "react";
import { Link, useBeforeUnload, useBlocker, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "../../shared/ui/button";
import { readSources } from "../../shared/api/adapters/studio";
import { apiKeys } from "../../shared/api/query/client";
import { ApiError } from "../../shared/api/client/errors";
import { legacyHref } from "../../shared/config/legacy";
import { documentLinks } from "./links";
import { families } from "./labels";
import { ReadError } from "./presentation";
import { creationIntent, submitCreation, verifyCreation } from "./creation";
import type { Intent, Outcome, Source, Template } from "./creation";

const sourceName = (kind: "trip" | "campaign") => kind === "trip" ? "Wycieczka" : "Kampania";
const confidentiality = { public: "Publiczne", client: "Dla klienta", internal: "Wewnętrzne", internal_restricted: "Wewnętrzne — ograniczony dostęp" };

function LeaveWarning({ dirty }: { dirty: boolean }) {
  useBeforeUnload((event) => { if (dirty) { event.preventDefault(); event.returnValue = ""; } });
  const blocker = useBlocker(dirty);
  const stay = useRef<HTMLButtonElement>(null);
  useEffect(() => { if (blocker.state === "blocked") stay.current?.focus(); }, [blocker.state]);
  return blocker.state === "blocked" ? <section role="alertdialog" aria-labelledby="leave-title" aria-describedby="leave-description" className="documents-notice">
    <h3 id="leave-title">Opuścić tworzenie dokumentu?</h3>
    <p id="leave-description">Formularz i dane odzyskiwania są tylko w pamięci tej strony. Utracisz je po wyjściu. Jeśli zapis był wysłany, dokument może już istnieć — najpierw sprawdź wynik.</p>
    <Button ref={stay} onClick={() => blocker.reset()}>Zostań w formularzu</Button>
    <Button variant="outline" onClick={() => blocker.proceed()}>Opuść formularz</Button>
  </section> : null;
}

export default function CreationWizard({ templates, canEdit }: { templates: Template[] | undefined; canEdit: boolean }) {
  const [params] = useSearchParams();
  const templateId = params.get("template") ?? undefined;
  // Changing the route starts a separate form only after the router blocker has
  // allowed leaving; step navigation itself never remounts or writes anything.
  return !canEdit ? <p role="alert">Brak uprawnień do tworzenia dokumentów.</p> : !templates ? <p role="status">Wczytywanie szablonów…</p> :
    !templates.length ? <p role="status">Brak dostępnych szablonów.</p> :
    templateId && !templates.some((item) => item.template_id === templateId) ? <p role="alert">Nieprawidłowy szablon. Wybierz go w katalogu.</p> :
      <Wizard key={templateId ?? "new"} templates={templates} initialTemplate={templateId} />;
}

function Wizard({ templates, initialTemplate }: { templates: Template[]; initialTemplate: string | undefined }) {
  const client = useQueryClient();
  const [step, setStep] = useState(1);
  const [templateId, setTemplateId] = useState(initialTemplate ?? "");
  const template = templates.find((item) => item.template_id === templateId);
  const [variant, setVariant] = useState(template?.layout_variants[0] ?? "");
  const [source, setSource] = useState<Source>();
  const [title, setTitle] = useState("");
  const [search, setSearch] = useState("");
  const [intent, setIntent] = useState<Intent>();
  const [outcome, setOutcome] = useState<Outcome>();
  const [failure, setFailure] = useState<Error>();
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  const controller = useRef<AbortController | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => () => controller.current?.abort(), []);
  useEffect(() => { heading.current?.focus(); }, [step, outcome?.kind]);
  const kind = template?.source_type ?? "trip";
  const sources = useQuery({ queryKey: [...apiKeys.studio, "sources", kind], queryFn: ({ signal }) => readSources(kind, signal),
    enabled: !!template && step >= 2 && !intent, gcTime: 0 });
  const mutation = useMutation({ mutationFn: ({ attempt, check }: { attempt: Intent; check: boolean }) =>
    (check ? verifyCreation : submitCreation)(attempt, controller.current?.signal), retry: false, networkMode: "always", gcTime: 0 });
  const saved = outcome?.kind === "saved" ? outcome.draft : undefined;
  const initialVariant = templates.find((item) => item.template_id === initialTemplate)?.layout_variants[0] ?? "";
  const dirty = !saved && (!!source || !!title.trim() || !!intent || (!!templateId && templateId !== initialTemplate) || variant !== initialVariant);
  const current = sources.data?.find((item) => item.source_id === source?.source_id);
  const changed = !!source && !!sources.data && (!current || current.revision !== source.revision);
  async function run(check = false) {
    if (lock.current || saved || !template || !source || (!intent && changed) || (check && !intent)
      || (intent && !check && outcome?.kind !== "missing")) return;
    lock.current = true; setBusy(true); setFailure(undefined); setOutcome(undefined);
    controller.current = new AbortController();
    try {
      const attempt = intent ?? creationIntent(template, variant, source, title);
      setIntent(attempt);
      const result = await mutation.mutateAsync({ attempt, check });
      if (controller.current.signal.aborted) return;
      setOutcome(result);
      if (result.kind === "saved") await client.invalidateQueries({ queryKey: apiKeys.studio });
    } catch (error) {
      if (!controller.current?.signal.aborted) setFailure(error instanceof Error ? error : new ApiError("invalid-response"));
    } finally { lock.current = false; setBusy(false); }
  }
  async function review() {
    if (lock.current) return;
    setBusy(true);
    // A failed refresh must not release the frozen attempt or allow a new write.
    const result = await sources.refetch();
    setBusy(false);
    if (result.isSuccess) { setIntent(undefined); setOutcome(undefined); setFailure(undefined); setSource(undefined); setStep(2); }
    else if (result.error) setFailure(result.error);
  }
  const definiteFailure = failure instanceof ApiError && failure.status !== undefined && failure.status < 500;
  const permissionFailure = failure instanceof ApiError && ["forbidden", "unauthenticated"].includes(failure.kind);
  const filtered = sources.data?.filter((item) => `${item.title} ${item.summary}`.toLocaleLowerCase("pl").includes(search.toLocaleLowerCase("pl")));
  return <section aria-labelledby="creation-title" className="creation-wizard">
    <LeaveWarning dirty={dirty} />
    <h2 id="creation-title" className="documents-section-title" ref={heading} tabIndex={-1}>{saved ? "Dokument został zapisany" : "Utwórz dokument"}</h2>
    {!saved && <ol className="creation-progress" aria-label="Etapy tworzenia">{["Typ dokumentu", "Źródło", "Potwierdzenie"].map((label, index) => <li key={label} aria-current={step === index + 1 ? "step" : undefined}>{index + 1}. {label}</li>)}</ol>}
    {saved ? <div className="document-card" role="status">
      <h3>{saved.title}</h3><p>{template?.name} · {saved.template_id} · Rewizja {saved.revision}</p>
      <p>Zweryfikowano zapis i zgodność migawki ze wskazaną rewizją źródła. Edycja dokumentu odbywa się w dotychczasowym Studio.</p>
      {documentLinks(saved.document_id ?? "", saved.revision) && <div className="creation-actions"><Button asChild><a href={documentLinks(saved.document_id ?? "", saved.revision)!.editor}>Otwórz dokument w edytorze</a></Button>
        <Link className="text-link" to={documentLinks(saved.document_id ?? "", saved.revision)!.detail}>Szczegóły dokumentu</Link><Link className="text-link" to="/documents/library">Wróć do biblioteki</Link></div>}
    </div> : <>
      {!intent && step === 1 && <>
        <fieldset><legend>Wybierz szablon</legend>{Object.entries(families).map(([family, label]) => <section aria-label={label} key={family}><h3>{label}</h3><div className="documents-grid">{templates.filter((item) => item.family === family).map((item) =>
          <label className="document-card creation-choice" key={item.template_id}><input type="radio" name="template" value={item.template_id} checked={templateId === item.template_id} onChange={() => {
            setTemplateId(item.template_id); setVariant(item.layout_variants[0] ?? "");
            if (item.source_type !== source?.source_type) { setSource(undefined); setTitle(""); setSearch(""); }
          }} /><span><strong>{item.name}</strong><span>{item.description}</span><span>{sourceName(item.source_type)} · {confidentiality[item.confidentiality]}</span></span></label>)}</div></section>)}</fieldset>
        {template && <label>Wariant układu<select value={variant} onChange={(event) => setVariant(event.target.value)}>{template.layout_variants.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>}
        <Button disabled={!template || !template.layout_variants.includes(variant)} onClick={() => setStep(2)}>Dalej: źródło</Button>
      </>}
      {!intent && step === 2 && template && <>
        <h3>Wybierz źródło: {sourceName(kind)}</h3>
        <p>Wybierz zapisane źródło. Programy Planera nie są źródłami Document Studio.</p>
        <label>Szukaj źródła<input type="search" maxLength={200} value={search} onChange={(event) => setSearch(event.target.value)} /></label>
        {sources.isPending && <p role="status">Wczytywanie źródeł…</p>}
        {sources.isError && <ReadError error={sources.error} retry={() => { void sources.refetch(); }} />}
        {sources.isSuccess && (!sources.data.length ? <p role="status">Brak zapisanych źródeł tego typu.</p> : !filtered?.length ? <p role="status">Brak źródeł pasujących do wyszukiwania.</p> :
          <fieldset><legend>Dostępne źródła</legend><div className="documents-grid">{filtered.map((item) => <label className="document-card creation-choice" key={item.source_id}>
            <input type="radio" name="source" value={item.source_id} checked={source?.source_id === item.source_id && source.revision === item.revision} onChange={() => { setSource(item); if (!title) setTitle(item.title); }} />
            <span><strong>{item.title}</strong><span>{sourceName(item.source_type)} · Rewizja {item.revision}</span><span>{item.summary}</span><span>Pochodzenie danych: {item.data_origin}</span>{item.incomplete && <span>Źródło jest niepełne. Sprawdź program przed użyciem dokumentu.</span>}</span>
          </label>)}</div></fieldset>)}
        {changed && <p role="alert">Źródło zmieniło się. Wybierz ponownie jego aktualną rewizję.</p>}
        <div className="creation-actions"><a className="text-link" href={`${legacyHref("/documents/demo")}#${kind === "trip" ? "trips" : "campaigns"}`}>Zarządzaj źródłami w dotychczasowym Studio</a>
          <Button variant="outline" onClick={() => { void sources.refetch(); }} disabled={sources.isFetching}>Odśwież źródła</Button></div>
        <div className="creation-actions"><Button variant="outline" onClick={() => setStep(1)}>Wstecz: typ dokumentu</Button><Button disabled={!source || changed || sources.isError || sources.isPending} onClick={() => setStep(3)}>Dalej: potwierdzenie</Button></div>
      </>}
      {(step === 3 || !!intent) && template && source && <>
        <h3>Sprawdź dane przed utworzeniem</h3>
        <dl className="document-metadata"><dt>Szablon</dt><dd>{template.name} ({template.template_id})</dd><dt>Wariant</dt><dd>{variant}</dd><dt>Źródło</dt><dd>{source.title} · {sourceName(source.source_type)}</dd><dt>Rewizja źródła</dt><dd>{source.revision}</dd><dt>Poufność</dt><dd>{confidentiality[template.confidentiality]}</dd></dl>
        <p>Nowy dokument będzie niezależną migawką wybranej rewizji źródła. Późniejsze zmiany źródła nie aktualizują dokumentu. Status i poufność nie oznaczają zgody na publikację.</p>
        {source.incomplete && <p role="note">Źródło jest niepełne. Dokument wymaga przeglądu i uzupełnienia w edytorze.</p>}
        <label>Tytuł dokumentu<input maxLength={200} required value={title} disabled={!!intent} onChange={(event) => setTitle(event.target.value)} /></label>
        {changed && <p role="alert">Źródło zmieniło się. Wróć do wyboru źródła i sprawdź aktualną rewizję.</p>}
        {busy && <p role="status">Zapisywanie lub sprawdzanie zapisu… Nie rozpoczynaj drugiego dokumentu.</p>}
        {!intent && <div className="creation-actions"><Button variant="outline" onClick={() => setStep(2)}>Wstecz: źródło</Button><Button disabled={busy || !title.trim() || changed} onClick={() => { void run(); }}>Utwórz i zapisz dokument</Button></div>}
        {intent && <p className="document-id">Identyfikator próby: {intent.payload.document_id}. Dane próby są tylko w pamięci strony.</p>}
        {outcome && outcome.kind !== "saved" && <div role="alert">
          <p>{outcome.kind === "missing" ? "Nie znaleziono zapisanego dokumentu. Możesz świadomie ponowić tę samą próbę z tym samym identyfikatorem." : outcome.kind === "mismatch" ? "Zapisany dokument nie odpowiada tej próbie. Nie nadpisujemy go. Sprawdź bibliotekę lub skontaktuj się z administratorem, podając identyfikator." : "Nie można potwierdzić wyniku zapisu. Dokument może już istnieć. Zachowano tę samą próbę; sprawdź wynik ponownie."}</p>
          {outcome.kind !== "mismatch" && <Button disabled={busy || permissionFailure} onClick={() => { void run(true); }}>Sprawdź zapis ponownie</Button>}
          {outcome.kind === "missing" && <Button disabled={busy || permissionFailure} onClick={() => { void run(); }}>Ponów tę samą próbę</Button>}
        </div>}
        {failure && <div role="alert"><p>{failure instanceof ApiError && failure.kind === "conflict" ? "Konflikt rewizji źródła lub identyfikatora. Sprawdź aktualne źródła i potwierdź dane od nowa." : failure instanceof ApiError && failure.kind === "validation" ? "Serwer odrzucił dane formularza. Sprawdź źródło i tytuł przed nową próbą." : permissionFailure ? "Brak uprawnień do tej operacji. Zapis nie został potwierdzony." : "Nie można potwierdzić operacji. Sprawdź wynik zapisu."}</p>
          {definiteFailure && !permissionFailure && <Button disabled={busy} onClick={() => { void review(); }}>Sprawdź aktualne źródła</Button>}
          {!definiteFailure && <Button disabled={busy} onClick={() => { void run(true); }}>Sprawdź zapis ponownie</Button>}
        </div>}
      </>}
    </>}
  </section>;
}
