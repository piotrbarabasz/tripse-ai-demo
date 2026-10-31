# UI architecture

Status: proposed, ARCH-001. See [source audit](../architecture/current-state-audit.md)
for current scripts and [ADR-0017](../adr/0017-modular-react-typescript-migration.md)
for decisions requiring approval.

Proposed source layout (directories below do not exist yet):

```text
frontend/
  src/
    app/                 # bootstrap, router, providers, error boundary, shell
    features/
      hub/
      planner/
      documents/
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

TanStack Query will own remote reads, polling, invalidation and mutation state after
API-001. Local form edits, dirty state and preview requests remain feature-owned;
never refetch over unsaved fields. Use revision-aware save responses to update cache;
409 presents a conflict instead of silently overwriting. Cache keys distinguish mode,
resource and filters; clear private data on session/auth failure. No persistent query
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

Build-time configuration is public. Never put IAP assertions, provider keys or backend
credentials into Vite variables. Build output uses same-origin URLs; no CDN/runtime
transpilation. Exact versions and build recipe are implementation-stage choices,
validated against supported Node/runtime and existing release provenance constraints.
