# Demo v0.1 — zakres i architektura

## 1. Co pokazujemy

**Jedno wejście:** wiadomość tekstowa „Zaplanuj wycieczkę…”.

**Jeden wynik:** krótki plan dzień po dniu, punkty na interaktywnej mapie, rzeczywista trasa samochodowa, czas i dystans jazdy, ostrzeżenia oraz URL wysłany na WhatsApp.

**Jedna intencja:** `trip.create`. Router ma zwrócić `trip.create` lub `unsupported` — bez autonomicznych agentów i bez prowadzenia długiej rozmowy.

## 2. Architektura minimum

```text
WhatsApp (testowy numer)     Formularz DEV / API
         |                         |
       WAHA                        |
         | webhook                 |
         +-------> FastAPI <-------+
                      |
               Intent (create?)
                      |
                SQLite: job QUEUED
                      |
                  Worker
                      |
          Brief -> LLM -> Places
                      |
           Day grouping -> Routes
                      |
             Validation -> JSON
                      |
              SQLite: COMPLETE
                     / \
           WAHA response   Viewer /trip/{token}
                            + Google Map
```

**WAHA** służy wyłącznie do odbioru i wysyłania wiadomości; planowanie jest niezależne od kanału. **Worker** obsługuje zadania poza HTTP webhooka. Jeden worker wystarczy na pokaz.

## 3. Algorytm minimalny

1. Odczytaj opis i wyciągnij `start`, `end`, `days`, `must_visit`, `preferences`, `max_daily_drive_min`.
2. LLM proponuje max. 6–8 atrakcji; backend sprawdza każdą przez Google Places. Nierozpoznane odrzuca lub oznacza jako `unresolved`.
3. LLM proponuje podział na dni i kolejność, w granicach punktów zweryfikowanych przez Places.
4. Backend wywołuje Routes dla kolejnych odcinków/dni; pobiera `distanceMeters`, `duration`, `encodedPolyline`.
5. Validator: `daily_drive_minutes > limit` ⇒ ostrzeżenie; brak geolokalizacji albo błąd Routes ⇒ brak potwierdzonej trasy, a nie zmyślona wartość.
6. Zapisz plan i wygeneruj read-only link z losowym tokenem, pokazujący harmonogram i Google Map. Odeślij podsumowanie przez WAHA.

**Uwaga:** Dane dot. trekkingu, godzin otwarcia i czasu zwiedzania, o ile LLM je zasugeruje, opisujemy jako **szacunkowe / niezweryfikowane**. Bez rzeczywistych dat nie potwierdzamy dostępności sezonowej.

## 4. Minimalny model wyniku

```json
{
  "trip_id": "uuid",
  "status": "complete",
  "title": "2 dni w Karkonoszach",
  "requirements": {
    "days": 2,
    "max_daily_drive_min": 180
  },
  "days": [
    {
      "number": 1,
      "stops": [{"place_id": "...", "name": "...", "lat": 0, "lng": 0}],
      "drive_minutes": 0,
      "distance_km": 0,
      "encoded_polyline": "...",
      "google_maps_url": "https://www.google.com/maps/dir/?api=1...",
      "warnings": []
    }
  ],
  "warnings": []
}
```

Liczby `0` i `...` w przykładzie to **placeholdery schematu**, nigdy wartości przypisywane wygenerowanej podróży. Pola niedostępne są `null` i mają status `unverified`/`routing_failed`.

## 5. Minimalne API

| Endpoint | Cel |
|---|---|
| `POST /api/webhooks/waha` | odbiór WAHA, weryfikacja HMAC, deduplikacja wiadomości |
| `POST /api/trips` | utwórz zadanie z tekstu (także formularz DEV) |
| `GET /api/trips/{id}` | status `queued/running/completed/failed` i wynik |
| `GET /trip/{token}` | read-only widok planu z mapą |
| `GET /health` | healthcheck |

Po `POST /api/trips`: `202 Accepted` + `trip_id`; worker dostarcza wynik później. Nie blokujemy webhooka na czas pracy LLM/map.

## 6. UI: jedna strona

Desktop: **lewa kolumna** — dni, przystanki, czasy jazdy, ostrzeżenia; **prawa kolumna** — Google Map z pinezkami i polylines. Mobile: najpierw plan, potem mapa. Nad planem tytuł i krótki opis wycieczki. Na każdy dzień przycisk „Open in Google Maps”.

Brak edytora tras, kont, panelu admina, rezerwacji, PDF, exportu, CRM i rozbudowanego design systemu.

## 7. Granice odpowiedzialności i zabezpieczenia

- LLM nie generuje żadnych `distance_km`, `drive_minutes` ani współrzędnych, które następnie byłyby przedstawiane jako zweryfikowane.
- Każdy wyświetlany punkt z mapy ma dopasowane Places ID, a każdy czas przejazdu ma status z Routes.
- Zabezpiecz webhook HMAC WAHA; ignoruj wiadomości wysłane przez własnego bota i duplikaty eventów.
- Ogranicz WAHA do numeru testowego / whitelisty nadawców; nie wystawiaj interfejsu WAHA do internetu.
- Viewer jest tylko do odczytu, z długim losowym tokenem i ograniczonym okresem ważności; brak danych osobowych w projekcie.
- Klucze API w zmiennych środowiskowych, serwerowy klucz Google tylko na backendzie; włącz budżety i limity Google.
- WAHA to nieoficjalna integracja — akceptujemy ryzyko wyłącznie w jednorazowym demo. Produkcja: Meta Cloud API.

## 8. Co świadomie pomijamy (P1/P2)

- Modyfikowanie planu kolejnymi wiadomościami, wersjonowanie i zatwierdzanie poprawek.
- Oddzielne Research Agent / Critic Agent; pełen web search i źródła atrakcji.
- Automatyczna optymalizacja globalna wielu dni i noclegów.
- Hotele, ceny, dostępność, szlaki, czasy otwarcia, rezerwacje.
- Kolejne intencje i moduły automatyzacji Tripse.

## 9. Oficjalna dokumentacja pomocnicza

- WAHA: https://waha.devlike.pro/docs/how-to/events/
- Google Routes: https://developers.google.com/maps/documentation/routes/reference/rest/v2/TopLevel/computeRoutes
- Maps URLs: https://developers.google.com/maps/documentation/urls/get-started
- Google Places: https://developers.google.com/maps/documentation/places/web-service/overview
