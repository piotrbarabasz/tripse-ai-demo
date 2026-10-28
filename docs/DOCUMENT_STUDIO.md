# TRIPSE Document Studio — funkcjonalne DEMO lokalne

## Katalog i edytor sekcyjny — implementacja lokalna 2026-10-28

Z Hubu otwórz **`/documents/demo#templates`**. Katalog pokazuje trzy grupy:
cztery oferty (`offer.private`, `offer.self_guide`, `offer.school`, `offer.incentive`),
trzy materiały pilotów (`pilot.basic`, `pilot.advanced`, `pilot.knowledge`) oraz
`marketing.collection` z wariantami `new_trips` i `theme_collection`.
Wszystkie osiem ID ma działający edytor, zapis snapshotu i podgląd/PDF roboczy.
Zmiany są przygotowane lokalnie; nie zostały wdrożone na DEV/PROD.

### Instrukcja pracy dla Adriana

1. Wybierz kafelek i, dla marketingu, wariant. W kolejnym ekranie typ jest już
   zapamiętany. Wskaż wycieczkę/kampanię albo wybierz utworzenie nowej.
   Nowa wycieczka otrzymuje wybraną liczbę dni z jawnym „do opracowania”.
   Nowa kampania wymaga co najmniej jednej wycieczki z biblioteki.
2. Edytor otworzy niezależny draft z domyślnymi sekcjami oraz danymi snapshotu.
   Uzupełnij pola rodzaju dokumentu. Nieznane terminy, kwoty i odległości
   pozostają puste, a podgląd pokazuje „Do ustalenia”.
3. W „Treść i kolejność sekcji” zmień tytuł/treść, dodaj tekst, listę, zdjęcie,
   galerię, tabelę, wyróżnienie lub sekcję dzienną. Tabelę wpisuj wierszami,
   oddzielając komórki tabulatorem; nagłówki wpisuj w osobnych wierszach.
   Przesuwaj przyciskami „W górę / W dół”. Dodatkowe sekcje można usuwać;
   domyślne można ukrywać i przywracać. Wymagane braki nadal widnieją w walidacji.
4. Pola źródłowe sekcji domyślnych edytuj w formularzu powyżej, a jej dodatkowe
   uwagi bezpośrednio w sekcji. Program bazuje na snapshotach i nadpisaniach
   dokumentu. Zmiana draftu nie zmienia Trip ani drugiego dokumentu.
5. Zdjęcia wybieraj z biblioteki lub wgraj własny JPG/PNG/WebP z potwierdzeniem
   praw. Kadrowanie sekcji: x/y 0–100, zoom 1–3. Brak zdjęcia daje placeholder.
6. Kliknij „Zapisz draft” (marketing: „Zapisz zmiany”), następnie odśwież stronę
   i otwórz dokument ponownie przez „Dokumenty robocze” → „Edytuj dokument”.
   Rewizja rośnie; 409 oznacza konflikt — odczytaj najnowszą wersję, nie nadpisuj jej.
7. Podgląd aktualizuje się po edycji. „Podgląd / PDF” otwiera zapisany dokument;
   wybierz A4, skalę 100%, tła, bez nagłówków przeglądarki. Marketing ma też
   układ 1080×1350. Długie teksty/tabele są dzielone na bloki i strony.

### Pola typów i granice publikacji

- Self-Guide zawsze ma widoczne oznaczenie **bez pilota na miejscu**. Zakres
  organizacji, samodzielne ustalenia, materiały i wsparcie uzupełniasz ręcznie;
  briefing online jest miejscem do uzgodnienia, bez gwarancji usługi.
- Szkoła: wiek/liczebność, odpowiedzialność opiekunów i cele trzech filarów
  **Edukacja / Przyroda / Integracja**, powiązane z dniem i atrakcją.
- Incentive: wyróżniony hotel, standard/nazwa, lokalizacja, pokoje, udogodnienia,
  przestrzenie wspólne i konferencyjne, zdjęcia i status ze źródłem potwierdzenia.
  Integracja i szkolenia są opcjonalne.
- Basic/advanced współdzielą `PilotData` i `OperationalEntry` dla lotów, noclegów,
  kontaktów i harmonogramu. Advanced dodaje sekcję logistyki każdego dnia:
  datę, trasę, czasy/dystanse/przewyższenie, strefę, referencję istniejącego noclegu,
  notatki i plan B. Zdarzenia drukują się chronologicznie według czasu ze strefą.
- Knowledge: trzy części każdego dnia (atrakcje/kontekst/narracja), tylko miejsca
  programu, ręczne opisy, dokładne źródła i daty sprawdzenia. Status `verified`
  wymaga źródeł z datami. Niezweryfikowane treści są tak oznaczone w PDF.
- Marketing używa dotychczasowego edytora i jednego renderera. Edycja draftu
  zmienia snapshot kampanii, nie kampanię źródłową; można zmieniać kolejność,
  dodawać/usuwać kierunki, kadrować zdjęcia, wpisać opcjonalnego prowadzącego
  oraz dodawać sekcje promocyjne.

Każdy nowy PDF ma oznaczenie wersji roboczej. Dla nowych typów możliwy jest PDF
roboczy pomimo braków biznesowych, z zachowaniem uwag i `data-final-valid`.
Nie jest to ścieżka zatwierdzenia/publikacji. `offer.private` zachowuje wcześniejszą
blokadę ceny/CTA: wpisz prawidłową wycenę albo świadomie wybierz `concept_only`.
Dotychczasowe blokady podstawowej rozpiski i marketingu pozostają. Błąd układu
nadal blokuje przycisk druku. Nie wprowadzono wielorolego workflow akceptacji.

