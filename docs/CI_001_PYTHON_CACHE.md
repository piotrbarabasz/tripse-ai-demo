# CI-001 — Python CI: cache pip i pomiary

CI-006 integration note (2026-10-29): this is the historical isolated-task report.
The selected implementation is now in the local integration candidate; current
combined validation and outstanding committed-source/hosted/cloud gates are in
[CI-006](CI_006_INTEGRATION_ACCEPTANCE.md). Original measurements below remain
attributed to their original worktree and source, not to a new release SHA.

Phase B update: operator-approved PR #7 now exercises this cache configuration.
Actual hosted runs, exact/miss/fallback classification, native step timings and
historical-baseline comparison are recorded in [CI-006](CI_006_INTEGRATION_ACCEPTANCE.md).
The original isolated-task status and measurements below remain historical.

2026-10-29, repozytorium `piotrbarabasz/tripse-ai-demo`.
Baza: `777e0662da5e57894371529f3af0bdafeb2fed11`. Gałąź do przeglądu:
`ci/ci-001-python-cache`. Zmiany lokalne; bez commita, pusha, uruchomienia workflow
i wdrożenia. Dotyczy wyłącznie CI-001 z [planu](ARTIFACT_REGISTRY_CICD_PLAN.md).

| Bramka | Stan |
|---|---|
| Implementacja lokalna | Gotowa |
| Walidacja lokalna | PASS, szczegóły poniżej |
| Walidacja nowej konfiguracji na GitHub Actions | NOT VERIFIED — nie wysłano gałęzi |
| Potwierdzona poprawa wydajności cold/warm | Not measured |
| CI-002–CI-005 | Bez zmiany statusu, niewdrażane w tym zadaniu |
| ADR-0015 | Nadal `proposed`; implementacja lokalna nie jest akceptacją ADR |

## Zmiana

Istniejący, przypięty SHA `actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065`
zachowuje Python `3.12` i otrzymuje:

```yaml
cache: 'pip'
cache-dependency-path: |
  requirements.txt
  requirements-dev.txt
```

Konfiguracja jest w trzech niezależnych jobach: `ci.yml/checks`,
`delivery.yml/dev`, `delivery.yml/prod`. Wszystkie nadal bezwarunkowo wykonują
`make install-dev`. Każdy runner tworzy własny `.venv`; ten katalog nie jest
cache'owany ani przekazywany między jobami. Cache obejmuje katalog pobrań/wheels
pip określany przez przypiętą akcję. Nie obejmuje aplikacji, danych, assetów,
konfiguracji GCP, ADC ani artefaktów wydania.

Nazwy kroków jasno rozróżniają instalację Python/cache, zależności, pytest,
kontrakty offline, Chromium i browser QA. Dodane podsumowanie `always()` zapisuje
wyłącznie sklasyfikowany wynik cache oraz wskazanie natywnych pomiarów Actions.
Nie wypisuje środowiska, tokenów, ścieżek ani konfiguracji wdrożenia. Działa też
po nieudanym setupie, bez zależności od `.venv`.

## Klucze, unieważnianie i bezpieczeństwo

