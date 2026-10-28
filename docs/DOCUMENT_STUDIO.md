# TRIPSE Document Studio — funkcjonalne DEMO lokalne

## Tworzenie dokumentu krok po kroku — DOC-FLOW-004

**Implementacja lokalna na dev; bez wdrożenia.**
[Instrukcja dla Adriana, diagram, trasy, testy, zrzuty i ograniczenia](DOC_FLOW_004.md).

Otwórz **Utwórz dokument**, wybierz rodzaj, następnie zapisany program/kampanię
lub przygotowanie nowego źródła. Nowy program uzupełnij w istniejącym edytorze:
dni, atrakcje, opisy, kierunek i terminy. **Zapisz program wycieczki** zapisuje
wyłącznie program; **Kontynuuj do dokumentu** tworzy niezależny dokument.
Analogicznie **Zapisz kampanię** nie tworzy materiału marketingowego.
**Zapisz program/kampanię i wróć później** pozwala odłożyć tworzenie dokumentu.

W edytorze dokumentu użyj **Zapisz dokument** lub **Zapisz i sprawdź**. Sprawdzenie
pokazuje faktyczny ostatni zapis, uwagi i dotychczasowy podgląd PDF. Marketing
obsługuje A4 i social. Zapis, kompletność i status biznesowy są oddzielne;
status „Gotowy” nie jest nadawany automatycznie. Dokument i źródło pozostają
niezależne. Biblioteka otwiera ten sam zapisany dokument, bez tworzenia nowego.

Menu obejmuje: **Utwórz dokument**, **Programy wycieczek**, **Kampanie marketingowe**
i **Biblioteka dokumentów**. Dotychczasowe adresy pozostają dostępne.

## Źródła, kategorie produktów i pochodzenie — DOC-UX-002

**Implementacja w repozytorium na dev; bez wdrożenia w tej iteracji.**
[Raport implementacji i ręczna kontrola DEV](DOC_UX_002.md).

Kategoria Trip opisuje produkt turystyczny, a szablon opisuje dokument. Jedna
wycieczka może należeć do kilku kategorii i być źródłem dowolnej oferty, rozpiski
pilota lub kampanii. Dostępne kategorie: `private`, `self_guide`, `school`,
`incentive`, `group`, `other`. Nie ma kategorii pilot ani marketing.
W edytorze **Programy wycieczek → Otwórz / Nowa wycieczka** zaznacz checkboxy kategorii
i zapisz. Pusta lista oznacza **Nieprzypisane**; duplikaty są usuwane podczas
walidacji, nieznane wartości odrzucane. Nie wnioskujemy kategorii z nazwy lub kraju.

`data_origin` jest niezależne od kategorii, statusu i wiarygodności:

| Wartość | Znaczenie |
| --- | --- |
| `business` | Dane robocze TRIPSE; jawna sugestia dla nowego źródła tworzonego ręcznie. |
| `demo` | Fikcyjny przykład demonstracyjny; wszystkie źródłowe fixture'y mają ten znacznik. |
| `synthetic_test` | Dane automatycznych testów; parity smoke oznacza nimi Trip i Campaign. |
| `unknown` | Pochodzenie nieustalone, domyślne dla starych rekordów i API pomijającego pole. |

Starsze Trip/Campaign otwierają się z `unknown`, a Trip dodatkowo z `categories: []`.
Nie chowamy ich w zwykłym widoku, nie wykonujemy automatycznej migracji. Odczyt
nie zapisuje nowych pól do istniejących obiektów. PUT starego klienta pomijający
nowe pola zachowuje zapisane oznaczenia; jawne `categories: []` usuwa przypisania.
Rewizje i konflikty działają jak wcześniej.

