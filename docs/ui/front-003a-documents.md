# FRONT-003A: React template catalog and document library

Implemented on `feature/front-003a-document-library`, based on latest `origin/dev`
`1da3d79` containing FRONT-002, 2026-10-31. The base
[DEV Delivery run](https://github.com/piotrbarabasz/tripse-ai-demo/actions/runs/41212693184)
was initially in progress and subsequently succeeded. No deployment was needed for
this work and no hosted acceptance of the feature branch is implied.

## Available routes and actions

| Route | Implemented behavior |
| --- | --- |
| `/app/documents` | All actual API templates, grouped into offers, pilot materials and marketing. |
| `/app/documents/library` | Saved metadata, title search, family/template/status/archive filters, sort/direction and server pagination. |
| `/app/documents/library/:documentId` | Current metadata and preserved revision summaries; historical preview links. |

These are nested React routes under the existing guarded FastAPI SPA entry.
Deep-link refresh works through its existing prefix-bound fallback. The Document
Studio navigation remains active on details. Route navigation has a loading state,
updates the document title and focuses the page heading. Catalog/library navigation
uses native links with current-page semantics, including keyboard and mobile access.

The Hub now says **Katalog i biblioteka dostępne**, with a React primary link and a
legacy secondary link. Planner remains operational. Creation and editing remain in
legacy Studio; Marketing, Automations and Assistant remain planned React modules.

The catalog comes from `readTemplates()`, not a frontend registry. It displays all
eight actual IDs: offer.private, offer.self_guide, offer.school, offer.incentive,
pilot.basic, pilot.advanced, pilot.knowledge and marketing.collection. Names,
description, source type and layout variants come from the response. Offers/pilot/
marketing are presentation labels for existing backend families. No publication
approval or customer-specific permission is inferred from family or confidentiality.

The library uses only saved API data. It shows title, template name or verified ID,
source title/type, business status, revision, modified date, confidentiality and
archived state. Status **Gotowy** is not approval to publish. All filters map to the
existing API query parameters. Page size is 25; offset, limit, total and has_more
come from the server. No all-document download is paginated in browser memory.
Search is delayed 300ms; each key change consumes AbortSignal to cancel the pending
timer or HTTP read. Old rows are not used as placeholders under a changed filter.
Filters reset the offset. They remain in component memory across detail/tab
navigation and reset when leaving the workspace or reloading. They are never put
in localStorage, sessionStorage, URL search strings or analytics. Transient reads
have zero inactive-cache retention (`gcTime: 0`), with API-001's default zero retry.

Details deliberately use metadata from revision summaries, newest first. They do
not fetch full editable drafts, private pilot operational fields or snapshot text.
History shows preserved revision numbers, title/status and timestamps; it does not
invent missing revisions or authors, restore historical content, or implement editing.

## Reused API contracts and narrow additions

| Existing GET | Adapter / guard |
| --- | --- |
| `/api/document-studio/access` | Existing readAccess, can_edit projection; gates resource reads and editor links. |
| `/api/document-studio/templates` | Existing readTemplates; projection extended only with description, present in all real template objects and synthetic FastAPI fixtures. |
| `/api/document-studio/library` | Existing readLibrary and generated LibraryPage/DocumentSummary; generated query guard validates filter values. |
| `/api/document-studio/library/{identifier}/revisions` | New readRevisions, generated DocumentSummary[] runtime validation; rejects responses belonging to a different document. |

Transport, same-origin credentials, no-store requests, safe errors and TanStack Query
come from API-001. The FRONT-002 observable session-failure mechanism clears private
cache and disables further requests after 401. The workspace displays a stable
expired-session message. A 403 remains a distinct permission error, with no automatic
retry. 404, 503, malformed responses, loading and empty states have safe messages;
recoverable read failures offer an explicit GET retry. No raw server detail, pilot
payload, assertion or credential is logged or displayed.

The access result is a UI hint. Existing backend local/IAP/membership/Host/Origin
guards remain authoritative for every API and preview. Current cloud shared-demo
permissions are preserved; this stage does not implement proposed per-customer or
per-pilot scope rules. A reader gets permitted metadata/history/previews and no
creation/editing links. An archived document has no editor link even for an editor.
No backend router, response model, endpoint, security policy or readonly composition
was changed. Readonly still exposes no private `/app` workspace. OpenAPI, generated
files and the existing wire fixture remain unchanged and pass drift checks.

## Legacy interoperability and preview safety

The following routes were verified against `studio.js`, `library.js` and the new
real-browser smoke, including the existing editor's save control being present:

- Editor: `/documents/demo#edit-draft/{identifier}` (editor-capable session only).
- Legacy history: `/documents/demo#revisions/{identifier}`.
- Legacy library: `/documents/demo#drafts`.
- Creation fallback: `/documents/demo#templates`, without inventing a per-template
  shortcut or claiming a React creation flow.
- Current preview: `/api/document-studio/drafts/{identifier}/preview`.
- Historical preview: `/api/document-studio/library/{identifier}/revisions/{revision}/preview`.

Identifiers must satisfy the generated identifier constraint and cannot be reserved
repository device names. Revisions must be positive safe integers. Links are built
from these values, never from an untrusted server URL. Preview anchors open a new
tab with `noopener noreferrer`; no arbitrary HTML is injected and no iframe or
second PDF engine is introduced. Existing frame-ancestors/DENY and strict SPA CSP
remain unchanged. The legacy history application's existing frame behavior is not
rewritten; React offers an explicit top-level preview tab under the existing guards.

The React workspace has no document write handlers or mutations. Existing API-001
write adapters are retained for future stages but are never called here. Browsing,
filtering, inspecting details and following preview links cannot create, save,
duplicate, archive, restore or change status. Legacy editor links transfer control
to the existing application; this stage does not perform an edit there.

## Packaging, validation and evidence

Document Studio is lazy-loaded as one feature chunk. The production build measures
13.57 kB minified / 4.13 kB gzip deferred until entering the workspace; main JS is
510.57 kB / 156.56 kB gzip. These are byte sizes, not a claimed latency benchmark.
The existing >500 kB main-chunk advisory remains visible and unsuppressed. There is
no unrelated vendor split, new package, lockfile change or new frontend framework.

New production files use existing `.ts`/`.tsx`/`.css` source inputs. FRONT-001B's
versioned allowlist already includes them; provenance tests explicitly include the
workspace/link files and retain historical-release checks. No source-contract
relaxation, Docker change, workflow permission/trigger/pin change, deployment logic,
IAM/IAP/WIF/Terraform or cloud-resource change was made. The new browser smoke is
registered in the existing test-browser command, which now runs 12 scripts.

Commands from the repository root (use `.venv/Scripts/python.exe` on Windows):

```sh
npm --prefix frontend ci
npm --prefix frontend run api:check
npm --prefix frontend run typecheck
npm --prefix frontend run lint
npm --prefix frontend test
npm --prefix frontend run build
python -m scripts.export_openapi --check
python -m scripts.export_api_fixtures --check
python -m pytest -q
python tests/browser_react_documents_smoke.py
python scripts/dev.py test-browser
python -m scripts.gcp.ci offline
git diff --check
```

The new browser test seeds only temporary synthetic JSON and existing fake-cloud
repositories. It browses all eight templates; tests real API filtering, search,
25-item pages, empty/archive states and revisions; follows historical preview and
legacy editor/history links; covers 320/390/768/1024 widths and keyboard navigation;
and checks strict CSP, zero React writes and no external requests. Stored JSON
fingerprints and fake-cloud object bytes are identical before/after the run,
including saved revisions. Python regression tests make the same preservation check.
Existing Studio/PDF behavior remains covered by the full browser command.

Inspected screenshots are gitignored under `local-data/react-documents-qa/`:
`local-*`, `cloud-editor-*`, `cloud-reader-*`, each with catalog, catalog-mobile,
library, library-mobile and history views. They contain synthetic QA data only.

Local validation on 2026-10-31:

- Clean npm ci, api:check, typecheck, ESLint, **195 Vitest/RTL tests**, production
  build and zero-finding npm audit passed. No dependency or lockfile changed.
- Full Python regression: **1,243 passed** in 77.94s, with one existing
  Starlette/AnyIO BlockingPortal deprecation warning. Final focused read-preservation,
  Makefile/CI/provenance/historical-release check: **103 passed**.
- OpenAPI and synthetic wire-fixture `--check`, generated-client drift, offline
  source/preview contracts, documentation links and whitespace checks passed.
- The new local/cloud-editor/cloud-reader browser flow passed. The complete
  **12-script** `scripts/dev.py test-browser` rerun passed, including Planner,
  legacy Studio/catalog/library/history/source/creation/reliability, marketing and
  trip-document PDFs, readonly preview, authenticated cloud, GT template matrix
  and simulator/worker/delivery regressions. No external services were called.
- The first broader browser attempt hit an existing legacy map-test timing race
  (`window.mapTest` not ready). That unchanged test immediately passed standalone;
  the subsequent full rerun passed. No assertion or legacy implementation was altered.
- Desktop/mobile and cloud-reader screenshots were visually inspected. Synthetic
  saved JSON/history fingerprints and cloud-double object bytes remain identical.
- Docker runtime validation is unavailable: `docker info` fails because the
  `dockerDesktopLinuxEngine` daemon pipe is absent. Existing Docker/source contract
  tests pass. Hosted feature-branch CI/IAP and container build/start are not claimed.

The source is ready for a review PR targeting dev. The final offline/provenance
checks are also run against the local commit containing the new source files.

## Deferred FRONT-003B/C/D boundaries and rollback

These are recommended follow-up boundaries requiring separately scoped tasks:

- **FRONT-003B:** source selection and document creation from existing Studio Trip/
  Campaign records, independent drafts, duplicate-submit protection and revisions.
  No implicit Planner TripPlan conversion.
- **FRONT-003C:** actual draft/section editing, dirty-state protection, revision
  conflicts, image rights/upload/crop and separately authorized library write actions.
- **FRONT-003D:** full review/preview/export integration and acceptance parity across
  all templates/marketing variants, long content, A4/social and existing PDF engine;
  decide cutover only after authorization and parity evidence. Preserve security policy.

No editor, document creation, mutation, AI generation, storage migration or rendering
rewrite is implemented by A. Template examples/copy workflows, full draft content,
asset management, historical-content restoration and publication remain deferred.

Rollback reverts the FRONT-003A commit, restoring the documents placeholder/Hub card
and removing the new adapter/description projection/feature routes/browser entry as
one unit. Retain FRONT-002 Planner, API-001, all legacy routes and every stored head,
snapshot, revision and asset. Users can immediately return to `/documents/demo`
and its verified hashes. No data rollback or restoration is needed. Any later image
release/rollback uses the unchanged separately authorized deployment process.

PR target: `dev`; [prepared title/body](front-003a-pr.md). No push, PR creation,
merge or deployment is performed here. Hosted feature-branch CI/IAP and actual
container-runtime acceptance remain separate from local PR readiness.
