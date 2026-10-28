# MAKE-001 — jeden interfejs developerski

Główny [Makefile](../Makefile) wywołuje dotychczasowe moduły i skrypty.
[scripts/dev.py](../scripts/dev.py) obsługuje tylko różnice systemowe: procesy,
zmienne środowiskowe, `.venv`, lokalne otwieranie stron, bezpieczne cache i harness
starszego testu. Nie zawiera poleceń gcloud ani logiki aplikacji.
Nie zmieniono modeli, endpointów, Compose ani kontraktu deploymentu.

## Audyt

Punkt odniesienia: commit `049f0cc2120db177f80015c41209d89a299a2a45`.
Sprawdzono README, instrukcje [Studio](DOCUMENT_STUDIO.md), [mock](MOCK_DEMO.md),
[GCP](DEPLOY_GCP.md), rejestry ADR/tracking, oba requirements, `.env.example`,
Dockerfile, oba Compose, `infra/gcp/`, `scripts/gcp/`, `tests/`, main i worker.

- API: `python -m uvicorn app.main:app`; worker: `python -m app.worker`.
  Document Studio nie wymaga workera; planer i symulator używają jednej kolejki
  SQLite i jednego osobnego workera.
- Strony: `/hub`, `/documents/demo`, `/planner`, `/demo/chat`. Ostatnia wymaga mock.
  `/` przekierowuje do Hubu; `make demo-planner` otwiera `/planner`.
- Bazowy Compose ma API/worker, opcjonalne profile `whatsapp` (WAHA) i `dev`
  (lokalny Caddy). API domyślnie wiąże `127.0.0.1:8000`.
  `compose.dev.yaml` to osobna publiczna konfiguracja z DNS/WAHA/Caddy;
  nie jest automatycznie używana przez Make.
- Jest siedem skryptów `browser*.py`. Sześć samo uruchamia API; tylko
  `browser_demo_smoke.py` wymaga już uruchomionego API i workera; zastany adres
  `localhost:8000` rozszerzono o opcjonalne `TRIPSE_BROWSER_BASE_URL` na potrzeby
  izolowanego harnessu. Domyślne uruchomienie ręczne testu pozostaje bez zmian.
  Osobny `container_cloud_preview_smoke.py` wymaga Dockera.
- Istnieje `requirements-dev.txt` z pytest, Playwright i pypdf. Nie ma
  skonfigurowanego formattera/lintera; `check` nie dodaje nowego.
- GCP ma cross-platform `deployment.py` z argumentami `action`,
  `--environment`, `--image-tag`, `--config-dir`, `--offline`, `--dry-run`.
  PowerShell nie jest wymagany przez Make. Publiczny Cloud Preview pozostaje
  read-only, odseparowany od lokalnej konfiguracji i danych.

## Wymagania i GNU Make

Python 3.12+ dla aplikacji i `.venv`. Sam adapter działa również pod Python 3.9+,
np. gdy systemowe `python` wskazuje starszą wersję, a `.venv` ma 3.12.
Instalacja nowego środowiska szuka wtedy `py -3.12` na Windows lub `python3.12`.
Możesz wskazać konkretny plik wykonywalny przez `PYTHON`; bez dodatkowych flag:

```powershell
make doctor "PYTHON=C:/Program Files/Python312/python.exe"
```