W katalogu wybierz szablon. Oferty preferują odpowiednio private, self_guide,
school lub incentive; wszystkie trzy szablony pilotów pokazują wszystkie kategorie.
Kampania pozostaje źródłem marketing.collection. Kategorie są filtrem, nie zakazem:
**Pokaż wszystkie kategorie** pozwala np. stworzyć prywatną ofertę z wyjazdu
grupowego; **Uwzględnij nieprzypisane** dodaje stare wycieczki do konkretnej kategorii.
Wyszukiwarka uwzględnia nazwę i kierunek, wielkość liter i polskie znaki.

Domyślne pochodzenie to biznesowe i nieustalone. DEMO włączasz checkboxem lub
filtrem „Tylko DEMO”; TEST jest dostępny jawnie w filtrze pochodzenia / sekcji
testowej. To organizacja list, nie kontrola dostępu. API nadal zwraca pełne źródła
uprawnionym użytkownikom. Widok Wycieczki, kreator i marketing używają tej samej
funkcji filtrowania. Pełne listy Trip/Campaign nadal pobiera istniejące refresh();
nie dodano indeksu ani nowej bazy. Szczegóły wybranego źródła są również wypisane
pod listą, aby długie nazwy i kategorie dało się odczytać na małym ekranie.

Źródło nie jest wybierane automatycznie. Zmiana filtra zachowuje wybór, jeśli
źródło nadal pasuje; w przeciwnym razie czyści go bez wybierania innego. Przycisk
tworzenia nowej wycieczki sugeruje kategorię oferty, którą można zmienić/rozszerzyć.
Po zapisaniu źródła kreator pamięta jego ID, także gdy późniejsze tworzenie dokumentu
zawiedzie. W DOC-FLOW-004 źródło najpierw trafia do edytora, a dokument powstaje
dopiero po jawnej kontynuacji. Nowe źródła i dokumenty zachowują stałe ID próby;
po niejednoznacznym błędzie wykonywany jest odczyt i porównanie danych. Jeśli
wyniku nie da się potwierdzić, wybierz **Sprawdź zapis**. Nie rozpoczynaj drugiego
formularza w celu obejścia niepewnego wyniku. Nie ma globalnej deduplikacji
niezależnych formularzy; szczegóły i ograniczenia opisuje raport DOC-FLOW-004.

Nowa kampania może wybrać wiele wycieczek poprzez filtrowaną listę. Wybrane kierunki
pozostają w podsumowaniu także po zmianie filtra; przycisk × usuwa je świadomie.
W Studio kolekcji wybieraj kolejne kierunki wyszukiwarką/kategorią, następnie
**Dodaj kierunek**. Już dodane Trip są wyłączone z wyboru, filtry pozostają podczas
przestawiania/dodawania pozycji. Kolejność CampaignItem, zdjęcia, kadry i daty
pozostają w dotychczasowym modelu. Kampanie również mają wyszukiwanie, wariant,
liczbę kierunków i pochodzenie.

Nowy DocumentDraft przejmuje `data_origin` bezpośrednio ze źródłowego Trip lub
Campaign w chwili tworzenia. Kopia zachowuje pochodzenie dokumentu. Zmiana kategorii
lub pochodzenia źródła nie synchronizuje istniejących snapshotów ani historii.
Pochodzenie kampanii jest jawne, nie jest zgadywane z jej mieszanych kierunków.
Stary DocumentDraft bez tego pola pozostaje `unknown`; nie odtwarzamy jego genezy.

Dla starszych parity records dostępny jest wyłącznie raport kandydatów:

```powershell
.venv/Scripts/python.exe -m scripts.classify_source_origins --root D:\path\to\isolated-json-export
```

Narzędzie czyta lokalny magazyn lub odizolowany eksport. Nie łączy się z GCS,
nie inicjalizuje katalogów, nie zapisuje rekordów i nie ma trybu apply. Sprawdza
nazwę **oraz** dokładny 15-dniowy program/znaczniki starego parity smoke; nazwa sama
nie wystarcza. Kampanie są kandydatami tylko przy zgodności powiązań. Operator musi
sprawdzić dowody pochodzenia, zatwierdzić konkretne ID i osobno wykonać dopuszczone
PUT z aktualną rewizją. Nie proponujemy przepisywania zapisanych dokumentów ani ich
snapshotów. Żadnej klasyfikacji DEV/PROD nie wykonano w tej iteracji.

