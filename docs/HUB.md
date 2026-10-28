# HUB-01 — TRIPSE AI Hub

Canonical navigation update (2026-10-28): `/` returns a relative 302 to `/hub`;
`/hub` renders directly; planner UI is `/planner`. Studio and mock simulator keep
their URLs. See [endpoint inventory, proxy limits and validation](ROUTING.md).

CLOUD-PARITY-001 (2026-10-26): the same Hub/router/frontend now supports the
authenticated `cloud_demo` composition. It links to the complete Studio,
planner and mock simulator; labels reflect cloud persistence. LOCAL retains
`local_only`; public `readonly_demo` retains its reviewed preview Hub. Cloud
membership and storage/task configuration are mandatory. DEV and PROD automated
deployment is now accepted; see [2026-10-28 evidence](RELEASE_2026_10_28.md).
The original implementation task itself performed no deployment. See [parity status](CLOUD_PARITY_AUDIT.md) and
[DEV acceptance](DEPLOY_GCP.md). Existing local instructions follow.

## Uruchomienie i pokaz

W PowerShell, z katalogu repozytorium:

```powershell
$env:PLANNING_MODE = "mock"
docker compose up --build -d api worker
```

Otwórz **http://localhost:8000/hub** (lub port wskazany przez `API_PORT`).
Nie są potrzebne klucze AI/Google ani prawdziwy telefon do demonstracji mock.

Uruchomienie natywne, po instalacji `requirements-dev.txt` w Python 3.12:

```powershell
$env:PLANNING_MODE = "mock"
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

W drugim terminalu, z tym samym `DATABASE_PATH`:

```powershell
$env:PLANNING_MODE = "mock"
.venv\Scripts\python.exe -m app.worker
```

Karty prowadzą do istniejących modułów:

| Karta | Adres | Zakres |
|---|---|---|
| AI Trip Planner & Maps | `/planner` | Formularz planowania; wynik otwiera tokenowy viewer mapy |
| Document Studio | `/documents/demo#templates` | Katalog ośmiu typów; wycieczki, kampanie i dokumenty zachowane; bez zależności od workera |
| WhatsApp Assistant | `/demo/chat` w mock | Symulator rozmowy bez prawdziwego WhatsApp |

W `PLANNING_MODE=live` symulator pozostaje wyłączony zgodnie z dotychczasowym
guardem. Jego karta prowadzi do instrukcji w sekcji `#demo-mode`, bez martwego
linku 404. Włączenie mocka wymaga ustawienia konfiguracji API i workera oraz ich
restartu. Hub nie zmienia konfiguracji ani nie wywołuje usług na wejściu.

Przebieg pokazu: planer → przykład → wynik i mapa; powrót do formularza i Hubu;
studio → edytor dokumentów → powrót; symulator → gotowy scenariusz → wynik.
Sekcja „Jak działa TRIPSE AI” pokazuje kierunek **Wiadomość → planowanie → mapa
→ dokument**, z jawną informacją, że przejście do dokumentów jest obecnie ręczne.
Hub nie importuje planów, nie synchronizuje danych i nie tworzy nowej automatyzacji.

## Wygląd i dostępność

Hub korzysta z istniejących roboczych tokenów `brand-tokens.css`, systemowych
fontów i własnych dekoracji HTML/CSS/SVG. Nie pobiera zdjęć ani fontów z internetu.
To roboczy branding, nie zatwierdzona identyfikacja TRIPSE.

Trzy spójne karty zawierają ikonę, opis, informację o trybie i zwykły link.
Strona działa bez JavaScriptu; ma skip link, semantyczne sekcje, widoczny focus,
obsługę klawiatury i `prefers-reduced-motion`. Układ zmienia się na tabletach
i telefonach. Dekoracje są ukryte przed czytnikami ekranu.

## Granice dostępu i dotychczasowe moduły

`app/hub.py` rejestruje dodatkowy router z tą samą zależnością `local_only`
co studio. Sprawdzane są adres klienta, Host, Origin i nagłówki proxy.
HTML Hubu jest poza publicznym StaticFiles; publiczne CSS/JS zawierają tylko
style i logikę wygodnego pokazywania linku, bez danych modułów.

Formularz `/planner` i symulator mają ukryty początkowo powrót, pokazywany przez
`module-nav.js` według stałego znacznika renderowanego przez backend: dla żądania
spełniającego lokalny guard albo uwierzytelnionego `cloud_demo`. Nazwa hosta nie
jest samodzielnym kryterium widoczności. To wyłącznie wygoda UI; decyzję
o dostępie do `/hub` i studia zawsze podejmuje backend. Chroniony panel studia
ma powrót w nagłówku, także w edytorach pod tym samym adresem.

Nie zmieniono `/trip/{token}`, jego szablonów, map ani tokenów. `Caddyfile`
pozwala na `/planner`, zachowując wcześniejszy publiczny formularz.
Hub jest przeznaczony do bezpośredniego lokalnego lub uwierzytelnionego wejścia, jak studio;
dostarczone publiczne proxy go nie wystawia. Oznaczenie trybu na Hubie wynika
z konfiguracji, nie jest healthcheckiem workera, kluczy API lub sesji WAHA.

## Testy i QA

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m playwright install chromium
.venv\Scripts\python.exe tests/browser_hub_smoke.py
```

Testy API sprawdzają dostępność, cel trzech kart, powroty, tryby mock/live,
odrzucenie zdalnego/proxy/cross-site dostępu, brak tworzenia danych na wejściu
oraz zachowanie istniejących tras. Browser smoke uruchamia własne API i worker
z tymczasowym JSON/SQLite i mockiem. Przechodzi do działającego planera, mapy,
studia i symulatora, wraca do Hubu, sprawdza klawiaturę, ograniczenie ruchu,
układy 320/390/768/1024 px oraz fallback po restarcie API w live.
Zrzuty ekranu: ignorowany katalog `local-data/hub-qa/`.

Szersze dotychczasowe kontrole UI:

```powershell
.venv\Scripts\python.exe tests/browser_document_studio_smoke.py
.venv\Scripts\python.exe tests/browser_marketing_smoke.py
.venv\Scripts\python.exe tests/browser_trip_documents_smoke.py
```

Weryfikacja 25.10.2026: **185 testów pytest przeszło**, w tym dotychczasowe
regresje planera, map, WAHA i studia (jedno istniejące ostrzeżenie deprecacji
Starlette/AnyIO). Przeszły wszystkie cztery skrypty przeglądarkowe wymienione
powyżej. Sprawdzono wizualnie Hub na desktopie i telefonie oraz mobilny powrót
ze studia. Konfiguracja Compose i budowa obrazu API przeszły.

## ADR, utrzymanie i kosztorys

[ADR-0008](adr/0008-local-demo-hub.md) dokumentuje granicę nawigacji; stanowi
uzupełnienie ADR-0001/0005/0006, bez zmiany ich statusów. Praca jest zapisana
jako HUB-01 w [worklogu](tracking/worklog.csv), bez wymyślonych godzin i kosztów.
Dowód commitu poprzedniego ADR-SETUP-01 uzupełniono na podstawie Git.

Nowe ograniczenie utrzymaniowe: lista wejść i opisy trybów Hubu są jawnie
utrzymywane w HTML/routerze. Dodanie modułu wymaga aktualizacji linków i testów
(COST-07). Publiczne wdrożenie, telemetria dostępności i integracja mapa–dokument
pozostają oddzielnym zakresem; nie zostały dodane w HUB-01.
