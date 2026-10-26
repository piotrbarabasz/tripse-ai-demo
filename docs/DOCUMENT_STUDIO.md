# TRIPSE Document Studio — funkcjonalne DEMO lokalne

CLOUD-PARITY-001 (2026-10-26): the existing models, service, editors and renderer
are shared with opt-in authenticated `cloud_demo`. The cloud repository uses
private GCS JSON overlays and generation-match optimistic concurrency (409),
immutable validated image bytes, fixture fallback, snapshots and revisions.
No persistent cloud data is written to Cloud Run disk. Both metadata and image
content require verified membership; only editors with exact Origin may write.
Approved members share Studio documents within DEV or PROD; those environments
use independent buckets. Pilot documents remain internal, and offer rendering
retains its operational-data whitelist. No additional templates were implemented.

LOCAL continues to use JSON/files and the unchanged localhost policy without
GCP configuration. Public `readonly_demo` does not register this private API/UI.
Cloud deployment, IAP/OAuth acceptance and restore testing are still pending;
see [audit](CLOUD_PARITY_AUDIT.md), [ADR-0011](adr/0011-authenticated-cloud-demo.md)
and [operator instructions](DEPLOY_GCP.md). Browser PDF remains client-side.

**DEMO-03:** edytowalne `offer.private` i `pilot.basic`, wspólny Trip i renderer,
lokalna logistyka oraz druk A4: [TRIP_DOCUMENTS.md](TRIP_DOCUMENTS.md).

**Aktualizacja DEMO-02:** pełny generator `marketing.collection`, edycja kampanii,
lokalne zdjęcia, kadrowanie, podgląd A4/1080×1350 i druk do PDF są opisane w
[MARKETING_COLLECTION.md](MARKETING_COLLECTION.md). Poniżej fundamenty modułu.

## Uruchomienie

