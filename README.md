# Tripse AI Trip Planner — Demo v0.1

Panel React (FRONT-001A/B): [frontend/README.md](frontend/README.md).
W `frontend/` uruchom `npm ci` i `npm run build`, następnie z katalogu głównego
`make dev-mock` i otwórz http://127.0.0.1:8000/app. Dotychczasowe interfejsy pozostają
dostępne. [Integracja, weryfikacja i rollback](docs/ui/front-001b-integration.md)
opisują nowy build obrazu i niepotwierdzone jeszcze bramki kontenerowe/hostowane.

## Quick Start — GNU Make

Python 3.12+ i GNU Make; nie trzeba aktywować `.venv` ani instalować Bash na Windows.

```text
make help
make install-dev
make dev-mock
```

W osobnym terminalu dla planera/czatu: `make worker PLANNING_MODE=mock`.
Testy: `make test`. Panel: `make demo-hub`. Dla browser QA najpierw
`make install-browser`; pełny zestaw: `make test-all` (wymaga też Dockera).
Instrukcje instalacji Make, wszystkie targety i zasady:
[docs/MAKEFILE.md](docs/MAKEFILE.md).

### Docker

```text
make docker-up
make docker-logs
make docker-down
```

Tryb mock: `make docker-mock`. Zwykły start nie uruchamia WAHA;
`docker-down` zachowuje wolumeny i dokumenty.

### GCP

```text
make gcp-preflight ENV=dev
make gcp-dry-run ENV=dev
```

Wymagane oba pliki konfiguracyjne GCP. Preflight online wymaga gcloud;
wariant bez chmury: `make gcp-preflight ENV=dev OFFLINE=1`.
PROD: chroniona promocja master przez GitHub Actions; ręczny target
`make deploy-prod TAG=<COMMIT_SHA> CONFIRM=prod` pozostaje dostępny.

## Cloud Run DEV/PROD — wdrożone cloud_demo

2026-10-28: prywatne DEV i PROD działają w `cloud_demo/mock` za IAP,
z osobnymi zasobami GCS, Firestore/Tasks i uprawnieniami. GitHub Actions przyjął
master na DEV i promował ten sam digest do chronionego PROD.
[Dowody wydania i granice odbioru](docs/RELEASE_2026_10_28.md),
[CI/CD](docs/GITHUB_CICD.md), [deployment i rollback](docs/DEPLOY_GCP.md).
`local` i publiczny `readonly_demo` pozostają obsługiwanymi trybami.
Logowanie każdego użytkownika w przeglądarce oraz gotowość na rzeczywiste dane
klienta nie zostały potwierdzone. LIVE i rzeczywisty WhatsApp pozostają wyłączone.

## Plan rozwoju Artifact Registry i CI/CD

[Plan TRIPSE CI-001–CI-005](docs/ARTIFACT_REGISTRY_CICD_PLAN.md) opisuje audyt
istniejącego rejestru, cache i warianty budowy obrazów. To dokumentacja propozycji,
bez nowego wdrożenia ani zmiany istniejącej promocji DEV → PROD.

## TRIPSE AI Hub — start demonstracji