Sprawdzono implementację dokładnie przypiętej akcji:
[pip-cache.ts](https://github.com/actions/setup-python/blob/a26af69be951a213d495a4c3e4e4022e16d87065/src/cache-distributions/pip-cache.ts),
[cache-distributor.ts](https://github.com/actions/setup-python/blob/a26af69be951a213d495a4c3e4e4022e16d87065/src/cache-distributions/cache-distributor.ts).
Klucz zależy od platformy, architektury, wersji systemu Linux, rozwiązanej wersji
Pythona i hashFiles obu jawnie wskazanych plików. Zmiana dowolnego requirements
zmienia dokładny klucz. Nie definiujemy drugiego generatora kluczy w projekcie.

Akcja może odtworzyć starszy cache przez klucz zapasowy bez hasha zależności.
Dlatego `cache-hit=true` oznacza dokładne trafienie, natomiast `false` może
oznaczać brak cache, fallback albo niedostępność usługi cache. Samo `false` nie
jest dowodem cold run. Log setup-python rozróżnia odtworzony klucz od
`pip cache is not found`. Nowe zależności nadal instaluje pip; pełny install
nie jest warunkowany wynikiem cache. Wersje bezpośrednie pozostają przypięte;
przechodnie nie mają nowego lockfile i mogą zmieniać się niezależnie od cache.

PR pozostaje bez tożsamości chmurowej i z `contents: read`. Nie dodano
`id-token: write`, uprawnień Actions ani nowej akcji cache. Zasady widoczności
cache są natywnymi zasadami GitHub; cache zależności nie jest kanałem przekazywania
sekretów ani dowodów wydania. Nie zmieniono środowisk, WIF, concurrency, refów,
pinów akcji, akceptacji DEV, promocji tego samego digestu, rollbacku i artefaktów.

## Baseline przed implementacją

Odczytano ostatnie udane runy i metadane jobów/stepów. Connector udostępniał
nazwy i statusy, ale pomijał znaczniki czasu; czasy pobrano read-only przez
`gh api repos/piotrbarabasz/tripse-ai-demo/actions/jobs/{job_id}`.
Różnica `completed_at - started_at` ma rozdzielczość jednej sekundy.
Wartość 0 s dla setupu jest odczytem API, nie deklaracją braku kosztu.

| Metryka | PR CI, job 123328693692 | Delivery CI, job 123328685515 | Master Delivery CI, job 123330868661 |
|---|---:|---:|---:|
| Python setup | 0 s | 0 s | 0 s |
| `make install-dev` | 14 s | 15 s | 13 s |
| `make test` | 25 s | 35 s | 27 s |
| Kontrakty offline | 2 s | 1 s | 1 s |
| Chromium i biblioteki systemowe | 17 s | 18 s | 23 s |
| `make test-browser` | 175 s | 191 s | 179 s |
| Cały job CI | 239 s | 264 s | 249 s |

Pierwsze dwie kolumny dotyczą bazowego SHA `777e066…`, runów
[40838439862](https://github.com/piotrbarabasz/tripse-ai-demo/actions/runs/40838439862)
i [40838437350](https://github.com/piotrbarabasz/tripse-ai-demo/actions/runs/40838437350).
Pierwszy run jest primary baseline tej zmiany. Trzecia kolumna to SHA `c3d3e922…`,
run [40839099491](https://github.com/piotrbarabasz/tripse-ai-demo/actions/runs/40839099491),
więc jest dodatkową obserwacją, nie identyczną próbą porównawczą.
Przed zmianą workflow nie miał jawnego cache pip; nie nazywamy tych uruchomień
kontrolowanymi próbami cold cache ani eksperymentem A/B.

W ostatnim runie Delivery niezależny DEV job `123332443318` trwał 226 s,
instalacja Python dependencies 16 s, instalacja Chromium 21 s. PROD job
`123333860790` trwał 131 s, instalacja zależności 14 s; nie instalował Chromium.
Razem trzy instalacje zależności tego runu zajęły 43 s na odrębnych runnerach.
To koszt wymaganych instalacji, nie dowód, że można je usunąć.

## Przegląd powtarzanej pracy

Nie znaleziono powtórnej instalacji zależności w tym samym jobie. CI testuje,
DEV uruchamia koordynator i browser acceptance, PROD weryfikuje dowody oraz
promuje obraz. Każdy potrzebuje własnych pakietów. Chromium jest w CI i DEV,
gdzie przeglądarka jest używana; PROD już go nie instaluje.

Nie usunięto `make install-dev`, nie dzielono requirements i nie warunkowano
instalacji cache-hitem. Węższy zestaw deployment dependencies, cache Chromium
lub podział browser QA wymagają odrębnego pomiaru i przeglądu kontraktów.
CI-001 nie zmienia Cloud Build ani sposobu tworzenia obrazu.

## Pomiary po zmianie i procedura hosted cold/warm

| Metryka | Before: primary baseline | After | Difference |
|---|---:|---|---|
| Dependency installation | 14 s | Not measured | Not measured |
| Pytest | 25 s | Not measured | Not measured |
| Browser setup | 17 s | Not measured | Not measured |
| Browser QA | 175 s | Not measured | Not measured |
| Total CI | 239 s | Not measured | Not measured |

Nie wykonano push/dispatch/rerun. Zysk i koszt odtworzenia/zapisu cache nie są
jeszcze zmierzone. Natywne czasy Actions są źródłem pomiaru; summary pokazuje
stan cache i przypomina o kosztach post-action. Nie dodano tokena/API telemetry
do credential-free PR ani wrapperów zmieniających propagację błędów poleceń.

Po osobnym opublikowaniu i przeglądzie gałęzi operator powinien:

1. Uruchomić wyłącznie workflow **CI**, na tej gałęzi, dwa razy dla tego samego
   SHA. Nie używać Delivery do benchmarku. Drugą próbę rozpocząć po zakończeniu
   pierwszej wraz z post-action zapisu cache.
2. Zapisać run/job ID, attempt, SHA, Python patch, obraz runnera, wynik każdego
   kroku, `cache-hit` i komunikat o kluczu cache. Użyć tych samych nazwanych kroków
   oraz `started_at`/`completed_at` i całkowitego czasu jobu, łącznie z post-action.
3. Cold uznać za wykazany tylko po logu potwierdzającym brak odtworzenia cache.
   Pierwszy run może otrzymać fallback z dozwolonej gałęzi. Nie usuwać cudzych
   cache w celu benchmarku; gdy brak czystej próby, jawnie odnotować ograniczenie.
4. Warm potwierdzić przez dokładne trafienie klucza w drugim runie. Powtórzyć
   kilka równoważnych prób; nie przypisywać cache naturalnych wahań browser QA.
5. Na osobnej gałęzi testowej zmienić komentarz w każdym requirements osobno,
   sprawdzić zmianę dokładnego klucza, nadal wykonywaną instalację i pełne testy.
   Fallback może pozostać skuteczny; nie jest to brak unieważnienia klucza.
6. Uzupełnić tabelę dopiero dla porównywalnych, zakończonych sukcesem prób.
   Hosted acceptance wszystkich trzech miejsc cache pozostaje otwarta; nie
   uruchamiać DEV/PROD tylko dla pomiaru bez odrębnej autoryzacji wdrożenia.

## Walidacja lokalna

- `actionlint` 1.7.12: oba workflow PASS. Narzędzie pobrano z oficjalnego wydania,
  ZIP sprawdzono względem opublikowanego SHA-256; pliki narzędzia są ignorowane.
- `tests/test_ci_python_cache.py`: 22 PASS. Sprawdza trzy joby, oba wejścia cache,
  zmianę każdego pliku, bezwarunkowy install, zachowane polecenia CI i podsumowanie
  wykonane w Bash: exact hit, brak exact hit, setup failure, niezaufana wartość
  i brak wycieku canary. Test fingerprintu sprawdza wejścia, nie emuluje usługi GHA.
- Ukierunkowane cache/CI/bootstrap/deployment/PROD contracts: 218 PASS.
- `make test`: 844 PASS, jedno istniejące ostrzeżenie Starlette/AnyIO.
- `python -m scripts.gcp.ci offline`, `make check` (diff i Compose config)
  oraz końcowe `git diff --check`: PASS, bez połączenia do GCP.
- Porównanie sparsowanych workflow z bazą: po odjęciu wyłącznie cache, nazw
  kroków, identyfikatora setupu i nowego summary wszystkie pozostałe pola są
  identyczne, w tym pełne joby i kolejność istniejących kroków.
- Cold-cache install: `make install-dev` w nowym lokalnym `.venv`, początkowo
  nieistniejący `PIP_CACHE_DIR`, jawne publiczne PyPI i pominięta lokalna konfiguracja
  pip — PASS, 31,25 s. Poprzednią próbę z konfiguracją hosta zatrzymano po błędach
  DNS. Nie zmieniano tej konfiguracji. Wynik Windows nie jest pomiarem hosted CI
  ani dowodem działania usługi cache GitHub.

Dowody lokalne: ignorowane `local-data/ci-001/` (baseline JSON, logi testów,
wynik cold install). Brak pomiarów warm na GitHub i brak porównania procentowego.

## Bezpieczeństwo, rollback i następny etap

Brak zmian aplikacji, pakietów, Makefile, Dockerfile, IAM/Terraform, rejestru,
Cloud Build/Run i koordynatora wdrożeń. Nie zmieniono GCP ani ochrony DEV/PROD;
nie wywołano wdrożenia. Zmiany są na izolowanej gałęzi, bez push/merge.
Rollback: cofnąć wyłącznie opcje cache/summary/nazwy kroków; wszystkie pierwotne
polecenia są zachowane. Nie trzeba usuwać cache ani danych.

Następny zakres to **CI-002**: audyt istniejącego obrazu API, pomiary rozmiaru
i startu, ocena digestu base image, uprawnień użytkownika i zapisywalnych katalogów
przy zachowaniu portu 8000, źródła obrazu i trybów aplikacji. CI-002 nie został
zaimplementowany w tym zadaniu.
