import { ApiError } from "../../shared/api/client/errors";

export const families = { offer: "Oferty", pilot: "Materiały pilota", marketing: "Marketing" };
export const statuses = { draft: "Roboczy", in_review: "Do przeglądu", ready: "Gotowy", archived: "Zarchiwizowany" };

export function documentError(error: unknown): string {
  if (!(error instanceof ApiError)) return "Nie udało się odczytać danych dokumentów.";
  switch (error.kind) {
    case "unauthenticated": return "Sesja wygasła. Zaloguj się ponownie i odśwież stronę.";
    case "forbidden": return "Brak uprawnień do tych dokumentów. Skontaktuj się z opiekunem przestrzeni.";
    case "not-found": return "Nie znaleziono dokumentu lub nie masz do niego dostępu.";
    case "unavailable": return "Biblioteka jest chwilowo niedostępna. Spróbuj ponownie później.";
    case "timeout": return "Przekroczono czas oczekiwania na dokumenty.";
    case "network": return "Nie udało się połączyć z usługą dokumentów.";
    case "invalid-response": return "Usługa zwróciła nieprawidłowe dane dokumentów.";
    default: return "Nie udało się odczytać danych dokumentów. Spróbuj ponownie później.";
  }
}
