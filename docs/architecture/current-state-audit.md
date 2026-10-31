# TRIPSE current-state technical audit

Status: **source-code audit**, 2026-10-31, ARCH-001; separated during final review.
This document was initially saved under the blueprint filename. It is not the original
user-authored product vision. That source is still unavailable in this review session;
see [reconciliation status](reconciliation.md). All technical findings are retained.
Audited baseline: `dev`,
commit `0956ea2`; documentation prepared on `docs/arch-001-foundation`.
Source observations below describe code, not a new claim of hosted acceptance.

## Current system: evidence from the working tree

| Area | Observed implementation and primary evidence |
| --- | --- |
| Composition | [app/main.py](../../app/main.py) composes FastAPI routers, job storage, Document Studio and Hub. readonly_demo selects a separate application before writable routers are registered. |
| Entry points | `/` redirects 302 to `/hub`; `/planner` serves create.html/create.js; `/trip/{token}` serves viewer.html/viewer.js; `/demo/chat` serves demo.html/demo.js; `/documents/demo` serves the Studio and its hash router. See [route inventory](../ROUTING.md). |
| Frontend dependencies | No package.json, Node lockfile, TypeScript/Vite/React setup found. HTML/CSS/JS are served directly. [viewer.py](../../app/viewer.py) supplies browser-map configuration and CSP; viewer.js loads Google Maps, while demo-map.js renders schematic mock maps. No frontend bundler is currently required. |
| Hub/navigation | [hub.py](../../app/hub.py) substitutes fixed values into [Hub HTML](../../app/hub_frontend/index.html). module-nav.js/CSS provide shared legacy navigation; visibility hints are not authorization. |
| Planner | [main.py](../../app/main.py) defines TripRequest/TripAccepted/TripStatus; [planning_models.py](../../app/planning_models.py) defines TripPlan and provider schemas. [planning.py](../../app/planning.py) orchestrates OpenAI, Places and Routes through bounded HTTP adapters in planning_providers.py. No general assistant tool orchestrator is implemented. |
| Local execution | [db.py](../../app/db.py) stores jobs/messages/viewer tokens in SQLite; [worker.py](../../app/worker.py) is a separate polling process. Preserve single-worker/recovery behavior; the API does not generate plans synchronously. |
| Cloud execution | [cloud_runtime.py](../../app/cloud_runtime.py) injects GCSRepository/asset bytes and [cloud_jobs.py](../../app/cloud_jobs.py) Firestore/Cloud Tasks adapters. There is no implicit local-storage fallback in cloud_demo. |
| Documents | [api.py](../../app/document_studio/api.py) adapts Pydantic models to DocumentService, DocumentLibrary, AssetStore and Repository. JSON/GCS implementations preserve snapshots, revision checks and historical saves. [models.py](../../app/document_studio/models.py), [templates.py](../../app/document_studio/templates.py) and sections.py are reusable domain interfaces. |
| Delivery | [Dockerfile](../../Dockerfile) is a pinned Python 3.12 single-stage image, installing requirements.txt and copying app plus reviewed gt-v1 fixtures. No Node build stage. [.dockerignore](../../.dockerignore) and [.gcloudignore](../../.gcloudignore) exclude local data, credentials and development outputs. |
| Release provenance | [deployment.source_files](../../scripts/gcp/deployment.py) restricts build inputs to Dockerfile/requirements/ignore files, app/ and demo-fixtures/gt-v1/. [build_proof.py](../../scripts/gcp/build_proof.py) checks recipe and exact source bytes. A new top-level frontend tree would currently be omitted from release source. |
| CI/testing | [ci.yml](../../.github/workflows/ci.yml) runs pytest, offline release contracts, Chromium browser QA and diff checks. PR trigger targets master only. [delivery.yml](../../.github/workflows/delivery.yml) reuses CI for dev/master delivery, builds/accepts DEV and promotes the same digest to protected PROD. Existing tests include browser and actual-PDF quality scripts; see roadmap validation limits. |