Python 3.12, z katalogu repozytorium (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
$env:PLANNING_MODE = "mock"
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Otwórz **http://localhost:8000/documents/demo** (działa też `127.0.0.1`).
Document Studio nie potrzebuje workera, kluczy API ani WhatsApp. Do generowania
planów w dotychczasowym planerze uruchom osobno `python -m app.worker` z tym samym
`DATABASE_PATH` i `PLANNING_MODE=mock`, zgodnie z instrukcją istniejącego demo.

Docker Compose:

```powershell
docker compose up --build -d api
```

API jest domyślnie wystawione na `127.0.0.1:8000`. Przy własnym `API_PORT` zmień
port w URL. Bind mount `./local-data/document-studio:/app/local-data/document-studio`
zachowuje dokumenty po odtworzeniu kontenera; niezależny wolumen SQLite nie został zmieniony.
Fixture'y są kopiowane do obrazu. Nie uruchamiaj publicznego `compose.dev.yaml`
do obsługi tego panelu: jego proxy nie udostępnia ścieżek studia.

## Ścieżka demonstracyjna

1. Otwórz Islandię (10 dni), Kanadę (15 dni) lub Norwegię (5 dni).
2. Wybierz „Nowa wycieczka”, zmień nazwę, kierunki, opis, status i opcjonalny termin.
3. Dodaj lub usuń dni oraz atrakcje; uzupełnij opisy. Zakończenie wylicza się
   z daty rozpoczęcia i liczby dni. Brak terminu pozostaje jawnym brakiem.
4. Zapisz wycieczkę. Odśwież stronę lub zrestartuj serwer i otwórz ją ponownie.
5. Wybierz typ dokumentu i opcjonalną notatkę; zapisz dokument roboczy.
   Niezapisana wycieczka jest najpierw zapisywana. Otwórz dokument w zakładce
   „Dokumenty robocze”; późniejsza edycja wycieczki nie zmienia jego snapshotu.
6. W „Kampanie” otwórz kolekcję trzech kierunków, przejdź do wycieczek lub zapisz
   dokument `marketing.collection` z wariantem `new_trips` / `theme_collection`.

## Architektura i zapis

Moduł `app/document_studio/`:

- `models.py`: Pydantic, wersja schematu, identyfikatory, daty, numeracja dni,
  unikalność dni i atrakcji, niezależne Trip / Campaign / DocumentDraft.
- `repository.py`: niewielki kontrakt `Repository` i implementacja `JsonRepository`.
  Odczyt i zapis są walidowane. Plik tymczasowy w tym samym katalogu, flush,
  fsync i `os.replace` zapewniają atomową podmianę; awaria nie niszczy starej wersji.
- `service.py`: referencje kampanii, dobór źródła, snapshot dokumentu;
  nie zależy od formatu plików i można podstawić repozytorium bazy danych.
- `templates.py`: osiem stabilnych ID z katalogu dokumentacji, wersja `0.1.0`,
  rodzina, odbiorca, poufność i wariant. To konfiguracja, nie renderer PDF.
- `api.py`: osobna przestrzeń API, obsługa błędów i ograniczenie lokalnego dostępu.
- `frontend/`: responsywny HTML/CSS/JS bez frameworka i zewnętrznych zasobów.

```text
demo-fixtures/                    # commitowalne, fikcyjne, tylko do odczytu
  trips/*.json
  campaigns/*.json
local-data/document-studio/       # ignorowane przez Git i Docker build context
  trips/*.json
  campaigns/*.json
  drafts/*.json
  assets/                        # zweryfikowane zdjęcia i metadane JSON
```

Zapis lokalnej edycji fixture'a tworzy nakładkę pod tym samym ID. Restart nie
kopiuje fixture'ów i nie nadpisuje zmian. Uszkodzona lokalna wersja daje błąd 503;
aplikacja nie ukrywa uszkodzenia przez odczyt starszego fixture'a. Niepoprawne ID,
rozbieżność ID z nazwą pliku i wyjście poza katalog są odrzucane.
Ścieżka domyślna jest liczona względem repozytorium; zmienna
`DOCUMENT_STUDIO_DATA_PATH` pozwala wskazać inny katalog trwały.

Zapis używa rewizji i blokady w procesie: stara rewizja daje 409. Uruchamiaj
**jeden proces Uvicorn (bez `--workers`)**. To lokalny edytor, bez transakcji
między plikami i bez gwarancji równoczesnych zapisów z wielu procesów.
`schema_version=1` rezerwuje miejsce pod późniejsze migracje; migratora jeszcze nie ma.

## API

Wspólny prefiks: `/api/document-studio`.

| Metoda | Ścieżka | Działanie |
|---|---|---|
| GET | `/templates` | Katalog ośmiu typów |
| GET, POST | `/trips` | Lista / utworzenie wycieczki |
| GET, PUT | `/trips/{id}` | Odczyt / pełny zapis z bieżącą rewizją |
| GET, POST | `/campaigns` | Lista / utworzenie kampanii |
| GET, PUT | `/campaigns/{id}` | Odczyt / zapis kampanii i kontrola referencji |
| GET, POST | `/drafts` | Lista / utworzenie snapshotu |
| GET | `/drafts/{id}` | Odczyt dokumentu roboczego |

Nowy Trip wymaga `title`; domyślnie ma zero dni. Gdy przekazujesz dni, przekaż też
zgodne `duration_days`. POST nadaje ID, jeśli go brak. PUT wymaga zgodnego ID ścieżki
i obiektu oraz aktualnej `revision`. Nowy Campaign wymaga `title` i niepustej
listy `items: [{trip_id, short_hook?, date_range_or_label?, highlights?}]`.
Wszystkie referencje muszą istnieć. Kampanie są przeglądane w UI; tworzenie
i edycja ich konfiguracji są obecnie dostępne przez API.

Przykładowe body POST `/drafts`:

```json
{
  "template_id": "offer.private",
  "source_type": "trip",
  "source_id": "demo-iceland",
  "layout_variant": "standard",
  "editorial_notes": "Do opracowania przez autora"
}
```

Marketing wymaga `source_type=campaign`, ID kampanii oraz jednego z wariantów
marketingowych. Snapshot zachowuje wersję źródła i kopie wszystkich wycieczek
kampanii. Notatki wewnętrzne dni są usuwane ze snapshotów `public` i `client`.
Status dokumentu pozostaje `draft`; zapis nie oznacza publikacji ani zatwierdzenia.

## Dostęp lokalny

Backend sprawdza adres połączenia, Host (`localhost`, `127.0.0.1`, `::1`), Origin
i nagłówki proxy, również dla CSS/JS. Odrzuca ruch z obcych originów i proxy.
Nie korzysta z nagłówków forwardowanych do uznania klienta za lokalnego.
Compose jawnie włącza `DOCUMENT_STUDIO_DOCKER_LOCAL=1`, aby dopuścić prywatny
adres mostu Dockera; nadal wymaga lokalnego Host i odrzuca nagłówki proxy.
Ta opcja jest przeznaczona wyłącznie dla dostarczonego bindu `127.0.0.1`.
Istniejący Caddy nie ma reguł udostępniających panel ani jego API.
Pliki JSON i assety użytkownika nie są montowane jako publiczny StaticFiles.

## Weryfikacja

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m playwright install chromium
.venv\Scripts\python.exe tests/browser_document_studio_smoke.py
docker compose config --quiet
```

Test przeglądarkowy uruchamia własny serwer na wolnym porcie i używa katalogu
tymczasowego. Sprawdza bibliotekę, 15 dni, dodawanie/usuwanie dni i atrakcji,
zapis, dokumenty, kampanię, polskie znaki, escapowanie HTML, ekran telefonu
i trwałość po rzeczywistym restarcie procesu. Nie wywołuje zewnętrznych usług.
Zrzuty zapisuje w ignorowanym `local-data/document-studio-qa/`.

Weryfikacja DEMO-01 wykonana 24.10.2026: **147 testów pytest przeszło**, w tym istniejące
regresje planera, viewera i WAHA; jedno ostrzeżenie deprecacji Starlette/AnyIO.
Test przeglądarkowy przeszedł na Chromium. `docker compose config --quiet`
i budowa obrazu API zakończyły się powodzeniem. Dodatkowy test odizolowanego
kontenera potwierdził lokalny dostęp do panelu, obecność fixture'ów, zapis JSON
na hoście przez bind mount i odczyt po usunięciu oraz ponownym utworzeniu kontenera.

## Zakres i kolejne kroki

To szybkie demo fundamentów na podstawie `docs/document-system/`, zwłaszcza
aktualnego `system-data/`. Dokumentacja docelowa opisuje szerszy produkt.
`marketing.collection` ma dwa układy i edytor kampanii. DEMO-03 dodaje edycję
oferty i rozpiski podstawowej, komunikaty braków oraz wspólny podgląd/PDF.
Pozostałe typy dokumentów pokazują snapshoty danych. Nie ma zatwierdzania,
logowania, chmury ani integracji z planerem.
Nie ma modeli uczestników, rezerwacji i sekretów. Programy demo są fikcyjne.

Kolejne prace: pola i walidacja `pilot.basic` oraz `offer.private`, edytowalne
pola dokumentów z rewizjami, zatwierdzony branding i pełne metadane licencji.
Centralną bazę i kontrolę dostępu wdrożyć dopiero przy przejściu do współdzielonego środowiska.
