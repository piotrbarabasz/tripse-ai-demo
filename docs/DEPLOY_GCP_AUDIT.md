# CLOUD-01 — źródła i granice adaptacji

Audyt 2026-10-25 wykonano z lokalnych checkoutów trzech wskazanych repozytoriów.
Nie czytano ich prywatnych `.env`, nie zmieniano referencyjnych repozytoriów,
nie odpytywano ani nie modyfikowano zasobów GCP.

| Repozytorium | Sprawdzony HEAD |
|---|---|
| TRIPSE | `462476001b6c3dac60ad15333631726729ad422c` |
| PAYBACK | `fef255a2ab65ab48bfd07c6a6444414cf460f493` |
| AI Software Studio | `6b1d7334bc7949a02c837eae7075d80ca1423a7d` |

## PAYBACK

Źródła: [infra/gcp](https://github.com/piotrbarabasz/payback-lightweight-assistant/tree/fef255a2ab65ab48bfd07c6a6444414cf460f493/infra/gcp),
[instrukcja](https://github.com/piotrbarabasz/payback-lightweight-assistant/blob/fef255a2ab65ab48bfd07c6a6444414cf460f493/docs/deployment_gcp_cloud_run.md),
[Dockerfile](https://github.com/piotrbarabasz/payback-lightweight-assistant/blob/fef255a2ab65ab48bfd07c6a6444414cf460f493/Dockerfile).

Przejrzano setup projektu, tworzenie Artifact Registry, build/push,
deploy Cloud Run, konto runtime i smoke. Zastosowano wzorzec małych jawnych
etapów setup → build → deploy → smoke, walidację wymaganej konfiguracji,
parametry zasobów usługi, odczyt rzeczywistego URL po deploy oraz instrukcję operatora.
To adaptacja zachowania, nie skopiowany stos PAYBACK.

Odrzucono `gcloud config set project`, lokalny obowiązkowy Docker build/push,
domyślny `latest`, wspólny plik URL i traktowanie błędu describe jako braku zasobu.
Nie przeniesiono BigQuery, Vertex AI, katalogu produktów ani ich ról IAM.
TRIPSE ma exec CMD Uvicorn i port 8000 zamiast shellowego startu na 8080.
Smoke asertuje status i treść, zamiast polegać na samym wykonaniu curl.

## AI Software Studio

Źródła: [scripts/gcp](https://github.com/piotrbarabasz/ai-software-studio/tree/6b1d7334bc7949a02c837eae7075d80ca1423a7d/scripts/gcp),
[deployment_contract.py](https://github.com/piotrbarabasz/ai-software-studio/blob/6b1d7334bc7949a02c837eae7075d80ca1423a7d/scripts/gcp/deployment_contract.py),
[infra/gcp](https://github.com/piotrbarabasz/ai-software-studio/tree/6b1d7334bc7949a02c837eae7075d80ca1423a7d/infra/gcp).

Przejrzano kontrakt, PowerShell preflight, Python deploy i smoke, przykładowe
konfiguracje, kontrakt produkcyjny i pliki Cloud Build. Zastosowano rozdział
cienkich wrapperów PowerShell od testowalnej logiki Python, jawny kontrakt
niesekretnych parametrów, ścisłe SHA/nazwy, oddzielny preflight i smoke oraz
zasadę referencji Secret Manager zamiast wartości sekretów.

Nie przeniesiono domeny Protolume, danych prawnych, SMTP, osobnych obrazów
frontend/backend, triggerów ani produkcyjnych kontraktów specyficznych dla tamtego
produktu. TRIPSE używa dwóch plików dotenv o tej samej strukturze, jednego obrazu,
prostego ręcznego Cloud Build i stdlib. Nie wymaga dodatkowego frontendu.

## TRIPSE — fakty i adaptacja

Źródła zastane: [Dockerfile](../Dockerfile), [compose](../compose.yaml),
[main](../app/main.py), [SQLite](../app/db.py), [worker](../app/worker.py),
[Document Studio](../app/document_studio/), [ADR](adr/README.md),
[tracking](tracking/README.md), [Hub](HUB.md).

- FastAPI rejestrowało lokalny Hub, planer/viewer, mock chat, webhook WAHA
  i Document Studio. Samo `--allow-unauthenticated` wystawiłoby więcej niż podgląd.
- SQLite i pojedynczy osobny worker wymagają trwałego wspólnego magazynu;
  skala/zamknięcie instancji Cloud Run nie zachowuje tego modelu działania.
- JSON i assety dokumentów mają lokalną trwałość i ochronę host/origin/peer,
  a nie uwierzytelnianie. Nie można bez zastępstwa usunąć local-only.
- Snapshoty, whitelisty dokumentów, renderer marketingowy i fixture'y pozwalają
  zbudować bezpieczny podgląd bez migrowania bazy czy uruchamiania providerów.

Wprowadzony [cloud_preview](../app/cloud_preview.py) jest osobnym grafem tras
w tej samej aplikacji/obrazie, wybieranym przed utworzeniem repozytoriów.
Lokalne routery i worker nie są uruchamiane w chmurze. Użyto istniejącego modelu
kampanii i renderera oraz publicznych fragmentów SCENARIOS do schematu mapy.
Nie wdrożono produkcyjnej bazy, kolejki, GCP ani logowania; nie rozszerzono
integracji backendowych. To ograniczenie zakresu zgodne ze zleceniem, nie dowód
historycznej decyzji o docelowej architekturze.

Oficjalne kontrakty sprawdzone podczas przygotowania:
[Cloud Build submit](https://cloud.google.com/sdk/gcloud/reference/builds/submit),
[Run deploy](https://cloud.google.com/sdk/gcloud/reference/run/deploy),
[Run container](https://cloud.google.com/run/docs/container-contract),
[Artifact Registry create](https://cloud.google.com/sdk/gcloud/reference/artifacts/repositories/create).
Ich przeczytanie nie zastępuje wykonania komend w docelowym projekcie.
