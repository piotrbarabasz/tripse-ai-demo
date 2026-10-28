# DEMO-02 — generator marketing.collection

DOC-PDF-003 rozszerza ten sam renderer o mierzoną paginację list i tekstu,
powtarzanie kontekstu oraz kontrolę zasobów przed drukiem. Social ma własną
kompozycję: okładkę nowości z istniejącym obrazem głównym lub neutralnym
placeholderem oraz większe kadry kart. Pochodzenie demo/test pozostaje jawne;
walidacja CTA/tematu nie została zmieniona. [Raport i kontrola PDF](audits/DOC_PDF_003.md).
Zmiany tej iteracji zweryfikowano lokalnie; bez wdrożenia.

## Start i eksport

```powershell
docker compose up --build -d api
```

Alternatywnie lokalnie, Python 3.12:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
$env:PLANNING_MODE = "mock"
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

1. Otwórz **http://localhost:8000/documents/demo** → **Kampanie** → **Otwórz** →
   **Edytuj kolekcję / podgląd PDF**. Bezpośredni przykład:
   `http://localhost:8000/documents/demo#marketing/demo-northern-journeys`.
2. Wybierz „Nowe kierunki” lub „Kolekcja tematyczna”. Zmień tytuł, wprowadzenie,
   temat, sezon i CTA. Tytuły/opisy kierunków są polami kampanii, a nie zmianą Trip.
3. Dodawaj wycieczki z biblioteki, usuwaj je i przesuwaj strzałkami.
   Dodatkowe wycieczki tworzysz w istniejącej zakładce „Wycieczki”.
4. Wybierz neutralne placeholdery lub własne legalne zdjęcia. W sekcji „Twoje
   zdjęcia” wskaż plik i cel, potwierdź prawo do użycia, kliknij „Wgraj”.
   Wybór zdjęcia i suwaki X/Y/powiększenie działają osobno dla każdej karty i okładki.
5. Podgląd aktualizuje się po edycji. Wybierz A4 albo 1080×1350. Przeczytaj uwagi;
   brak CTA lub tematu kolekcji blokuje druk, a brak terminu pozostaje widoczną etykietą.
6. „Zapisz zmiany” zapisuje kampanię w JSON. „Zapisz dokument / PDF” zapisuje
   kampanię, tworzy niezależny snapshot i otwiera jego podgląd w nowym oknie.
7. W nowym oknie kliknij **Zapisz jako PDF**, wybierz systemową drukarkę
   **Zapisz jako PDF**, skalę **100%**, wyłącz nagłówki/stopki przeglądarki i włącz
   grafikę tła. Układ A4 deklaruje A4; social deklaruje stronę 285,75×357,1875 mm,
   odpowiadającą proporcji i wymiarom CSS 1080×1350 przy 96 dpi.
   Zweryfikowano Chromium. Inne przeglądarki mogą inaczej obsłużyć niestandardowy papier.

Nie ma automatycznej publikacji ani wysyłki. Sam zapis PDF nie zatwierdza treści.
Podgląd na żywo może być drukowany bez tworzenia snapshotu; przy archiwizacji
używaj „Zapisz dokument / PDF”. Zapisane snapshoty otworzysz też przez
„Dokumenty robocze” → „Podgląd A4 / PDF” / „Układ 1080×1350”.

## Podział implementacji

- **Dane**: istniejące `Campaign` / `CampaignItem` rozszerzone o opcjonalny tytuł
  redakcyjny, opis kampanii, oznaczenie, obraz główny i pozycje kadru. Domyślne
  wartości zachowują zgodność z plikami DEMO-01. Trip i jego API nie zmieniły się.
- **Projekcja i walidacja**: `marketing.py` wybiera tylko pola marketingowe.
  W HTML nie ma dni wycieczki, notatek wewnętrznych ani danych operacyjnych.
- **Komponenty**: `rendering/components.py` — fotografia/placeholder, karta,
  escapowanie tekstu; `rendering/__init__.py` — kompozycja dwóch wariantów.
- **Wygląd**: `frontend/brand-tokens.css` — robocze kolory, fonty, marginesy,
  odstępy; `marketing.css` — strony, nagłówki, karty, stopki i print CSS.
  Branding podmienisz w jednym pliku tokenów. Znak TRIPSE jest tymczasowym
  znakiem tekstowym, nie reprodukcją oficjalnego logo. Fonty systemowe; brak
  pobierania zdjęć czy fontów z internetu. Przeglądarka osadza fonty przy druku.
- **Skład**: `frontend/print-export.js` mierzy rzeczywiste bloki w docelowym
  rozmiarze, przenosi całe karty na kolejne strony i numeruje strony. Nie redukuje
  globalnej wielkości tekstu. Nadmierna zawartość pojedynczej karty daje błąd;
  eksport jest blokowany zamiast obcinać treść. Obrazy muszą się wczytać przed drukiem.
- **Eksport**: kontrolowany przycisk wywołuje `window.print()`.
  Serwer nie uruchamia Chromium/Playwright i nie przechowuje PDF.
- **Edytor**: osobny `marketing-editor.js` / `.css`, zwykły HTML/CSS/JS.
  Dotychczasowy edytor wycieczek i ekran kampanii pozostają dostępne.

