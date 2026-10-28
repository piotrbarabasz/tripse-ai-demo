# DEMO-03 — offer.private i pilot.basic

Aktualizacja DOC-PDF-003 (lokalna, bez wdrożenia): pełne akapity, listy i tabele
dzieli teraz przeglądarka według rzeczywistego układu. Nagłówki tabel są powtarzane,
a bardzo wysokie komórki kontynuowane bez kopiowania godzin/statusów. Kontekst
dnia i klasyfikacja pozostają na kolejnych stronach. Szczegóły, macierz PDF i
artefakty do oceny: [DOC-PDF-003](audits/DOC_PDF_003.md).

Aktualizacja implementacji lokalnej 2026-10-28: pełny katalog ośmiu ID ma wspólny
edytor sekcji i podgląd; nowe dokumenty mają wersję szablonu 0.4.0. Instrukcja
aktualnej pracy, API, kompatybilności i rozszerzania: [Document Studio](DOCUMENT_STUDIO.md).
Poniższy scenariusz DEMO-03 i wyniki opisują pierwotne private/basic. Zachowano je
jako działającą ścieżkę oraz historię; blokada ceny private nie została osłabiona.

## Uruchomienie

```powershell
docker compose up --build -d api
```

Panel: **http://localhost:8000/documents/demo**. Dokumenty nie wymagają workera,
WhatsApp ani kluczy API. Natywnie: Python 3.12, instalacja zależności i Uvicorn:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
$env:PLANNING_MODE = "mock"
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Używaj jednego procesu API. JSON i zdjęcia są w dotychczasowym
`local-data/document-studio/`, ignorowanym przez Git. Compose zachowuje bind mount.

## Scenariusz demonstracji TRIPSE

1. Otwórz wycieczkę **Islandia** (10 dni). Dane pochodzą z jednego `Trip`.
2. Wybierz **Wyjazd indywidualny**, zaznacz **Wypełnij fikcyjnym przykładem DEMO**
   i kliknij **Zapisz dokument roboczy**. Przykład jest dostępny dla Islandii;
   bez zaznaczenia nowe dokumenty mają puste pola, bez wymyślonej ceny/logistyki.
3. Kliknij **Edytuj dokument**. Zmień tytuł, zalety, zakwaterowanie, świadczenia
   oraz opis pierwszego dnia. Wybierz zdjęcie z istniejącej lokalnej biblioteki
   lub wgraj własny legalny JPG/PNG/WebP. Brak zdjęcia daje oznaczony placeholder.
4. Sprawdź **FIKCYJNĄ CENĘ DEMO** i jej założenia. Nie jest to cena wycieczki.
   Dla własnych danych wpisz wycenę organizatora ze źródłem albo świadomie zaznacz
   **wersję koncepcyjną BEZ WYCENY**. Brak kwoty bez tego wyboru blokuje PDF.
5. Kliknij **Zapisz draft** — rewizja wzrośnie. Kliknij **Podgląd / PDF**,
   następnie w nowym oknie **Zapisz jako PDF**. Wybierz A4, skalę 100%, grafikę
   tła, wyłącz nagłówki i stopki przeglądarki. Podgląd pokazuje też listę braków.
6. Wróć do tej samej Islandii i wybierz **Rozpiska podstawowa**, z fikcyjnym
   przykładem. Otwórz edytor, zmień lokalną godzinę harmonogramu, status noclegu,
   kontakt i sprawy otwarte. Status „Potwierdzone” wymaga wpisanego źródła.
7. Zapisz i wydrukuj drugi PDF. Rozpiska ma tabele, lokalne godziny ze strefami,
   numerację dni i oznaczenie **WEWNĘTRZNE** na każdej stronie. Oferta ma okładkę,
   program i cenę, bez prywatnej logistyki i notatek pilota.
8. Zrestartuj API i otwórz oba dokumenty z **Dokumenty robocze**. Edycja oferty
   nie zmienia `Trip`, rozpiski ani innych snapshotów. Kampanie marketingowe
   z DEMO-02 nadal działają swoim edytorem i tym samym rendererem stron.

