# Audyt repozytorium — 2026-10-25

## Zakres i wiarygodność

Przegląd lokalnej gałęzi `master`, HEAD
`f9035e5ff16c293b8fddbe33938a29b96eb6ca87`, przed dodaniem ADR i rejestru prac.
Drzewo robocze na początku było czyste. Zbadano kod, konfigurację i dokumenty
wymienione niżej oraz wszystkie **5 commitów dostępnych w lokalnej historii**.
Nie pobierano historii zdalnej, PR, zgłoszeń, telemetrii, rachunków ani ewidencji czasu.
Brak danych nie oznacza, że takie materiały nie istnieją poza tym checkoutem.

Kategorie dowodów:

- **Fakt implementacji:** widoczny kod/konfiguracja, ze wskazanym plikiem i symbolem.
- **Uzasadnienie udokumentowane:** wyraźny zapis celu/ograniczenia w dokumentacji.
- **Wniosek:** interpretacja audytu, nie historyczna wypowiedź autora.
- **Plan:** opis systemu docelowego lub przyszłej pracy; nie dowód implementacji.

Nie uruchamiano aplikacji ani jej testów w tym zadaniu dokumentacyjnym. Wyniki
83/147/167/176 testów podane w dotychczasowych instrukcjach to raporty historyczne,
nie nowe pomiary ani potwierdzenie produkcyjnych integracji live.

## Moduły i aktualny zakres

| Moduł | Stan widoczny w kodzie | Dowody |
|---|---|---|
| FastAPI / wejście HTTP | Jedna aplikacja, routery planera, viewer, demo i studio | [main.py](../../app/main.py), `create_app` |
| Planer live/mock | OpenAI structured output, rozpoznanie Places, Routes; live 1–2 dni, do 8 lokalizacji, ostrzeżenia | [planning.py](../../app/planning.py), `TripPipeline`; [modele](../../app/planning_models.py), `Candidate`; [providerzy](../../app/planning_providers.py); [instrukcja](../PLANNING.md) |
| SQLite / worker | Joby, deduplikacja, tokeny viewerów i kolejka wiadomości; osobny polling worker i odzyskiwanie przerwanych prac | [db.py](../../app/db.py), `Database`; [worker.py](../../app/worker.py), `main` |
| WhatsApp | Adapter WAHA, filtrowanie/deduplikacja webhooków i ponawianie wysyłki; realna sesja niepotwierdzona w dokumentacji | [waha.py](../../app/waha.py), [messaging.py](../../app/messaging.py), [WAHA.md](../WAHA.md) |
| Viewer / udostępnienie planu | HTML/JS, tokeny z terminem ważności, mapy dla planów; to nie publiczne udostępnienie studia | [viewer.py](../../app/viewer.py), [sharing.py](../../app/sharing.py), [VIEWER.md](../VIEWER.md) |
| Demo offline | Fikcyjne scenariusze, symulator rozmowy i lokalna mapa | [demo.py](../../app/demo.py), [demo_data.py](../../app/demo_data.py), [MOCK_DEMO.md](../MOCK_DEMO.md) |
| Dane Document Studio | Własne Trip/Days/Stops, kampanie wielu wycieczek, snapshoty i pola dokumentów; bez adaptera planera | [modele](../../app/document_studio/models.py), [serwis](../../app/document_studio/service.py) |
| Zapis studia | JSON, lokalne nakładki na fixture'y, atomowa podmiana, rewizje; jeden proces API | [repository.py](../../app/document_studio/repository.py), `JsonRepository`; [DEMO-01](../DOCUMENT_STUDIO.md) |
| Szablony / rendering | 8 zarejestrowanych ID; pełne generatory: marketing.collection, offer.private, pilot.basic | [templates.py](../../app/document_studio/templates.py), [renderer](../../app/document_studio/rendering/__init__.py), [renderer podróży](../../app/document_studio/rendering/trip_documents.py) |
| UI / PDF | HTML/CSS/JS, edytory kampanii i dwóch typów draftów, A4 i social dla marketingu, druk w przeglądarce | [frontend](../../app/document_studio/frontend/index.html), [print-export.js](../../app/document_studio/frontend/print-export.js), [DEMO-02](../MARKETING_COLLECTION.md), [DEMO-03](../TRIP_DOCUMENTS.md) |
| Zdjęcia i kontrola treści | Lokalne JPG/PNG/WebP, dekodowanie i usunięcie metadanych; lista dozwolonych pól oferty, walidacja braków | [assets.py](../../app/document_studio/assets.py), [trip_documents.py](../../app/document_studio/trip_documents.py), [marketing.py](../../app/document_studio/marketing.py) |
| Uruchomienie | Jeden obraz aplikacji, Compose: API/worker i opcjonalne WAHA/Caddy; bind mount studia oddzielny od wolumenu SQLite | [Dockerfile](../../Dockerfile), [compose.yaml](../../compose.yaml), [Caddyfile](../../Caddyfile), [DEV_DEPLOY.md](../../DEV_DEPLOY.md) |

