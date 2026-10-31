# TRIPSE React frontend — FRONT-001A

Standalone application shell, 2026-10-31. This directory is independent of the
existing FastAPI application and legacy interfaces. Nothing is deployed or added
to the Cloud Run image. ADR-0017 remains proposed; this implementation is evidence
for review, not blanket architecture approval.

## Run locally

Use Node.js 24 LTS (`.nvmrc` pins the tested version, 24.18.0) and npm 11.
Node 24 remains supported through April 2028 ([release schedule](https://github.com/nodejs/Release#release-schedule)).
Keep the pinned patch updated as part of dependency maintenance.

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
This only changes full-page anchors in development; it sends no API requests and
uses no proxy or forwarded identity headers. Existing FastAPI access checks still
apply. Without this option links stay relative to the frontend origin, which
does not serve legacy pages. Production builds always use `/hub`, `/planner`, and
`/documents/demo`, even if the development variable is present during build.
All Vite configuration is public: never put secrets in `VITE_*` variables.

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
    features/hub/HubPage.tsx    # informative landing page, module/legacy links
    shared/
      components/               # PageHeader, ErrorBoundary
      config/                   # navigation metadata, development legacy URLs
      lib/                      # class-name helper
      ui/                       # selected shadcn/ui Button, Badge, Sheet
    styles/globals.css          # local tokens, Tailwind, responsive application CSS
    test/setup.ts
```

No empty future feature folders, provider layers, global store or API abstractions
are created. Future Planner, Documents, Marketing, Automations and Assistant modules
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

Vite `base: '/app/'` is the single source for the BrowserRouter basename.
Fixed desktop navigation uses `aria-current`; below 768px a Radix Dialog drawer
provides focus containment, Escape/outside dismissal and trigger focus restoration.
Route transitions move focus to the new heading and update the document title.
A skip link, semantic landmarks and visible keyboard focus are included.
Desktop collapse is intentionally omitted: the compact fixed navigation fits the
current six destinations. The drawer scrolls on short screens. PageHeader,
Button, Badge, Sheet and ErrorBoundary are reusable; no loading primitive is needed
because the shell makes no remote reads. Proposed navy/warm accent tokens are
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
See [local verification evidence](../docs/ui/front-001a-validation.md) for actual
results and browser limitations. No hosted checks are inferred from local tests.

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

**FRONT-001B recommended exact scope:**

1. Add same-origin compiled `/app` assets and a prefix-bounded HTML navigation
   fallback to FastAPI in local/cloud_demo only. Preserve readonly isolation and
   all legacy/API/internal behavior. Missing assets must return 404, not HTML.
2. Add deterministic Node build and compiled output to the existing Cloud Run
   image; update source allowlists, build recipe/manifests and provenance tests
   together. Do not add a separate frontend service.
3. Validate IAP, CSP, Host/Origin, asset MIME/cache behavior, authentication/session
   failure and all security denial cases without relaxing existing guards.
4. Add the bounded read-only same-origin `/health` PoC with validated response,
   loading/error/auth/cancellation states; no business mutations.
5. Run local compiled-image/worker and legacy/browser regressions, then explicitly
   authorized hosted IAP, chunk and deep-link acceptance with evidence and rollback.

This is the explicit split of the combined FRONT-001 roadmap. FRONT-001A does not
register FastAPI routes, package assets, change Caddy/auth/CSP, or prove hosted
acceptance. A Vite dev/preview fallback is not evidence for production fallback.
The read-only health PoC remains outstanding in FRONT-001B.

**API-001 and later:** generated OpenAPI client and TanStack Query; real Planner/
Trip Catalog workflows; Document Studio migration including print/PDF parity;
Marketing data; Assistant orchestration; Automations execution/history/approval.
No backend APIs, databases, paid providers or infrastructure are added here.
