# DOC-PDF-003 — skład, paginacja i jakość PDF

Data: 2026-10-28. Gałąź `dev`, bazowy HEAD
`83f520883c379293ca02d832c3f8b5ece53c3ab8` (`ux ubdate`). Repozytorium było czyste.
Zmiany są lokalne, bez commita, pusha, wdrożenia i modyfikacji danych DEV/PROD.

## Wynik i granice

Istniejący model **Python → kontrolowany HTML/CSS → paginacja w przeglądarce →
window.print()** został zachowany. Podgląd i wydruk wykorzystują te same strony.
Nie powstał serwerowy Chromium, serwis eksportów, magazyn PDF ani nowy schemat
zapisywanych dokumentów. Wygląd jest przygotowany do dalszej oceny biznesowej,
nie jest zatwierdzonym brand bookiem ani automatycznym potwierdzeniem treści.

Zweryfikowano 16 syntetycznych scenariuszy rzeczywistych PDF, wszystkie osiem ID,
oba warianty marketingu, A4 i social. Nowe testy sprawdzają pełną integralność
akapitów/list/komórek DOM, unikalne markery w PDF, kolejność, bounding boxes tekstu,
bloków i komórek, nagłówki/stopki, numerację, wymiary i rastry.

## 1. Stan początkowy i dowody

Baseline: istniejące testy ofert/pilota i marketingu przeszły; 52 testy sekcji
i regresji audytu przeszły w 13,94 s. Później tę samą nową macierz wykonano na
odizolowanym `git archive` wskazanego HEAD, bez przełączania bieżącego checkoutu.

| Ograniczenie | Potwierdzenie | Zmiana |
| --- | --- | --- |
| Cały blok przenoszony na następną stronę; podzielny, ale zbyt wysoki blok blokował druk | Stary test karty z 80 wyróżnikami oczekiwał błędu. Nowa regresja wymaga paginacji i wszystkich 80 markerów dokładnie raz w rzeczywistym PDF. | Dzielenie semantycznych elementów po pomiarze DOM. Nie osłabiono warunku dla niepodzielnego elementu. |
| Stałe porcje 650/500/180 znaków nie odpowiadały wysokości fontów i kolumn | Porównanie tej samej treści: Self-Guide 29→24 strony, długi advanced 46→40, knowledge 55→37. | Usunięto porcjowanie używane przez komponenty tekstu/tabel; helper chunks() zachowany dla zgodności i regresji audytu. |
| Ogólna tabela dziedziczyła proporcje pierwszej/ostatniej kolumny tabeli operacyjnej | W baseline ośmiokolumnowym 180 krótkich identyfikatorów zostało rozłamanych w środku przez wąskie kolumny. Wszystkie odzyskują się po usunięciu białych znaków: to błąd czytelności, nie dowód utraty znaków źródła. | Ogólne kolumny mają równą szerokość; tylko operational-table ma 26/56/18%. Nowy PDF zachowuje wszystkie 240 identyfikatorów bez rozłamania. |
| operational_entry() powielał wartości podczas porcjowania opisu | Izolowane wywołanie starej funkcji: dla 10 tys. znaków opisu tytuł i godzina 09:15 występowały po 20 razy. Obecnie po jednym. Dowód: component-comparison.json. | Jeden logiczny wiersz; kontynuacja zawiera pozostałą treść komórek. Powtarzane są nagłówki, nie wartości rezerwacji/godzin/statusów. |
| Ogólny komunikat o zbyt dużej karcie nie podawał kontekstu | Stary print-export.js tworzył jedną ogólną wiadomość o overflow. | Osobne diagnostyki resource/layout/preparation z nazwą sekcji; walidacja biznesowa ma osobny komunikat. |
| Marginesy/paginacja korzystały z zaokrąglonych 794×1122 px | Wymiary fizyczne deklarowano przez @page, a arkusz ekranowy miał inną precyzję. | A4 210×297 mm i social 285,75×357,1875 mm w obu mediach; podgląd jest tylko transformowany. |