Osiem ID nie oznacza ośmiu gotowych generatorów. `offer.self_guide`, `offer.school`,
`offer.incentive`, `pilot.advanced`, `pilot.knowledge` są w katalogu, lecz nie mają
pełnej ścieżki edytor–renderer–PDF. Klasa `public` w metadanych marketingu nie publikuje dokumentu.

## Co wynika z historii Git

| Commit | Data zapisana w Git | Potwierdzony zakres |
|---|---|---|
| `2e291a90577d6281824ec798a7b20827bf6b4a6b` | 2026-10-22 | Pierwszy commit zawiera już planer, SQLite, worker, WAHA, viewer, konfigurację i testy; nie rozdziela tasków 01–05 |
| `0899d333ebb19fb843ef37150b8c9b16bebdc04a` | 2026-10-24 | Rozbudowa mocka, symulatora, mapy i powiązanych testów |
| `5ea86655c0eae87f2033c11dca9d03f360090e46` | 2026-10-24 | Dodanie specyfikacji systemu dokumentów; nie implementacji Document Studio |
| `429991676bfabffe1c2b700386b15dfea874d663` | 2026-10-24 | Dodanie dokumentów pod `system-data`; sam komunikat o zmianie lokalizacji nie dowodzi osobnej migracji aplikacji |
| `f9035e5ff16c293b8fddbe33938a29b96eb6ca87` | 2026-10-25 | Łączne dodanie implementacji i instrukcji DEMO-01–03; brak rozdzielnych commitów tych etapów |

Można odtworzyć przez `git log --all`, `git show --stat HASH` i
`git log -- app/document_studio`. Dokumenty DEMO raportują weryfikację 24.10.2026,
a commit zawierający implementację jest z 25.10.2026. Są to różne rodzaje dat;
nie ustalamy z nich daty decyzji, czasu wykonania ani liczby godzin pracy.
Nie ma dostępnych dowodów akceptacji ADR ani powiązanych PR.

## Decyzje i poziom potwierdzenia

| ADR | Potwierdzona implementacja | Udokumentowany powód | Wniosek / niepotwierdzone |
|---|---|---|---|
| [0001](../adr/0001-modular-fastapi.md) | Router studia w tym samym FastAPI, odrębny zapis i logika | Modułowy rozwój bez przebudowy planera w specyfikacji | Mniejsza liczba usług to wniosek; brak zmierzonej oszczędności |
| [0002](../adr/0002-local-json-storage.md) | JsonRepository, fixture'y, lokalne dane i bind mount | Lokalny zakres i trwałość w DEMO-01 | Brak zatwierdzonego docelowego magazynu i skali |
| [0003](../adr/0003-document-snapshots.md) | Trip/Campaign, snapshoty i dozwolone pola oferty | Jedne dane → wiele dokumentów, niezależna redakcja | Brak wymaganej polityki pełnej historii i retencji |
| [0004](../adr/0004-controlled-html-browser-pdf.md) | Kontrolowane komponenty, paginacja, window.print | DEMO-02 definiuje przeglądarkowy eksport; specyfikacja zabrania HTML od LLM | Brak benchmarku kosztów eksportu serwerowego |
| [0005](../adr/0005-local-only-studio.md) | local_only, localhost bind, brak reguł proxy studia | DEMO-01/03 ograniczają zakres do lokalnego narzędzia | Brak akceptacji bezpieczeństwa dla realnych danych/produkcji |
| [0006](../adr/0006-template-registry-shared-components.md) | Rejestr ID, shell, foto, tokeny | Katalog i design system opisują wspólne elementy | Branding jest roboczy; brak zatwierdzonego CMS/brand booka |
| [0007](../adr/0007-sqlite-single-worker.md) | SQLite, osobny pojedynczy worker | Minimum demo poza HTTP w specyfikacji i README | Brak profilu obciążenia i finansowego porównania brokerów |