## Jak korzystać z biblioteki dokumentów TRIPSE — DOCUMENT-LIBRARY-001

**Implementacja lokalna na dev, 2026-10-28; bez wdrożenia na DEV/PROD.**
Otwórz `/documents/demo#drafts` albo „Biblioteka dokumentów” w istniejącym menu.
Biblioteka przechowuje rzeczywiste, zapisane konfiguracje wszystkich ośmiu typów;
nie dodaje demonstracyjnych dokumentów automatycznie. Katalog nowych dokumentów
pozostaje pod `#templates`, a starsze odnośniki `#drafts/{id}` nadal działają.

### Praca z biblioteką

1. Utwórz dokument przez katalog, wybierz źródło i uzupełnij edytor.
   „Zapisz zmiany” zachowuje pełny model: snapshoty, sekcje i ich ID/kolejność/
   widoczność, listy, tabele, zdjęcia i kadry, dane ofert, logistyki, wiedzy i notatki.
2. „Wróć do biblioteki” prowadzi do zapisanych dokumentów. Niezapisane zmiany
   wymagają potwierdzenia opuszczenia edytora, również przy przeładowaniu strony.
   Nie ma autosave. Przy błędzie zapisu treść formularza pozostaje; 409 oznacza
   konflikt — nie nadpisuj cudzej wersji. Zapis potwierdza rzeczywisty numer rewizji.
3. Szukaj po nazwie; filtruj rodzinę, konkretny szablon, status i archiwum.
   Domyślnie ostatnio edytowane są na początku. Dostępne są również sortowanie
   po nazwie/utworzeniu i kierunek sortowania oraz strony po 25 pozycji.
4. „Otwórz / Edytuj” wznawia ten sam dokument; „Podgląd” pokazuje jego zapisany
   stan, nie niezapisany formularz. Późniejsze zmiany Trip nie synchronizują draftu.
5. „Duplikuj” tworzy niezależny dokument z dopiskiem „— kopia”, nowym ID,
   rewizją 1 i statusem Roboczy. Zachowuje snapshot, cały stan redakcji i referencje
   do zdjęć w tym samym chronionym środowisku. Nie zmienia typu ani poufności.
6. „Archiwizuj” ukrywa dokument na domyślnej liście, zachowując treść i zdjęcia.
   Włącz „Tylko archiwum” lub „Aktywne i archiwalne”. Archiwalny dokument można
   podejrzeć i skopiować; przed edycją kliknij „Przywróć”. Przywracanie świadomie
   ustawia Roboczy, nie poprzedni status Gotowy. Nie ma trwałego usuwania w UI.
7. „Historia” pokazuje zapisane rewizje i ich podgląd/PDF roboczy. Każda starsza
   zachowana wersja pozostaje tylko do odczytu. Historia jest zbierana od tej
   funkcji; wcześniejsze utracone wersje nie są odtwarzane ani wymyślane.
   Przywracanie dawnej treści jako nowej rewizji pozostaje poza obecną iteracją.

Statusy biznesowe: **Roboczy / Do przeglądu / Gotowy do użycia / Zarchiwizowany**.
**Gotowy nie jest formalną aprobatą ani pozwoleniem na publikację.** Cena,
`concept_only`, kompletność, rezerwacje i ograniczenia eksportu nadal obowiązują.
Podgląd historyczny używa zapisanych danych i aktualnie zainstalowanego renderera;
nie jest pobraniem wcześniej zapisanego PDF-a.

### Metadane i dostęp

Zachowano techniczne `status: draft`; workflow biblioteki to oddzielne
`document_status`. Dodano `archived_at`, `created_by`, `updated_by`,
`duplicated_from_document_id` oraz wewnętrzny znacznik idempotentnej operacji.
`source_id`, `source_type` i nazwa źródła w odpowiedzi listy są wyliczane ze
snapshotu, bez drugiego, niezależnie edytowalnego zestawu tożsamości źródła.

