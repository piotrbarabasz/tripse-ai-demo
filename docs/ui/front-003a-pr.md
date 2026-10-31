# feat(frontend): add read-only Document Studio catalog and library

Target: `dev`.

Replace `/app/documents` with the real API-backed eight-template catalog and saved
document library. Add server search/filter/sort/pagination, metadata/history details
at `/app/documents/library/:documentId`, and validated links to existing legacy
editing/history and new-tab previews. Update the Hub to describe the catalog/library
as available while keeping creation/editing in legacy Studio.

Reuse API-001 transport, generated metadata/query validators and TanStack Query;
extend only the fixture-backed template description projection and revision-summary
read adapter. Keep read-only sessions free of write links, stop reads after 401,
cancel stale searches, and render no editable snapshot/HTML payload. No React writes,
backend/permission/storage/rendering changes, new dependencies or CI/deployment changes.
Lazy-load the new feature (13.57 kB minified deferred); retain the existing main-bundle
advisory without suppressing it.

Validation, screenshot locations, deferred B/C/D scope and rollback:
[FRONT-003A evidence](front-003a-documents.md). Clean install, typecheck, lint, 195
frontend tests, build, zero-finding npm audit and schema/client drift checks pass.
Full pytest: 1,243 passed; final focused reads/Makefile/CI/provenance/history: 103
passed. All 12 browser scripts pass on the complete rerun, including real PDFs.
New local/mock-cloud checks verify zero React writes and identical saved document/
revision data before/after reads. One unchanged legacy map-test timing failure was
followed by successful standalone/full reruns. Docker daemon is unavailable;
hosted feature acceptance remains separate.

Rollback restores the placeholder and old Hub labels by reverting this commit;
retain Planner, all existing Studio routes and all saved data. No data restoration,
storage migration, cloud change, merge or deployment is part of this PR.
