# feat(frontend): create documents from revisioned Studio sources

Target: `dev`. Branch: `feature/front-003b-document-creation`.

An editor can now create a saved document in React from an existing Studio Trip or
Campaign, review its source revision/confidentiality and continue in the actual
legacy editor. Extend FRONT-003A with `/app/documents/new`, server-backed template
and variant choices, searchable source selection, explicit final confirmation and
verified success/library/detail navigation. Query-based template preselection keeps
deep-link refresh compatible with the unchanged SPA fallback.

Use generated DraftRequest/DocumentDraft/Trip/Campaign validators and the existing
transport/service. Freeze one ID and payload per intent, prevent duplicate clicks,
disable mutation retries and verify the persisted snapshot. Ambiguous outcomes use
GET recovery; only a verified 404 permits an explicit identical retry. Conflicts
require fresh source review. Reuse session-expiry/cache clearing and server-derived
editor capability; keep readers non-actionable. Add supported data-router dirty
link/Back blocking, native unload warnings and a safe route error page.

No backend engine, schemas, storage, permissions, rendering, dependencies, lockfile,
Docker recipes, source verification, CI or delivery boundaries change. Source and
full document editors/PDF/assets remain legacy; React C/D are deferred.

Validation: clean npm install/audit 0; schema/wire/generated drift, TypeScript,
ESLint, **256 frontend tests**, production build, **1,243 pytest tests**, **105 focused
creation/source/provenance/tooling tests**, offline source checks and the complete
**13-script browser suite** pass. Real temporary FastAPI JSON/fake-GCS flows verify
Offer/Pilot/Marketing, immutable sources, snapshots/default sections, committed-write
503 recovery, stable-ID repeat, editor/reader/Origin behavior and legacy handoff.
Final affected React browser checks run against the final build. Main bundle retains
its unsuppressed size advisory. Docker daemon and hosted feature acceptance are
unavailable/unverified.

[Audit, contracts, evidence, limitations and rollback](front-003b-creation.md).
Rollback reverts this increment and rebuilds; retain every created document,
snapshot, revision and asset, accessible through legacy Studio. No migration or
compensating deletion. Prepared locally; no push, hosted PR, merge or deployment.