Autor pochodzi wyłącznie ze zweryfikowanego principal w cloud_demo. Lokalnie
oraz w historycznych dokumentach bez autora pozostaje null; nie przypisuje się
ich fikcyjnie Adrianowi ani operatorowi. Dokumenty nadal są współdzielone między
uprawnionymi członkami danego środowiska. Nie dodano izolacji per pracownik ani
nowych ról. Czytelnicy nie zapisują, a niezalogowani nie czytają biblioteki,
historii ani prywatnych zdjęć. LOCAL zachowuje guard peer/Host/Origin/proxy;
readonly_demo nie rejestruje biblioteki. Nie powstają publiczne linki GCS.

### API biblioteki

Istniejące GET/POST/PUT `/api/document-studio/drafts` i `/drafts/{id}` pozostają.
GET `/drafts` jest zachowany dla zgodności; nowy frontend nie używa go do listy.
Nowe ścieżki mają prefiks `/api/document-studio`:

| Metoda | Ścieżka | Kontrakt |
|---|---|---|
| GET | `/library` | Lekkie `items`, `total`, `offset`, `limit`, `has_more`, bez sekcji i snapshotów |
| POST | `/library/{id}/duplicate` | `revision`, `operation_id` UUID → niezależna kopia |
| POST | `/library/{id}/archive` | `revision`, `operation_id` → archiwizacja |
| POST | `/library/{id}/restore` | `revision`, `operation_id` → przywrócenie do draft |
| POST | `/library/{id}/status` | Jak wyżej + `document_status`: draft/in_review/ready |
| GET | `/library/{id}/revisions` | Metadane dostępnych rewizji, najnowsze najpierw |
| GET | `/library/{id}/revisions/{revision}` | Pełny zapisany model wskazanej wersji |
| GET | `/library/{id}/revisions/{revision}/preview` | Chroniony podgląd A4; marketing również `output_format=social` |

Parametry GET `/library`: `search`, `family`, `template_id`, `document_status`,
`archived=exclude|include|only`, `sort=title|created_at|updated_at`,
`direction=asc|desc`, `offset` i `limit` (1–100, domyślnie 50). Filtr statusu
archived wybiera archiwalne dokumenty także bez osobnego przełącznika.
Metadane źródła są nazwą ze snapshotu, nie późniejszą nazwą zmienionego Trip.
PUT `/drafts/{id}` może ustawić draft/in_review/ready; archiwizacja idzie przez
osobną operację. Edycja zarchiwizowanej treści daje 409 do czasu przywrócenia.
Zmiana ID, template_id, poufności lub pól autorstwa przez payload jest odrzucana.

Każda mutacja wymaga aktualnej rewizji; konflikty dają 409. `operation_id`
umożliwia bezpieczne ponowienie tego samego żądania. Frontend blokuje wielokrotne
kliknięcia i zachowuje klucz po nieudanej odpowiedzi. Duplikat ma deterministyczne
nowe ID dla konkretnego klucza operacji; ponowienie nie tworzy kolejnej kopii.
Zwykły PUT nadal wymaga standardowej kontroli rewizji. Nie wykonuje się w tle
automatycznego nadpisania po konflikcie lub niejednoznacznym błędzie sieci.

### Trwałość, historia i awarie

Aktualny dokument nadal jest w `drafts/{id}.json` lokalnie lub
`documents/drafts/{id}.json` w prywatnym bucketcie środowiska.
Przed zmianą głowy Repository zachowuje **poprzednią skutecznie zapisaną wersję**
w `revisions/{id}/{revision:010d}.json` (GCS: `documents/revisions/...`).
Rewizja bieżąca jest dostępna z głowy; trafia do niezmiennego obiektu przed
kolejną zmianą. Nowe i stare dokumenty korzystają z tego samego kontraktu.
Nie archiwizujemy kandydatów, które przegrały konflikt.

