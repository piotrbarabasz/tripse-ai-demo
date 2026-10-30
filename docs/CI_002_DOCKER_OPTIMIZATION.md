# CI-002 — audyt i ograniczony hardening istniejącego obrazu

CI-006 integration note (2026-10-29): this is the historical isolated-task report.
The selected implementation is now in the local integration candidate; current
combined validation and outstanding committed-source/hosted/cloud gates are in
[CI-006](CI_006_INTEGRATION_ACCEPTANCE.md). Original measurements below remain
attributed to their original worktree and source, not to a new release SHA.

2026-10-29. **Lokalny odbiór kontenerowy PASS; release provenance i Cloud Run niezweryfikowane.**
Checkout: `D:\Projects\tripse-ai-ci-002`, gałąź `ci/ci-002-docker-hardening`,
baza `777e0662da5e57894371529f3af0bdafeb2fed11` (udane CI tej bazy odczytano
w CI-001). Bez commita, push, merge i wdrożenia.

CI-001 pozostaje nietknięte w `D:\Projects\tripse-ai-demo` na
`ci/ci-001-python-cache`, z własnymi niezacommitowanymi zmianami. Nie wykonano
stash/reset ani kopiowania tych zmian. CI-002 powstało przez `git worktree add`
z czystej bazy; jego pliki zobaczysz w Source Control po otwarciu tego checkoutu.

## Aktualny Container Acceptance — 2026-10-29 po uruchomieniu Dockera

**Lokalny odbiór funkcjonalny obu obrazów: PASS.** Brak silnika z poprzednich
prób jest usunięty po uruchomieniu Dockera przez użytkownika. Implementacji
CI-002 ani konfiguracji Desktopa nie zmieniano. Kandydat jest nadal lokalnym,
niezacommitowanym patchem, nie zatwierdzonym obrazem wydania. Cloud Run/IAP
oraz proweniencja przyszłego commita pozostają **NOT VERIFIED**.

### Preflight i metodologia

Docker Desktop 4.81.0 (232925), Engine/CLI 29.6.1, API 1.55, linux/amd64,
kernel `6.18.54.1-microsoft-standard-WSL2`, 8 CPU, RAM 8 304 390 144 B
(około 7,73 GiB), overlayfs/containerd snapshotter. Host Windows/amd64,
Ryzen 3 3100. Zasoby odczytano z demona, bez zmiany ustawień.

Baseline wyeksportowano przez niezmienione `source_files()` dla rzeczywistego
SHA `777e0662da5e57894371529f3af0bdafeb2fed11`. Kandydat ma identyczne
zatwierdzone pliki aplikacji/fixture’ów oraz jawny overlay trzech plików:
Dockerfile i oba ignore. Manifesty SHA-256 wejść zapisano osobno.
`app/_build_version.txt` identyfikuje bazowy kod aplikacji, który jest identyczny;
nie przedstawia niezacommitowanej receptury jako zatwierdzonego commita.
Nie wywoływano produkcyjnego buildu ani nie omijano `clean_head()`/build proof.

Jednorazowe tagi: `tripse-ci002-qa:4e78846881-baseline` i
`tripse-ci002-qa:4e78846881-candidate`; bez publikacji. Druga macierz używała
`docker build --platform=linux/amd64 --pull --no-cache` dla cold oraz zwykłego
powtórzonego builda dla warm. Nie czyszczono współdzielonego cache; cold oznacza
wyłączone ponowne użycie warstw RUN/COPY, nie pusty daemon. To lokalne QA,
bez zmiany receptury Cloud Build i bez implementacji CI-003.

Każdy czas to pojedyncza sekwencyjna próba. Startup oznacza czas samego
`docker start`; healthy jest czasem od rozpoczęcia startu do pierwszego HTTP 200
`/health` przy odpytywaniu co 100 ms, z narzutem klienta Docker/HTTP.

### Rzeczywiste before/after