W trakcie implementacji regresje markerów wykryły błąd przenoszenia niezmieszczonego
wiersza w pierwszej wersji nowego algorytmu. Naprawiono go przed akceptacją;
pełne porównanie tekstów komórek i markerów pozostaje w testach. Nie przedstawiamy
tej przejściowej usterki jako problemu bazowego HEAD.

## 2. Paginacja i tabele

- Python generuje pełny akapit, element listy i wiersz tabeli, z escapowaniem
  treści. Nie dodaje kontynuacji opartych na liczbie znaków.
- JS czeka na fonty i dekodowanie zdjęć. Bloki o zwykłej długości mogą pozostać
  razem; dłuższe teksty wykorzystują wolne miejsce, a zbyt wysoki blok jest dzielony.
- Podział preferuje akapity, linie, pełne słowa i elementy list. Wyszukiwanie
  binarne mierzy największy mieszczący się fragment tekstu. Krótka godzina/adres
  przechodzi w całości do kontynuacji; wyjątkowo długi token większy od strony
  może wymagać podziału znakowego, z ochroną par UTF-16.
- Zwykły wiersz tabeli przechodzi razem. Dopiero wiersz wyższy od obszaru świeżej
  strony jest dzielony komórka po komórce. Pozostałe wartości trafiają do kolejnych
  fragmentów w tej samej kolejności i kolumnach; krótkie wartości nie są kopiowane.
- Każdy fragment tabeli ma thead i kontekst tytułu. Długi wiersz ma etykietę
  „cd. · wiersz N”. Dodatkowy kontekst dnia jest pokazywany na początku nowej strony
  logistyki/wiedzy. Tytuł nie jest akceptowany jako samodzielny fragment.
- Krótkie początki podzielonego akapitu są przenoszone zamiast zostawiania jednej
  linii pod nagłówkiem. Nagłówek dnia i pierwsza część programu są utrzymywane razem,
  gdy mieszczą się wspólnie. Zakończenie/CTA może zachować poprzedzający kontekst.
- Puste arkusze są usuwane. Numeracja powstaje po zakończeniu paginacji.
- Font dokumentu nie jest automatycznie pomniejszany. Klasa compact może zmniejszyć
  jedynie kadr zdjęcia do istniejącej dolnej granicy. Niepodzielny element nadal
  blokuje eksport; błąd wskazuje odpowiedzialną sekcję.

Algorytm wykonuje pomiary dopiero po załadowaniu zasobów i oddaje sterowanie UI
co 12 bloków przez setTimeout(0). Nie czeka na requestAnimationFrame w ukrytym
iframe/oknie. Zwykłe wiersze nie wymagają binarnego dzielenia każdej komórki.
Nie wprowadzono Web Workers, frameworka ani arbitralnego progu czasu renderowania.

## 3. Wygląd, zdjęcia i warianty

Wspólne tokeny sterują rozmiarem pisma, interlinią, nagłówkami, tabelami i kadrami.
Zachowano paletę TRIPSE, systemowe Segoe UI/Arial i zastępczy wordmark. Nie dodano
fontów zdalnych, zdjęć z internetu, nowych faktów, źródeł ani nowego brandingu.

Oferty zachowują okładkę, podsumowanie, program, warunki i CTA. Self-Guide nadal
eksponuje „bez pilota na miejscu”, a szkolna trzy filary. Incentive ma spokojny
blok hotelu, większy nagłówek i przestrzeń na fotografie; puste opcjonalne pola
nie tworzą sztucznych pustych linii. Zasady potwierdzania hotelu pozostają bez zmian.

Motyw pilotów ma mniej dekoracji, czytelne reguły tabel, wyróżnione godziny i
tekstowe statusy. Legacy pilot.basic nadal jest wewnętrzny; etykieta „tylko
lokalnie” została zastąpiona poprawnym „roboczy”, ponieważ istnieje także prywatny
cloud_demo. Materiały wiedzy nie są automatycznie skracane; niezweryfikowane treści
i istniejące źródła pozostają w dokumencie.

