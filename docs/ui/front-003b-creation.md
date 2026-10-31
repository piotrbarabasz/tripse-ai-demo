# FRONT-003B: React document creation

Branch `feature/front-003b-document-creation`, based on latest `origin/dev`
`ac1a276` containing FRONT-003A. The working tree was clean before branching.
The baseline [Delivery run](https://github.com/piotrbarabasz/tripse-ai-demo/actions/runs/41215817382)
succeeded. This does not establish hosted feature acceptance.

## Existing workflow audit and reuse

Reviewed the migration roadmap, API-001 contracts, document-system design,
models/templates/repository/service/API, legacy studio.js, document-flow.js and
source-picker.js, React catalog/library, generated schemas, transport/query rules
and existing creation/source/browser tests. The backend registry is authoritative:
four Offer and three Pilot templates use Trips and standard; Marketing collection
uses Campaigns with new_trips/theme_collection. Confidentiality is client for offers,
internal_restricted for pilot basic/advanced, internal for knowledge and public for
marketing. React does not carry a second template registry.

DocumentService already validates compatibility/source revision, copies sanitized
or internal source snapshots according to confidentiality, initializes offer/pilot
data and default sections, and persists a DocumentDraft. Campaign creation also
copies its Trips in order and sets the document snapshot's chosen layout. Original
sources stay unchanged. A stable existing document_id is checked against creation
fields before re-reading a possibly newer source; identical repeats return the
saved document. Different payloads conflict. Repository JSON/GCS generation rules
remain authoritative. No backend implementation or rendering changes were needed.

The legacy creation flow already freezes the intent and checks stored identity on
ambiguous errors. React follows that contract. Legacy `#trips`/`#campaigns` open
source management; `#edit-draft/{id}` opens the saved document (marketing has its
own existing editor). React only selects existing Studio sources; it does not
create Trips/Campaigns or convert Planner jobs. Organizational provenance labels
are displayed from actual data; they do not establish access permissions.

## Routes, interface and contracts

`/app/documents/new` provides three Polish steps: template/variant, searchable
source/revision, and final confirmation with proposed title/confidentiality and
independent-snapshot explanation. Catalog links preselect the actual template via
`?template=...`. Query preselection deliberately avoids dotted template IDs in a
path segment, preserving the existing extensionless SPA fallback and refresh.
Unknown template IDs fail safely; only returned variants can be selected, and
generated request validation plus runtime compatibility checks guard submission.
No navigation, selection or preview creates a draft.

Native radio groups/labels, selected cards, focusable step headings, progress with
aria-current, keyboard actions, responsive grids, loading/empty/search/error states
and incomplete-source warnings support the wizard. Back/forward steps retain title,
source and variant; incompatible source types clear selection. An explicit refresh
never silently substitutes a newer selected revision. Legacy source management
remains available when the list is empty. No source editor or new global state.

The existing adapter now uses:

| API | Runtime contract and use |
| --- | --- |
| GET access | Existing can_edit guard, checked before actionable UI/private source reads |
| GET templates | Existing fixture-backed projection plus actual confidentiality |
| GET trips / campaigns | Generated TripOutput[] / CampaignOutput[], reduced to selector metadata |
| POST drafts | Generated DraftRequest; generated DocumentDraft response validation |
| GET drafts/{id} | Generated DocumentDraft and explicit intent comparison |

API-001 transport keeps same-origin credentials, no-store reads, five-second timeout,
safe errors and cancellation. TanStack mutations have retry=false/networkMode=always,
so they do not queue offline replays. No backend endpoints or schemas are added.
The wire exporter now captures actual Campaign/source-list responses, with no
changes to existing draft/library fixtures. Full draft data is fetched only for
creation verification; the library/detail routes keep their metadata-only contract.

## Persistence and recovery

Each explicit final confirmation creates a random accepted-format ID and freezes
the exact generated request fields in memory. A synchronous lock prevents duplicate
clicks, all controls are disabled/removed while pending, and each action POSTs once.
The request includes the selected source_revision, trimmed title, empty editorial
notes and demo_example=false. Sections/snapshot/private field initialization belongs
entirely to DocumentService.

Both the POST response and persisted GET must match the frozen ID, template, variant,
source identity/revision, title, notes, example flag, confidentiality and exactly one
source snapshot type. Mismatches stop writes and never overwrite an existing document.
A valid matching GET enables success; source edits after creation do not make the
saved snapshot magically current. Success invalidates Studio queries and shows
title/template/revision, a primary legacy editor link and React detail/library links.

Network errors, timeouts, invalid responses and 5xx can occur after commit. The flow
GETs the same document ID before offering retry. Only a definite 404 enables an
explicit repeat of the identical frozen payload/ID. Inconclusive checks offer GET
only; no fresh ID or second document is silently created. 409 requires a successful
refresh and a new explicit source review/confirmation; 422 similarly returns through
review. There is no autosave or generic mutation-retry control.

The root uses createBrowserRouter/RouterProvider with the original tree/basename for
supported SPA link/browser-Back blocking. It is constructed once outside StrictMode.
Its route error presentation reuses the safe shell fallback rather than exposing
the router's default diagnostic page.
Native unload/reload warns too. Data remains only in component/query memory; leaving
or reloading loses the form and recovery state. The unresolved ID is shown so a user
can locate it in the library. No storage, logs, raw errors or confidential fields are
written by this workflow.

## Access and security

Reader URLs show permission denial with no creation/source controls. The server
remains authoritative; 403 is distinct from session expiry. 401 uses the existing
query/mutation cache handler to clear private data, stop queries and hide the form.
Cloud IAP, same-origin write Origin, roles and readonly_demo exclusion are unchanged.
Legacy links validate identifiers and construct only known local paths. No IAM,
provider/storage/deployment/CI changes, packages or lockfile changes. Exact reviewed
frontend-source selection continues to include these TS/TSX/CSS files; the provenance
test explicitly covers both new implementation modules without widening its allowlist.

## Validation and remaining boundaries

Executed on 2026-10-31, Python 3.12.5 / pinned Node 24.18.0:

- Clean `npm --prefix frontend ci`: PASS, 325 packages installed and audit 0 findings.
- OpenAPI export, synthetic wire fixtures and generated TypeScript/Zod drift: PASS.
  No OpenAPI or generated schema changes; only additive source wire fixtures.
- TypeScript, ESLint and Vitest: PASS, **256 tests / 12 files**. New cases cover all
  eight templates/nine variants, compatibility, selectors, state preservation,
  explicit confirmation/duplicate locks, stable-ID retry, real transport timeout,
  ambiguous network/5xx/schema failures, read-back/mismatch, source refresh, 401/403,
  409/422, safe editor links, dirty layout/title/navigation and template read errors.
  Source projection tests ensure snapshots/private fields do not enter selector data.
- Production build: PASS. Deferred Document Studio **26.47 kB / 7.63 kB gzip**;
  main **567.94 kB / 174.31 kB gzip**. Supported data-router blocking adds to the
  existing main-bundle size advisory; it remains visible and is not suppressed.
- Full pytest: **1,243 passed**, 91.68 seconds, existing Starlette/AnyIO deprecation
  warning. Focused creation/source/provenance/Makefile: **105 passed**.
- Complete `python scripts/dev.py test-browser`: **all 13 scripts PASS**, including
  new React creation, A library, Planner, SPA, legacy Studio/source/reliability flows,
  viewer/Hub, both Marketing variants, actual PDF matrices, offline cloud and GT
  templates. The final mock API/worker/chat/idempotency/delivery smoke also passed.
  After final router/error/projection hardening, the final production build passed
  creation (including private-note redaction), catalog/library, Planner and SPA
  browser smokes again. No external service calls or CSP violations.
- Offline GCP source/preview contracts: PASS. Exact-source/provenance tests include
  both new modules. No Docker recipe, source allowlist or delivery changes.
- Changed documentation links, worklog CSV structure and `git diff --check`: PASS.

The new real-browser flow creates Offer, advanced Pilot and Marketing collection
documents against disposable JSON and offline verified-identity/fake-GCS stores.
It verifies POST → matching persisted GET → actual saved default sections/snapshots
→ real legacy editor, one browser POST per action, repeat-ID server semantics and
unchanged source records. A committed Pilot POST is deliberately replaced by a 503;
the UI recovers by GET without another POST. Reader direct URLs have no active
creation controls; reader writes and missing/foreign Origin writes are rejected.
Keyboard selection, browser-Back/stay, reload preselection, strict CSP and source
selection at 320/390/768/1024 pixels pass. Synthetic restricted notes are retained in
Pilot snapshots and removed from Offer/Marketing snapshots by existing server rules;
the React selector/review never displays them.

Screenshots are generated under ignored `local-data/react-document-creation-qa/`
(sources/review mobile and saved desktop for each family/local/cloud editor).
Mobile Pilot confirmation and desktop cloud Marketing success were visually inspected.
No GCP, paid AI/maps or production data is used.

Docker runtime is **not verified**: `docker info` cannot reach the absent
`dockerDesktopLinuxEngine` pipe. Hosted feature CI, real IAP and Cloud Run acceptance
are **not verified**. The successful baseline Delivery is not feature acceptance.
No push, hosted PR, merge, deployment or master modification is performed.

PR readiness: **ready for review targeting dev**, subject to the normal hosted gates
and owner merge/deployment process. [Prepared PR description](front-003b-pr.md).

FRONT-003A is catalog/library/metadata/history; B is creation/recovery and legacy
handoff. FRONT-003C remains React section editing and revision-aware saves; D remains
React preview, private assets, PDF/export and visual parity. Full editing, source
management, exports and rendering remain legacy workflows. ADR-0017 stays proposed;
this commissioned increment does not claim approval of the entire migration.

## Rollback

Revert this feature commit, rebuild and use the existing delivery procedure when
authorized. The A catalog/library and all legacy routes remain available. Open any
already-created document at `/documents/demo#edit-draft/{document_id}`. Retain all
saved documents, snapshots, revisions and assets; no data migration, deletion or
compensating write is required. No merge or deployment is performed by this task.
