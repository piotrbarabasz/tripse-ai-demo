# TRIPSE Cloud Run — ręczne DEV i PROD

## CLOUD-PARITY-001 — opt-in authenticated demo (2026-10-26)

Prepared offline; **no GCP resources or deployed services were changed**. The
historical sections below describe `readonly_demo`. Full authenticated demo is
governed by [ADR-0011](adr/0011-authenticated-cloud-demo.md) and the
[audit/acceptance matrix](CLOUD_PARITY_AUDIT.md). Keep current PROD configuration
and data intact. No automatic migration, deployment or promotion is performed.

### Configuration and access

Use existing Make/deployment commands and the existing project/region/image
registry. In an operator-reviewed DEV configuration directory, keep both dotenv
files and change **only DEV** to `CLOUD_FEATURE_MODE=cloud_demo` and
`GCP_PUBLIC_ACCESS=false`. Uncomment/fill every required field shown in
`infra/gcp/.env.dev.example`; values are literal and no interpolation occurs.
Resources must use exactly the selected environment's names. `PUBLIC_BASE_URL`
is the existing service's reviewed HTTPS `run.app` origin. Members are explicit
email addresses separated by `|`; `DEMO_READERS=` is allowed, editors cannot be empty.
Readers can read internal demo documents; only editors can mutate them. Members
share Studio data inside an environment. Jobs, viewer tokens and conversations
are scoped to the verified IAP subject as well as environment.