| Metric | Before: baseline | After: CI-002 | Difference |
|---|---:|---:|---:|
| `docker image inspect .Size` | 76 088 695 B | 76 099 557 B | +10 862 B |
| Suma warstw `history --human=false` | 248 373 248 B | 248 430 592 B | +57 344 B |
| `docker image ls` SIZE | 324 MB | 325 MB | Zaokrąglona prezentacja CLI |
| Dependency layer (`pip install`) | 113 524 736 B | 113 524 736 B | 0 B |
| Cold Docker build (`--pull --no-cache`) | 23,725 s | 23,056 s | −0,669 s |
| Warm Docker build | 1,537 s | 1,603 s | +0,066 s |
| API startup: `docker start` | 0,357 s | 0,370 s | +0,013 s |
| Time to healthy | 1,710 s | 1,761 s | +0,051 s |
| Worker `docker start` | 0,317 s | 0,313 s | −0,004 s |
| API restart → healthy | 1,668 s | 1,671 s | +0,003 s |
| Runtime UID/GID | 0/0 | 0/0 | Bez zmiany USER |
| Warstwy filesystem | 9 | 9 | Bez multi-stage |

Docker 29/containerd ma różne liczniki treści i danych rozpakowanych. Podano
surowe pola inspect, sumę history i zaokrągloną prezentację CLI osobno; nie
utożsamiamy ich ze sobą ani z dodatkowym fizycznym przyrostem zajętości dysku
współdzielonych warstw. [Dokumentacja containerd storage](https://docs.docker.com/engine/storage/containerd).

**Nie wykazano zysku wydajności ani zmniejszenia obrazu.** Baseline uruchomił
Python **3.12.15**, kandydat **3.12.16**. Potwierdzono różne DiffID warstw bazowych,
także w powtórzeniu z `--pull`; obie linie FROM w logach rozwiązały indeks
`aa943ce…`, ale materializacja floating tagu pozostała odmienna. Przyczyny tej
rozbieżności lokalnego buildera nie ustalono ani nie zmieniano konfiguracji
Dockera. Warstwy kandydata odpowiadają oficjalnemu, zweryfikowanemu SHA-256
configowi przypiętego manifestu amd64. Są to obserwacje before/after, nie
kontrolowany eksperyment A/B ani dowód wpływu samego COPY na czas/rozmiar.

Pierwsza para bez `--pull` również przeszła: cold 23,186 → 36,719 s,
warm 1,491 → 1,847 s. Zachowano ją jako `initial-cached-base-*`;
nie wybrano wyłącznie korzystniejszego pomiaru do deklaracji przyspieszenia.

### Runtime, bezpieczeństwo i uprawnienia

Macierz dziewięciu kontroli dla każdego obrazu (18 oznaczonych kontroli) **PASS**:

- Audyt obrazu: Python 3.12, dokładne wersje wszystkich bezpośrednich requirements
  produkcyjnych, import cloud adapters bez sieci, brak pytest, Playwright, pypdf
  i PyMuPDF. Brak projektowych tests/docs/scripts/infra/.git, env, kluczy i baz
  w `/app`. SHA-256 wszystkich **78** plików aplikacji, fixture’ów i requirements
  są zgodne z manifestem kontekstu.
- Domyślny entrypoint API, `/health` po inicjalizacji DB i trasy aplikacji.
  Pięć źródłowych Trip i dziewięć przykładów GT jest dostępnych.
- Worker z niezmienionym `python -m app.worker`, jedna instancja, mock.
  Wynik zadania ma `is_mock=true`; bez płatnych providerów.
- Nowy wspólny named volume SQLite: ukończone oraz oczekujące zadanie przetrwały
  stop/start obu kontenerów; oczekujące zadanie przetworzono po restarcie.
- Zapis kopii dokumentu, nowej i poprzedniej rewizji oraz upload syntetycznego
  PNG. Po restarcie cały draft, historia i dokładne bajty znormalizowanego
  assetu pozostały identyczne.
- Efektywne UID/GID **0/0**; zapis do `/data`, Windows bind mounta Document Studio
  i `/tmp` działa dla obu obrazów, bez PermissionError w logach aplikacji.
- Readonly preview na `--read-only`, tmpfs `/tmp`, `--cap-drop ALL`, port 8000:
  health, oba warianty marketingu, baked source SHA, write denial 403 oraz brak
  prywatnych tras dokumentów. Były to rzeczywiste kontenery.
- SIGTERM przez `docker stop --time 10`: API i worker kończą z exit 0, log API
  zawiera `Application shutdown complete`. Restart zachowuje stan.

| Ścieżka QA | UID:GID / tryb | Root zapis | UID 10001 zapis |
|---|---|---|---|
| `/data` | 0:0 / 0755 | PASS | PermissionError |
| `/app/local-data/document-studio` (Windows bind) | 0:0 / 0777 nadane przez Desktop | PASS | PASS |
| `/tmp` | 0:0 / 01777 | PASS | PASS |

Próba `--user 10001:10001` była jednorazową oceną na własnym wolumenie,
nie zmianą Dockerfile/Compose. Wykazała blokadę migracji non-root dla wolumenu
utworzonego przez root. Nie wykonywano chown/chmod; 0777 bind mounta jest
obserwacją Desktopa, nie zmianą praw hosta dokonaną przez QA. USER pozostaje
bez zmian. Skan CVE, rzeczywiste IAM/IAP i Cloud Run nie były częścią tych prób.

### Istniejące testy i niepowodzenia harnessu

- `make test`: **827 PASS**, jedno istniejące ostrzeżenie Starlette/AnyIO.
- `make test-container`: **PASS** — istniejący test linux/amd64, readonly
  filesystem, port 8000, SHA, fixture’y, write denial i SIGTERM exit 0.
- `make check` i `python -m scripts.gcp.ci offline`: **PASS**.
- Kod aplikacji, Compose, workflow i kontrakty release pozostały bez zmian.

Pierwsze próby harnessu ujawniły jego błędne założenia, nie poprawki aplikacji:
sieć `--internal` nie dostarczyła oczekiwanego mapowania portu, ponowne użycie
katalogu QA zostało odrzucone, upload prawidłowo normalizuje PNG, nieobsługiwana
dowolna prośba została odrzucona przez istniejący mock, a losowy port hosta
zmienił się po restarcie. Użyto nowej dedykowanej sieci bridge, unikalnego ID
próby, porównania znormalizowanego obrazu i bajtów po zapisie, gotowych SCENARIOS
oraz ponownego odczytu portu. Nie zmieniono ani nie osłabiono testów aplikacji.
Nieudane próby zachowano osobno; końcowa macierz ma zero failures. Wszystkie
próby korzystały wyłącznie z własnych zasobów.

### Izolacja, dowody i status

Użyto nowych wolumenów `tripse-ci002-qa-db-…` i bind mountów w ignorowanym
`local-data/ci-002/acceptance/bind-…`, wyłącznie dane syntetyczne. Kontenery
nie dostały credentials; działały w mock/readonly. Nie montowano istniejących
danych użytkownika. Własne kontenery/sieci/wolumeny usuwano po sprawdzeniu ID
i etykiety. Zachowano katalogi z dowodami. Usunięto tylko cztery własne tagi
obrazów, bez globalnego prune. Wszystkie wolumeny sprzed pierwszej próby nadal
istnieją, a odciski plików CI-001 są identyczne. Bez GCP, publikacji,
commit/push/merge/deploy; współdzielonego cache Docker nie czyszczono.

Dowody i metodologia w ignorowanym `local-data/ci-002/acceptance/`:
`builds.py`, `builds_fresh.py`, `runtime.py`, manifesty wejść, build-report.json,
inspect/history, runtime-report.json, logi pytest/container/offline,
content-verification.json i cleanup-verification.json.

**Bramki:** lokalny build/runtime/persistencja — PASS; migracja USER — odłożona
z udokumentowaną blokadą; proweniencja przyszłego zatwierdzonego commita —
niezweryfikowana; cloud acceptance — NOT TESTED. Po review i commicie istniejący
pipeline nadal musi wykonać kontrole źródła i odbiór DEV przed promocją PROD.
CI-003–CI-005 nie były implementowane.

## Historyczna próba Container Acceptance — 2026-10-29T10:14:08+01:00

**Wynik: nadal BLOCKED.** Odczytano raport, plan/ADR, Dockerfile, oba pliki
ignore, Compose oraz source allowlist i build proof. Implementacji nie zmieniano.
Gałąź i baza pozostały zgodne z opisem powyżej. CI-001 nie było modyfikowane.

| Preflight | Obserwacja |
|---|---|
| `docker context show` | `desktop-linux`, exit 0 |
| `docker context inspect desktop-linux` | endpoint `npipe:////./pipe/dockerDesktopLinuxEngine`, exit 0 |
| `docker version` i wariant JSON | klient 29.6.1 / API 1.55 / windows-amd64; server null; exit 1 |
| `docker info` | sekcja Server kończy się błędem połączenia; exit 1 |
| Daemon OS/arch, CPU i przydzielona pamięć | Niedostępne — nie wywodzimy zasobów demona z konfiguracji hosta |

Dokładny błąd: `open //./pipe/dockerDesktopLinuxEngine: The system cannot find
the file specified.` Potwierdza brak dostępu do endpointu; nie rozstrzyga, czy
Desktop jest zatrzymany, uruchamia się, czy ma inną usterkę. Nie zmieniano jego
konfiguracji i nie uruchamiano go automatycznie.

Zgodnie z warunkiem przerwania nie wykonywano buildów bazowego/CI-002 obrazu,
nie tworzono tagów, kontenerów ani wolumenów QA i nie zastępowano wyników
symulacją. Tabela before/after pozostaje **Not measured**. Nie obchodzono
clean-head ani reguł pochodzenia źródła dla niezacommitowanej zmiany.

| Zakres odbioru w tej próbie | Wynik |
|---|---|
| Image size, warstwy i ich rozmiary, cold/warm build | NOT MEASURED — brak demona |
| Kontenerowy API startup, `/health`, mock API i worker | NOT RUN — brak demona |
| Wspólna SQLite, zapisy Document Studio i zachowanie stanu po restarcie | NOT RUN — brak demona |
| Readonly preview, fixture’y, SIGTERM/graceful shutdown | NOT RUN — brak demona |
| Efektywne UID/GID i zapis do `/data`, `/app/local-data/document-studio`, `/tmp` | NOT RUN — brak demona; non-root nie wdrażano |
| Używalność pinu, Python/dependencies oraz brak dev packages/sekretów w gotowym obrazie | NOT VERIFIED — metadane i testy statyczne nie zastępują inspekcji obrazu |
| `python -m pytest tests/test_docker_image_contract.py -q` | **5 PASS**, 0 FAIL |
| `python -m scripts.gcp.ci offline` | **PASS**, bez cloud credentials ani operacji GCP |
| Rzeczywisty Cloud Run / IAP | NOT TESTED — poza lokalnym odbiorem |

Nowe dowody: ignorowane `local-data/ci-002/acceptance-preflight.json`,
`acceptance-static-tests.log` i `acceptance-offline.log`. Wynik 827 testów
w dalszej części jest wynikiem wcześniejszej implementacji; pełnej regresji nie
powtarzano dla samej aktualizacji raportu. Nie uruchamiano ponownie testu
kontenerowego po negatywnym preflight. Status CI-002 nie został podniesiony.
Nie wykonano operacji GCP, publikacji, push/merge/deploy, zmian własności hosta
ani kasowania/zmian istniejących danych i wolumenów. Kolejny warunek to dostępny
lokalny Linux Engine; dopiero wtedy można wykonać procedurę odbioru poniżej.

## Historyczny baseline przed uruchomieniem Engine

Windows/amd64, AMD Ryzen 3 3100, 8 logicznych procesorów. Docker CLI 29.6.1,
API 1.55, kontekst `desktop-linux`. `docker version` zgłasza brak named pipe
`dockerDesktopLinuxEngine`. Silnik Linux nie działa; nie uruchamiano Desktopa,
nie zmieniano konfiguracji hosta ani nie zatrzymywano kontenerów użytkownika.

Nie udało się zbudować bazowego ani zmienionego obrazu. `make test-container`
przerwał się przy lokalnym `docker build` z kodem błędu; nie jest to dowód
regresji Dockerfile, bo dostęp do daemon był niedostępny już przed zmianami.
Nie mierzono rozmiaru, historii warstw aplikacji, warstwy zależności, startupu,
gotowości `/health` ani rzeczywistych UID/GID i praw Linux. Nie deklarujemy ich
poprawy na podstawie testów Windows.

| Metric | Before | After | Difference |
|---|---|---|---|
| Image size | Not measured | Not measured | Not measured |
| Dependency installation layer size | Not measured | Not measured | Not measured |
| Cold Docker build | Not measured | Not measured | Not measured |
| Warm Docker build | Not measured | Not measured | Not measured |
| API startup | Not measured | Not measured | Not measured |
| Time to healthy | Not measured | Not measured | Not measured |
| Runtime user | Root inferred from base config; not executed | Unchanged; not executed | No USER migration |
| Security findings | Mutable base tag; broad demo COPY | Digest pin; GT-only COPY; additional context exclusions | Static controls implemented; runtime not verified |

## Zweryfikowany obraz bazowy

Przed zmianą odczytano anonimowo oficjalny Docker Hub Registry API dla
`docker.io/library/python:3.12-slim`. Nie pobierano ani nie drukowano prywatnych
credentials. SHA-256 odpowiedzi manifestu i config blob porównano z ich digestami.

- Multi-platform index:
  `sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159`.
- Linux/amd64 manifest:
  `sha256:1148dbb014615300fa7e713b2f94f550c0d1c69780c0805f84f093ceee34dd0b`.
- Config: `sha256:ae4e8b7c575fabea88a029b6cae757f342ca2525e07f7c22272d5105c346b35e`.
- Metadane configu: `PYTHON_VERSION=3.12.16`, `os=linux`, `architecture=amd64`,
  `User=""` (domyślny root). Są to metadane, nie wynik uruchomienia kontenera.
- Index ma również linux/arm64 i inne warianty; pin nie ogranicza Dockerfile
  do amd64. Cloud Build i test kontenerowy zachowują dotychczasową platformę.

Manifest bazowy ma cztery skompresowane warstwy: 29 855 236, 1 289 740,
12 121 979 i 251 bajtów. **Nie są to Docker image size ani warstwa zależności
TRIPSE** i nie są używane jako baseline rozmiaru aplikacji.
Dowody odczytu: ignorowane `local-data/ci-002/base-index.json`, `base-metadata.json`.

Pin indeksu utrzymuje rodzinę Python 3.12-slim i stabilizuje wybór bazowego
obrazu. Nie oznacza automatycznie braku podatności ani pełnej reprodukowalności
niezablokowanych zależności przechodnich pip.
[Docker opisuje kompromis digest pinning i aktualizacji bezpieczeństwa](https://docs.docker.com/build/building/best-practices/#pin-base-image-versions);
[oficjalny obraz Python](https://hub.docker.com/_/python).

## Zmiany implementacyjne

| Plik | Zmiana i powód |
|---|---|
| `Dockerfile` | Ten sam tag Python 3.12-slim przypięty digestem indeksu; komentarz z datą i runbookiem odświeżenia. COPY fixture’ów ograniczony do `demo-fixtures/gt-v1`, wymaganego przez obecne modele i renderer. |
| `.dockerignore`, `.gcloudignore` | Dodatkowe wykluczenia `.tmp`, `.worktrees`, output/tmp, node_modules, cache narzędzi, coverage, pyc/pyo, logów i kontenerów kluczy p12/pfx. Zachowano wcześniejsze wykluczenia env, prywatnych kluczy, danych, testów, docs, infra i credentials. |
| `tests/test_docker_image_contract.py` | Pięć testów statycznych: pin i entrypoint, kolejność warstw, dozwolone COPY i źródła, obie listy wykluczeń, wspólny model wolumenów API/workera. |
| Dokumentacja i tracking | Ten raport, status CI-002 w planie, instrukcja deploymentu, notatki ADR-0015/indeks i worklog. |

Nie dodano narzędzi kompilacji ani pakietów systemowych. Pozostaje instalacja
wyłącznie `requirements.txt`, `pip install --no-cache-dir` i warstwa zależności
przed aplikacją. Wszystkie wersje pakietów pozostają bez zmian. Build multi-stage
nie ma wykazanej korzyści: obecny obraz nie zawiera osobnego toolchainu do usunięcia.
Nie dodano drugiego obrazu, nowego entrypointu, process managera ani healthchecka.

## Użytkownik, storage i decyzja o non-root

Obraz jest wspólny dla API i workera. `compose.yaml` nadal uruchamia worker jako
`python -m app.worker`, z tym samym wolumenem SQLite co API.

| Ścieżka | Potrzeba i granica |
|---|---|
| `/app/app`, `/app/demo-fixtures/gt-v1` | Źródła, assety statyczne i fixture’y do odczytu. `PYTHONDONTWRITEBYTECODE=1` zachowane. |
| `/data/tripse.sqlite3` i katalog `/data` | API i worker muszą tworzyć/zmieniać DB oraz pliki towarzyszące SQLite. Istniejący named volume `tripse_data` pozostaje wspólny. |
| `/app/local-data/document-studio` | Bind mount hosta: katalogi Trip/Campaign/Draft, rewizje, metadane, atomic temp files i assety. API wymaga zapisu; worker nie dostaje tego mounta. |
| `/tmp` | Systemowe pliki tymczasowe; uprawnienia i read-only wariant trzeba sprawdzić w Linux. |
| `readonly_demo` | Nie tworzy lokalnej bazy ani repozytorium dokumentów; istniejący test kontenerowy używa read-only rootfs i tmpfs `/tmp`. |
| `cloud_demo` | Wspólne SDK/adapters GCS/Firestore/Tasks i IAP pozostają bez zmian; fake SDK tests nie potwierdzają rzeczywistych IAM ani runtime Linux. |

**Nie wprowadzono USER ani chown/chmod.** Aktualna próba na własnym syntetycznym
wolumenie wykazała PermissionError dla UID 10001 w `/data`; Windows bind i `/tmp`
były zapisywalne. To dowód blokady migracji przy obecnym modelu storage.
Istniejących danych użytkownika nie montowano. Zmiana USER pozostaje odłożonym
follow-up; nie zmieniano własności hosta, istniejących wolumenów ani praw chmod.

## Zachowany kontrakt Cloud Run i proweniencja

CMD pozostaje exec-form Uvicorn: `app.main:app`, bind `0.0.0.0`, port `8000`,
`--no-access-log`, graceful shutdown 8 s. Zachowano zmienne, tryby local,
readonly_demo, cloud_demo, istniejące `/health`, startup/shutdown i kontrolę IAP.

`source_files()` nadal eksportuje wyłącznie zatwierdzone pliki wybranego SHA.
Oba nowe COPY mają wszystkie wejścia w istniejącej allowliście. Nie rozszerzano
jej. Baked `_build_version.txt`, kontrola digestu obrazu, immutable tags,
source archive verification i akceptacja DEV → promocja PROD pozostają identyczne.

**Nie zmieniono** `scripts/gcp/deployment.py`, `build_proof.py`,
`deployment_contract.py` ani workflow. Receptura nadal wymaga jednego Cloud Build
Docker kroku `build --network cloudbuild --no-cache -t IMAGE:SHA .`.
Cache lokalnego Dockera nie został dodany do release path. Nie wykonano GCP
builda, publikacji obrazu, wdrożenia, rollbacku ani zmian IAM/Terraform.

## Historyczna walidacja pierwszej implementacji

Aktualne wyniki kontenerowe są w sekcji odbioru powyżej. Poniżej zachowano
wcześniejszy stan z niedostępnym silnikiem.

| Kontrola | Wynik / granice |
|---|---|
| `make test` | **827 PASS**, jedno istniejące ostrzeżenie Starlette/AnyIO. Pięć nowych testów jest częścią tej liczby; CI-001 nie jest częścią tej bazy. |
| `python tests/browser_hub_smoke.py` | PASS: rzeczywiste lokalne procesy mock API/workera, zapis/odczyt wspólnej SQLite, planer i chat oraz UI. Bez płatnych providerów. Nie jest to próba kontenera ani Linux volume permissions. |
| `python -m scripts.gcp.ci offline` | PASS: source/provenance i tryby preview, bez cloud credentials/deploymentu. |
| `make check` | PASS: diff i `docker compose -f compose.yaml config --quiet`, bez uruchomienia usług. |
| `make test-container` | **BLOCKED / exit nonzero**: brak daemon już w baseline; build/readonly-runtime/SIGTERM test nie został wykonany. |
| Zmodyfikowany obraz z committed/allowlisted source | NOT VERIFIED: zmiany są niezacommitowane zgodnie z poleceniem; nie nadano im fałszywej tożsamości SHA i nie obchodzono clean-head gate. |
| Container API/worker writable mounts i restart | NOT VERIFIED: wymagają silnika Linux. |
| Cloud Run runtime i rzeczywiste IAP | NOT TESTED: wdrożenie poza zakresem; zachowano i przetestowano kontrakty offline. |

Logi QA pozostają w ignorowanym `local-data/ci-002/`. Nie zmieniano danych
biznesowych, nie resetowano DB i nie przenoszono zawartości istniejących mountów.

## Procedura referencyjna odbioru zatwierdzonego commita

Lokalną macierz wykonano powyżej na jawnie opisanym overlayu QA. Po review
i commicie nadal wymagane są istniejące kontrole proweniencji wydania.

1. Operator uruchamia lokalny Linux Engine. Zachować bieżące wolumeny/dane.
   Po osobnym przeglądzie i commicie przygotować dla wybranego SHA allowlistowany
   kontekst przez obecny `source_files()` i baked SHA, bez developer working tree.
2. Zbudować lokalny obraz tej bazy i zmiany, rejestrując `docker version/info`,
   `docker image inspect`, `docker history --no-trunc`, rozmiar warstwy pip,
   cold `docker build --no-cache` i zwykły powtórzony warm build. Nie zmieniać
   receptury Cloud Build ani nazywać lokalnego warm cache wdrożeniem CI-003.
3. `make test-container`: sprawdzić readonly_demo, fixture’y, baked SHA, write
   denial i SIGTERM. Zweryfikować Python 3.12, brak dev packages i wykluczonych
   plików w obrazie. Brak cache w pip nie dowodzi sam w sobie małego obrazu.
4. Na **nowych syntetycznych** named volume i katalogu bind QA uruchomić API
   i worker z dotychczasowymi poleceniami, mock i wspólną SQLite. Zmierzyć czas
   startu procesu i first successful `/health` osobno; zapisać UID/GID i prawa.
   Utworzyć job, poczekać na wynik, zapisać dokument i asset, zrestartować oba
   procesy i potwierdzić zachowanie danych. Nie montować danych biznesowych.
5. Próby non-root wykonać osobno dla nowych oraz istniejących formatów wolumenów
   i Windows bind mounta. Dopiero dowód poprawnego zapisu API/workera uzasadnia
   zmianę USER. Nie naprawiać niepowodzenia masowym chown/chmod hosta.
6. Uzupełnić porównanie i odbiór CI-002. Ewentualne rzeczywiste cloud_demo/IAP
   wymaga odrębnie zatwierdzonego wdrożenia, nie automatycznej operacji tego zadania.

## Utrzymanie, rollback i CI-003

Przeglądać oficjalny digest przy wydaniach bezpieczeństwa Python/Debian i regularnie
w utrzymaniu. Każde odświeżenie: odczytać nowy index/amd64 config, sprawdzić rodzinę
Python 3.12, zaktualizować pin i raport, wykonać unit oraz container/API/worker
smoke na syntetycznych danych, dopiero potem osobny review/release. Pin zamraża
również aktualizacje bezpieczeństwa; sam udany odczyt manifestu nie zastępuje skanu.

Rollback: przed commitem wycofać wyłącznie przejrzany patch CI-002, bez resetu
CI-001; po commicie przygotować revert tych zmian. Poprzednio zaakceptowany
digest wydania pozostaje dostępny w istniejącym procesie rollbacku; tego procesu
nie uruchamiano. Nie usuwać danych ani wolumenów.

CI-003 pozostaje osobnym benchmarkiem buildera/cache z porównywalnym źródłem,
bez publikacji i bez podmiany Cloud Build. Nie wdrożono Buildx, cache warstw,
nowego rejestru ani żadnego elementu CI-003–CI-005. ADR-0015 pozostaje proposed.
