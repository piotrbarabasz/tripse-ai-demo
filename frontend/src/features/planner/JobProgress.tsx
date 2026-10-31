import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "../../shared/ui/button";
import { apiKeys, jobQuery } from "../../shared/api/query/client";
import { completedResultSchema, safeViewerPath } from "./result";
import { authorizationError, plannerError } from "./messages";
import { useSessionFailure } from "../../shared/api/query/useSessionFailure";

export const POLLING_WINDOW_MS = 120000;
const statuses = { queued: "W kolejce", running: "Przygotowanie planu", completed: "Plan gotowy", failed: "Błąd przygotowania planu" };

function CompletedResult({ value }: { value: unknown }) {
  const result = completedResultSchema.safeParse(value);
  const [now, setNow] = useState(Date.now);
  const expiry = result.success ? result.data.viewer_expires_at : undefined;
  useEffect(() => {
    if (!expiry || expiry * 1000 <= now) return;
    const timer = window.setTimeout(() => setNow(Date.now()), Math.min(expiry * 1000 - now + 1, 2147483647));
    return () => window.clearTimeout(timer);
  }, [expiry, now]);
  if (!result.success) return <p role="alert">Plan zakończony, ale jego wynik jest niekompletny. Nie można bezpiecznie otworzyć podglądu.</p>;
  const data = result.data;
  const path = safeViewerPath(data.viewer_url, window.location.origin, expiry, now);
  return <div className="planner-result">
    <p>{data.is_mock ? "Plan DEMO / MOCK — miejsca, czasy i trasa są przykładowe i niezweryfikowane." :
      data.verification_status === "verified" ? "Dopasowania miejsc i trasy są oznaczone w wyniku jako zweryfikowane. Czasy są szacunkowe; sprawdź dostępność i wszystkie uwagi." :
      "Szkic LIVE zawiera niezweryfikowane miejsca lub trasy. Sprawdź wszystkie uwagi przed użyciem."}</p>
    {!!data.warnings?.length && <p>Wynik zawiera uwagi do sprawdzenia w podglądzie planu.</p>}
    {path ? <Button asChild><a href={path} onClick={(event) => {
      if (!safeViewerPath(data.viewer_url, window.location.origin, expiry)) { event.preventDefault(); setNow(Date.now()); }
    }}>Otwórz plan i mapę</a></Button> :
      <p role="alert">Link do planu jest niedostępny, nieprawidłowy lub wygasł. Wróć do planera, aby przygotować nowy plan.</p>}
  </div>;
}

export function JobProgress({ tripId, onNewRequest }: { tripId: string; onNewRequest: () => void }) {
  const client = useQueryClient();
  const sessionExpired = useSessionFailure();
  const [paused, setPaused] = useState(false);
  const [windowId, setWindowId] = useState(0);
  const options = jobQuery(tripId);
  const query = useQuery({ ...options, enabled: !paused && !sessionExpired,
    refetchInterval: (state) => paused || sessionExpired ? false : typeof options.refetchInterval === "function" ? options.refetchInterval(state) : options.refetchInterval });
  const terminal = query.data?.status === "completed" || query.data?.status === "failed";
  useEffect(() => {
    if (terminal || sessionExpired) return;
    const timer = window.setTimeout(() => {
      setPaused(true);
      void client.cancelQueries({ queryKey: apiKeys.job(tripId) });
    }, POLLING_WINDOW_MS);
    return () => window.clearTimeout(timer);
  }, [client, tripId, windowId, terminal, sessionExpired]);
  const blocked = sessionExpired || authorizationError(query.error);
  return <section className="planner-panel" aria-labelledby="job-heading">
    <p className="eyebrow">Twoja prośba</p>
    <h2 id="job-heading">Postęp planowania</h2>
    <p className="planner-job-id">Numer zadania: {tripId}</p>
    <p role="status" aria-live="polite">{query.data ? statuses[query.data.status] : "Odczytywanie statusu…"}</p>
    {sessionExpired ? <p role="alert">Sesja wygasła. Zaloguj się ponownie i odśwież stronę.</p> : query.isError && <p role="alert">{plannerError(query.error)}</p>}
    {paused && !terminal && <p role="status">Wstrzymano automatyczne sprawdzanie po dwóch minutach. Zadanie może nadal działać. Sprawdź status ponownie.</p>}
    {query.data?.status === "failed" && <p role="alert">Nie udało się przygotować planu. Sprawdź, czy opis pasuje do dostępnego trybu; w DEMO wybierz gotowy przykład.</p>}
    {!sessionExpired && !query.isError && query.data?.status === "completed" && <CompletedResult value={query.data.result} />}
    {(query.isError || paused) && !blocked && <Button type="button" variant="outline" disabled={query.isFetching} onClick={() => {
      setPaused(false); setWindowId((value) => value + 1); void query.refetch();
    }}>Sprawdź status ponownie</Button>}
    {terminal && !sessionExpired && !query.isError && <Button type="button" variant="outline" onClick={onNewRequest}>Zaplanuj kolejną podróż</Button>}
    <p className="planner-note">Odczyt statusu nie tworzy nowego zadania. Wyjście z tej strony zatrzymuje sprawdzanie, ale nie anuluje pracy serwera.</p>
  </section>;
}