Wariant `new_trips` ma fotograficzne karty i jasny nagłówek; `theme_collection`
ma dużą fotografię, ciemny blok tematu i numerowane, kompaktowe pozycje.
Format social otrzymuje większą typografię i inną kompozycję kart.
Paginacja zależy od treści; osiem kierunków tworzy kilka czytelnych stron.
Tekst jest escapowany, kod HTML/CSS/JS pochodzi wyłącznie z kontrolowanych plików.
Nie ma ścieżki pozwalającej LLM ani użytkownikowi wstrzyknąć wykonywalny HTML.

## Zdjęcia i trwałość

`assets.py` przyjmuje statyczne JPG/PNG/WebP do **8 MiB** i **24 megapikseli**.
Sprawdza rzeczywisty format dekoderem Pillow, zgodność MIME, rozszerzenie, liczbę
klatek i rozmiar. Odrzuca SVG, animacje, uszkodzone pliki i niezgodność MIME.
Ponownie koduje piksele, stosuje orientację EXIF i usuwa metadane, m.in. GPS.
Oświadczenie o prawie użycia jest obowiązkowe; nie stanowi automatycznej
weryfikacji licencji. System nie pobiera fotografii z innych serwisów.

Plik obrazu i metadane JSON otrzymują wygenerowany identyfikator. Nazwa pliku
użytkownika jest wyłącznie etykietą. `local-data/document-studio/assets/` nie jest
publicznym StaticFiles; zdjęcia są czytane przez chroniony lokalnie endpoint.
Pliki obrazów są niezmienne, dzięki czemu późniejszy wybór innego zdjęcia nie
zmienia snapshotu. Aktualny zakres nie zawiera usuwania zdjęć i garbage collection.

Zapis kampanii korzysta z dotychczasowego atomowego repozytorium JSON i kontroli
rewizji (409 przy konflikcie). Zdjęcia, kadry, kolejność i opisy przetrwają restart;
Compose korzysta z istniejącego bind mountu. Nadal wymagany jest jeden proces API.
Wgrywane obrazy są trwałe po uploadzie; ich przypisanie i kadr utrwala „Zapisz zmiany”.

## Nowe endpointy

Prefiks `/api/document-studio`; istniejące API nie zostało zastąpione.

| Metoda | Ścieżka | Zawartość |
|---|---|---|
| GET | `/assets` | Metadane biblioteki |
| POST | `/assets?filename=photo.jpg&rights_confirmed=true` | Surowe bajty, nagłówek Content-Type JPG/PNG/WebP |
| GET | `/assets/{id}/content` | Zweryfikowane lokalne zdjęcie |
| POST | `/marketing/validate` | `{campaign, output_format: "a4" lub "social"}` → lista uwag |
| POST | `/marketing/preview` | Ten sam kontrakt → kontrolowany HTML niezapisanych danych |
| GET | `/campaigns/{id}/preview?output_format=a4` | HTML zapisanej kampanii |
| GET | `/drafts/{id}/preview?output_format=a4` | HTML niezależnego snapshotu marketingowego |

Template `marketing.collection` ma wersję **0.2.0**. DEMO-03 dodaje wersję **0.3.0**
dla `offer.private` i `pilot.basic`; pozostałe typy zachowują 0.1.0.
Podgląd starych snapshotów marketingowych DEMO-01 korzysta z bieżącego renderera
i domyślnych wartości nowych pól. Nie ma archiwum historycznych rendererów.
Wersja szablonu w metadanych nie oznacza jeszcze deterministycznego archiwum PDF
między różnymi systemami, fontami i wersjami przeglądarki.

## Testy i QA

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m playwright install chromium
.venv\Scripts\python.exe tests/browser_document_studio_smoke.py
.venv\Scripts\python.exe tests/browser_marketing_smoke.py
docker compose config --quiet
docker compose build api
```

QA używa tymczasowego magazynu i własnej neutralnej ilustracji testowej. Sprawdza
oba warianty przy 1/3/8 kierunkach, A4 i social, długie tytuły/opisy, brak zdjęcia,
brak terminu i blokadę pustego CTA. Testuje edycję, kolejność, upload, wybór obrazu,
kadr, ekran telefonu i rzeczywisty restart procesu. Generuje osiem PDF-ów przez
przeglądarkę, weryfikuje liczbę stron, wymiary, polskie znaki i treść stopki/CTA.
Artefakty są ignorowane przez Git w `local-data/marketing-qa/`.

Weryfikacja 24.10.2026: **167 testów pytest przeszło** (jedno istniejące
ostrzeżenie deprecacji Starlette/AnyIO). Oba skrypty przeglądarkowe przeszły.
Osiem PDF-ów (16 stron) sprawdzono również po renderowaniu Popplerem.
Zweryfikowano długie teksty, oba formaty dla 1/3/8 kierunków i blokadę druku
nadmiernie dużej karty. Konfiguracja Compose i budowa obrazu API przeszły.

## Granice etapu

Brak logowania, GCP, WhatsApp, AI research, publikacji, serwerowego PDF i eksportu
PNG. Układ 1080×1350 to rzeczywisty układ stron do podglądu i druku, bez osobnego
przycisku pobrania obrazu. Dane i branding DEMO wymagają przeglądu przed użyciem
handlowym. To generator dokumentu roboczego z eksportem w przeglądarce.
