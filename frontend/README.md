# TRIPSE React frontend — FRONT-001A / FRONT-001B / API-001

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

Open **http://127.0.0.1:8000/app** (or `/app/`). Legacy links and the `/health`
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
| `/app/planner` | Planned React view with link to existing `/planner` |
| `/app/documents` | Planned React view with link to existing `/documents/demo` |
| `/app/marketing` | Planned module only |
| `/app/automations` | Planned module only |
| `/app/assistant` | Planned module only; no AI requests |
| Unknown path under `/app` | Not-found page with Hub recovery |

Vite `base: '/app/'` is the source for BrowserRouter's `/app` basename (trimmed
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

**Later stages:** real Planner/
Trip Catalog workflows; Document Studio migration including print/PDF parity;
Marketing data; Assistant orchestration; Automations execution/history/approval.
No backend APIs, databases, paid providers or infrastructure are added here.