- LOCAL: flush/fsync pliku tymczasowego, publikacja historii create-only przez
  hard link, następnie atomowa podmiana bieżącego JSON. Powtórny zapis historii
  musi odpowiadać istniejącej treści. Blokada jest współdzielona przez instancje
  repozytorium w jednym procesie; nadal wymagany jest jeden proces API.
- GCS: historia ma `if_generation_match=0`; głowa zachowuje istniejący CAS
  generacji. Nie ma transakcji wielu obiektów. Błąd historii blokuje zmianę głowy;
  błąd późniejszego zapisu może pozostawić poprawny, redundantny snapshot poprzedniej
  wersji. Po timeoutcie po faktycznym commicie odczytaj głowę; starej rewizji nie
  wolno bezwarunkowo nadpisywać. Historia nie usuwa żadnego starego dokumentu/zdjęcia.
- Metadane GCS są dołączane do obiektu w tym samym uploadzie (`tripse_document`).
  Listowanie biblioteki i historii korzysta z metadanych obiektów. LOCAL ma
  odtwarzalny cache `metadata/`, powiązany z inode/rozmiarem/mtime pliku danych.
  Awaria cache nie unieważnia zapisanego dokumentu. Brak/stary cache lub stare
  obiekty GCS bez metadanych powodują walidowany odczyt dokumentu; jawny kolejny
  zapis dodaje metadane. Odczyt nie przepisuje legacy dokumentów w GCS.

To archiwum aplikacyjne, nie WORM, polityka prawnej retencji ani niezależny backup.
Nie przywraca brakujących rewizji sprzed biblioteki. Po zmianie rendererów wygląd
historycznego podglądu może się zmienić; pełny stan danych jest nadal zachowany.
Starszy kod aplikacji może odrzucać nowe pola — rollback po zapisach biblioteki
wymaga sprawdzenia zgodności, nie usunięcia pól z dokumentów użytkowników.

### Przyszłe indeksowanie i DocumentExport

Dla małej biblioteki backend skanuje lekkie metadane, filtruje i stronicuje je
w aplikacji: O(n), bez pełnotekstowego przeszukiwania treści. API stronicowania
oddziela odpowiedź od Repository, więc późniejszy `query_documents`/indeks
Firestore może przejąć zapytania przy zachowaniu ID/revision i filtra środowiska.
Wymaga to osobnego projektu spójności indeksu, migracji i uprawnień. Nie utworzono
teraz Firestore dla Document Studio i nie połączono go z bazą jobów planera.

Przyszły **DocumentExport** może przechowywać rzeczywisty PDF w prywatnym GCS,
powiązany z document_id/revision/template_version, formatem, sumą kontrolną i
czasem eksportu. Nie jest zaimplementowany. Obecne przyciski generują podgląd
oraz PDF w przeglądarce; nie udają pobrania pliku zapisanego na serwerze.

### Sprawdzenie lokalne

Uruchom API jak w instrukcji poniżej, następnie otwórz `#templates`, utwórz
wybrany typ i zapisz zmiany. Wejdź do `#drafts`, wyszukaj dokument, skopiuj go,
zarchiwizuj oryginał, pokaż archiwum i przywróć. W Historii wybierz poprzednią
rewizję. Odśwież i zrestartuj API z tym samym katalogiem danych; treść i historia
mają pozostać. Dokumenty katalogu pozostają niezależne od późniejszych zmian Trip.

Testy biblioteki: `python -m pytest -q tests/test_document_library.py` oraz
`python tests/library_qa.py`. Pełny `browser_document_studio_smoke.py` obejmuje
bibliotekę, katalog, dotychczasowy edytor oraz restart prawdziwego lokalnego API.
Artefakty: ignorowany `local-data/document-library-qa/`. Testy GCS używają fake
adaptera z generacjami, metadanymi i symulowanymi awariami. Nie wykonano zapisu
na rzeczywistych bucketach DEV/PROD. Restart kontenera nie został zweryfikowany:
Docker Linux Engine był niedostępny. Formalna akceptacja i wdrożenie są osobne.