Zainstaluj GNU Make i dodaj katalog jego pliku wykonywalnego do PATH.
Windows: przykładowo `winget install -e --id GnuWin32.Make`, następnie otwórz
nowy terminal i sprawdź `make --version`. Dostępny jest też
[przenośny pakiet GnuWin32](https://gnuwin32.sourceforge.net/packages/make.htm)
(dla ZIP potrzebne są również DLL z paczki dependencies). Nie jest wymagany Bash,
Git Bash, WSL ani Unix `rm`, `sed`, `awk`. Windows używa `cmd.exe`; PowerShell jest
powłoką, z której wygodnie wywołujesz `make`.

Linux (Debian/Ubuntu): `sudo apt-get install make python3 python3-venv` oraz
dostępny Python 3.12+. macOS: narzędzia deweloperskie `xcode-select --install`,
następnie `make --version`; zainstaluj również Python 3.12+.
Nie zmieniaj systemowego Pythona tylko dla tego projektu.

`make help` używa wyłącznie funkcji GNU Make: działa bez Dockera, Pythona,
aktywnego virtualenv i gcloud. `make doctor` jest raportem diagnostycznym, zwraca
0 mimo braku opcjonalnych narzędzi. Pokazuje Python, pip, `.venv`, Git, GNU Make,
Docker daemon/Compose i opcjonalne gcloud/PowerShell. Właściwe targety kończą się
błędem, jeśli brakuje wymaganego dla nich narzędzia.

## Quick Start

Z katalogu repozytorium, bez aktywowania virtualenv:

```text
make help
make install-dev
make dev-mock
```

W drugim terminalu, dla planera i symulatora:

```text
make worker PLANNING_MODE=mock
```

W kolejnym terminalu:

```text
make demo-hub
make test
```

`install` tworzy lub wykorzystuje `.venv` i instaluje `requirements.txt`.
`install-dev` instaluje `requirements-dev.txt`, które już zawiera runtime.
`make install-browser` osobno instaluje Chromium Playwright. Linux może wymagać
dodatkowych bibliotek systemowych dla przeglądarki; nie instalujemy ich z sudo
automatycznie. Żaden install nie uruchamia Dockera, GCP ani aplikacji.

## Wszystkie targety

| Kategoria | Targety |
|---|---|
| Help / Configuration | `help`, `doctor` |
| Installation | `install`, `install-dev`, `install-browser` |
| Local Development | `dev`, `dev-mock`, `dev-live`, `worker` |
| Docker | `docker-up`, `docker-down`, `docker-build`, `docker-logs`, `docker-ps`, `docker-restart`, `docker-mock`, `docker-waha` |
| Testing / Quality | `test`, `test-unit`, `test-browser`, `test-container`, `test-all`, `check` |
| Demo | `demo-hub`, `demo-docs`, `demo-planner`, `demo-whatsapp` |
| GCP | `gcp-preflight`, `gcp-setup`, `gcp-build`, `deploy-dev`, `deploy-prod`, `gcp-smoke`, `gcp-rollback`, `gcp-dry-run` |
| Maintenance | `clean` |

Wszystkie są `.PHONY`; domyślnym targetem jest `help`. Operacje uruchamiane
w jednej komendzie Make są sekwencyjne, także przy `-j`. Serwer i worker są
procesami blokującymi, uruchamiaj je w osobnych terminalach.

## Praca lokalna i demo

`dev` i `worker` czytają opcjonalny główny `.env`, a zmienne powłoki/argumenty Make
mają pierwszeństwo. Parser przyjmuje `KEY=value`, puste wartości, komentarze
w osobnych liniach i opcjonalne cudzysłowy. Nie wykonuje pliku jako kodu,
nie rozwija `${...}` ani backticków, nie obsługuje inline comments.
Nie czyta `.env.dev/.env.prod`; to konfiguracje innego kontraktu GCP.
Nie wypisuje kluczy. Brak `PLANNING_MODE` zachowuje istniejący domyślny `live`.

`dev-mock` ustawia mock tylko dla uruchamianego API. Nie przełącza już działającego
workera. `dev-live` ustawia live i wywołuje istniejące `configured_generator()`
przed startem, aby sprawdzić klucze OpenAI i Places/Routes. Konstrukcja providerów
nie wykonuje zapytań sieciowych. `worker` sprawdza tę samą konfigurację w live.
Maps browser key jest osobną, opcjonalną konfiguracją viewera, nie kluczem serwera.
Nie ma cichego fallbacku na mock ani wykrywania trybu z innych procesów.

Używaj tego samego `DATABASE_PATH`, `PUBLIC_BASE_URL` i trybu w API/workerze;
przy zmianie trybu zatrzymaj i uruchom oba świadomie. Nie uruchamiaj drugiego
workera na tej samej bazie. Make nie jest menedżerem procesów.

Opcjonalnie `HOST=127.0.0.1` i `PORT=8001` (albo `API_PORT` w `.env`).
HOST musi być loopback, zgodnie z lokalnym zakresem demo. Przy zmianie portu
ustaw też pasujący `PUBLIC_BASE_URL` dla linków workera.

`demo-*` tylko sprawdza zdrowie istniejącego API i otwiera podany adres.
Nie startuje kolejnego serwera. Przykład: `make demo-docs PORT=8001` lub
`make demo-hub BASE_URL=http://localhost:8001`. BASE_URL musi być lokalnym originem,
bez loginu/hasła. `demo-whatsapp` odrzuca API live; wymóg mock workera jest
komunikowany, ale jego procesu/trybu nie da się potwierdzić samym `/health` API.
Gdy system nie potrafi otworzyć przeglądarki, wypisywany jest URL.

## Docker

```text
make docker-up
make docker-logs
make docker-ps
make docker-down
```

Wykorzystywany jest jawnie tylko `compose.yaml`. `docker-up` buduje i uruchamia
API/worker bez WAHA. Respektuje jego `.env`, porty i domyślny live.
`docker-mock` jawnie ustawia mock oraz odtwarza API/worker; nie usuwa danych.
`docker-restart` restartuje API/worker, ale nie zmienia ich konfiguracji.
`docker-build` tylko buduje te obrazy lokalnie. `docker-waha` uruchamia istniejący
profil `whatsapp` i API/worker/WAHA: najpierw skonfiguruj [WAHA](WAHA.md).
Nie uruchamia Caddy ani publicznego `compose.dev.yaml`. Zmienna COMPOSE_PROFILES
nie aktywuje dodatkowych profili przez ten adapter.

`docker-down` deleguje `docker compose -f compose.yaml down`, bez `-v`.
Wolumeny SQLite/sesji oraz bind mount dokumentów pozostają. `docker-logs` blokuje
terminal do Ctrl+C. Usługi uruchomione innymi narzędziami mogą nadal zajmować porty.

## Testy i jakość

```text
make test
make install-browser
make test-browser
make test-container
make test-all
make check
```

`test` i `test-unit` to ten sam standardowy `python -m pytest -q`, łącznie
z obecnymi testami integracyjnymi offline. Testy nie czytają głównego `.env`.
`test-browser` uruchamia kolejno wszystkie siedem istniejących skryptów:
viewer, Hub, Studio, marketing, pilot/oferta, Cloud Preview i starszy symulator.
Nie przekazuje im wymyślonych wspólnych argumentów. Dla starszego symulatora
tworzy własne tymczasowe SQLite/JSON, API i worker, które sprząta również po błędzie.
Harness wybiera wolny port i przekazuje go przez `TRIPSE_BROWSER_BASE_URL`;
test nie podłącza się do Twojej aktywnej bazy ani nie zatrzymuje istniejącego API.
Pozostałe skrypty samodzielnie wybierają porty. Wyniki/screenshoty/PDF pozostają
w dotychczasowych ignorowanych katalogach skryptów.

`test-all`: pytest → siedem browser smoke → istniejący Docker container smoke.
Potrzebuje zależności dev, Chromium i działającego Dockera. Niczego nie pomija
po cichu; pierwszy błąd przerywa wykonanie. `check`: `git diff --check` oraz
`docker compose -f compose.yaml config --quiet`; wymaga Git i Compose, bez startu
usług. Nie dodano formattera, lintera ani komend chmurowych do testów.

## GCP DEV/PROD

Najpierw przygotuj oba pliki zgodnie z [DEPLOY_GCP](DEPLOY_GCP.md).
`CONFIG_DIR` opcjonalnie wskazuje katalog zawierający `.env.dev` i `.env.prod`.
Make nie ładuje ich do własnego środowiska — robi to istniejący deployment.py.

Bez połączenia z GCP:

```text
make gcp-preflight ENV=dev OFFLINE=1
make gcp-dry-run ENV=dev
make gcp-dry-run ENV=prod TAG=<COMMIT_SHA>
```

Ręczne operacje GCP po osobnej decyzji operatora:

```text
make gcp-setup ENV=dev
make gcp-preflight ENV=dev
make gcp-build ENV=dev
make deploy-dev TAG=<COMMIT_SHA>
make gcp-smoke ENV=dev TAG=<COMMIT_SHA>
make deploy-prod TAG=<COMMIT_SHA> CONFIRM=prod
make gcp-smoke ENV=prod TAG=<COMMIT_SHA>
make gcp-rollback ENV=prod TAG=<PREVIOUS_COMMIT_SHA> CONFIRM=rollback
```

`<COMMIT_SHA>` zastąp prawdziwym pełnym SHA (40 małych znaków hex); nie kopiuj
nawiasów. Build wymaga czystego, zatwierdzonego HEAD. PROD promuje istniejący obraz,
bez rebuild; `latest` jest odrzucany przez wspólny walidator deploymentu.

- `ENV=dev` jest domyślne wyłącznie dla preflight, smoke i dry-run.
- `gcp-setup`, `gcp-build`, `gcp-rollback` wymagają jawnego ENV.
- `deploy-dev`/`deploy-prod` jawnie wybierają środowisko, sprzeczne ENV jest błędem.
- Setup/build dopuszczają tylko DEV, bo projekt i repozytorium są wspólne.
- PROD deployment wymaga `TAG` i `CONFIRM=prod`; każdy rollback `TAG`, ENV
  i `CONFIRM=rollback`. Dla rollback PROD ta ostatnia wartość jest jawną intencją.
- PROD smoke i dry-run wymagają TAG zgodnie z istniejącym kontraktem.
- `OFFLINE=1` dotyczy wyłącznie preflight. Bez tej flagi preflight czyta GCP;
  dry-run zawsze deleguje `deploy --dry-run` i nie wywołuje GCP.
- Make nie obchodzi clean HEAD, ownership/IAM, source SHA, prywatnego smoke
  ani innych zabezpieczeń istniejącego deployment.py. Nie pobiera sekretów.

## Błędy i clean

`make deploy-prod` / brak CONFIRM: odmowa przed delegowaniem procesu.
`ENV=staging`: błąd walidacji. Brak `.venv`: komunikat `make install-dev`.
Brak kluczy w `dev-live`: komunikat istniejącego kontraktu bez wartości sekretów.
Brak gcloud nie blokuje lokalnych targetów, ale zatrzymuje operację online.

Adapter zachowuje kod procesu potomnego. GNU Make sam zwraca zwykle **2** po błędzie
recipe (nie musi zwrócić identycznego numeru jak dziecko); w logu pozostaje jego
kod. Nie stosujemy prefiksu ignorowania błędów `-`, `|| true` ani cichego fallbacku.

`make clean` usuwa tylko `.pytest_cache` i `__pycache__` pod app/scripts/tests.
Odrzuca symlinki/junctions oraz ścieżki wychodzące poza workspace.
Nie przechodzi przez `.venv`, data, local-data ani fixture'y. Nie usuwa `.env*`,
SQLite, wolumenów, zdjęć, draftów ani zrzutów QA przechowywanych w danych.
Nie dodano clean-all.

## ADR, ograniczenia i weryfikacja

MAKE-001 dodaje interfejs do istniejących operacji; nie zmienia decyzji
architektonicznych. Nie utworzono nowego ADR. Istotne pozostają
[ADR-0007](adr/0007-sqlite-single-worker.md) i
[ADR-0009](adr/0009-cloud-run-readonly-preview.md).
Nieznane godziny/koszty w [worklogu](tracking/worklog.csv) pozostają puste.

Weryfikacja 2026-10-25:

- Windows: natywny GNU Make 3.81, PowerShell, bootstrap Python 3.9 i `.venv` 3.12.
  `make help`, `doctor`, `install`, `install-dev`, `install-browser`, `test`,
  `check` uruchomione. Ostatni `make test`: **288 PASS**, jedno ostrzeżenie
  zależności Starlette/AnyIO. `make test-all`: PASS (w tym przebiegu 286 pytest;
  dwa dodatkowe testy adaptera dodano później i potwierdzono przez `make test`),
  siedem browser smoke i kontener Cloud Preview, bez żądań do zewnętrznych API.
- Rzeczywisty `make dev-mock` + `make worker PLANNING_MODE=mock` z tymczasową bazą:
  health, Hub i zadanie planera ukończone. `make dev-live` z pustymi kluczami:
  odmowa startu. Nie wykonano planowania live.
- `make gcp-preflight OFFLINE=1` i `make gcp-dry-run` dla DEV i PROD: PASS.
  Testowano także ścieżkę Pythona i CONFIG_DIR ze spacjami, blokady ENV/TAG/CONFIRM
  oraz przekazanie kodu błędu dziecka bez wywoływania GCP.
- Bazowy Compose oraz `compose.dev.yaml` z fikcyjnym `DEV_DOMAIN=make-qa.invalid`:
  config PASS. Nie uruchamiano/stoppowano lokalnego stosu użytkownika ani WAHA.
- Linux w kontenerze: GNU Make 4.4.1 / Python 3.12, help i doctor PASS;
  **24 testy adaptera PASS** oraz `make install` tworzący nowe `.venv` i instalujący
  runtime PASS. Nie jest to pełny browser QA na Linux.

`clean` sprawdzono na fixture'ach z danymi użytkownika oraz symlinkach/junctions;
rzeczywisty target objęto również kontrolą zachowania plików danych.
Nie wykonujemy live GCP ani testów płatnych providerów w tym zadaniu.
macOS wymaga osobnego sprawdzenia na rzeczywistym systemie. Wspólna implementacja
nie stanowi dowodu wykonania tam testów. Nie dodano nowego długu aplikacyjnego;
adapter i lista istniejących skryptów wymagają aktualizacji wraz z repozytorium.