Python dependencies are pinned in [requirements.txt](../../requirements.txt): FastAPI,
Pydantic, Uvicorn, HTTPX, Pillow, tzdata, GCP Storage/Firestore/Tasks SDKs and PyJWT.
[requirements-dev.txt](../../requirements-dev.txt) adds pytest, Playwright, pypdf,
PyMuPDF and PyYAML. No dependency change is made here.

Infrastructure source: [cloud-demo Terraform](../../infra/gcp/cloud-demo/main.tf)
declares private GCS objects with versioning/soft delete and destruction protection,
protected Firestore with PITR, and a bounded Cloud Tasks queue. The PROD root reuses
that module with separate state/environment; [GitHub Actions IAM](../../infra/gcp/github-actions/main.tf)
separates WIF deployment and probe identities. [Compose](../../compose.yaml) binds API
to loopback, shares SQLite with the worker and keeps Studio data in its existing mount;
WAHA/Caddy are optional profiles. These are source observations, not verification of
current cloud resources, backup restoration or permissions. No Terraform/cloud action
is required or performed for ARCH-001.

## Security boundaries to preserve

| Mode | Actual boundary | Migration constraint |
| --- | --- | --- |
| local | Studio and Hub use api.local_only: loopback peer and localhost Host; private Docker peer only with explicit opt-in; forwarded headers rejected, Origin checked when present, cross-site fetch rejected. Planner/job APIs are not globally protected by this guard. WAHA separately verifies webhook authentication/session/sender rules. | A future private `/app` must reuse the guard; do not turn it into a new public proxy surface. Preserve public planner/viewer behavior independently. |
| cloud_demo | main.cloud_boundary checks exact Host and authenticates signed IAP assertions except app-level `/health`. CloudAccess verifies signature/issuer/audience/expiry; reader/editor membership, exact Origin on writes, fetch-site checks and dedicated internal task identity. Principal scopes jobs; documents use the shared demo repository, not tenant isolation. Cloud modes require mock and reject server-provider credentials. | All shell, deep links, chunks and APIs stay inside the existing middleware. UI permissions only reflect server decisions. No new login, proxy-header trust, shared credentials or claim of customer-ready isolation. |
| readonly_demo | Separate fixture-only app; non-GET/HEAD requests return 403; no writable Studio/planner/demo APIs registered; reviewed assets only, restrictive CSP. | `/app` remains absent initially. No general SPA fallback, asset mount or assistant registration in this composition. |

Sources: [local guard](../../app/document_studio/api.py),
[IAP policy](../../app/cloud_access.py), [mode composition](../../app/cloud_preview.py),
[security history](../document-system/architecture/security.md).
[Caddyfile](../../Caddyfile) explicitly proxies public planner/viewer/job/webhook paths;
Hub and Studio are excluded. Adding `/app` to that allowlist is outside the proposal.
Cloud health's middleware exception does not make the deployed service bypass IAP.
Token viewers remain token-validated; cloud_demo also requires its outer IAP boundary.

## Document rendering and export

Current flow: source Trip/Campaign → independent DocumentDraft snapshots → typed sections
and render projections → Python-controlled escaped HTML/CSS → browser layout measurement
and pagination → window.print(). [print-export.js](../../app/document_studio/frontend/print-export.js)
waits for fonts/images, splits content, records layout diagnostics and gates printing on
data-valid and layout readiness. A4 and social are separate layouts; social is PDF,
not a PNG export service. There is no server Chromium service, persistent PDF export
resource or export queue. `ready` business status does not override validation.

Editors request validation and HTML previews; DocumentFlow.embeddedPreview uses srcdoc
with the existing print button hidden. Separate windows expose full print pages.
Library history embeds a preview URL directly. cloud_demo sets
X-Frame-Options DENY globally: embedded URL history previews therefore need explicit
browser verification under IAP; do not assume local iframe behavior proves cloud parity.
Keep external preview windows as the safe existing integration path. Any framing-policy
change needs separate security review, not an incidental React migration adjustment.
Detailed historical QA: [DOC-PDF-003](../audits/DOC_PDF_003.md) and
[document architecture](../document-system/architecture/system-architecture.md).

## Coupling, duplication and reusable seams