Decyzja i uzasadnienie: [ADR-0014](adr/0014-document-library-history.md).


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

## Weryfikacja DOCUMENT-LIBRARY-001 (2026-10-28)

Pełne pytest: **699 passed**, jedno zastane ostrzeżenie Starlette/AnyIO.
Dedykowany zestaw biblioteki: **35 passed**. Obejmuje wszystkie osiem typów i oba
warianty marketingowe, pełne kopie i snapshoty, metadane/paginację/filtry,
legacy JSON/GCS i nieustalonych autorów, historię, konflikty, idempotencję,
awarie przed historią/przed głową oraz timeout po commicie. Przegrana kandydatura
CAS nie jest zapisaną rewizją. Testy sprawdzają też prawa do historii, guard LOCAL,
readonly_demo oraz to, że `ready` nie omija braku ceny w ofercie.

Przeglądarka: `browser_document_studio_smoke.py` obejmuje bibliotekę i katalog;
`browser_cloud_demo_smoke.py`, `browser_trip_documents_smoke.py` i
`browser_marketing_smoke.py` przeszły regresję. Biblioteka została sprawdzona
po rzeczywistym restarcie API, z zachowaniem zdjęć, kadrowania, sekcji i historii.
Zweryfikowano ostrzeżenie przed porzuceniem edycji i układ mobilny; zrzuty są
w `local-data/document-library-qa/`. Kontrakty CI offline i składnia JS przeszły.
Nie testowano restartu kontenera ani nowego wydania na prawdziwym GCP.

## Pliki zmienione w DOCUMENT-LIBRARY-001

- Backend i modele: [app/document_studio/api.py](../app/document_studio/api.py), [app/document_studio/cloud_storage.py](../app/document_studio/cloud_storage.py), [app/document_studio/library.py](../app/document_studio/library.py), [app/document_studio/models.py](../app/document_studio/models.py), [app/document_studio/repository.py](../app/document_studio/repository.py), [app/document_studio/service.py](../app/document_studio/service.py).
- Frontend: [app/document_studio/frontend/index.html](../app/document_studio/frontend/index.html), [app/document_studio/frontend/library.js](../app/document_studio/frontend/library.js), [app/document_studio/frontend/marketing-editor.js](../app/document_studio/frontend/marketing-editor.js), [app/document_studio/frontend/studio.css](../app/document_studio/frontend/studio.css), [app/document_studio/frontend/studio.js](../app/document_studio/frontend/studio.js), [app/document_studio/frontend/trip-editor.js](../app/document_studio/frontend/trip-editor.js).
- Testy: [tests/browser_document_studio_smoke.py](../tests/browser_document_studio_smoke.py), [tests/library_qa.py](../tests/library_qa.py), [tests/test_cloud_demo.py](../tests/test_cloud_demo.py), [tests/test_document_library.py](../tests/test_document_library.py), [tests/test_document_sections.py](../tests/test_document_sections.py).
- Dokumentacja i tracking: [docs/DOCUMENT_STUDIO.md](../docs/DOCUMENT_STUDIO.md), [docs/adr/0002-local-json-storage.md](../docs/adr/0002-local-json-storage.md), [docs/adr/0003-document-snapshots.md](../docs/adr/0003-document-snapshots.md), [docs/adr/0011-authenticated-cloud-demo.md](../docs/adr/0011-authenticated-cloud-demo.md), [docs/adr/0014-document-library-history.md](../docs/adr/0014-document-library-history.md), [docs/adr/README.md](../docs/adr/README.md), [docs/document-system/architecture/system-architecture.md](../docs/document-system/architecture/system-architecture.md), [docs/tracking/worklog.csv](../docs/tracking/worklog.csv).