Wszystkie statusy pozostają `proposed`. Wdrożenia i obecność commitów nie zastępują
potwierdzenia właściciela. Ustalone cele demo nie dowodzą akceptacji dla produkcji.

## Dług techniczny i ograniczenia

Poniższe ID są identyfikatorami audytu, nie fikcyjnymi zgłoszeniami w zewnętrznym trackerze.

| ID | Obserwacja i dowód | Przyszła praca / obszar kosztowy |
|---|---|---|
| DEBT-01 | `JsonRepository` ma RLock i rewizję w jednym procesie, brak transakcji wielu plików oraz migratora schema_version | Współbieżność, migracje, centralny magazyn — COST-01 |
| DEBT-02 | Zapis nadpisuje plik bieżącej rewizji; przeglądarka zapisuje PDF poza aplikacją; brak historii rendererów | Historia, retencja, archiwum eksportów — COST-01/03 |
| DEBT-03 | `local_only` i konfiguracja sieci zamiast tożsamości, ról i audytu | Kontrola dostępu przed współdzielonym wdrożeniem — COST-02/06 |
| DEBT-04 | PDF zależny od stanowiska, systemowe fonty, roboczy branding; brak eksportu PNG | Branding, odtwarzalność i docelowe formaty — COST-03 |
| DEBT-05 | `AssetStore` używa konkretnej ścieżki repozytorium; brak retencji/usuwania assetów; deklaracja praw nie weryfikuje licencji | Cykl życia, metadane praw i magazyn zdjęć — COST-04 |
| DEBT-06 | Są statusy/źródła i walidacja podstawowa; brak pełnej kontroli konfliktów harmonogramu, DST, dostępności usług i sekretów w wolnym tekście | Walidacja i przegląd treści — COST-02/07 |
| DEBT-07 | `Candidate.day` ≤2, `TripPipeline` akceptuje 1–2 dni; studio ma dłuższe Trip, bez adaptera | Import i integracja kontraktów — COST-05 |
| DEBT-08 | 5 ID katalogowych nie ma pełnych generatorów; brak akceptacji wieloosobowej, języków i CMS | Zakres następnych typów i workflow — COST-07 |
| DEBT-09 | Specyfikacja opisuje stan historyczny i system docelowy oraz zawiera stare nazwy katalogów w zwykłym tekście; DEMO-01 opisuje rejestr 0.1.0 mimo nowszych wersji w kodzie. Wykryte stare odnośniki `data/` poprawiono w tym zadaniu | Dalsze porządkowanie dokumentacji i utrzymanie zgodności — COST-07 |
| DEBT-10 | `/health` sprawdza SQLite, nie liveness workera ani JSON; live OpenAI/Maps/WhatsApp i publiczny DEV nie są potwierdzone raportami wdrożenia | Monitoring, testy środowiska i operacje — COST-05/06 |
| DEBT-11 | Requeue przerwanych zadań może ponowić płatne wywołania; potwierdzenie wysyłki po awarii może się powtórzyć | Idempotencja, limity wydatków, protokół retry — COST-05 |

To lista obserwacji, nie autoryzacja implementacji ani dowód wystąpienia incydentu.
Szczegóły kosztowe i pytania do TRIPSE: [estimates.md](estimates.md).

## Plany, których nie wolno przedstawiać jako wdrożenia

- GCP/Cloud Run, Cloud Tasks, Cloud Storage i wybór Firestore/PostgreSQL:
  [architektura GCP](../document-system/architecture/gcp-deployment.md) jest propozycją.
- Logowanie, role, wieloosobowa akceptacja i uprawnienia per dokument:
  [security.md](../document-system/architecture/security.md) opisuje wymagania docelowe.
- Serwerowy renderer, kolejka eksportów, `DocumentExport`, hashe i autoryzowane
  pobrania: [architektura](../document-system/architecture/system-architecture.md).
- Pozostałe generatory, wiedza pilota ze źródłami, adapter planera, importy i AI
  research: [roadmapa](../document-system/development/roadmap.md).
