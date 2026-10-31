import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { PageHeader } from "../../shared/components/PageHeader";
import { Button } from "../../shared/ui/button";
import { Badge } from "../../shared/ui/badge";
import { legacyHref } from "../../shared/config/legacy";
import { createTripMutation } from "../../shared/api/query/client";
import { readCapabilities, readScenarios } from "../../shared/api/adapters/planner";
import type { PlannerTarget } from "../../shared/api/adapters/planner";
import { ambiguousCreate, authorizationError, plannerError } from "./messages";
import { JobProgress } from "./JobProgress";
import { useSessionFailure } from "../../shared/api/query/useSessionFailure";

type Operation = { text: string; target: PlannerTarget };
export function PlannerPage() {
  const sessionExpired = useSessionFailure();
  const [text, setText] = useState("");
  const [validation, setValidation] = useState(false);
  const [tripId, setTripId] = useState<string | null>(null);
  const [blocked, setBlocked] = useState(false);
  const [operation, setOperation] = useState<Operation | null>(null);
  const inFlight = useRef(false);
  const pendingController = useRef<AbortController | null>(null);
  const mounted = useRef(false);
  const textarea = useRef<HTMLTextAreaElement>(null);
  const capabilities = useQuery({ queryKey: ["private-api", "workspace", "capabilities"], queryFn: ({ signal }) => readCapabilities(signal), enabled: !sessionExpired, refetchOnMount: "always", gcTime: 0 });
  const mode = capabilities.data?.planning_mode;
  const examples = useQuery({ queryKey: ["private-api", "planner", "scenarios"], queryFn: ({ signal }) => readScenarios(signal), enabled: !sessionExpired && mode === "mock" && !capabilities.isError, gcTime: 0 });
  const permitted = !sessionExpired && capabilities.isSuccess && !capabilities.isFetching && capabilities.data.can_create_trip && !blocked;
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; pendingController.current?.abort(); };
  }, []);
  const mutation = useMutation({
    mutationFn: (intent: Operation) => createTripMutation(intent.target, pendingController.current?.signal).mutationFn({ text: intent.text }),
    retry: false,
    onSuccess: (response) => { if (mounted.current) { setTripId(response.data.trip_id); setOperation(null); } },
    onError: (error) => { if (mounted.current) { if (!ambiguousCreate(error)) setOperation(null); if (authorizationError(error)) setBlocked(true); } },
    onSettled: () => { inFlight.current = false; },
  });
  const ambiguous = mutation.isError && ambiguousCreate(mutation.error);
  const locked = mutation.isPending || tripId !== null || ambiguous;
  const trimmed = text.trim();
  // Count Unicode code points, matching Pydantic rather than UTF-16 code units.
  const count = [...trimmed].length;
  function send(intent: Operation) {
    if (inFlight.current || !permitted || tripId || intent.target.mode !== capabilities.data?.runtime_mode) return;
    inFlight.current = true;
    pendingController.current = new AbortController();
    setOperation(intent);
    mutation.mutate(intent);
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (locked || !permitted || inFlight.current) return;
    if (!count || count > 10000) { setValidation(true); textarea.current?.focus(); return; }
    setValidation(false);
    const target: PlannerTarget = capabilities.data.runtime_mode === "cloud_demo" ? { mode: "cloud_demo", idempotencyKey: crypto.randomUUID() } : { mode: "local" };
    send({ text: trimmed, target });
  }
  function newRequest() { setTripId(null); setOperation(null); mutation.reset(); setValidation(false); queueMicrotask(() => textarea.current?.focus()); }
  return <>
    <PageHeader eyebrow="Od pomysłu do planu" title="Planer podróży">Opisz trasę na 1–2 dni: początek, koniec, miejsca i limit jazdy. Plan jest szkicem do sprawdzenia, bez rezerwacji hoteli i biletów.</PageHeader>
    <div className="planner-layout">
      <div className="planner-main">
      <section className="planner-panel" aria-labelledby="request-heading">
        <div className="planner-panel-heading"><h2 id="request-heading">Zaplanuj podróż</h2><Badge>{mode === "mock" ? "DEMO / MOCK" : mode === "live" ? "LIVE" : "Sprawdzanie trybu"}</Badge></div>
        {mode === "mock" && <p className="planner-note">Dane przykładowe, bez wywołań AI i Google. Demo obsługuje Karkonosze, Ojców i Trójmiasto. Miejsca, czasy i dostępność nie są zweryfikowane.</p>}
        {mode === "live" && <p className="planner-note">Tryb LIVE korzysta z istniejących dostawców AI i map. Sugestie wymagają sprawdzenia, a czasy są szacunkowe.</p>}
        {sessionExpired && !tripId && <p role="alert">Sesja wygasła. Zaloguj się ponownie i odśwież stronę. Tworzenie planów jest wyłączone do czasu potwierdzenia dostępu.</p>}
        {capabilities.isPending && !sessionExpired && <p role="status">Sprawdzanie trybu i uprawnień…</p>}
        {capabilities.isError && !sessionExpired && <div role="alert"><p>{plannerError(capabilities.error)} Tworzenie planów jest wyłączone do czasu potwierdzenia dostępu.</p>{!authorizationError(capabilities.error) && <Button type="button" variant="outline" disabled={capabilities.isFetching} onClick={() => { void capabilities.refetch(); }}>Sprawdź dostęp ponownie</Button>}</div>}
        {capabilities.isSuccess && !capabilities.data.can_create_trip && <p role="status">Dostęp tylko do odczytu. Tworzenie planów wymaga uprawnień edytora.</p>}
        <form onSubmit={submit} noValidate>
          {mode === "mock" && !!examples.data?.length && <fieldset className="planner-examples" disabled={locked || !permitted}><legend>Wybierz przykład DEMO</legend>{examples.data.slice(0, 3).map((example) => <Button key={example.id} type="button" variant="outline" onClick={() => { setText(example.text); setValidation(false); textarea.current?.focus(); }}>{example.name}</Button>)}</fieldset>}
          <label htmlFor="trip-description">Opisz wycieczkę</label>
          <textarea ref={textarea} id="trip-description" name="text" rows={7} value={text} disabled={locked} aria-required="true" aria-invalid={validation} aria-describedby={`trip-help trip-counter${validation ? " trip-validation" : ""}`} onChange={(event) => { setText(event.target.value); setValidation(false); }} />
          <div className="planner-field-help"><p id="trip-help">Wpisz od 1 do 10 000 znaków. Skrajne spacje są pomijane.</p><p id="trip-counter" aria-live="polite">{count.toLocaleString("pl-PL")} / 10 000 znaków</p></div>
          {validation && <p id="trip-validation" role="alert">Wpisz od 1 do 10 000 znaków po usunięciu skrajnych spacji.</p>}
          <Button type="submit" disabled={!permitted || locked}>{mutation.isPending ? "Wysyłanie prośby…" : "Przygotuj plan"}</Button>
        </form>
        {mutation.isPending && <p role="status">Wysyłanie prośby. Poczekaj na potwierdzenie przyjęcia zadania.</p>}
        {mutation.isError && !sessionExpired && <div role="alert"><p>{plannerError(mutation.error)}</p>{ambiguous && <>
          <p>Nie można potwierdzić przyjęcia prośby. Zadanie mogło już powstać. Nie wysyłamy kolejnego automatycznie.</p>
          <p>{operation?.target.mode === "cloud_demo" ? "Ponowienie tej samej prośby zachowa klucz operacji, aby nie tworzyć duplikatu." : "W trybie lokalnym ponowienie może utworzyć drugie zadanie. Wybierz świadomie, czy ponowić prośbę."}</p>
          <div className="planner-actions"><Button type="button" disabled={!permitted} onClick={() => { if (operation) send(operation); }}>{operation?.target.mode === "cloud_demo" ? "Ponów tę samą prośbę" : "Wyślij ponownie mimo ryzyka duplikatu"}</Button><Button type="button" variant="outline" onClick={newRequest}>Rozpocznij nową prośbę</Button></div>
        </>}</div>}
      </section>
      {tripId && <JobProgress key={tripId} tripId={tripId} onNewRequest={newRequest} />}
      </div>
      <aside className="planner-guide planner-panel" aria-labelledby="planner-help"><p className="eyebrow">Dobry opis pomaga</p><h2 id="planner-help">Podaj kierunek i ramy</h2><ol><li>Skąd ruszasz i gdzie kończysz?</li><li>Ile dni masz do dyspozycji?</li><li>Co chcesz zobaczyć i ile czasu spędzić w drodze?</li></ol><p>Po przygotowaniu plan otworzysz w obecnym podglądzie z mapą. Zwróć uwagę na ostrzeżenia i weryfikację danych.</p><a className="text-link" href={legacyHref("/planner")}>Otwórz obecny planer</a><Link className="text-link" to="/">Wróć do pulpitu</Link><a className="text-link" href={legacyHref("/hub")}>Otwórz obecny Hub</a></aside>
    </div>
  </>;
}