Photo nadal używa object-fit:cover oraz zapisanych x/y/zoom. Kadry są przycinane
wewnątrz kontenera, bez rozciągania źródła. Podpis jest związany ze zdjęciem;
galeria nie dodaje fikcyjnej informacji „do uzupełnienia” przy wybranych obrazach
bez opisu. Brak wyboru daje oznaczony neutralny placeholder. Żaden oryginalny asset
nie jest modyfikowany. Jakości niskiej rozdzielczości nie można odzyskać samym CSS;
syntetyczne obrazy QA testują geometrię/kadrowanie, nie aprobatę zdjęć do druku 300 dpi.

Marketing A4 zachowuje kompaktowe karty i dwa warianty. Social jest osobną
kompozycją: okładka new_trips korzysta z istniejącego obrazu głównego lub neutralnego
placeholdera, karty mają większe kadry i osobną skalę pisma; theme_collection
zachowuje własną okładkę i układ z bocznym zdjęciem. Social jest nadal PDF o stronie
1080×1350 CSS px przy 96 dpi, nie nowym eksportem PNG.

Pochodzenie demo/test jest oznaczone na otwarciu i w klasyfikacji na każdej stronie.
W nowym dokumencie etykieta łączy się z istniejącym banerem roboczym zamiast dodawać
drugi baner. Pochodzenie pozostaje organizacyjną informacją, nie potwierdzeniem ceny.
MarketingDocument otrzymał wyłącznie pole projekcji data_origin; nie zmieniono
persistowanych modeli Trip/Campaign/DocumentDraft ani zapisanych snapshotów.

## 4. Walidacja i bezpieczeństwo

Nie zmieniono reguł danych, routingu/autoryzacji, GCS, historii ani zapisów zdjęć.
Ready nie jest zgodą na eksport. Brak ceny/CTA lub inne błędy nadal wyznaczają
data-valid zgodnie z poprzednimi regułami, w tym istniejącym rozróżnieniem roboczych
PDF dla nowszych typów. Nie podmieniono tego na data-final-valid i nie usunięto błędów CSS.

layoutErrors zachowuje zgodny kontrakt listy napisów. Nowa layoutDiagnostics
rozróżnia zasób, układ i błąd przygotowania. documentReady oznacza zakończenie próby,
także nieudanej; przycisk pozostaje wtedy wyłączony. Niewybrane zdjęcie jest
placeholderem/uwagą, błąd pobrania wybranego obrazu blokuje druk. Kontrolowany HTML
i CSP bez unsafe-eval pozostają aktywne. Publiczne/klientowskie projekcje nie
otrzymują wewnętrznych notatek pilota; macierz i wcześniejsze regresje to sprawdzają.

## 5. Testy

| Weryfikacja | Wynik |
| --- | --- |
| Bazowe testy sekcji i audytu | 52 passed, 13,94 s. |
| Nowe testy komponentów Python | 9 passed; pełne teksty/wiersze/listy, brak powielania zdarzeń, escapowanie, crop, klasyfikacja i walidacja. |
| Pełna regresja pytest | **760 passed**, 55,44 s; jedno wcześniejsze ostrzeżenie Starlette/AnyIO. |
| Studio browser smoke | PASS wraz z katalogiem, biblioteką, audytem, DOC-UX-002 i nową macierzą PDF. |
| Oferty/pilot, marketing, cloud_demo browser smoke | PASS; istniejące rzeczywiste eksporty, poufność, obrazy/kadry, edycja i restart. |
| Nowa macierz | **16 rzeczywistych PDF**, wszystkie typy i oba warianty social; pełna lista poniżej. |
| Offline CI/source contracts oraz node --check | PASS; bez poświadczeń i deploymentu. |

Macierz porównuje dokładny textContent każdego źródłowego p/li/td z konkatenacją
jego fragmentów po składzie. Równolegle unikalne markery w PDF muszą wystąpić
dokładnie raz i w oczekiwanej kolejności. Powtarzane nagłówki/stopki są prezentacją
i nie są traktowane jako duplikowanie danych.

