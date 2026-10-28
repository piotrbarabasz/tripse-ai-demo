# Wspólny model danych wycieczki

Stan implementacji lokalnej 2026-10-28: Bieżące klasy: Trip/TripDay/Stop, OfferData/OfferDetails, PilotData/OperationalEntry i DocumentDraft.sections. DayLogistics, KnowledgeContent/KnowledgeSource oraz zdjęcia i tabele sekcji są walidowanymi strukturami; metryki nieznane są null. Pozostałe encje opisane dalej pozostają modelem docelowym.

Szczegóły operacyjne: [Document Studio](../../DOCUMENT_STUDIO.md).

**Status:** proponowany kontrakt logiczny v1. Nie jest aktualnym schematem bazy ani automatycznie zgodny z istniejącym `app/planning_models.py`. Konkretne tabele/API powstaną w etapie implementacji.

## 1. Główna zasada

`Trip` jest pojedynczym źródłem podstawowych informacji o podróży. `DocumentDraft` zawiera **snapshot** danych wykorzystanych do danego szablonu wraz z lokalnymi, edytowalnymi polami oferty; `DocumentExport` jest niezmienną wersją wygenerowanego pliku. Operacyjne dane osobowe i sekrety są logicznie i dostępowo wydzielone.

## 2. Encje i identyfikatory

| Encja | Klucz | Najważniejsze pola | Dostęp |
|---|---|---|---|
| `Trip` | `trip_id` | `title`, `destinations[]`, `start_date?`, `end_date?`, `duration_days`, `status`, `days[]` | wewnętrzny |
| `TripDay` | `day_id` | `day_number`, `date?`, `title`, `stops[]`, `schedule_items[]`, `accommodation_ref?`, `notes` | wewnętrzny |
| `Stop` | `stop_id` | `place_id?`, `name`, `location`, `visit_status`, `estimated_visit_duration_min?` | wewnętrzny |
| `RouteSegment` | `segment_id` | `from_stop_id`, `to_stop_id`, `distance_meters?`, `duration_seconds?`, `source`, `verified_at?` | wewnętrzny |
| `Accommodation` | `accommodation_id` | `name`, `location`, `status`, `dates`, `type`, `amenities[]` | wewnętrzny, bez sekretów |
| `OfferData` | `offer_id` | `audience`, `pricing`, `included[]`, `excluded[]`, `assumptions[]`, `cta` | kliencki snapshot, bez PII |
| `Operations` | `operations_id` | `leader`, `flights[]`, `bookings[]`, `meetings[]`, `open_items[]` | ograniczony |
| `Participant` | `participant_id` | tylko minimalne dane wymagane operacyjnie | silnie ograniczony |
| `KnowledgeItem` | `knowledge_id` | `day_id/stop_id`, `category`, `content`, `sources[]`, `verification_status` | wewnętrzny |
| `Asset` | `asset_id` | typ, owner, prawa, URL magazynu, focal point | zależny od licencji |
| `DocumentDraft` | `document_id + revision` | `template_id`, `template_version`, `trip_snapshot`, `overrides`, `status` | zależny od szablonu |
| `DocumentExport` | `export_id` | `document_revision`, `format`, `storage_path`, `sha256`, `created_at` | zależny od szablonu |

## 3. Statusy i źródła

- `trip.status`: `idea | draft | planned | confirmed | completed | cancelled` (do uzgodnienia z procesem TRIPSE).
- Pole potwierdzalne: `verification_status: unverified | proposed | verified | rejected`.
- Rezerwacja: `booking_status: unknown | proposed | pending | confirmed | cancelled`.
- Zasób: `asset.status: draft | approved | rejected`.
- Dokument: `draft | needs_review | approved | generated | archived`.
- Źródło: `source_type: user | organizer | google_places | google_routes | provider | official_site | external_research | ai_draft` oraz identyfikator/referencja.

**Nie utożsamiaj:** `google_places` = potwierdzenie istnienia/dopasowania miejsca, **nie** potwierdzenie jego otwartości; `google_routes` = oszacowanie dla zapytania, **nie** gwarancja czasu przejazdu.

## 4. Przykładowy minimalny obiekt (dane fikcyjne)

