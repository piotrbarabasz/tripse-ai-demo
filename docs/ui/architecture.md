# UI architecture

Status: FRONT-001A shell, FRONT-001B private FastAPI integration, API-001 client/query foundation, FRONT-002 Hub/Planner and FRONT-003A read-only Studio implemented.
See [FRONT-002 flow, capability security and rollback](front-002-planner.md).
The [FRONT-003A feature](front-003a-documents.md) owns catalog/library/details under
`features/documents`, lazy-loads its workspace, and uses generated summary metadata
without loading editable snapshots. All document writes remain in legacy Studio.
See [frontend instructions](../../frontend/README.md) and
[current integration evidence/limits](front-001b-integration.md). ADR-0017 remains proposed.
See [source audit](../architecture/current-state-audit.md)
for current scripts and [ADR-0017](../adr/0017-modular-react-typescript-migration.md)
for decisions requiring approval.

Target requirements: [blueprint sections 1, 3, 6–8](../architecture/TRIPSE_ARCHITECTURE_BLUEPRINT.md).
See the [reconciliation crosswalk](../architecture/reconciliation.md) for stage IDs and
deliberate differences in module names/layout. FRONT-001A implements `app`,
`features/hub`, `shared/{ui,components,config,lib}` and `styles`; future feature,
provider and API folders below are created only when needed.

Target source layout (includes future directories):

```text
frontend/
  src/
    app/                 # bootstrap, router, providers, error boundary, shell
    features/
      hub/
      planner/
      documents/
      marketing/         # future workspace; existing campaign parity starts in Documents
      automations/       # future job/history/approval UI (blueprint AUTO-001)
      assistant/
    shared/
      api/               # generated types/client plus narrow transport adapters
      ui/                # selected primitives and TRIPSE presentation components
      lib/               # browser helpers without feature/domain dependencies
```

Use React + TypeScript in strict mode, Vite builds and React Router with `/app`
basename. Features own pages, view state, hooks and API-facing mappings. The app layer
composes features; shared code does not import features, and features do not reach into
another feature's internals. Introduce feature public exports only when needed. Avoid a
generic framework of empty modules in FRONT-001.

Blueprint `dashboard`/`trips` map to the narrower initial `hub`/`planner` modules;
Trip Catalog editing/reuse remains future scope. Its components/ui, components/layout,
api, hooks and lib map here to shared/ui, app shell, shared/api and feature-owned hooks.
This is a proposed organization choice, not a backend rename or owner-approved taxonomy.
Create future feature folders only when implementing their approved use cases.

API-001 now supplies TanStack Query at the application boundary and reusable
remote read/polling/invalidation/mutation options. See the
[API client guide](../api/api-001.md) for concrete usage and remaining schema gaps.
Local form edits, dirty state and preview requests remain feature-owned;
never refetch over unsaved fields. Use revision-aware save responses to update cache;
409 presents a conflict instead of silently overwriting. Cache keys distinguish
domain/resource and filters within one same-origin application composition; recreate
the client if a future mode/identity switch is introduced. Clear private data on
session failure (401). No persistent query
cache, token storage or customer payload logging by default.

Domain rules remain in FastAPI services/models. React renders validation results and
client-side hints; it does not decide editor permissions, final export eligibility,
confirmed prices or route verification. Generated API models do not equate planner
plans with Studio trips. Assistant UI will call a server orchestration boundary,
never provider APIs or storage directly.

Initial FRONT-001 shell contains navigation, accessible layout, error/not-found pages
and ordinary links to legacy workflows. It does not import global legacy scripts into
the React DOM. Later feature migrations preserve Polish labels, keyboard behavior,
loading/empty/error states and unsaved-change protections. See [component strategy](component-strategy.md).

FRONT-001A supplies an informative Hub with module cards and direct legacy links;
full operational Hub/Planner workflows were delivered separately in FRONT-002.
The historical FRONT-001A shell performed no API reads.
FRONT-001B adds compiled private assets/navigation and the same-origin `/health`
PoC (blueprint section 15), with loading, HTTP/schema errors, timeout and unmount
cancellation. Health only proves connectivity; its existing cloud middleware exception
is unchanged. It cannot establish session/authentication. API-001 reuses its existing
UI lifecycle with the shared transport and preserves its regression tests.
The router derives `/app` from Vite's `/app/` base and handles both entry forms.
FRONT-003B uses `createBrowserRouter`/`RouterProvider` with the same route tree and
basename so `useBlocker` can protect dirty creation forms, including browser Back.
It is constructed once in main.tsx outside StrictMode; API reads/writes stay in
TanStack Query. Native document navigations use a beforeunload warning.
`app/spa.py` owns serving/security presentation, not domain logic. Per-response style
nonces support Radix scroll-lock CSS without unsafe-inline/eval; main.tsx sets the
shared get-nonce value before rendering. Local uses `frontend/dist`; the Python-only
runtime image uses `app/spa_dist`. Node stays in the pinned builder stage. Exact
committed inputs and historical contexts are checked by the versioned source contract.

Build-time configuration is public. Never put IAP assertions, provider keys or backend
credentials into Vite variables. Build output uses same-origin URLs; no CDN/runtime
transpilation. Exact versions and build recipe are implementation-stage choices,
validated against supported Node/runtime and existing release provenance constraints.