Bounding boxes obejmują arkusz, nagłówek, stopkę, bloki, komórki oraz prostokąty
tekstu z Range.getClientRects; sprawdzają granice, zachodzenie, puste strony i
samotne nagłówki. Kontrole PDF weryfikują liczbę stron, treść i fizyczne wymiary:
A4 około 595,28×841,89 pt; social 810×1012,5 pt. Crop jest sprawdzany przez
object-fit, clipping, object-position i macierz skali wobec zapisanych parametrów.

Pierwsza strona każdego PDF jest porównywana z obrazem podglądu przy 96 dpi,
z tolerancją średniej różnicy kanałów 8% na rasteryzację fontów. To kontrola
uzupełniająca, nie zamiennik sprawdzania tekstu i geometrii. Wszystkie strony
są rasteryzowane i trafiają do contact sheets; reprezentatywne otwarcia, tabele,
kontynuacje, hotele i galerie zostały obejrzane lokalnie. Nie wymagamy identycznych
pikseli pomiędzy systemami operacyjnymi.

Dodatkowe negatywne przypadki sprawdzają naprawdę niepodzielny element ze sztywną
wysokością, błąd załadowania wybranego zdjęcia oraz poprawny layout z błędem danych.
Stary test „80 wyróżników musi blokować druk” zastąpiono silniejszym wymaganiem:
rzeczywisty PDF z kompletem 80 unikalnych wartości. Blokada niepodzielnej zawartości
ma oddzielną regresję. Wait-for-function w testach używa jawnej funkcji zamiast
eval napisu; sporadyczny błąd strict CSP w polling helperze nie został naprawiony
przez poluzowanie polityki aplikacji.

## 6. Artefakty i odtwarzanie

Wszystkie pliki QA są ignorowane przez Git:

```text
D:\Projects\tripse-ai-demo\local-data\pdf-quality-qa\
  baseline-matrix\results.json            # macierz oryginalnego HEAD
  baseline-matrix\<nazwa>.pdf             # porównawcze PDF i rastry
  component-comparison.json               # 20→1 kopii tytułu/godziny zdarzenia
  current\results.json                   # aktualne pomiary i wyniki
  current\index.html                     # lokalny indeks PDF/contact sheets
  current\overview.png                   # otwarcia wszystkich scenariuszy
  current\<nazwa>.pdf                     # rzeczywisty PDF
  current\<nazwa>.png                     # screenshot pierwszej strony HTML
  current\<nazwa>-dom.txt                 # tekst złożonego DOM
  current\<nazwa>\page-001.png             # raster PDF; kolejne strony analogicznie
  current\<nazwa>\contact.png              # wszystkie strony danego PDF
```

```powershell
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
.venv/Scripts/python.exe tests/pdf_quality_qa.py
# Opcjonalne porównanie z kontrolowanym archiwum bazowego commita:
.venv/Scripts/python.exe tests/pdf_quality_qa.py --compare-baseline --baseline-ref 83f520883c379293ca02d832c3f8b5ece53c3ab8
```

PyMuPDF 1.26.5 służy wyłącznie do testowej rasteryzacji; Poppler nie był dostępny
w tej sesji Windows. Nie dodano go ani PyMuPDF do zależności aplikacji uruchomieniowej.
Testy używają rzeczywistych routerów z odizolowanymi fake adapterami, mock planning
i wyłącznie syntetycznymi Trip/Campaign/DocumentDraft. Nie łączą się z realnym GCP.

### Zestaw wygenerowanych PDF i pomiary

Nazwy w tabeli są nazwami plików pod current/ (dopisz .pdf). To pojedyncze próbki
navigationReadyMs — nawigacja, fonty, zasoby i skład lokalny, nie SLA ani pomiar
rzeczywistej chmury. Zmienność cache/CPU nie pozwala deklarować procentowego
przyspieszenia. layoutMetrics w results.json osobno podaje czas przygotowania JS.
W zamian za dzielenie i większą czytelność niektóre dokumenty mają więcej stron.