```json
{
  "trip_id": "sample-trip-001",
  "title": "Weekend w górach — przykład",
  "destinations": ["Przykładowy region"],
  "start_date": null,
  "end_date": null,
  "duration_days": 2,
  "status": "draft",
  "days": [
    {
      "day_id": "day-001",
      "day_number": 1,
      "date": null,
      "title": "Spacer i zwiedzanie",
      "stops": [
        {
          "stop_id": "stop-001",
          "name": "Przykładowy punkt widokowy",
          "place_id": null,
          "verification_status": "unverified"
        }
      ],
      "schedule_items": [],
      "public_description": "Proponowany dzień na łonie natury.",
      "internal_notes": null
    }
  ]
}
```

Ten JSON ilustruje **kształt danych**, nie jest gotowym payloadem API ani zweryfikowaną trasą. W szczególności nie wolno przedstawiać przykładowych nazw jako wyników Google Places.

## 5. Dane ofertowe i marketingowe

- Oferty: `offer.included[]`, `offer.excluded[]`, `offer.pricing {amount, currency, pricing_unit, participant_count, status, valid_until}`, `offer.cta`, `offer.audience_specific`.
- `audience_specific` może zawierać grupy: `self_guide`, `school`, `incentive`; walidator danego szablonu wymaga odpowiednich podkluczy.
- Kampania: `campaign {title, season, layout_variant, cta, trips[]}`; pozycja `trips[]` wiąże wycieczkę, obraz, termin/status i krótkie wyróżniki.
- Pola redakcyjne (`short_hook`, `highlights`, `description`) są edytowalne i mogą mieć źródło `ai_draft`, ale mają status zatwierdzenia autora.

## 6. Dane pilota i bezpieczeństwo

`Operations` przechowuje minimalną logistykę; zaszyfrowane sekrety dostępu, PIN-y, pełne dane uczestników i rezerwacje z identyfikatorami nie powinny mieszać się z publicznym `Trip`. Jeśli organizacja naprawdę potrzebuje sekretów w narzędziu, wymagany jest osobny model uprawnień, szyfrowanie i bezpieczna dystrybucja. Nigdy nie dodawaj ich do `DocumentDraft` oferty ani marketingu.

## 7. Model wiedzy

`KnowledgeItem` powinien mieć `topic`, `day_id`, `stop_id?`, `category (history|nature|geology|culture|story|observation)`, `body`, `sources[] (url, title, publisher, checked_at)`, `verification_status`, `editor_approved_at`, `seasonal_caveat?`. Powiązanie z miejscem zapobiega generowaniu losowych historii nieobecnych w programie.

## 8. Wersje, snapshoty i audyt

- Przed stworzeniem draftu zapisz identyfikator źródłowej wersji wycieczki.
- Lokalna edycja tekstu w dokumencie nie zmienia automatycznie `Trip`.
- `approved` wskazuje zamrożone `template_version`, `trip_snapshot` i wersje wykorzystanych assetów.
- Nowa wersja wycieczki może proponować aktualizację dokumentu, ale nie nadpisuje zatwierdzonego eksportu.
- Każda zmiana statusu: aktor, czas, powód; daty w UTC w bazie, lokalny czas w UI.

## 9. Adapter istniejącego planera

Aktualny model `TripPlan` ma `days` z punktami Places, dystansami/czasem/geometry i warningami; `Candidate.day` ogranicza się do `1..2`, maksymalnie 8 kandydatów. Adapter może zaimportować zatwierdzone nazwy miejsc, Places ID, sprawdzone odcinki i ostrzeżenia, ale **nie** stworzy nieobecnych pól: dat, noclegów, cen, rezerwacji, wiedzy pilota czy aktywności z godzinami. Braki pozostają puste i widoczne.

## 10. Warunki akceptacji modelu

Obsługa minimum 15 dni bez twardego limitu 2; brak wymyślonych brakujących pól; referencyjność miejsc; rozdzielenie public/operations; wersjonowanie i odtwarzalność dokumentu; automatyczne testy schematu oraz migracji danych.

**Powiązania:** [pola szablonów](template-fields.md) · [walidacja](content-validation.md) · [architektura](../architecture/system-architecture.md).
