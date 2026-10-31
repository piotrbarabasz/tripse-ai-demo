# feat(frontend): migrate Hub and Trip Planner to React

Target: `dev`.

`/app/planner` replaces its placeholder with a Polish request form, trusted MOCK/LIVE
capabilities, existing mock examples, explicit create/retry decisions, bounded job
polling and a validated same-origin link to the existing plan/map viewer. The Hub
now presents Planner as available and keeps a secondary legacy link. Studio and
other planned modules retain their current scope.

Add a minimal guarded `GET /api/workspace/capabilities` Pydantic contract; cloud
permissions come from the existing verified actor, and readonly gets no endpoint.
Regenerate OpenAPI/types/guards and extend synthetic fixtures. Reuse API-001 transport
and query conventions, preserving cloud operation UUIDs and local non-idempotency.
Keep session expiry visible after private-cache clearing. No new dependencies,
storage, maps implementation, auth mechanism, infrastructure or deployment changes.

Validation and remaining limits: [FRONT-002 implementation evidence](front-002-planner.md).
Clean install, schema/client drift, typecheck, lint, 162 frontend tests, build and
zero-finding npm audit pass. Full pytest: 1,240 passed; final focused Makefile/CI/
provenance/historical-release check: 100 passed. All 11 browser smoke scripts pass,
including the real React/API/mock-worker/viewer flow, offline cloud reader/editor,
legacy modules and actual PDF checks; strict CSP and no external requests verified.
Docker runtime is unavailable because its daemon is stopped. The eager bundle has
an unsuppressed 506 kB minified chunk advisory. Hosted IAP/feature-branch CI acceptance
remains a separate gate. No PR, push, merge or deployment has been performed.

Rollback restores the placeholder/Hub navigation and removes only this feature's
capability/client integration, retaining API-001, legacy routes and all existing jobs/data.