| Plik (bez .pdf) | Strony baseline → teraz | Do gotowości baseline → teraz (ms) | JS teraz (ms) |
| --- | --- | --- | --- |
| `offer-private-standard-2-a4` | 3 → 3 | 212.5 → 254.2 | 86.3 |
| `offer-self_guide-standard-5-a4` | 29 → 24 | 113.1 → 196.8 | 136.4 |
| `offer-school-standard-5-a4` | 4 → 4 | 76.6 → 71.5 | 19.7 |
| `offer-incentive-standard-10-a4` | 7 → 7 | 83.0 → 121.3 | 43.0 |
| `pilot-basic-standard-10-a4` | 6 → 7 | 80.7 → 76.0 | 30.6 |
| `pilot-advanced-standard-15-a4` | 46 → 40 | 131.3 → 218.7 | 166.5 |
| `pilot-knowledge-standard-15-a4` | 55 → 37 | 119.6 → 188.7 | 125.8 |
| `pilot-basic-standard-2-a4` | 32 → 18 | 119.3 → 177.0 | 100.0 |
| `marketing-collection-new_trips-1-a4` | 1 → 1 | 73.6 → 72.9 | 10.4 |
| `marketing-collection-new_trips-3-a4` | 2 → 2 | 72.5 → 75.8 | 9.8 |
| `marketing-collection-new_trips-8-a4` | 4 → 4 | 95.4 → 76.8 | 10.2 |
| `marketing-collection-new_trips-8-social` | 8 → 9 | 108.1 → 104.4 | 34.7 |
| `marketing-collection-theme_collection-1-a4` | 2 → 2 | 71.6 → 75.3 | 10.0 |
| `marketing-collection-theme_collection-3-a4` | 3 → 2 | 75.1 → 93.4 | 24.1 |
| `marketing-collection-theme_collection-8-a4` | 4 → 4 | 81.5 → 89.2 | 14.5 |
| `marketing-collection-theme_collection-8-social` | 5 → 5 | 96.5 → 98.0 | 23.1 |

Łącznie: 16 PDF / 169 stron. Największa zmierzona średnia różnica obrazu podgląd–PDF w tym przebiegu: 1.55%. Wyniki i czasy to zapis ostatniego lokalnego przebiegu, nie statystyka populacji.

## 7. Pliki zmienione w implementacji

- `app/document_studio/frontend/print-export.js`: mierzone fragmentowanie, kontekst,
  zasoby przed składem, diagnostyka, numeracja i bezpieczny druk.
- `app/document_studio/frontend/brand-tokens.css`, `marketing.css`,
  `trip-documents.css`: wspólne skale i siatki, tabele, okładki, social i podpisy.
- `app/document_studio/rendering/trip_documents.py`: semantyczne akapity/listy i
  jeden logiczny wpis operacyjny; poprawna klasyfikacja legacy pilota.
- `app/document_studio/rendering/sections.py`: pełne tabele, kontekst dnia,
  hotel bez pustych linii, galerie z podpisami i przekazanie formatu marketingu.
- `app/document_studio/rendering/__init__.py`: spójny shell, pochodzenie demo/test,
  okładka social i komunikat blokady.
- `app/document_studio/marketing.py`: pochodzenie w nietrwałej projekcji marketingu.
- `requirements-dev.txt`: przypięty QA-only PyMuPDF, bez zmiany requirements.txt.
- `tests/pdf_quality_qa.py`, `tests/test_pdf_rendering.py`: nowa macierz, rastry,
  porównania, negatywne przypadki i regresje komponentów.
- `tests/browser_document_studio_smoke.py`: włączenie macierzy do istniejącego
  wejścia browser QA, bez zmiany CI/CD ani wyłączania starych testów.
- `tests/browser_marketing_smoke.py`, `tests/browser_trip_documents_smoke.py`,
  `tests/studio_catalog_qa.py`, `tests/reliability_qa.py`: silniejsze sprawdzenie
  podzielnej karty i polling zgodny z CSP.
