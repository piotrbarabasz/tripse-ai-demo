# GCP: propozycja środowiska i wdrożenia

**Status:** projekt architektoniczny, nie instrukcja uruchomienia konkretnego istniejącego środowiska. Repozytorium zawiera dziś lokalny stack Compose, a publiczne wdrożenie produkcyjne/demonstracyjne nie było potwierdzone w sprawdzonym README.

## 1. Minimalna topologia

```text
Użytkownik (HTTPS)
       |
Autoryzacja panelu
       |
Cloud Run — FastAPI + UI
       |               +--> Cloud Storage: zdjęcia, PDF
       +--> Database
       |
       +--> Cloud Tasks (kolejka)
                    |
              Worker / Cloud Run endpoint
                    |
               PDF render + Storage
```

Dobór komponentów jest **propozycją**. Cloud Tasks może wywoływać chroniony endpoint Cloud Run; przy długich i ciężkich eksportach rozważyć Cloud Run Jobs. Należy sprawdzić aktualne limity i sposób rozliczania przy implementacji.

## 2. Stan danych i bazy

Nie przenoś 1:1 wspólnego SQLite na nietrwały dysk kontenera Cloud Run. Należy zdecydować między:

- **Firestore:** prosty model dokumentowy, łatwy start i przechowywanie metadanych, ale z wymaganiami dotyczącymi zapytań i transakcji.
- **Cloud SQL (PostgreSQL):** relacje, transakcje i bogatsze zapytania, lecz większe wymagania operacyjne i koszty utrzymania.

**Decyzja [DO UZGODNIENIA]:** na podstawie liczby użytkowników, danych rezerwacyjnych, potrzeby audytu i kosztów. Nie zakładać, że żadne z rozwiązań jest „za darmo”.

## 3. Zasoby plikowe

- Private Cloud Storage dla bazowych zdjęć, assetów, preview i gotowych PDF.
- Osobne logiczne prefiksy/buckety dla zasobów publicznych i wewnętrznych; polityka IAM bez publicznego czytania materiałów pilota.
- Pliki są wskazywane przez ID, nie publiczny URL; dostęp do pobrania jest wydawany po sprawdzeniu roli.
- Lifecycles / retencja / backups konfigurowane po decyzji biznesowej.
- Przetwarzanie i skanowanie uploadów przed publiczną ekspozycją.

## 4. Security & secrets

Klucze OpenAI/Google Maps, tokeny i dane API w Secret Manager / ograniczonym kontekście wykonania, nigdy w repozytorium i HTML. Minimalne konta serwisowe per komponent. Logi nie powinny zawierać pełnych danych uczestników, PIN-ów i tokenów dostępu. Frontend może otrzymywać tylko właściwe dane po autoryzacji.

## 5. CI/CD i środowiska

Preferowane `dev` i `prod` jako odrębne konfiguracje/zasoby; na początku wystarczy prywatne `dev`. Deployment z kontenera, healthcheck, migracje schematu, testy endpointów, test renderu PDF i skan podstawowych podatności. Każdy release szablonu ma zapisany numer wersji niezależnie od wersji API.

## 6. Obserwowalność i koszty

Metryki: liczba eksportów, typ szablonu, czas renderowania, rozmiar dokumentu, błędy walidacji, błędy renderu, liczba aktywnych plików. Monitoruj koszty przetwarzania i storage, ustal budżety/alerty GCP oraz limity żądań. AI research i generowanie obrazów mogą kosztować znacznie więcej niż zwykły PDF — nie uruchamiać ich przy każdej edycji podglądu.

## 7. Integracje istniejącego demo

- Planner przez API/adapter; włączenie do panelu po ustaleniu wspólnego modelu danych.
- Google Places/Routes obsługiwane tylko dla sprawdzonych/zadeklarowanych zadań.
- Obecny WAHA jest nieoficjalnym klientem WhatsApp Web ze stanem sesji; **nie należy zakładać**, że da się przenieść go bez zmian na bezstanowy Cloud Run. Obsługę wiadomości oddzielić i rozważyć oficjalną integrację przed produkcją.

## 8. Warunki wdrożenia dev

- DNS/TLS i uwierzytelnienie działają; nie wystawiono publicznie panelu administracyjnego.
- Draft i PDF przeżywają restart oraz zmianę instancji.
- Materiały pilotów są niedostępne publicznie nawet po znajomości ID.
- Wygenerowano próbne trzy dokumenty i porównano wynik z podglądem.
- Brak automatycznego wydawania pieniędzy na LLM i mapy bez ustawionych limitów.

## 9. Nierozstrzygnięte decyzje

Wybór bazy, mechanizm tożsamości (np. logowanie kontem firmowym), polityka retencji, preferowana domena, format generacji obrazu social, limit rozmiaru uploadu, wolumen i koszty. Dopiero po ich wyborze pisać szczegółowy runbook deploy.

**Powiązania:** [architektura](system-architecture.md) · [security](security.md).