- Kryteria publikacyjnego MVP/V1 w [acceptance-criteria.md](../document-system/development/acceptance-criteria.md)
  są wymaganiami docelowymi, nie potwierdzeniem ich wykonania w obecnym demo.

## Kontrole tego zadania

Sprawdzenie metadanych YAML, dziewięciu sekcji ADR, numeracji, referencji ADR/task,
CSV i pustych pól finansowych oraz lokalnych odnośników w nowej dokumentacji.
Kontrola zmian Git ma potwierdzić brak zmian kodu, konfiguracji i zależności.
Odnośniki internetowe i lokalne adresy uruchomieniowe nie są testowane jako deployment.
Poprawiono 26 zastanych odnośników w 15 plikach specyfikacji z `data/` na
istniejące `system-data/`. Jest to naprawa ścieżek, nie zmiana planowanego zakresu
ani uznanie historycznych propozycji za wdrożone funkcje. Pozostałe niespójności
aktualności opisów są odnotowane jako DEBT-09.

Pliki z korektą odnośników, względem `docs/document-system/`:

- `README.md`;
- `architecture/security.md`, `architecture/system-architecture.md`;
- `general/document-workflow.md`, `general/overview.md`, `general/template-catalog.md`;
- `templates/marketing/collections.md`;
- `templates/offers/incentive.md`, `templates/offers/private.md`,
  `templates/offers/school.md`, `templates/offers/self-guide.md`;
- `templates/pilots/advanced.md`, `templates/pilots/basic.md`, `templates/pilots/knowledge.md`;
- `development/acceptance-criteria.md`.

Wynik kontroli 25.10.2026:

- 7 ADR-ów: poprawny YAML, ciągła numeracja, dziewięć wymaganych sekcji,
  statusy `proposed` i zgodne powiązania task/ADR/rejestr.
- 8 wierszy worklogu: zgodny nagłówek CSV, istniejące commity, puste pola godzin
  i kosztów. Nie wprowadzono pomiarów ani estymacji bez źródła.
- 47 plików Markdown: parsowanie oraz 262 odnośniki lokalne bez brakujących celów;
  w podzbiorze nowego standardu/rejestru i głównego README sprawdzono 163 odnośniki.
- Porównanie 15 zmienionych plików specyfikacji z HEAD potwierdziło wyłącznie
  26 podmian ścieżek odnośników; nie zmieniono historycznej treści merytorycznej.
- Statycznie sprawdzono m.in. 8 ID szablonów, wersję oferty 0.3.0, limit
  planera, podpięcie `local_only` i atomową podmianę w repozytorium.
- `git diff --check` bez błędów. Zmieniono wyłącznie 29 plików dokumentacji
  (w tym CSV); kod, testy, zależności i konfiguracja aplikacji są identyczne z HEAD.

To kontrola dokumentacji, nie ponowne wykonanie testów runtime ani audyt bezpieczeństwa.

## Pełna lista plików tego zadania

Nowe pliki i zmiany względem wskazanego HEAD; żaden plik aplikacji nie jest na liście:

```text
README.md
docs/adr/README.md
docs/adr/template.md
docs/adr/0001-modular-fastapi.md
docs/adr/0002-local-json-storage.md
docs/adr/0003-document-snapshots.md
docs/adr/0004-controlled-html-browser-pdf.md
docs/adr/0005-local-only-studio.md
docs/adr/0006-template-registry-shared-components.md
docs/adr/0007-sqlite-single-worker.md
docs/tracking/README.md
docs/tracking/worklog.csv
docs/tracking/estimates.md
docs/tracking/repository-audit.md
docs/document-system/README.md
docs/document-system/architecture/security.md
docs/document-system/architecture/system-architecture.md
docs/document-system/development/acceptance-criteria.md
docs/document-system/general/document-workflow.md
docs/document-system/general/overview.md
docs/document-system/general/template-catalog.md
docs/document-system/templates/marketing/collections.md
docs/document-system/templates/offers/incentive.md
docs/document-system/templates/offers/private.md
docs/document-system/templates/offers/school.md
docs/document-system/templates/offers/self-guide.md
docs/document-system/templates/pilots/advanced.md
docs/document-system/templates/pilots/basic.md
docs/document-system/templates/pilots/knowledge.md
```