- `docs/TRIP_DOCUMENTS.md`, `docs/MARKETING_COLLECTION.md`,
  `docs/document-system/design/brand-guidelines.md`, `layout-rules.md`,
  `docs/adr/0004-controlled-html-browser-pdf.md` i ten raport: rzeczywisty kontrakt,
  dowody i ograniczenia. Status ADR i zatwierdzenie brandingu pozostają bez zmian.

## 8. Co obejrzeć ręcznie przed akceptacją

Zacznij od current/overview.png i indeksu current/index.html. Priorytetowe PDF:

1. **offer-private-standard-2-a4.pdf** — otwarcie, hierarchia, marginesy, program i CTA.
2. **offer-incentive-standard-10-a4.pdf** — hotel, dwa kierunki zdjęć, podpisy galerii.
3. **pilot-advanced-standard-15-a4.pdf** — długi tekst, kontekst dni, tabela i
   bardzo wysoka komórka; obejrzyj również środkowe strony, nie tylko okładkę.
4. **pilot-basic-standard-2-a4.pdf** — osiem kolumn; czytelność wymaga oceny
   w rzeczywistej skali 100%, a nie tylko miniatury.
5. **pilot-knowledge-standard-15-a4.pdf** — ciągłość narracji i oznaczenia nieweryfikowane.
6. **marketing-collection-new_trips-8-social.pdf** oraz
   **marketing-collection-theme_collection-8-social.pdf** — okładka, proporcje
   i czytelność social na docelowym urządzeniu. Także A4 z 1/3/8 kierunkami.

Self-Guide i szkolna są w tej samej macierzy; sprawdź niezmienione obietnice
wsparcia oraz widoczność trzech filarów. Nie akceptuj syntetycznych treści jako oferty.

## 9. Ręczne sprawdzenie DEV i pozostałe ograniczenia

Po osobno autoryzowanym wdrożeniu DEV odśwież zasoby przeglądarki. Na zatwierdzonych
fikcyjnych danych utwórz dokument, dodaj długi opis, tabelę i zdjęcia, zapisz, otwórz
podgląd i poczekaj na „Gotowe”. W drukowaniu ustaw skalę 100%, grafikę tła, bez
nagłówków/stopki przeglądarki, właściwy papier. Porównaj podgląd z PDF przy 100%.
Sprawdź klasyfikację/rewizję, każdą stronę tabeli, końcową pozycję oraz brak ceny
bez świadomego wyboru wersji koncepcyjnej. Ready nadal nie uchyla walidacji.
Sprawdź także historyczną rewizję — korzysta z aktualnego renderera, nie zamrożonego PDF.

Nie wykonano realnego drukowania na papierze, testów Firefox/Safari ani integracji
z żywym GCP w tej iteracji. Nie ma gwarancji identycznego wyniku przy innych fontach,
sterownikach, skalowaniu drukarki lub wyłączonym tle. Oficjalne logo/fonty nadal
wymagają dostarczenia i osobnego zatwierdzenia. Nie powstał eksport PNG ani archiwum PDF.

Przypadek ośmiu kolumn jest bezstratny i nieprzepełniony, lecz długie wartości
w bardzo wąskich kolumnach nadal dają wiele linii; przed publikacją może wymagać
redakcyjnej zmiany struktury danych. Ekstremalny niepodzielny nagłówek/obraz pozostaje
błędem, a bardzo długi pojedynczy token może być kontynuowany znakowo. Nie skracamy
treści ani nie udajemy dopasowania przez mikroskopijny font.

Macierz nie pokrywa wszystkich maksymalnych kombinacji 500 sekcji i ogromnych
komórek. Wydajność realnej sieci/assetów i maksymalnych dokumentów wymaga osobnego
profilowania. Dane klientów, uprawnienia, retencja i akceptacja biznesowa nie są
zatwierdzone przez samą jakość renderowania.