Otwórz **[http://localhost:8000/hub](http://localhost:8000/hub)**, aby przejść do
planera i map, Document Studio lub lokalnego symulatora WhatsApp.
W PowerShell uruchom cały pokaz w trybie mock:

```powershell
$env:PLANNING_MODE = "mock"
docker compose up --build -d api worker
```

Strona `/` przekierowuje kodem 302 do `/hub`; planer jest pod `/planner`.
Studio `/documents/demo` i symulator `/demo/chat` zachowują adresy. Ten sam układ
działa w uwierzytelnionym `cloud_demo`; readonly używa `/preview/*`.
[Inwentarz tras i granica publicznego proxy](docs/ROUTING.md).
W trybie live karta symulatora pokazuje instrukcję jego
włączenia. Moduły mają powroty do Hubu; mapa publiczna nadal ma dotychczasową nawigację.
Szczegóły, zakres i testy: [docs/HUB.md](docs/HUB.md).

## Decyzje architektoniczne i rejestr prac

[Architecture foundation (ARCH-001)](docs/architecture/README.md) ·
[Documentation index](docs/README.md) ·
[UI architecture](docs/ui/README.md) · [API contracts](docs/api/README.md).
React + TypeScript migration is proposed; the existing demo is unchanged.

[Rejestr ADR i zasady pracy agentów](docs/adr/README.md) ·
[Rejestr prac](docs/tracking/README.md) ·
[Audyt repozytorium](docs/tracking/repository-audit.md) ·
[Podstawy przyszłego kosztorysu](docs/tracking/estimates.md).
Retrospektywne ADR-y opisują wdrożone rozwiązania; status `proposed` oznacza
brak potwierdzenia decyzji przez właściciela, nie brak implementacji.

## TRIPSE Document Studio — lokalne demo

Panel dokumentów: [http://localhost:8000/documents/demo#templates](http://localhost:8000/documents/demo#templates).
Katalog zawiera osiem typów: cztery oferty, trzy materiały pilota i marketing
z dwoma wariantami. Wybierz typ i źródło, edytuj sekcje, zapisz draft i otwórz
roboczy PDF. [Instrukcja pracy i ograniczenia](docs/DOCUMENT_STUDIO.md).
Oddzielne modele wielodniowych wycieczek, kampanie wielu kierunków i zapisywane
snapshoty dokumentów; dane w lokalnych plikach JSON, bez zmian SQLite planera.
Start: `docker compose up --build -d api` lub lokalny Uvicorn.
Pełna instrukcja, architektura, API, testy i ograniczenia:
[docs/DOCUMENT_STUDIO.md](docs/DOCUMENT_STUDIO.md).

Generator `marketing.collection` ma teraz dwa warianty, edytor kampanii,
lokalne zdjęcia i kadrowanie, podgląd A4 / 1080×1350 oraz druk do PDF.
Otwórz **Kampanie → Otwórz → Edytuj kolekcję / podgląd PDF**.
Instrukcja eksportu i QA: [docs/MARKETING_COLLECTION.md](docs/MARKETING_COLLECTION.md).

Z jednej wycieczki można też utworzyć edytowalną ofertę `offer.private`
i rozpiskę `pilot.basic`: własne treści, logistyka, statusy, rewizje, podgląd A4
i PDF. Dla Islandii dostępny jest jawnie fikcyjny przykład demonstracyjny.
Scenariusz prezentacji: [docs/TRIP_DOCUMENTS.md](docs/TRIP_DOCUMENTS.md).

## Pełne demo offline (mock)

Tryb `PLANNING_MODE=mock` zawiera teraz trzy przykładowe wycieczki, lokalną mapę
interaktywną i symulator WhatsApp bez konta telefonu oraz kluczy API.
Uruchom `docker compose up --build -d` i otwórz
[symulator rozmowy](http://localhost:8000/demo/chat) lub
[formularz](http://localhost:8000/planner). Instrukcja i scenariusze:
[docs/MOCK_DEMO.md](docs/MOCK_DEMO.md).

Wszystkie miejsca, czasy i odległości mocka są demonstracyjne. Linie na mapie
są schematem połączeń, a nie obliczonym przebiegiem dróg. Starszy opis pustego
mocka poniżej dokumentuje wcześniejszą wersję; aktualny mock prezentuje pełny plan.

## Task 01 — application foundation

Implemented: FastAPI, persistent SQLite jobs, and one separate polling worker.
Task 01's fixed sample generator remains available through `PLANNING_MODE=mock`.
It makes no external calls and labels every result MOCK. Live planning is now
implemented in Task 03 below; missing map values remain `null`, with explicit
verification status and warnings.

## Task 02 — WhatsApp gateway

Implemented: optional pinned WAHA service, persistent test sessions, authenticated
webhooks, an explicit sender allowlist, a minimal command router, atomic message
deduplication and durable acknowledgements through a reusable messaging adapter.
See [WAHA setup and pairing](docs/WAHA.md) before enabling the `whatsapp` Compose
profile. Default Compose still starts API and worker without WAHA or credentials.
Real WhatsApp delivery is **NOT VERIFIED** without a paired dedicated test number.

## Task 03 — AI trip planning pipeline

Implemented: strict OpenAI structured output, Google Places matches, simple day
grouping, Google Routes distance/duration/polyline, deterministic warnings,
persistent plans, expiring read-only links and WhatsApp result summaries.
See [pipeline configuration and verification](docs/PLANNING.md).

`PLANNING_MODE=live` is now the default. Set `OPENAI_API_KEY` and a server-side
`GOOGLE_MAPS_API_KEY` with Places API (New) and Routes API enabled, or separate
`GOOGLE_PLACES_API_KEY` / `GOOGLE_ROUTES_API_KEY` values. Missing keys produce an
explicit failed job; they never silently select mock generation. For the no-cost
sample, set `PLANNING_MODE=mock` in `.env` before starting Compose. API startup and
health do not require provider keys. Native Python requires exported variables.

Tokens expire after 24 hours. Set `PUBLIC_BASE_URL` to your reachable DEV HTTPS
origin before using viewer links from WhatsApp.

## Task 04 — minimal trip viewer

`GET /trip/{token}` serves a responsive, read-only HTML/CSS/vanilla-JavaScript
viewer. It displays ordered daily stops, Google Routes driving estimates, warnings,
directions links, verified Google Places markers and decoded Routes polylines.
Click a day to highlight its route; on mobile the itinerary appears above the map.
The token-protected JSON payload is now at `GET /api/viewer/{token}`. Invalid or
expired tokens return 404 on both endpoints.

Set **`GOOGLE_MAPS_BROWSER_KEY` to a separate browser key**, restricted to Maps
JavaScript API and your HTTP referrers. Never reuse the server Places/Routes key.
Without this key the itinerary and directions links still work, with an explicit
map-unavailable message. See [viewer setup and testing](docs/VIEWER.md).

## Task 05 — final integration and DEV stack

The four-service `api` / `worker` / `waha` / `caddy` stack and the standalone browser
form at `/planner` are implemented. [DEV_DEPLOY.md](DEV_DEPLOY.md) contains the exact local
HTTPS and public-host commands, pairing steps, repeatable smoke and status matrix.

**Verified locally:** HTTPS at `https://localhost:8443` with the exported local CA,
the complete API/worker/viewer flow in explicit MOCK mode, browser layouts and
private admin paths. **83 automated tests pass**, including the full signed-webhook
to planning/viewer/result chain with mocked external HTTP.

**NOT VERIFIED:** live OpenAI, real Places/Routes calculations, Google browser-map
authorization, WhatsApp phone delivery and public HTTPS deployment. Credentials,
pairing, allowed testers and a public host are not configured. Do not describe
the local mock run as a real-route or WhatsApp demonstration.

### Run with Docker Compose

Requires Docker Engine/Desktop running with Linux containers and Docker Compose.
From the repository root:

```powershell
Copy-Item .env.example .env # optional; defaults work without .env
docker compose up --build
```

API: http://localhost:8000 · Interactive API docs: http://localhost:8000/docs.
`api` and `worker` share the `tripse_data` named volume at `/data`; ordinary
container restarts and `docker compose down` preserve jobs. `docker compose down -v`
deletes that volume and all jobs. Compose binds the API to localhost for local DEV.
Run exactly **one worker**; do not scale the worker service. On startup it requeues
jobs left `running` by an interrupted worker. Live generation may repeat paid calls
after a crash; providers have bounded timeouts and no automatic request retries.
`/health` checks API/database availability, not worker liveness; use
`docker compose ps` and `docker compose logs worker` to inspect the worker.

### Run natively (Python 3.11+)

Windows PowerShell, from the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal, from the same repository root:

```powershell
.\.venv\Scripts\python -m app.worker
```

On Linux/macOS use `python3 -m venv .venv` and `.venv/bin/python` for the commands
above. Native processes default to `data/tripse.sqlite3`. To change it, set
`DATABASE_PATH` to the **same absolute file path in both terminals**. Native Python
does not load `.env` automatically. `WORKER_POLL_SECONDS` defaults to `1` (valid:
greater than `0`, at most `60`). Compose always uses its shared `/data` path;
`API_PORT` controls the host port (default `8000`). Live generation requires the
keys listed above; mock generation and server startup require no paid API keys.

### API smoke test

With the API and worker running:

```powershell
Invoke-RestMethod http://localhost:8000/health
$body = @{ text = 'Zaplanuj 2 dni: Wrocław → Karpacz → Wrocław.' } | ConvertTo-Json
$job = Invoke-RestMethod http://localhost:8000/api/trips -Method Post -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
$job # HTTP 202: trip_id and status=queued
Invoke-RestMethod "http://localhost:8000/api/trips/$($job.trip_id)"
```

Repeat the last request until `status` is `completed` or `failed`. Status progression
is `queued → running → completed/failed`; the POST only stores a job. GET returns
the original `request_text`, timestamps, `result` (null until completion), and
`error` (null unless failed). Failed generation records a readable error; the
worker continues with the next job. Generation details are in worker logs.
`text` must be a nonblank string of at most 10,000 characters; invalid input returns
422, missing trip IDs return 404, malformed UUIDs return 422. The POST also returns
a `Location` header pointing to the status endpoint.

### Automated tests

```powershell
.\.venv\Scripts\python -m pytest -q
```

Tests use temporary SQLite files and cover validation, health, persistent job
lifecycle, mock data labeling, failed generation, exclusive claims and recovery.
The API never runs generation in the HTTP process. SQLite serializes writes with
a 30-second busy timeout; each operation opens and closes its own connection.

The original full-demo plan follows; Tasks 01–05 are implemented, with live
verification blockers recorded in DEV_DEPLOY.md.

**Cel:** w jeden dzień przygotować i uruchomić na środowisku DEV małe demo, w którym wiadomość WhatsApp uruchamia generowanie szkicu wycieczki z prawdziwymi trasami i linkiem do mapy.

## Scenariusz pokazowy (Definition of Done)

1. Adrian wysyła na testowy WhatsApp: „Zaplanuj 2 dni: Wrocław → Karpacz → Szklarska Poręba → Wrocław. Natura, maksymalnie 3 godziny jazdy dziennie”.
2. System potwierdza otrzymanie zadania i nadaje `trip_id`.
3. AI proponuje **2 dni i maks. 6–8 przystanków**, których lokalizacje są potwierdzane w Google Places.
4. Google Routes oblicza **odległości, czas jazdy i przebieg trasy**; nie są one wymyślane przez LLM.
5. Walidator sygnalizuje przekroczenie limitu czasu jazdy oraz nieustalone lokalizacje.
6. WhatsApp odsyła zwięzłe podsumowanie i **link do webowego widoku planu z mapą**.
7. Ten sam przypadek działa także bez WhatsApp, przez testowy formularz WWW / endpoint API (plan awaryjny).

**Nie obiecujemy:** finalnej oferty, zweryfikowanych godzin otwarcia, cen i dostępności hoteli, pełnej optymalizacji całej wyprawy czy edycji planu z poziomu czatu.

## Stack (najszybsza droga)

- **Backend:** Python + FastAPI + Pydantic.
- **LLM:** OpenAI, JSON/structured output, tylko generowanie i układanie propozycji.
- **Mapy:** Google Places API (New) + Google Routes API + Google Maps JavaScript API.
- **WhatsApp demo:** WAHA w Dockerze (nieoficjalny klient WhatsApp Web; **tylko numer testowy**, ryzyko ograniczenia/blokady konta).
- **Frontend:** pojedyncza prosta strona HTML + JS serwowana przez FastAPI. **Bez Angulara w v0.1**.
- **Zadania i przechowywanie:** SQLite + jeden worker w osobnym procesie/kontenerze, wolumen trwały.
- **DEV:** Docker Compose na pojedynczej maszynie/VPS, HTTPS przez Caddy; alternatywnie lokalny Docker + tymczasowy tunel HTTPS na czas demo.

## Pliki projektowe

- [`docs/DEMO_SPEC.md`](docs/DEMO_SPEC.md) — funkcje, przepływ, model danych, endpointy, cięcia zakresu.
- [`docs/BUILD_DAY.md`](docs/BUILD_DAY.md) — lista tasków, test demo, kryteria go/no-go, plan awaryjny.

## Warunki startowe

- Docker + Docker Compose, Python 3.11+, repo Git.
- Klucz OpenAI i klucze Google Maps Platform (Places, Routes, Maps JavaScript) z billingiem i limitami.
- Oddzielny **testowy numer WhatsApp**, dostęp do skanowania QR.
- Adres HTTPS dla webhooka / widoku DEMO (lub tunel dla lokalnego pokazu).
- Nie umieszczamy kluczy w repo ani nie pokazujemy WAHA dashboardu publicznie.

## Zasada projektu

**WhatsApp jest adapterem wejściowym.** Całe planowanie musi działać niezależnie od niego poprzez `POST /api/trips`. Dzięki temu demo nie jest zakładnikiem sesji WhatsApp.

**Zakres i terminy:** max. 1 dzień pracy, bez przerabiania tego na produkcyjny system. Przyszłe moduły intencji, edycji tras i multi-agent orchestration odkładamy.

Przykładowe dokumenty GT v1: `/documents/demo#examples` — dziewięć konfiguracji,
kopie do edycji i PDF. [Instrukcja przykładów DOC-TEMPLATES-006](docs/DOCUMENT_STUDIO.md#dziewięć-gotowych-przykładów--doc-templates-006).