Przykład w `demo-fixtures/document-presets/iceland.json` zawiera wyłącznie
fikcyjne dane. Kontakty mają domenę `example.invalid`; pilot jest fikcyjną rolą,
brak list uczestników, rzeczywistych rezerwacji i PIN-ów. Harmonogram/noclegi
przykładowe są tworzone względem dni snapshotu po jawnym wyborze użytkownika.
Statusy w tym przykładzie są demonstracją prezentacji, nie potwierdzeniem usług.

## Dane i API

Model `Trip` nie został rozszerzony o rezerwacje ani ofertę. `DocumentDraft`
zachowuje `trip_snapshot`, `template_id`, `template_version`, `revision`,
`created_at` i `updated_at`. Nowe pola dokumentu:

- `date_label` — redakcyjny opis terminu; puste pole pokazuje daty Trip albo brak.
- `day_overrides[]` — `day_id`, własny tytuł i opis; puste wartości dziedziczą snapshot.
- `offer_data` — we wszystkich ofertach: podsumowanie, zalety, publiczny opis
  noclegów/transportu, listy świadczeń, cena i założenia, publiczne CTA, zdjęcia.
- `pilot_data` — w `pilot.basic` i `pilot.advanced`: pilot, liczebność, zbiórka, loty, transfery,
  noclegi, rezerwacje atrakcji, harmonogram, kontakty, sprawy otwarte i notatki.

Zdarzenia operacyjne mają opcjonalne powiązanie z dniem, lokalny początek/koniec,
strefy IANA, status (`unknown`, `planned`, `confirmed`), źródło, szczegóły
i opcjonalny numer rezerwacji. Nie istnieje pole PIN ani kod dostępu.
Model odrzuca nieznane strefy, godziny bez strefy, koniec przed początkiem po
uwzględnieniu stref i potwierdzenie bez źródła. `tzdata` zapewnia strefy też na Windows.

Istniejące endpointy zostały zachowane; prefiks `/api/document-studio`:

| Metoda | Ścieżka | Zastosowanie |
|---|---|---|
| POST | `/drafts` | Dotychczasowy kontrakt + opcjonalne `demo_example: true` |
| GET | `/drafts/{id}` | Otwarcie draftu |
| PUT | `/drafts/{id}` | Pełny zapis pól redakcyjnych z bieżącą `revision` |
| POST | `/trip-documents/validate` | `{draft: DocumentDraft}` → lista błędów/ostrzeżeń |
| POST | `/trip-documents/preview` | Ten sam kontrakt → HTML niezapisanych zmian |
| GET | `/drafts/{id}/preview` | Wspólny podgląd A4 zapisanych dokumentów |

PUT przyjmuje wyłącznie `revision`, `title`, `date_label`, `editorial_notes`,
`day_overrides`, `offer_data`, `pilot_data`, `offer_details`, `sections` i dla marketingu
`campaign_snapshot`. Nie pozwala podmienić tożsamości źródła,
szablonu, poufności ani snapshotu. Konflikt rewizji daje 409. Pola niepasujące
do typu dokumentu i błędne referencje dni są odrzucane. Zapis wersji roboczej
jest możliwy mimo braków biznesowych; blokady dotyczą eksportu.

Historyczne wersje DEMO-03: oferta i rozpiska **0.3.0**, marketing **0.2.0**;
nowe instancje sekcyjne: **0.4.0**.
Stare drafty są odczytywane z domyślnymi nowymi polami. Nie ma migracji Trip
ani zmian w modelach/API planera i jego SQLite.

## Renderowanie i poufność

Wszystkie osiem typów korzysta z `render_shell`, wspólnych tokenów, zdjęć,
escapowania tekstu, paginacji i przeglądarkowego eksportu z DEMO-02.
`rendering/trip_documents.py` dodaje okładkę, sekcje programu i tabele operacyjne.
Długie teksty są dzielone bez utraty znaków na kolejne bloki, z powtórzonym
kontekstem dnia. Zbyt duży blok wciąż blokuje druk, zamiast obcinać treść.

