import { ApiError } from "../../shared/api/client/errors";

export function plannerError(error: unknown): string {
  if (!(error instanceof ApiError)) return "Nie udało się odczytać odpowiedzi. Spróbuj ponownie później.";
  switch (error.kind) {
    case "unauthenticated": return "Sesja wygasła. Zaloguj się ponownie i odśwież stronę.";
    case "forbidden": return "Brak uprawnień do tej operacji. Skontaktuj się z opiekunem przestrzeni.";
    case "not-found": return "Nie znaleziono zadania lub nie masz do niego dostępu.";
    case "validation": return "Sprawdź opis: wpisz od 1 do 10 000 znaków po usunięciu skrajnych spacji.";
    case "bad-request": return "Żądanie zostało odrzucone. Otwórz planer pod właściwym adresem.";
    case "timeout": return "Przekroczono czas oczekiwania. Zadanie może nadal być przetwarzane.";
    case "network": return "Brak połączenia z usługą. Sprawdź połączenie i spróbuj ponownie później.";
    case "unavailable": return "Usługa jest chwilowo niedostępna. Spróbuj ponownie później.";
    case "invalid-response": return "Usługa zwróciła nieprawidłową odpowiedź. Nie można potwierdzić wyniku.";
    case "cancelled": return "Przerwano oczekiwanie. Zadanie na serwerze nie zostało anulowane.";
    default: return "Operacja nie powiodła się. Spróbuj ponownie później.";
  }
}

export function ambiguousCreate(error: unknown): boolean {
  return !(error instanceof ApiError) || ["network", "timeout", "invalid-response", "unavailable", "http", "cancelled"].includes(error.kind);
}

export function authorizationError(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 401 || error.status === 403);
}