### Modele, API i kompatybilność

`DocumentDraft.sections` zawiera walidowane `DocumentSection`: ID, rodzaj, rolę
szablonu, tytuł, treść, kolejność, widoczność i opcjonalny dzień; listy, zdjęcia,
tabele, logistyka i wiedza mają własne pola strukturalne. `offer_data` służy
wszystkim ofertom; `offer_details` dodaje pola ich wariantów. `pilot_data` jest
wspólne dla basic/advanced; knowledge nie przyjmuje danych rezerwacyjnych.
`Campaign` i `CampaignItem` przyjmują opcjonalne `leader`.

Zachowano istniejące URL-e i repozytoria JSON/GCS. `PUT /api/document-studio/drafts/{id}`
przyjmuje dodatkowo `sections`, `offer_details`, a dla marketingu edytowalny
`campaign_snapshot`. ID kampanii, typ, poufność i źródłowy Trip są niezmienne;
nowo dodane kierunki kampanii są snapshotowane przez serwis z bezpiecznej projekcji.
Pola pominięte w PUT nie są zerowane przez starszego klienta.
`POST /trip-documents/preview` i `/validate` obsługują cały katalog; preview przyjmuje
`output_format`. `POST /api/document-studio/trip-documents/initialize` przygotowuje
sekcje starego draftu bez zapisu; nadal obowiązuje autoryzacja routera.

Nowe szablony mają wersję **0.4.0**, a wersja schematu pozostaje 1 dzięki polom
opcjonalnym. Brak `sections` w starym JSON oznacza legacy; odczyt nie przepisuje
pliku. Stare private/basic/marketing zachowują podgląd; dawniej katalogowe typy
otrzymują domyślne sekcje w podglądzie. Pierwszy jawny zapis sekcji podnosi wersję
szablonu. Nie wolno zamienić sekcyjnego dokumentu z powrotem na `sections: null`.
Wymagania pochodzą z definicji szablonu, nie z edytowalnej flagi użytkownika.

Oferty i marketing snapshotują wyłącznie pola klientowskie; nigdy nie pobierają
`PilotData`, prywatnych źródeł atrakcji ani notatek wewnętrznych. Basic/advanced
pozostają `internal_restricted`, knowledge `internal`; istniejąca autoryzacja,
prywatne assety i kontrola zapisu pozostają bez zmian. Ręcznie wpisany tekst nadal
wymaga przeglądu człowieka przed przekazaniem klientowi.

### Rozszerzanie i testowanie

Nowy szablon dodaj do `templates.py` wraz z konfiguracją `SectionSpec`; określ
wymagane role, bezpieczne domyślne dane w `sections.py`, pola Pydantic i ich
kontrolki. Nowy rodzaj sekcji wymaga typu w `DocumentSection`, walidacji,
prezentacji w `rendering/sections.py` i kontrolek `section-editor.js`.
Nie dodawaj arbitralnego HTML ani równoległego magazynu dokumentów.

Testy: `python -m pytest -q`; przeglądarka:
`python tests/browser_document_studio_smoke.py` (obejmuje też cały katalog),
`python tests/browser_trip_documents_smoke.py`,
`python tests/browser_marketing_smoke.py`, `python tests/browser_cloud_demo_smoke.py`.
PDF-y i zrzuty katalogu: ignorowany `local-data/studio-catalog-qa/`.
Dane QA są fikcyjne; nie użyto przesłanych materiałów klientów ani zewnętrznych usług.

### Do dalszego uzgodnienia

Z Adrianem: obowiązkowe pola finalnych ofert, dokładny zakres wsparcia Self-Guide,
zasady cen szkolnych, standard rozpisek i odpowiedzialność za weryfikację źródeł,
branding/licencje zdjęć, retencja i formalna akceptacja treści. AI research, DOCX,
rezerwacje, wysyłka, briefing online i nowe role pozostają poza tą iteracją.
Poniższe instrukcje opisują zachowane wcześniejsze ścieżki i historię modułu.

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
Automated private DEV/PROD deployment is accepted as of 2026-10-28; individual
human IAP login and restore testing remain unverified. See
[release evidence](RELEASE_2026_10_28.md);
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

## Weryfikacja iteracji katalogu (2026-10-28)

- Pełne pytest: **664 passed**, jedno zastane ostrzeżenie Starlette/AnyIO.
- `browser_document_studio_smoke.py`: biblioteka i restart procesu oraz katalog
  wszystkich ośmiu ID / obu wariantów marketingu; 2/10/15 dni, edycja sekcji,
  wielokrotny zapis, zdjęcia, mobilny układ i dziewięć rzeczywistych PDF A4.
  Tekst początku i końca długiej sekcji zachowany w odczycie PDF; brak overflow.
- `browser_trip_documents_smoke.py`: zachowane private/basic, sześć PDF,
  cena/concept_only, lokalne godziny i izolacja prywatnych danych.
- `browser_marketing_smoke.py`: osiem PDF, 1/3/8 kierunków, oba warianty,
  formaty A4/social, zdjęcia, kadry, brak CTA i restart procesu.
- `browser_cloud_demo_smoke.py` i `browser_hub_smoke.py`: regresje nawigacji,
  edytorów i dotychczasowego planera/symulatora. Cloud QA używa prywatnych
  adapterów z fake stores, nie rzeczywistych zasobów GCP.
- Sprawdzono składnię JS, offline kontrakty CI oraz Markdown/ADR i whitespace.
  Nie wykonywano deploymentu, zmiany IAM, migracji danych ani wywołań AI.
