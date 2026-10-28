# DOC-UX-002 — kategorie i wybór źródeł Document Studio

Implementacja: 2026-10-28, gałąź `dev`, bazowy HEAD
`8fb388b5f257eb9a8a544df2581635aee5259c8c` — `post ui audit changes`.
Repozytorium było czyste. Zmiany tej iteracji pozostają bez commita/pusha.
Nie wykonano wdrożenia ani operacji na danych DEV/PROD.

## Wynik

Trip ma wiele niezależnych kategorii produktu; Trip, Campaign i DocumentDraft mają
pochodzenie danych. Kreator, biblioteki źródeł i marketing korzystają ze wspólnego
selektora wyszukiwania/filtrowania. Nie powstała relacja jeden Trip–jeden szablon.
Wyjazd grupowy nadal może być źródłem prywatnej oferty lub każdej rozpiski pilota.

Nowe pola:

| Model | Pole i wartości | Zgodność wsteczna |
| --- | --- | --- |
| Trip | `categories`: private, self_guide, school, incentive, group, other | Domyślnie []; unikalne wartości, bez inferencji z nazwy/kraju. |
| Trip / Campaign | `data_origin`: business, demo, synthetic_test, unknown | Domyślnie unknown; ręczny formularz jawnie sugeruje business. |
| DocumentDraft | `data_origin` | Kopia oznaczenia źródła w chwili tworzenia; stare dokumenty unknown. |

Nie zmieniono schema_version, ID, CampaignItem, szablonów, historii, repozytoriów
JSON/GCS, kontroli konfliktów, obrazów ani generatorów PDF. PUT źródeł pomijający
nowe pola zachowuje wcześniejsze kategorie/pochodzenie. Pochodzenie jest opisem
organizacyjnym, nie dowodem prawdziwości ani uprawnieniem.

## Kreator i marketing

- Oferty private/self_guide/school/incentive mają odpowiedni domyślny filtr.
  Pilot basic/advanced/knowledge nie ogranicza kategorii. Marketing wybiera Campaign.
- Domyślne listy zawierają business i unknown. DEMO/TEST można włączyć jawnie.
  O pochodzeniu decyduje pole, a nie fragment nazwy CLOUD-PARITY.
- Wyszukiwanie nazwy/kierunku toleruje wielkość liter i polskie znaki, również ł.
  Lista ma natywną obsługę klawiatury i opis wyników/pustego stanu. Brak automatycznego
  wyboru pierwszej pozycji. Niewidoczny po filtrze wybór jest czyszczony bez zamiany.
- Nowe źródło zachowuje kontekst szablonu i sugeruje jego kategorię. Checkboxy
  pozwalają dodać inne. Po zatwierdzeniu źródła ID jest zachowane przed kolejnym
  żądaniem; test awarii tworzenia draftu potwierdza brak duplikatu przy retry.
- Wybrane kierunki nowej kampanii pozostają w podsumowaniu podczas zmiany kategorii.
  Edytor marketingu wyklucza już dodane Trip i zachowuje filtry po dodaniu/przesunięciu.
  Oba warianty nadal używają jednego modelu Campaign.
- W istniejącej zakładce Wycieczki są filtry kategorii, pochodzenia i nazwy/kierunku,
  etykiety kategorii oraz pochodzenia na kartach. Kampanie mają analogiczny wybór,
  wyszukiwanie i pochodzenie. Szczegóły zaznaczonego źródła zawijają się pod listą.

## Stare dane i klasyfikacja

Nie usunięto ani masowo nie przeklasyfikowano żadnych rekordów. Wszystkie cztery
źródłowe fixture'y otrzymały demo. Nowe obiekty parity smoke są synthetic_test;
dokumenty dziedziczą to oznaczenie w serwisie. Kampania z kierunkami mieszanego
pochodzenia ma własne, jawne oznaczenie; nie zgadujemy go na podstawie pozycji.