Direct IAP protects `run.app` without a load balancer or custom domain:
[Google setup](https://docs.cloud.google.com/run/docs/securing/identity-aware-proxy-cloud-run).
Bootstrap the custom OAuth client and IAP service agent in Console, initially on
DEV only. For external Google accounts configure External audience, consent/test
users as required, and explicit IAP access. A non-Workspace Google account works;
non-Google identities require a separate Identity Platform/federation design and
validation. No broad domain, allUsers or allAuthenticatedUsers grant is needed.
Mirror approved members in IAP and the application lists. Remove revoked users
from both. Never use unsigned identity headers as proof of authorization.

The application verifies the ES256 IAP signature and service-specific audience
`/projects/PROJECT_NUMBER/locations/europe-central2/services/tripse-ai-dev`, issuer,
subject, email and time claims:
[signed-header contract](https://docs.cloud.google.com/iap/docs/signed-headers-howto).
It also requires exact configured Origin for writes, rejects cross-site requests,
protects private images/frontend assets and disables public API docs. `/health`
is the probe exception and returns only deployment metadata, not private data.

### Declarative resources and least privilege

`infra/gcp/cloud-demo/main.tf` is an additive, opt-in module. It does not own
existing Cloud Run services or deploy images. Review/import existing matching
resources before applying; do not create duplicate resources or overwrite state.
Use distinct secured Terraform state for DEV/PROD, and do not commit tfvars,
state or plan files. The checked provider lock is included. After an operator
chooses to provision DEV, the sequence is:

1. Bootstrap external custom OAuth/IAP on DEV and establish the IAP and Tasks
   service agents. Existing zero-role runtime identities come from `make gcp-setup`.
2. Copy `dev.tfvars.example` to a private tfvars file; replace project identity and
   approved human members. `terraform init`, `terraform validate`, then review a
   DEV-only plan before an explicitly authorized apply. No `destroy` or PROD apply.
3. Verify bucket public-access prevention, uniform access, versioning/soft delete;
   database PITR/delete protection; separate queue/task account. Runtime gets only
   bucket object access, database-conditioned `datastore.user`, queue enqueue and
   actAs on its dedicated task account. The Tasks agent mints tokens for that
   account; the IAP agent invokes the selected Run service. The task account has
   IAP access but no document/API membership in the application.
4. For Tasks OIDC, configure the reviewed OAuth client in IAP's programmatic
   access allowlist and grant the dedicated task caller IAP access. OAuth client
   ID is the task token audience; the application's signed-header audience is the
   Cloud Run resource path. These are different values. A Google-managed default
   OAuth client is insufficient for this OIDC flow:
   [programmatic auth](https://docs.cloud.google.com/iap/docs/authentication-howto).
5. Acquire an operator IAP token through the approved OAuth flow and set
   `CLOUD_DEMO_SMOKE_TOKEN` **only in the shell**, never dotenv, argv, logs or Git.
   Inspect configured OAuth consent/programmatic access before deployment.

Optional browser Maps uses a pinned Secret Manager reference
`GCP_BROWSER_MAPS_SECRET=projects/PROJECT/secrets/tripse-ai-dev-maps-browser/versions/N`.
Grant `secretAccessor` only on that environment's secret, using the module's
`live_secret_ids` list (references only; no payloads/state). Configure Maps JS API
and exact referrer restrictions/budget first. Never reuse a server key. The
application deliberately returns the browser key to its authenticated browser;
it is distinct from OpenAI/Places/Routes keys. Leaving this reference unset keeps
the schematic map and makes no Google Maps request. No server provider secrets
are accepted in either cloud mock mode. Future live secrets need separate IDs,
Secret Manager injection, quotas and a reviewed deployment extension; LIVE is
currently rejected for both DEV and PROD.

### Staged rollout and acceptance

Before building, commit reviewed changes so the image SHA represents the source.
Continue using immutable SHA tags/digests; never `latest`:

```powershell
make test
make test-browser
make gcp-preflight ENV=dev OFFLINE=1 CONFIG_DIR=PRIVATE_CONFIG_DIRECTORY
make gcp-dry-run ENV=dev CONFIG_DIR=PRIVATE_CONFIG_DIRECTORY
# Only following a separate operator deployment decision:
make gcp-build ENV=dev CONFIG_DIR=PRIVATE_CONFIG_DIRECTORY
make deploy-dev TAG=FULL_COMMIT_SHA CONFIG_DIR=PRIVATE_CONFIG_DIRECTORY
make gcp-smoke ENV=dev TAG=FULL_COMMIT_SHA CONFIG_DIR=PRIVATE_CONFIG_DIRECTORY
```

The cloud deployment branch uses IAM enforcement plus `--iap`, verifies the
reviewed origin and runs authenticated read smoke. It never calls `publish`.
Preview retains private smoke followed by its existing public-access procedure;
preview rollback explicitly disables IAP before optional preview publication.
Cloud offline preflight validates configuration only; full fake-adapter/router
coverage is in pytest/browser smoke, and neither proves deployed IAM behavior.

Controlled DEV acceptance is supplied and **has not been run against GCP**:

```powershell
.venv\Scripts\python.exe -m scripts.gcp.parity_smoke --config-dir PRIVATE_CONFIG_DIRECTORY
# Separate operator choice: persist synthetic fixtures and enqueue mock jobs:
.venv\Scripts\python.exe -m scripts.gcp.parity_smoke --config-dir PRIVATE_CONFIG_DIRECTORY --allow-writes
```

The write smoke creates a clearly named 15-day trip, offer/pilot, campaign and
photo, verifies 409 conflicts and runs planner/chat mock jobs, dedup and token
expiry. It leaves synthetic data for investigation and prints its trip ID.
It performs no deploy or paid generation. Separately verify browser forms,
image upload, A4/social printing, and an operator-triggered DEV revision restart
followed by read-back of the printed ID. Use two authenticated users to verify
job/conversation/viewer isolation and read-only membership. Attempt access using
the DEV runtime identity to each PROD bucket/database/queue and vice versa;
expect IAM denial. Record the tested identities, revision and digest. Verify
an expired/forged IAP assertion, missing/cross-site Origin, and anonymous private
document/image denial. Never accept an IAP login HTML page as a successful API read.

### Retry recovery and backups

Tasks retries delivery up to 12 times within one hour; job processing has a
120-second fenced lease and at most 3 claims. Mock semantic failures are terminal.
The simulator's delivery-failure case exercises one durable retry. Terminal
results/outbox commit together. Named tasks prevent ambiguous enqueue duplication.
Clients retain idempotency/event keys across failed submission retries; cloud
POST `/api/trips` accepts an optional `Idempotency-Key` UUID (the shared UI supplies
it). Existing JSON-only clients still receive 202; without a key, repeated POSTs
are separate submissions and cannot recover an ambiguous enqueue as one request.

Enqueue and Firestore cannot commit atomically. Failed enqueue returns 503 with
the job retained. Retry the same key/event, or inspect task/log/job state and use
the explicit recovery command after an expired lease/queue exhaustion:

```powershell
.venv\Scripts\python.exe -m scripts.gcp.recover_job --environment dev --trip-id JOB_UUID --config-dir PRIVATE_CONFIG_DIRECTORY
```

This uses ADC and creates a replacement task only for a nonterminal expired job;
it does not reset attempts or run generation locally. No automatic reconciler is
included. Monitor queued/running age and terminal failures during DEV acceptance.

GCS keeps object versions and seven-day soft delete; noncurrent versions are
bounded by the configured newer-version count. Firestore PITR is enabled. These
are the baseline recovery strategy, not proof of restore readiness. Before
customer data or PROD acceptance, perform a DEV restore drill into isolated
resources: restore a prior document generation with generation-match against the
current generation; check its referenced immutable image blobs; recover a
Firestore PITR copy; verify jobs/tokens without replaying notifications. Preserve
current data before restoring. Define retention/RPO/RTO and independently managed
exports if required; budget storage, access controls and maintenance. No backup
restore or deletion has been executed in this task.

PROD remains unchanged until a separate manual acceptance and promotion of the
tested DEV digest (`make deploy-prod TAG=... CONFIRM=prod`). Create/review separate
PROD resources and configuration first; no copying DEV drafts, photos, jobs or
tokens into PROD. Keep the previous SHA and matching mode configuration for
`make gcp-rollback ENV=... TAG=... CONFIRM=rollback`. Rollback changes code, not
stored data; retain format compatibility and take a backup before any future
schema migration. No automatic migration or promotion exists.

See audit for separate cost categories and OPEN/BLOCKED gates. No hours or
billed amounts are available. DEV is for experiments; PROD is a stable client
demo, not approved for real customer data.

Stan 2026-10-25, task `CLOUD-01`. Przygotowano kod i skrypty; **nie wykonano
wdrożenia GCP ani smoke live**. PROD w tej instrukcji to druga instancja
demonstracji tylko do odczytu. Nie oznacza gotowości pełnego systemu produkcyjnego.
Decyzja: [ADR-0009](adr/0009-cloud-run-readonly-preview.md).
Zmiana dostępu `GCP-ACCESS-001`: [ADR-0010](adr/0010-cloud-run-public-access.md).
Źródła i adaptacje: [audyt trzech repozytoriów](DEPLOY_GCP_AUDIT.md).

## Kontrakt

Jeden projekt z aktywnym billingiem, jeden region (domyślnie `europe-central2`),
jedno Docker Artifact Registry `tripse-ai`, jeden obraz `tripse-ai` na pełny
40-znakowy SHA commitu. Dwie usługi `tripse-ai-dev` i `tripse-ai-prod`, osobne
runtime service accounts i konfiguracje. PROD używa **tego samego digestu** co
przetestowany DEV. Skrypty nie używają `latest`, lokalnego Docker push, Terraform,
triggerów CI/CD, własnej domeny ani Caddy. Nie zmieniają globalnego projektu gcloud.

| Obszar | Lokalnie (bez zmiany) | Cloud `readonly_demo` |
|---|---|---|
| `/hub` | Nawigacja do lokalnych modułów | Osobny publiczny ekran z prawdziwymi linkami do podglądów |
| Planner | SQLite + osobny worker, mock/live | Trzy stałe scenariusze, schemat SVG; bez zadań i providerów |
| Dokumenty | JSON, drafty, uploady, 3 generatory | Przegląd marketingowej kolekcji; dwa warianty, druk PDF |
| Pilot/oferta prywatna | Local-only | Niedostępne; preset operacyjny nie trafia do Cloud Build |
| WhatsApp / symulator | Dotychczasowy lokalny worker | Niedostępne; webhook i API nie są rejestrowane |
| Zapis | Lokalne SQLite/JSON/bind mounts | Żaden; GET/HEAD, pozostałe metody zwracają 403 |

Publiczny router czyta tylko trzy jawne fixture'y wycieczek i jedną kampanię
z obrazu. Renderer marketingowy stosuje listę pól dozwolonych. Nie ma routingu do
lokalnych draftów ani uploadów. Statyczne zasoby mają zamkniętą listę nazw.
`K_SERVICE` bez poprawnego trybu cloud powoduje odmowę startu, podobnie jak
`PLANNING_MODE=live`, niezgodne APP_ENV/usługa, klucze providerów lub niezgodna
wersja zaszyta w obrazie. Worker odmawia startu w chmurze. Local-only nie jest
osłabiane ani zastępowane zaufaniem do nagłówków proxy.

## Wymagania operatora

- Windows PowerShell 5.1+ lub PowerShell 7, Git, Python 3.12 i zależności
  `requirements.txt` (lokalny preflight uruchamia Uvicorn; pytest/Playwright nie są
  wymagane do deploymentu). Wrapper wybiera `.venv/Scripts/python.exe`, potem `python`.
- Aktualny Google Cloud SDK `gcloud` w PATH; `gcloud auth login`.
- Istniejący projekt, aktywny billing, zgoda organizacji na wybrany region i,
  jeśli `GCP_PUBLIC_ACCESS=true`, anonimowy invoker. Utworzenie projektu, podpięcie
  billingu i zmiana polityk organizacji pozostają poza skryptami.
- Administrator pierwszego setup potrzebuje możliwości włączenia API, utworzenia
  repozytorium i kont usług oraz nadania roli builderowi. Przykładowe role do
  uzgodnienia z administratorem: Service Usage Admin, Artifact Registry Admin,
  Service Account Admin, Project IAM Admin i Cloud Run Admin. Nie nadawaj Owner
  rutynowemu operatorowi tylko po to, by uruchomić skrypt.
- Operator build/deploy: uprawnienia Cloud Build Editor, odczyt Artifact Registry,
  Cloud Run Admin oraz `roles/iam.serviceAccountUser` (`actAs`) na właściwym koncie
  build/runtime. Każdy operator deploy/smoke potrzebuje również Cloud Run Invoker
  (weryfikacja prywatnej rewizji przed upublicznieniem).
  Efektywne polityki, warunki IAM, deny i billing wymagają sprawdzenia w projekcie;
  skrypt testuje wybrane uprawnienia, a każda operacja gcloud egzekwuje pozostałe.

`setup` identyfikuje projekt i testuje IAM. Następnie odczytuje włączone API
i włącza brakujące z jawnej listy: Run, Artifact Registry, Cloud Build, IAM,
Logging, Resource Manager. To jedyna zmiana bootstrap przed listowaniem zasobów,
bo wyłączone API nie pozwala ich zidentyfikować. Jeśli organizacja wymaga osobnego
bootstrap, administrator włącza te API wcześniej. Następnie skrypt identyfikuje
repozytorium, oba serwisy i trzy konta. Błąd odczytu nigdy nie oznacza „nie istnieje”.

Nowe zasoby mają `app=tripse-ai,managed-by=tripse-scripts`; usługi dodatkowo
`environment=dev|prod`. Istniejące zasoby bez zgodnych etykiet lub z inną
konfiguracją zatrzymują operację. Nie przejmuj ich przez dopisanie etykiet bez
audytu właściciela, konfiguracji i IAM. Skrypty niczego nie usuwają. Konta usług
identyfikowane są przez email oraz displayName `TRIPSE managed build|dev|prod`.

`setup` tworzy `tripse-ai-build` z rolą `roles/cloudbuild.builds.builder` w projekcie
(szersza rola bootstrap: build/push/logi/staging; przyszłe zawężenie wymaga osobnej
analizy IAM). Konta `tripse-ai-dev` i `tripse-ai-prod` nie otrzymują żadnej roli
projektowej. Operator musi mieć `actAs`; skrypt nie nadaje sobie tej roli.
Google-managed service agents Run/Build pozostają zarządzane przez GCP.

## Konfiguracja

W katalogu głównym repozytorium:

```powershell
Copy-Item infra/gcp/.env.dev.example .env.dev
Copy-Item infra/gcp/.env.prod.example .env.prod
```

Uzupełnij `GCP_PROJECT_ID` w obu plikach tym samym rzeczywistym ID. Oba pliki
są wymagane nawet przy pracy z DEV, żeby preflight mógł zweryfikować izolację.
Są ignorowane przez Git. `-ConfigDir C:\moja-konfiguracja` pozwala wskazać inny
katalog zawierający oba pliki; nie jest to skrypt PowerShell ani shell dotenv.
Parser dopuszcza tylko zadeklarowane pola; odrzuca duplikaty, interpolację,
nieznane pola i puste wartości. Nie drukuje ich treści przy błędzie.

| Zmienne | Przeznaczenie |
|---|---|
| `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_ARTIFACT_REPO`, `GCP_IMAGE_NAME` | Wspólne adresowanie zasobów; wyłącznie deployment |
| `GCP_SERVICE_NAME` | Ściśle `tripse-ai-dev` lub `tripse-ai-prod` |
| `GCP_PUBLIC_ACCESS` | `true`: anonimowy podgląd; `false`: IAM, token do smoke |
| `GCP_MIN_INSTANCES` | Wymagane `0` |
| `GCP_MAX_INSTANCES` | `1` domyślnie; dopuszczalne 1–3 |
| `GCP_CPU`, `GCP_MEMORY` | `1` CPU, `512Mi` lub `1Gi` |
| `APP_ENV`, `PLANNING_MODE`, `CLOUD_FEATURE_MODE` | Runtime: `dev|prod`, `mock`, `readonly_demo` |
| `EXPECTED_IMAGE_SHA` | Dodawane przez skrypt; musi odpowiadać plikowi wersji wewnątrz obrazu |

Do kontenera trafia wyłącznie ostatnia grupa i `EXPECTED_IMAGE_SHA`.
Pozostałe zmienne lokalnego `.env` (SQLite, WAHA, OpenAI, Google Maps,
Document Studio) **nie są potrzebne** i nie są przekazywane. Obraz jest wspólny;
runtime APP_ENV i konto usługi rozróżniają środowiska. Nie ma zapisywalnego stanu
dzielonego między DEV i PROD.

## Przygotowanie i dry-run — bez operacji GCP

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
./scripts/gcp/preflight.ps1 -Environment dev -Offline
./scripts/gcp/setup.ps1 -Environment dev -DryRun
./scripts/gcp/build.ps1 -Environment dev -DryRun
./scripts/gcp/deploy.ps1 -Environment prod -ImageTag SHA_40_ZNAKOW -DryRun
```

Zastąp `SHA_40_ZNAKOW` rzeczywistym SHA, np. z `git rev-parse HEAD`.
Offline/dry-run walidują konfiguracje i uruchamiają lokalny proces cloud z minimalnym
środowiskiem bez odziedziczonych sekretów; sprawdzają startup, fixture preview
i odmowę write API. Nie łączą się z GCP i nie potwierdzają IAM, regionu online,
istnienia obrazu ani deployowalności niezatwierdzonego drzewa roboczego.
Preflight sprawdza dozwolony kontekst **commitu**, runtime check — kod roboczy.
Prawdziwy build dodatkowo wymaga czystego, zatwierdzonego HEAD z trybem cloud.

## Pierwsze uruchomienie i DEV — operacje GCP

Poniższe komendy są ręcznie wywoływane przez operatora, poza fazą przygotowania:

```powershell
gcloud auth login
./scripts/gcp/setup.ps1 -Environment dev
./scripts/gcp/preflight.ps1 -Environment dev
./scripts/gcp/build.ps1 -Environment dev
$ImageSha = git rev-parse HEAD
./scripts/gcp/deploy.ps1 -Environment dev -ImageTag $ImageSha
./scripts/gcp/smoke.ps1 -Environment dev -ImageTag $ImageSha
```

Przed build zatwierdź przeglądnięte zmiany w Git. Skrypt nie tworzy commitów.
Budowanie pakuje tylko `Dockerfile`, `requirements.txt`, pliki ignore, `app/`
oraz publiczne `demo-fixtures/trips/` i `campaigns/` z `git archive SHA`.
Nie pakuje presetów pilota. Dodaje `app/_build_version.txt` do tymczasowego kontekstu.
Odrzuca symlinki, ścieżki wrażliwe i rozpoznawane wzorce kluczy. `.gcloudignore`
i `.dockerignore` są kolejną warstwą ochrony. Ten skan nie zastępuje przeglądu
fixture'ów i pełnego secret scanning; dowolnych sekretów nie da się rozpoznać po nazwie.

Build wywołuje ręczny `gcloud builds submit --tag REGION-docker.pkg.dev/PROJECT/REPO/IMAGE:SHA`
z kontem build, regionem oraz `--default-buckets-behavior=regional-user-owned-bucket`.
Build ma timeout 600 s. Lokalny Docker nie jest wymagany. Tworzone przez Cloud Build regionalne buckety
staging/logów są artefaktami procesu; ustal ich retencję i uprawnienia w projekcie.
Istniejący SHA w repozytorium z immutable tags jest ponownie używany bez rebuild.

Deployment pobiera digest z Artifact Registry i wdraża `IMAGE@sha256:...`.
Domyślnie: port **8000**, CPU 1, pamięć 512Mi, min 0, max 1 (limit usługi i rewizji),
concurrency 16, request timeout 60 s, CPU request-based, HTTP startup probe `/health`.
Resetuje poprzednie command/args do CMD obrazu. Uvicorn jest procesem PID 1,
otrzymuje SIGTERM i ma 8 s na zamknięcie. Kontrakt Cloud Run przewiduje 10 s
przed SIGKILL; system plików kontenera jest nietrwały i zużywa pamięć:
[kontrakt kontenera](https://cloud.google.com/run/docs/container-contract).

Przed aktualizacją istniejącej usługi skrypt identyfikuje jej IAM i usuwa własne
bezwarunkowe `allUsers/roles/run.invoker`; nietypowe publiczne bindingi wymagają
ręcznego audytu. Wdraża rewizję prywatnie, kieruje 100% ruchu na nią, odczytuje faktyczny `status.url`,
sprawdza Ready i digest, zapisuje osobno `.gcp-state/dev.json` / `prod.json`
(ignorowane przez Git), a następnie wykonuje smoke z tokenem operatora. Dopiero
po jego sukcesie, dla `GCP_PUBLIC_ACCESS=true`, wykonuje `gcloud run services update
SERVICE --no-invoker-iam-check --project=PROJECT --region=REGION` i powtarza smoke
anonimowo (`/hub` musi zwrócić 200). Nie dodaje bindingu `allUsers` ani nie używa
`--allow-unauthenticated`. Dla `GCP_PUBLIC_ACCESS=false` pozostawia włączony
`--invoker-iam-check` i wymaga tokenu. Dotyczy to również ponownego deploymentu
usługi, która wcześniej miała wyłączoną kontrolę IAM.
Oznacza to krótką przerwę publicznego dostępu podczas
deploy; to świadomy kompromis tego demo. Błąd smoke oznacza niezerowy
exit code, mimo że rewizja mogła już zostać wdrożona. Nie ma automatycznego rollbacku.
Stan zapisany przed smoke pomaga odnaleźć usługę; nie jest dowodem udanego QA.

### Polityki organizacji i błąd publikacji

Błąd `FAILED_PRECONDITION: One or more users named in the policy do not belong
to a permitted customer` przy nadawaniu `allUsers` jest zgodny z ograniczeniem
Domain Restricted Sharing. Wyłączenie kontroli invokera jest osobnym,
[udokumentowanym mechanizmem Cloud Run](https://docs.cloud.google.com/run/docs/authenticating/public).
Wymaga uprawnień `run.services.create`, `run.services.update` oraz
`run.services.setIamPolicy`; online preflight już je sprawdza. Operator wykonujący
private smoke potrzebuje również prawa wywołania usługi i niepustego identity tokenu.

Organizacja może zabronić tej operacji przez
`constraints/run.managed.requireInvokerIam` lub starsze `constraints/run.requireInvokerIam`.
Jeśli aktualizacja dostępu zostanie odrzucona, deployment kończy się błędem,
bez publicznego smoke i bez alternatywy przez `allUsers`. Skrypt jawnie przywraca
`--invoker-iam-check` i wykonuje private smoke. Tak samo zamyka dostęp po błędzie
publicznego smoke lub niejednoznacznym błędzie połączenia z CLI. Zachowuje kod
wyjścia pierwotnego błędu gcloud; nie wypisuje surowych odpowiedzi CLI ani tokenów.
Jeśli przywrócenia prywatności nie uda się potwierdzić, raportuje to jawnie;
operator musi natychmiast sprawdzić dostęp w Cloud Console. Nie deklaruje wtedy,
że usługa jest prywatna. Nie zmienia polityk organizacji ani nie próbuje ich obchodzić.
Odrzucenie publikacji przez politykę pozostawia wcześniej prywatną usługę prywatną.

Diagnostyka operatora: sprawdź powyższe polityki w autoryzowanej konsoli,
uprawnienia oraz wsparcie flag w aktualnym SDK (`gcloud run services update --help`).
Jeśli polityka wymaga IAM, ustaw `GCP_PUBLIC_ACCESS=false` dla odpowiedniego
środowiska i wdrażaj je prywatnie. Publiczny deployment pozostaje nieudany do
czasu zgodnego z polityką rozwiązania uzgodnionego z administratorem.

## Promocja PROD i rollback

Po ocenie DEV zapisz jego SHA z `.gcp-state/dev.json`. Użyj go jawnie:

```powershell
./scripts/gcp/preflight.ps1 -Environment prod -ImageTag $ImageSha
./scripts/gcp/deploy.ps1 -Environment prod -ImageTag $ImageSha -DryRun
./scripts/gcp/deploy.ps1 -Environment prod -ImageTag $ImageSha
./scripts/gcp/smoke.ps1 -Environment prod -ImageTag $ImageSha
```

Skrypt `build -Environment prod` odmawia działania. Deploy PROD nie buduje obrazu,
nie odczytuje tagu latest i nie wybiera automatycznie bieżącego HEAD.
Identyczny digest zapewnia promocję tego samego obrazu.

Rollback to ponowny deployment wskazanego, istniejącego obrazu ze starszym SHA:

```powershell
./scripts/gcp/rollback.ps1 -Environment prod -ImageTag $PreviousImageSha -DryRun
./scripts/gcp/rollback.ps1 -Environment prod -ImageTag $PreviousImageSha
```

Obraz musi pochodzić ze sprawdzonego commitu z trybem cloud, dostępnego w lokalnej
historii Git, i pozostać w Artifact Registry. Nie można cofnąć się do wersji
sprzed Cloud Preview. Nie są przywracane historyczne `.env` ani IAM; używana jest
bieżąca konfiguracja środowiska. Brak danych do cofania w tym stateless demo.
Nie usuwaj obrazów wymaganych do rollback. Przed kolejną operacją napraw błąd
z poprzedniego polecenia; PowerShell wrapper zwraca natywny kod błędu gcloud.
Skrypty tłumią pełne odpowiedzi CLI, by nie ujawniać sekretów; do diagnostyki
operator korzysta z Cloud Console/Cloud Logging w swoim autoryzowanym kontekście.

## Smoke i URL

`smoke.ps1` ponownie odczytuje usługę z GCP, więc nie ufa zapisanej lokalnie kopii
URL. Sprawdza `/health`, środowisko, nazwę usługi, wersję zaszytą w obrazie,
tryb mock/read-only, Hub, mapę fixture, kolekcję i assety. Sprawdza 403/404 dla
write API, webhooka, lokalnego edytora, draftów, uploadów i pilota.
Dla publicznej konfiguracji robi to anonimowo. Dla prywatnej testuje anonimowe
403 i resztę z przechwyconym tokenem `gcloud auth print-identity-token` bez logowania
tokenu. Jeśli organizacja blokuje anonimowość albo token operatora nie daje
Invoker, smoke zakończy się błędem, a nie deklaracją sukcesu.

Etap private smoke jest obowiązkowy również dla konfiguracji publicznej:
anonimowy `/hub` musi zwrócić 403, a trasy podglądu są sprawdzane z tokenem.
Po publikacji `/hub` zwraca 200 bez tokenu; niedozwolone API i operacje zapisu
nadal muszą zwracać 403/404. Samodzielny `smoke.ps1` nie zmienia dostępu usługi.

URL można odczytać z `.gcp-state/dev.json`, wypisany jest też po udanym deploy.
Ręcznie, z parametrami odpowiedniego środowiska:

```powershell
gcloud run services describe tripse-ai-dev --project TWOJ_PROJECT --region europe-central2 --format="value(status.url)"
```

## Sekrety i koszty

Ten tryb nie potrzebuje sekretów ani roli Secret Accessor. Nie dodawaj kluczy
do `.env.dev/.env.prod`, argumentów CLI, obrazu ani logów. Parser odrzuca inne pola.
Przyszła integracja wymaga rozszerzenia jawnego kontraktu o **referencje**, np.
`OPENAI_API_KEY_SECRET=tripse-openai-dev:3`, oddzielnych sekretów DEV/PROD i
minimalnego Secret Accessor na konkretnym sekrecie. Dopiero wtedy wdrożenie
przekaże `--set-secrets=OPENAI_API_KEY=tripse-openai-dev:3`. Obecne skrypty tego
nie wykonują i świadomie nie włączają Secret Manager API.

Min 0 ogranicza koszt bezczynności, ale nie gwarantuje rachunku 0. Koszt mogą
generować requesty/CPU/RAM, transfer, Artifact Registry, Cloud Build, Cloud Storage
staging/logów i Cloud Logging. Ustal alerty budżetowe, retencję logów/artefaktów
i nadzór przed publicznym udostępnieniem. Limit instancji nie jest twardym limitem
rachunku. Nie dodano automatycznego kasowania zasobów ani fikcyjnych kwot.
Źródła do aktualnej kalkulacji: [Cloud Run](https://cloud.google.com/run/pricing),
[Cloud Build](https://cloud.google.com/build/pricing),
[Artifact Registry](https://cloud.google.com/artifact-registry/pricing).

## Kontrole lokalne i ograniczenia

GCP-ACCESS-001 (2026-10-25): pełny pytest **311 PASS** (w tym 52 przypadki
deploymentu; jedno ostrzeżenie deprecacji Starlette/AnyIO), offline preflight
DEV/PROD oraz dry-run deploymentu DEV/PROD PASS. Nie wykonano zmian ani testów
live GCP; nie uruchamiano ponownie browser/Docker QA dla tej zmiany skryptów.
`deployment_contract.py` i adapter `scripts/dev.py` przeanalizowano: istniejący
kontrakt true/false, izolacja środowisk i promocja SHA nie wymagają zmiany.
Poniższy raport 264 PASS dotyczy wcześniejszego CLOUD-01.

```powershell
./.venv/Scripts/python.exe -m pytest -q
./.venv/Scripts/python.exe tests/browser_cloud_preview_smoke.py
./.venv/Scripts/python.exe tests/container_cloud_preview_smoke.py
```

Raport tego etapu: pytest 264 PASS (jedno ostrzeżenie zależności Starlette/AnyIO);
nowy browser QA (320/390/768/1440 px, dwa warianty PDF) PASS; cztery istniejące
browser QA (Hub/planner/chat, Studio, marketing, pilot/oferta) PASS. Kontener
linux/amd64: port 8000, filesystem read-only, fixture preview, odmowa zapisu,
wersja i SIGTERM exit 0 — PASS. PowerShell AST, offline DEV/PROD, dry-run wrapperów,
Git ignore, Compose config oraz linki/CSV/YAML ADR — PASS. Szczegóły w worklogu.
Browser/Docker QA to opcjonalne zależności developerskie; build GCP ich nie wymaga.

Nie testowano GCP live: w środowisku przygotowania brak gcloud i dostępu do projektu.
Online preflight nie dowodzi zgodności wszystkich polityk organizacji ani
historycznej poprawności obrazów. Nie ma podpisów obrazu, automatycznego skanera
luk, rate limitingu aplikacyjnego ani uwierzytelniania użytkowników. Wspólny projekt
to separacja usług i konfiguracji, nie osobna granica IAM/billing dla organizacji.

Przed pełną chmurą trzeba uzgodnić autoryzację i poufność, trwały magazyn oraz
migrację JSON/SQLite, backupy, kolejkę i model pracy workera, zarządzanie sekretami,
limity providerów, monitoring i odpowiedzialność operacyjną. Obecny interfejs
Repository ułatwia przyszłą podmianę storage dokumentów; nie implementuje jej.
Nie uruchamiaj lokalnego compose jako substytutu tego kontraktu na Cloud Run.

Lokalny podgląd samego trybu chmurowego (bez gcloud i bez workera):

```powershell
$env:APP_ENV = "dev"
$env:PLANNING_MODE = "mock"
$env:CLOUD_FEATURE_MODE = "readonly_demo"
./.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Otwórz `http://localhost:8000/hub`. Użyj powłoki bez kluczy providerów;
nie wczytuj lokalnego `.env` planera. Wersja obrazu poza Cloud Run może mieć
wartość `unversioned`. Po zakończeniu usuń zmienne cloud lub otwórz nową powłokę,
aby wrócić do lokalnych edytorów.