- studio.js owns hash routing, API/error handling, mutable collections, dirty state,
  form assembly and source/draft workflows. trip-editor.js and marketing-editor.js
  combine UI state, domain-shaped payloads, debounced validation, saves and previews.
  Shared window globals (SectionEditor, SourcePicker, DocumentFlow, editors, library)
  and script ordering prevent treating these as independent React components.
- create.js, demo.js and studio.js each implement fetch/error handling; planner and
  chat separately poll asynchronous state. Image upload/rights handling appears in
  trip-editor.js, marketing-editor.js and section-editor.js. Editors repeat field and
  preview-state handling. These are consolidation candidates, not proven interchangeable
  behavior: preserve timeout, idempotency, binary response and conflict semantics.
- DOM string assembly and explicit escaping are pervasive. React text rendering can
  replace UI assembly, but server HTML must remain an isolated preview document; never
  insert it as arbitrary app HTML. Dirty navigation guards, stale preview responses,
  pending saves and object-URL cleanup need explicit parity tests.
- Reuse DocumentService/DocumentLibrary/Repository, template registry, Pydantic
  validators, source snapshots and renderers. Do not move authoritative validation or
  storage policy into TypeScript. `sections: null` denotes legacy initialization;
  an empty list deliberately stays empty. IDs, revisions and operation UUIDs are contracts.
- Planner TripPlan and Studio Trip are different models and separate stores. A planner
  result is not already a Studio source. Any conversion needs a later explicit adapter
  and acceptance requirements, not an unsafe type cast or an implied automated workflow.

## Proposed target, subject to ADR approval

Browser `/app` → React + TypeScript + Vite shell → feature modules (Hub, Planner,
Documents, Assistant) → typed API adapter/TanStack Query → existing FastAPI routes
→ domain services → existing storage/providers. React Router owns only `/app` routes.
Tailwind CSS and selected shadcn/ui primitives serve application UI; document print
tokens/layouts remain independent. See [UI architecture](../ui/architecture.md),
[API architecture](../api/architecture.md) and [ADR-0017](../adr/0017-modular-react-typescript-migration.md).

Initially serve compiled assets from the existing FastAPI/Cloud Run image and origin.
No extra service, bucket, IAM role or deployment is authorized. Proposed source tree:
`frontend/`; a later reviewed change must include deterministic Node build inputs and
output in Docker/provenance contracts. Do not bypass the source allowlist by committing
unverified build output. Version selection, lockfile and exact build recipe belong to
FRONT-001. Existing release digest acceptance/promotion must remain verifiable.

## Risks and follow-up ownership

| Risk | Required response / stage |
| --- | --- |
| SPA fallback swallows APIs or private routes | Prefix-scoped routing, mode matrix and denial tests in FRONT-001. |
| Authenticated chunks/deep links fail, or Vite proxy weakens local guard | Same-origin assets; loopback-only development setup; never trust forwarded identity; FRONT-001. |
| Weak OpenAPI response schemas hide real payloads | Offline schema inventory, explicit supplemental types/runtime checks, API-001. |
| Query retries duplicate writes or resurrect stale drafts | Read-only retries bounded; writes not automatically retried; preserve operation IDs/CAS; API-001/FRONT-003. |
| Tailwind resets/fonts break measured PDF layout | Scope app CSS; retain print document boundary and full PDF matrix; FRONT-003. |
| Local iframe assumptions fail cloud headers/IAP | Verify separate preview windows and history behavior without relaxing headers; FRONT-003. |
| Two UIs drift while both are maintained | Migrate one vertical workflow at a time; parity gates and legacy links; FRONT-002/003. |
| Release source/recipe verification rejects Node inputs | Deliberately extend allowlists, manifests and provenance tests with immutable build inputs; FRONT-001. |
| PRs to dev lack CI | Separate CI improvement before frontend merge: expand PR trigger to dev/master; keep unprivileged CI and protected delivery separate. |
| Assistant bypasses policies or spends provider budget | Server tool allowlist, authorization and confirmation policy; mock first; separate approval for live cloud capability; AI-001. |

Owner approval is outstanding for the stack, `/app` coexistence, packaging and assistant
scope. Cost/time impacts are unmeasured; see [estimation work packages](../tracking/estimates.md).
