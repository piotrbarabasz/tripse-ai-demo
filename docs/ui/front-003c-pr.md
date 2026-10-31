# feat(frontend): edit document content with revision-safe manual saves

Target: `dev`. Branch: `feature/front-003c-document-editor`.

An editor can open a persisted document from the library or creation success, edit
supported content/sections, save a new revision and continue in the same legacy
editor/renderer. Add `/app/documents/:documentId/edit`, immutable baseline/separate
form state, title/date/editorial/day-override fields, typed forms for all existing
section kinds, keyboard reordering, protected template bindings and custom-section
confirmation. Mobile structure/information panels collapse accessibly.

Use existing generated GET/PUT contracts and server revision CAS. Send required
title/revision plus changed groups only, keeping exclude_unset intact and advanced
business objects/snapshots/status untouched. Prevent concurrent saves, verify response
and stored content, invalidate metadata/history, and never retry automatically.
409 retains local input for explicit server inspection/confirmed discard; uncertain
writes require GET recovery before any deliberate same-payload repeat. Reuse A/B
permissions/session clearing and supported dirty navigation/native unload warnings.

Image references/crops/captions and structured offer/Pilot/Marketing data survive
unrelated changes. Advanced business forms, image management and integrated preview/
PDF UX remain legacy/FRONT-003D. The existing saved preview opens in a separate tab.
No backend engine/schema/storage/auth/renderer changes, new packages, Docker/source
weakening, infrastructure or CI/delivery changes.

[Eight-template matrix, exact field scope, validation evidence, gaps and rollback](front-003c-editor.md).
Clean npm ci/audit0, drift, TypeScript, ESLint, **318 frontend tests**, production
build, **1,243 pytest tests**, **105 focused tests**, offline provenance and the
complete **14-script browser suite** pass. Final editor smoke runs against the final
build. Real temporary JSON/fake-GCS cases cover Offer, Pilot logistics/knowledge and
Marketing, including real gallery attachments, unchanged business/source objects,
prior history, stale409, lost-response503 recovery and reader/Origin denial.
The main-bundle advisory remains visible; Docker daemon and hosted feature acceptance
are unavailable/unverified. Rollback reverts this UI increment and rebuilds while
retaining every saved record, revision and private asset.
Prepared locally; no push, hosted PR, merge, deployment or master modification.
