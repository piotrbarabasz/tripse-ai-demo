# TRIPSE React frontend — FRONT-001A / FRONT-001B / API-001 / FRONT-002 / FRONT-003A/B/C

React shell with FastAPI same-origin integration, 2026-10-31. FRONT-001A supplied
the shell; FRONT-001B adds private `/app` serving, a bounded health read and the
multi-stage image/source contract. No deployment is performed. ADR-0017 remains
proposed; implementation evidence does not imply blanket architecture approval.

## Run locally

Use Node.js 24 LTS (`.nvmrc` pins the tested version, 24.18.0) and npm 11.
Node 24 remains supported through April 2028 ([release schedule](https://github.com/nodejs/Release#release-schedule)).
Keep the pinned patch updated as part of dependency maintenance.

For the integrated application, build once, then start the existing mock backend:

```bash
cd frontend
npm ci
npm run build
cd ..
make dev-mock
```

Open **http://localhost:8000/app** (or `/app/`). This matches the existing default
`PUBLIC_BASE_URL` used by the worker's viewer links. If you choose another origin
(including `127.0.0.1`, HTTPS or a different port), configure `PUBLIC_BASE_URL` to
that exact browser origin for both API and worker; the React Planner rejects viewer
URLs from another origin. Legacy links and the `/health`
PoC now use the same origin. Local serving reads `frontend/dist`; the Docker image
contains only compiled output at `app/spa_dist`. An unbuilt source checkout keeps
legacy pages working and returns 503 for the SPA entry. Build before running
`make test-browser`/`make test-all`. Docker runtime acceptance is separately recorded
in the [integration guide](../docs/ui/front-001b-integration.md).

For standalone HMR development:

```bash
cd frontend
npm ci
npm run dev
```

Open **http://127.0.0.1:5173/app/**. Both dev and preview bind to loopback;
occupied ports fail instead of silently selecting another port. Nested routes can
be opened/refreshed directly in Vite. The bare `/app` entry redirects to `/app/`
in dev/preview, preserving the query string. `npm run preview` serves the last build at
http://127.0.0.1:4173/app/; it is a local verification server, not production hosting.

Legacy links require an independently running FastAPI backend. In a separate
terminal, from the repository root, use the existing `make dev-mock` instructions
(see [development guide](../docs/MAKEFILE.md)); no backend change is required.
For links to that local backend, create ignored `frontend/.env.local`:

```dotenv
VITE_DEV_BACKEND_ORIGIN=http://127.0.0.1:8000
```

Restart Vite after changing the variable. It must be an HTTP(S) origin without a
path, credentials, query or fragment. Use loopback when running the local backend.
This option only changes full-page anchors in development; it does not redirect API requests and
uses no proxy or forwarded identity headers. Existing FastAPI access checks still
apply. Without this option links stay relative to the frontend origin, which
does not serve legacy pages. Production builds always use `/hub`, `/planner`, and
`/documents/demo`, even if the development variable is present during build.
All Vite configuration is public: never put secrets in `VITE_*` variables.
The health PoC always requests `/health` from the current origin. Standalone Vite
has no health endpoint and displays the explicit connection error; use the compiled
FastAPI application for this PoC. No proxy, CORS bypass or alternate health origin is added.

## Structure and ownership

```text
frontend/
  src/
    main.tsx                    # strict-mode bootstrap
    app/
      App.tsx, router.tsx       # /app basename, route composition
      layouts/                  # header, sidebar, mobile drawer, route focus
      ModulePage.tsx            # generic planned-module presentation
      NotFoundPage.tsx
    features/hub/               # Hub, module/legacy links, bounded health read/status
    shared/
      api/                      # generated types/guards, transport, adapters and query conventions
      components/               # PageHeader, ErrorBoundary
      config/                   # navigation metadata, development legacy URLs
      lib/                      # class-name helper
      ui/                       # selected shadcn/ui Button, Badge, Sheet
    styles/globals.css          # local tokens, Tailwind, responsive application CSS
    test/setup.ts
```

API-001 adds `shared/api/{generated,client,adapters,query}` and a root
QueryClientProvider. Generated TypeScript and Zod guards follow actual OpenAPI;
schema gaps use minimal runtime-checked projections. No empty future feature
folders or global form store are created. Future Planner, Documents, Marketing, Automations and Assistant modules
will own their pages/UI/hooks under `features/`; shared code must stay independent
of their business logic. The app layer owns composition and routing.

## Routes and components

| Route | Current behavior |
| --- | --- |
| `/app`, `/app/` | Hub, welcome copy, five module cards and direct legacy links |
| `/app/planner` | Operational request form, trusted mode/permissions, job polling and existing viewer link; legacy `/planner` fallback |
| `/app/documents` | Real template catalog; editor-capable users can continue creation in legacy Studio |
| `/app/documents/library` | Read-only saved library with server filters/search/sort/pagination |
| `/app/documents/library/:documentId` | Metadata and revision history; safe legacy and preview links |
| `/app/marketing` | Planned module only |
| `/app/automations` | Planned module only |
| `/app/assistant` | Planned module only; no AI requests |
| Unknown path under `/app` | Not-found page with Hub recovery |

Vite `base: '/app/'` is the source for the router's `/app` basename (trimmed
trailing slash accepts both entry forms).
Fixed desktop navigation uses `aria-current`; below 768px a Radix Dialog drawer
provides focus containment, Escape/outside dismissal and trigger focus restoration.
Route transitions move focus to the new heading and update the document title.
A skip link, semantic landmarks and visible keyboard focus are included.
Desktop collapse is intentionally omitted: the compact fixed navigation fits the
current six destinations. The drawer scrolls on short screens. PageHeader,
Button, Badge, Sheet and ErrorBoundary are reusable. HealthStatus owns its bounded
loading/error/timeout presentation and aborts on unmount. Proposed navy/warm accent tokens are
adapted locally without importing legacy CSS, scripts, fonts, images or print styles.

## Validation and CI

```bash
npm ci
npm run typecheck
npm run lint
npm run test
npm run build
npm run preview
```

Tests cover bootstrap, Hub, all module routes, client navigation/active state,
not-found recovery, route focus, mobile dismissal/focus containment, named semantic
navigation, error recovery and development/production legacy URL policy.
See [FRONT-001B verification and rollback](../docs/ui/front-001b-integration.md)
for current results/screenshots and [historical FRONT-001A evidence](../docs/ui/front-001a-validation.md).
No hosted acceptance is inferred from local or mocked-cloud tests.

The existing CI `checks` job installs SHA-pinned setup-node, uses `.nvmrc`, runs
`npm ci`, typecheck, lint, tests and build. Existing Python/offline/browser gates,
read-only permissions, checkout settings and workflow_call remain intact.
`delivery.yml` is unchanged. A later merge to dev can still trigger existing DEV
delivery; this task performs no merge, push, PR creation or deployment.

All direct packages use exact versions and `package-lock.json` must be committed.
The `minimatch` 11.0.3 override resolves
[GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249) in lint-only
transitive dependencies. Remove it when ESLint/typescript-eslint adopt the fixed
major; rerun clean install and typed lint when changing it. Owned shadcn adaptations
and attribution are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Stage split and limitations

**FRONT-001A implemented:** bootstrap, responsive shell, navigation, informative Hub,
UI primitives, error/not-found states, local toolchain and unprivileged CI validation.
The Hub has no fabricated metrics, authentication identity or permission claims.
Module screens are explicitly placeholders, not migrated workflows.

**FRONT-001B implemented in source:**

1. Same-origin compiled `/app` assets and a prefix-bounded HTML navigation
   fallback to FastAPI in local/cloud_demo only. Preserve readonly isolation and
   all legacy/API/internal behavior. Missing assets must return 404, not HTML.
2. Pinned multi-stage Node build and compiled output in the existing Python
   image; update source allowlists, build recipe/manifests and provenance tests
   together. Do not add a separate frontend service.
3. Local and offline cloud tests for IAP, CSP, Host/Origin, MIME/cache and denial
   behavior, including compiled browser tests with a nonce-protected drawer.
4. Bounded read-only same-origin `/health` PoC with validated response,
   loading/error/auth/cancellation states; no business mutations.
5. Local compiled FastAPI and legacy browser regressions. Container runtime and
   hosted Cloud Run/IAP acceptance remain separate evidence gates, not claimed complete.

The [integration guide](../docs/ui/front-001b-integration.md) documents security,
cache policy, versioned source selection, container limitations and exact rollback.
Caddy, business APIs, identity policies, data and delivery workflow stay unchanged.

**API-001 implemented:** deterministic isolated offline schema and TypeScript/Zod
generation, shared JSON/HTML/byte transport, guarded Planner/Studio adapters,
TanStack Query provider and cancellation/invalidation/retry conventions. Existing
health UI uses the shared transport. Exact commands, schema gaps, security boundaries
and evidence: [API-001 guide](../docs/api/api-001.md). Regenerate from the repository
root with `python -m scripts.export_openapi` and
`npm --prefix frontend run api:generate`; check with the Python `--check` option
and `npm --prefix frontend run api:check`. Synthetic wire fixture generation is
`python -m scripts.export_api_fixtures` (also supports `--check`).

**Later stages:** Trip Catalog and plan editing; advanced document business-field editing and full print/PDF parity;
Marketing data; Assistant orchestration; Automations execution/history/approval.
FRONT-001 and API-001 add no backend APIs, databases, paid providers or infrastructure.

**FRONT-002 implemented:** operational Hub/Planner migration using API-001. The
minimal guarded `/api/workspace/capabilities` endpoint confirms runtime mode and
create permission; creation is disabled when that check is unavailable. Creates
never retry automatically, cloud manual retries retain their operation UUID, and
local retries explicitly warn of duplication. Polling stops on errors/terminal
state/unmount and pauses after two minutes, with a GET-only manual refresh.
Completed results use a narrow runtime projection and exact same-origin, expiring
viewer link. No plan editing, embedded map, Studio migration or catalog is added.
See [contracts, screenshots, validation and rollback](../docs/ui/front-002-planner.md)
and the [prepared PR description](../docs/ui/front-002-pr.md).

**FRONT-003A implemented:** lazy-loaded Document Studio catalog/library, real saved
metadata, cancelable debounced search, server pagination, read-only details/history
and verified legacy/preview links. No document writes or full draft snapshots are
loaded by this workspace. The eight-template catalog comes from the existing API;
creation was deferred to FRONT-003B; editing remains in `/documents/demo`. Access hints and session expiry reuse
the existing API-001/FRONT-002 mechanisms. See
[routes, validation, screenshots, security and B/C/D boundaries](../docs/ui/front-003a-documents.md)
and the [prepared PR description](../docs/ui/front-003a-pr.md).

**FRONT-003B implemented:** `/app/documents/new` is the three-step editor-only
creation wizard. Catalog links use `?template=offer.private` (actual server ID)
so refresh works with the unchanged extensionless SPA fallback. Choose the layout,
an existing Studio Trip/Campaign and its revision, then confirm the title and
confidentiality before one POST. No Planner conversion or source editor is added.
The generated DraftRequest and DocumentDraft validators reuse API-001 transport.
An in-memory frozen payload/ID survives ambiguous failures; GET verifies the saved
snapshot, a definite 404 permits an explicit identical retry, and inconclusive
results permit reads only. Success invalidates Studio queries and links to legacy
editing and React library/details. No browser storage or automatic mutation replay.
The root now uses React Router's data router, constructed once before StrictMode,
for supported dirty-form link/Back blocking; native unload also warns. Form state
is lost on leaving/reloading and cannot be recovered from storage.
Run `.venv/Scripts/python.exe tests/browser_react_document_creation_smoke.py`
after building, or use the complete `python scripts/dev.py test-browser` command.
See [audit, contracts, validation and rollback](../docs/ui/front-003b-creation.md)
and the [prepared PR description](../docs/ui/front-003b-pr.md).
FRONT-003C adds the editing increment below; FRONT-003D assets/preview/PDF remains
separate work. A/B descriptions record their original implementation boundaries.

**FRONT-003C implemented:** `/app/documents/:documentId/edit` loads a persisted
draft into an immutable baseline and separate in-memory form. Library/details and
creation success link to it; invalid identifiers, readers and archived documents
have no editable form. Manual **Zapisz zmiany** sends the loaded revision and only
changed supported groups, validates the response and verifies stored content by GET.
No autosave, background form replacement, automatic retry or browser persistence.
Successful saves update revision/timestamp and invalidate Studio/library/history.
409 preserves local input for explicit inspection/discard; ambiguous failures lock
the attempt for GET-only recovery. A confirmed unchanged baseline permits a deliberate
same-payload retry under the server's existing revision CAS.

Supported fields: title/date label/editorial notes, day-ID-preserving overrides,
section title/body/visibility/order and custom section structure. Typed forms cover
text/list/callout/day, structured tables, image/gallery captions with retained
attachments/crops, source notes with fixed bindings, Pilot advanced logistics and
Pilot knowledge with evidence/date validation. Required roles/types/day/knowledge
parts are protected. Legacy null sections are retained without automatic migration.
Desktop structure/workspace/information columns collapse to accessible mobile details.
Existing data-router blocking and native unload warnings protect unsaved input,
including navigation to legacy editing. Preview opens the saved document in a new
tab, without embedding HTML or claiming to include unsaved changes.

Advanced offer price/hotel/benefits, shared Pilot operational records/contacts,
Marketing campaign/item composition, image uploads/crops and business status changes
remain legacy workflows. No advanced objects or source snapshots are serialized in
unrelated updates. No backend/schema/storage/auth/renderer/dependency/delivery changes.
See [eight-template compatibility, contracts, validation and rollback](../docs/ui/front-003c-editor.md)
and the [prepared PR description](../docs/ui/front-003c-pr.md).
Run `.venv/Scripts/python.exe tests/browser_react_document_editor_smoke.py` after
building, or `python scripts/dev.py test-browser` for all 14 browser scripts.