Stare JSON-y są walidowane z nowymi domyślnymi wartościami bez zapisu podczas
odczytu. Snapshoty dokumentów pozostają niezależne przy klasyfikowaniu źródła.
Nowy dry-run `scripts.classify_source_origins` generuje raport kandydatów na
lokalnym magazynie/eksporcie, sprawdzając również strukturalne znaczniki starego
testu. Nie ma trybu apply, połączenia z chmurą ani zmian snapshotów. Każdy realny
PUT wymaga osobnej, jawnej decyzji operatora i aktualnej rewizji. Procedura:
[dokumentacja źródeł](DOCUMENT_STUDIO.md#źródła-kategorie-produktów-i-pochodzenie--doc-ux-002).

## Zmienione pliki

| Pliki | Cel |
| --- | --- |
| `app/document_studio/models.py` | Typy kategorii/pochodzenia, deduplikacja kategorii, addytywne pola. |
| `app/document_studio/api.py` | Zachowanie nowych pól dla starszych PUT; udostępnienie source-picker.js pod istniejącym guardem. |
| `app/document_studio/service.py` | Pochodzenie nowego dokumentu ze źródła. |
| `app/document_studio/trip_documents.py` | Publiczna projekcja snapshotu zachowuje organizacyjne kategorie i pochodzenie; bez zmian renderera. |
| `frontend/source-picker.js` w tym module | Wspólne filtrowanie, wyszukiwanie, selekcja pojedyncza/wielokrotna i etykiety. |
| `frontend/studio.js`, `frontend/marketing-editor.js` | Formularze źródeł, biblioteki, kreator, marketing i bezpieczny retry po utworzeniu źródła. |
| `frontend/index.html`, `frontend/studio.css` | Ładowanie komponentu i responsywna prezentacja. |
| `demo-fixtures/trips/demo-{iceland,canada,norway}.json` | Jawne pochodzenie demo. |
| `demo-fixtures/campaigns/demo-northern-journeys.json`, `demo-fixtures/README.md` | Pochodzenie kampanii demo i instrukcja użycia filtrów. |
| `scripts/gcp/parity_smoke.py` | Jawne synthetic_test dla nowych źródeł testu. |
| `scripts/classify_source_origins.py` | Wyłącznie odczytowy raport kandydatów, bez apply. |
| `tests/test_source_categories.py`, `tests/source_ux_qa.py` | Regresje backendu i rzeczywistego zachowania Chromium. |
| `tests/studio_catalog_qa.py`, `tests/browser_document_studio_smoke.py`, `tests/browser_marketing_smoke.py` | Jawny wybór DEMO/kategorii/źródła zamiast założenia pełnej listy i automatycznego pierwszego wyboru; dołączenie nowej QA. |
| `docs/DOCUMENT_STUDIO.md`, `docs/DOC_UX_002.md` | Instrukcja i ten raport. |

Nie zmieniono IAP/autoryzacji, Terraform, workflow publikacji, repozytorium historii,
magazynu zdjęć ani istniejących szablonów. Nie dołączano nowej zależności ani usługi.

## Testy i CI

| Weryfikacja | Wynik |
| --- | --- |
| Istniejąca pełna regresja po dodaniu modeli, przed nowymi testami | 724 passed, 43.67 s. |
| `pytest tests/test_source_categories.py -q` | 27 passed, 5.26 s. |
| Pełny `pytest -q` po implementacji | **751 passed**, 51.96 s; jedno wcześniejsze ostrzeżenie Starlette/AnyIO. |
| `tests/source_ux_qa.py` | PASS: cztery preferencje ofert, trzy piloty, polskie wyszukiwanie, klawiatura, DEMO/TEST, unknown, brak filtrowania po nazwie, stabilny wybór, dowolna kategoria, multi-kategorie/reload, kampania z kilku kategorii, retry bez duplikowania, mobile. |
| `tests/browser_document_studio_smoke.py` | PASS wraz z catalogue QA, library QA, regression QA po TRIPSE-QA-001 i nową source UX QA. |
| `tests/browser_cloud_demo_smoke.py` | PASS przez rzeczywiste routery z odizolowanymi adapterami. |
| `tests/browser_marketing_smoke.py` | PASS, osiem rzeczywistych PDF; obrazy, kadry, kolejność i dwa warianty. |
| `tests/browser_trip_documents_smoke.py` | PASS, sześć rzeczywistych PDF; 2/10/15 dni, tekst, poufność, restart. |
| `python -m scripts.gcp.ci offline` | PASS; bez poświadczeń i wdrożenia. |
| `node --check` dla trzech zmienionych JS | PASS. |

Nowe testy backendu wykonują zapis/odczyt i konflikt rewizji w JSON oraz fake GCS,
odrzucają nieznane kategorie/pochodzenie, sprawdzają stare payloady, niezależność
snapshotów wszystkich ośmiu typów i obu wariantów marketingu, kopie dokumentów,
fixture'y i faktyczne payloady parity smoke. Test dry-run porównuje bajty wszystkich
plików przed/po i odrzuca kandydata mającego tylko podejrzaną nazwę.

GitHub connector sprawdzono dla pełnego SHA bazowego commita. Zwrócił puste listy
`workflow_runs` i `statuses`. Nie ma więc potwierdzonego wyniku CI tego commita
w tej sesji. Nie uruchamiano workflow ani wdrożenia. Wyniki powyżej są lokalne.

## Ręczna kontrola po osobnym wdrożeniu na DEV

1. Jako uprawniony edytor otwórz `/documents/demo#trips`. Istniejące rekordy unknown
   powinny być widoczne; DEMO/TEST pojawiają się dopiero po jawnym filtrze. Nie
   klasyfikuj starych obiektów tylko na podstawie nazwy.
2. Otwórz fixture DEMO po włączeniu filtra. Sprawdź checkboxy pustych kategorii i
   pochodzenie demo; nie zapisuj zmian do istniejących obiektów bez zgody operatora.
3. Do sprawdzenia zmian tworzących rekordy użyj wyłącznie zatwierdzonych, fikcyjnych
   danych w DEV. Katalog → Self-Guide → nowa wycieczka: zaznacz dodatkową kategorię,
   świadomie wybierz pochodzenie demo i utwórz. Ponownie otwórz źródło i sprawdź
   checkboxy po odświeżeniu. W zwykłych formularzach ręcznych business jest sugestią,
   nie automatycznym oznaczaniem fikcyjnego scenariusza jako prawdziwego.
4. Prywatna oferta powinna preferować private. Pokaż wszystkie kategorie i wybierz
   fikcyjne źródło grupowe; utworzony dokument nadal powinien być offer.private.
5. Wyszukaj „Żółć” / „zolc”, wybierz wynik i zmień filtr tak, by go wykluczyć.
   Wybór ma się wyczyścić; inny wynik nie może zostać wybrany sam.
6. Marketing → nowa kampania: wybierz kierunki z różnych kategorii; sprawdź
   podsumowanie po zmianie filtrów, kolejność po zapisie i wykluczenie dodanych
   Trip z selektora kolejnego kierunku. Sprawdź oba warianty.
7. Porównaj istniejący dokument przed i po zatwierdzonej zmianie kategorii jego
   źródła: snapshot i historia dokumentu muszą pozostać bez zmian.
8. Sprawdź ekran 390 px i obsługę klawiatury. Zapis/eksport/history nadal podlegają
   dotychczasowej walidacji i uprawnieniom.

## Ograniczenia

Filtrowanie jest po stronie klienta nad istniejącym pełnym refresh Trip/Campaign.
To świadomie mała iteracja UX: nie zmniejsza kosztu pobierania dużych programów,
nie daje stronicowania serwerowego ani indeksowania. Do większej skali potrzebny
będzie osobny pomiar i kontrakt lekkich metadanych; nie dodano nowej bazy.

Natywna lista obsługuje klawiaturę; długie wiersze mogą wymagać odczytu pełnego
opisu wybranej pozycji pod listą na telefonie. Chromium i zrzuty desktop/mobile
zweryfikowano lokalnie; innych silników przeglądarek nie testowano.

Dry-run obejmuje rozpoznany strukturalnie stary scenariusz parity, a nie dowolne
syntetyczne dane. Stare unknown pozostają widoczne. Pochodzenie nie jest ACL ani
automatycznym sprawdzeniem faktów. Nie zmieniono globalnej idempotencji POST źródeł;
przy niepewnym timeoutie samego tworzenia źródła trzeba sprawdzić bibliotekę.