Strukturalna lista dozwolonych pól oferty znajduje się w `trip_documents.py`:
`OFFER_TRIP_FIELDS`, `OFFER_DAY_FIELDS`, `OFFER_STOP_FIELDS`. Projekcja od nowa
konstruuje snapshot; pomija notatki wewnętrzne i źródła/metadane przystanków.
Model `OfferData` nie przyjmuje kontaktów pilota, uczestników, numerów rezerwacji
ani PIN-ów. Nie może współistnieć z `PilotData` w ofercie. Renderer oferty
nie odczytuje logistyki pilota, wewnętrznych notatek ani źródła potwierdzenia ceny.
Redakcyjna notatka dokumentu nie jest drukowana w ofercie.

To rozdzielenie strukturalne; użytkownik odpowiada za treść wpisaną ręcznie
w publiczny opis lub CTA. System nie rozpoznaje dowolnych sekretów w wolnym tekście.
Przed rzeczywistym użyciem wymagany jest przegląd danych i treści przez autora.

Wszystkie strony, zdjęcia i API pozostają za dotychczasową kontrolą lokalnego
adresu, Host i Origin oraz blokadą proxy. Nie ma publicznych linków pilotów.
Brak noclegu jest wyraźnym ostrzeżeniem krytycznym w roboczej rozpisce; nie tworzy
fikcyjnego hotelu. Puste godziny pozostają nieustalone, nie zamieniają się w 00:00.

## Testy i QA

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m playwright install chromium
.venv\Scripts\python.exe tests/browser_document_studio_smoke.py
.venv\Scripts\python.exe tests/browser_marketing_smoke.py
.venv\Scripts\python.exe tests/browser_trip_documents_smoke.py
docker compose config --quiet
docker compose build api
```

QA używa własnego serwera i tymczasowego JSON/SQLite; nie edytuje danych użytkownika.
Nowy skrypt sprawdza pełną ścieżkę UI z Islandii do dwóch dokumentów, zapis,
reotwarcie po restarcie, mobilny ekran, godziny, rewizje i sześć rzeczywistych PDF-ów:
oba typy dla 2/10/15 dni. Sprawdza długie opisy do ostatniego znacznika, polskie
znaki, brak ceny/noclegu, poufność również w tekście PDF i numerację stron.
Artefakty są ignorowane w `local-data/trip-documents-qa/`.

Weryfikacja 24.10.2026: **176 testów pytest przeszło**, w tym regresje planera,
viewera i WAHA (jedno istniejące ostrzeżenie deprecacji Starlette/AnyIO).
Wszystkie trzy skrypty przeglądarkowe przeszły. Nowe sześć PDF-ów obejmuje
30 stron, dodatkowo sprawdzonych po renderowaniu Popplerem. Marketing ponownie
wygenerował osiem PDF-ów. Budowa i konfiguracja Compose oraz test działania
obu szablonów, presetów, stref czasu i trwałości w obrazie Docker przeszły.

## Istotne braki przed produkcją

- To lokalne wersje robocze, bez logowania, uprawnień, audytu i akceptacji treści.
- JSON ma atomowy zapis i blokadę w jednym procesie; brak centralnych transakcji,
  kopii zapasowych, historii pełnych rewizji i zarządzania współbieżnością wielu procesów.
- PDF jest zapisywany przez użytkownika, bez archiwum eksportów i niezmiennego
  historycznego renderera. Wynik może zależeć od przeglądarki i fontów systemowych.
- Branding, logo i fonty pozostają robocze; prawa do zdjęć są deklaracją użytkownika.
- Ceny/statusy potwierdza ręcznie organizator. Brak sprawdzania dostępności usług,
  automatycznej weryfikacji źródeł i dedykowanego magazynu sekretów.
- Należy rozszerzyć walidację harmonogramu o konflikty zdarzeń, pełną zgodność
  z terminem oraz niejednoznaczne/nieistniejące godziny przy zmianach czasu.

Nie dodano GCP, logowania, centralnej bazy, AI ani integracji WhatsApp.
