# FRONT-003C: React document editor and revision-safe saving

Branch `feature/front-003c-document-editor`, based on fetched `origin/dev` `32be5be`
containing A and B, with a clean initial working tree. Before implementation the B
real-browser creation/recovery smoke passed. Latest baseline
[DEV Delivery](https://github.com/piotrbarabasz/tripse-ai-demo/actions/runs/41218186251)
was initially in progress and subsequently succeeded. The most recent available
[PR CI](https://github.com/piotrbarabasz/tripse-ai-demo/actions/runs/41209553296)
also succeeded; there was no separate B PR CI run in the recent history. These are
baseline evidence, not hosted acceptance of this feature.

## Audit and compatibility matrix

Reviewed roadmap/API-001, document-system architecture/security/acceptance/layout
and template-content-ground-truth (still DRAFT), A/B React code, generated contracts,
models/service/sections/templates/repository, legacy section/trip/marketing editors
and studio hash routing, creation/source/library/section/history/PDF regressions.
Actual models and DocumentService remain authoritative; no new engine or endpoint.

| Actual template | React editing in C | Structured groups retained for legacy editing |
| --- | --- | --- |
| offer.private | Core, source-section notes, custom sections, day overrides | offer_data, offer_details: summary/benefits/pricing/hotel/route/CTA/image management |
| offer.self_guide | Same core/section/day tools, existing Self-Guide roles retained | Scope/support/materials/briefing/route/pricing/accommodation |
| offer.school | Same core/section/day tools, existing school roles retained | Group, goals, supervision, safety, offer/business details |
| offer.incentive | Same core/section/day tools, existing incentive roles retained | Hotel/conference/team/meals/workshops/variants/pricing |
| pilot.basic | Core, source notes, custom sections and day overrides | pilot_data operational groups, contacts, booking references and shared logistics |
| pilot.advanced | Above plus typed logistics sections with day association, metrics, IANA zone, evidence, notes, plan B and existing accommodation reference | Shared pilot_data operational records/contacts/bookings |
| pilot.knowledge | Core/day/custom sections plus typed knowledge content, part, program stops, source references/check dates and verification | Original source program and general source editing; no factual generation |
| marketing.collection | Core and section tools; both layouts accepted as persisted | Campaign fields/item text/order/photos and campaign_trip_snapshots; no source refresh |

Core fields are title, date_label and editorial_notes. day_overrides edit only title/
description against original snapshot day IDs; explicit removal preserves empty-array
semantics. Business status is displayed, never automatically reset or approved.
Every advanced object above is omitted from unrelated PUTs and retained server-side.
No generic JSON editor or claim of full legacy parity.

## Route, loading and state

`/app/documents/:documentId/edit` is nested under the existing guarded workspace.
Library/details expose **Edytuj w React** to editors of active documents; B success
also links there. Existing legacy editor links/hashes remain intact. Identifiers are
validated before draft reads (including reserved filesystem names); a draft returned
for another ID or without unique stable section IDs is rejected. Readers and archived
documents receive no editable form. Direct reload uses the unchanged SPA fallback;
no root routing/server/security changes were made.

GET drafts/{id} uses the existing generated DocumentDraft output validator. An
immutable deep-cloned baseline and independent form are initialized once per document.
The form key excludes revision. Even explicit cache invalidation/refetch cannot
overwrite local input or silently replace the revision. Full private draft query
data is transient (gcTime=0); no local/sessionStorage persistence or document logs.
Template metadata comes from GET templates, including actual default_sections;
failed access/template/document reads have explicit error/loading/permission states.

The layout provides structure, selected-section workspace and document information.
Native details panels start collapsed below 768px and remain keyboard operable;
desktop uses three columns (two at intermediate widths). Polish labels show title,
selection/type/visibility, source snapshot revision, template, confidentiality, status,
confirmed revision and last saved time. Reordering uses buttons, not drag-and-drop.

## Supported sections and constraints

All ten existing kinds are recognized; kind/role/source binding are never editable.

| Kind | Controlled fields in C |
| --- | --- |
| text, callout, day | Title/body, permitted day association, visibility and order |
| list | Ordered items with add/remove/move-up controls and 200-item limit |
| table | Separate header/cell controls, add/remove columns/rows, matching row widths; max 8 columns/200 rows |
| image, gallery | Title/body and existing image captions; preserve asset IDs, image order and every x/y/zoom value |
| logistics | Actual DayLogistics fields including nullable metrics/date/reference, zone, route, evidence, verification, notes and plan B |
| knowledge | Actual KnowledgeContent strings, part, day-local stop IDs, verification and up to 100 references/check dates |
| source | Title and additional body notes; fixed template role/binding and derived snapshot/business content remain intact |

Title/body, all unedited structured properties, stable section IDs and source/day
associations survive updates. Reorder/remove normalizes order to contiguous indexes.
All template-bound sections are protected from removal; required source roles come
from server metadata, and bound logistics/knowledge roles remain required as in
section_issues(). A hidden required section may be restored, but a visible required
section cannot be hidden. Bound role/kind/day/knowledge part cannot change.
Custom sections have client-generated accepted-format IDs and generated-schema
defaults. Source sections cannot be fabricated. Logistics/knowledge additions are
offered only in their actual compatible template and require a snapshot day.
Custom removal requires explicit confirmation before changing the local array.

Generated limits/type validation is supplemented by table-width, nonblank-title,
IANA-zone and verification-evidence checks. Blank numeric inputs are null, not zero;
zero remains zero. Knowledge verified requires nonempty references with check dates;
logistics verified requires measurement evidence. No facts are generated. Required
missing sections and incomplete content are warnings where the backend permits
saving them: service calls section_issues(), but does not reject its returned
completeness issues. Warnings do not claim export/publication readiness. Unknown
roles/invalid structured references remain backend 422 errors.

`sections=null` identifies a legacy document: core/day edits preserve it and do not
automatically invoke default_sections or migrate template version. Section migration
is explicitly legacy-only. An actual empty array stays distinct from null.
Advanced assets/upload/crop, source editors, campaign composition and full business
forms remain legacy. Server/model validation and rendering determine final correctness.

## Narrow save, verification and recovery

Only **Zapisz zmiany** initiates a PUT. A synchronous lock and disabled fields prevent
duplicate/concurrent saves and interaction during the save/read-back interval.
Mutation retry=false/networkMode=always prevents automatic retry/offline replay.
The attempt freezes baseline and exact payload in memory.

Payload always includes loaded revision and required trimmed title. Only changed
date_label, editorial_notes, day_overrides and/or the complete intended section array
are added. Unchanged optional fields, business status, snapshots, offer_data,
offer_details, pilot_data and campaign objects are never serialized. `saveDraft`
validates with generated DraftUpdate but sends the original object, avoiding defaults
that would defeat Pydantic exclude_unset. Section titles/table headers/source references
are normalized consistently with backend whitespace constraints. No backend changes.

A successful response must match exactly baseline revision + 1 and intended content,
including all unchanged draft fields. Only server-owned revision/updated_at/updated_by/
last_library_operation are excluded from content equality. The subsequent stored GET
must match too. Only then does the editor adopt the new immutable baseline/form,
clear dirty state, show saved revision/timestamp and invalidate Studio queries (library,
details and history included). An unexpected result never clears local work.

409 retains the local form and old revision in a dedicated conflict state. An explicit
GET shows current server title/status/section content without replacing form values.
Adopting it requires an explicit discard confirmation. There is no force-save or
automatic last-write-wins. Advanced three-way merge is not implemented.

Timeout/network/503/other 5xx or invalid response leaves an uncertain, dirty attempt.
Only explicit read-only inspection is available. Exact expected new revision/content
confirms success; unchanged exact old baseline enables a deliberate identical retry;
a different/newer stored version becomes a conflict. A failed/inconclusive/mismatched
resource read keeps uncertainty. Repeating the same loaded revision still uses the
repository CAS, so a late original commit cannot produce a blind second update.
401 propagates through the existing cache/session handler and stops/unmounts private
operations; 403 remains permission denial with retained input. Raw errors are not shown.

## Dirty navigation and preview/legacy interoperability

The explicit states are clean/dirty, saving, saved, conflict, validation, uncertain,
confirmed-not-saved and denied. Shared supported useBlocker/beforeunload warnings
protect React route/Back navigation and native refresh/close/legacy navigation.
Discard/reset/removal confirmations do not submit data. No manual history rewriting.
Leaving intentionally loses memory-only changes/attempts; record recovery details
before leaving. Preview uses the existing saved GET endpoint in a new tab with
noopener/noreferrer, and explicitly excludes unsaved changes. No injected HTML,
iframe, new PDF engine or CSP relaxation. A/B behavior remains available.

## Validation and evidence

Executed on 2026-10-31, pinned Node 24.18.0 and Python 3.12.5:

- Clean npm ci: 325 packages installed; audit **0 findings**.
- OpenAPI, actual wire fixture and generated TypeScript/Zod drift checks: **PASS**;
  no backend schema or generated files changed.
- TypeScript, ESLint and Vitest: **PASS, 318 tests / 14 files**. New tests cover
  eight-template payload omission, all ten section kinds (including source notes),
  null/empty arrays, image retention, tables, logistics/knowledge validation, required
  sections, stable IDs/order, noncontiguous-index normalization, removal/discard,
  source-day overrides, loading, readers/archive/invalid IDs, no refetch overwrite,
  one PUT, revision/invalidation, 409, 401/403/422, timeout/network/5xx/schema ambiguity,
  mismatched-resource refusal and explicit read-back/retry.
- Production Vite build: **PASS**. Deferred Studio chunk **53.67 kB / 14.87 kB gzip**;
  main **568.24 kB / 174.38 kB gzip**. The existing >500 kB advisory stays visible,
  with no warning suppression or dependency/lockfile changes.
- Full pytest: **1,243 passed**, 79.57 seconds; one pre-existing Starlette/AnyIO
  BlockingPortal deprecation warning. Focused sections/creation/provenance/Makefile:
  **105 passed**.
- Complete `python scripts/dev.py test-browser`: **all 14 scripts PASS**. This
  includes C editing, B creation, A catalog/library, Planner, SPA, legacy Studio/
  source/reliability flows, Marketing, actual PDF matrices, cloud, GT templates and
  the final mock worker/chat/idempotency/delivery smoke. After the final add-order
  hardening, the editor smoke was rerun against the final production build.
- Offline GCP source/preview and exact-source provenance: **PASS**, with the four
  new implementation modules explicitly covered by the unchanged source contract.
  Changed documentation links, CSV structure and `git diff --check`: **PASS**.

Browser QA uses temporary synthetic data only: B creation → React load/edit/source notes/custom section/reorder
→ narrow PUT → matching persisted GET → reload → metadata/history → same legacy
editor and actual saved HTML preview. Offer, advanced Pilot logistics, Pilot knowledge
and Marketing run against JSON and offline verified-identity/fake-GCS stores.
Tests seed real private image assets/gallery crop/caption, confirmed synthetic offer
price, Pilot contacts/bookings and Marketing content. Unrelated fields, original
sources and prior saved revision are compared exactly after the React save.
Real stale-revision 409 and committed-but-lost PUT response503 exercise explicit
inspection/recovery. Reader URLs, missing/foreign Origin, keyboard/mobile and strict
CSP are checked without paid/external calls. Evidence is ignored under
`local-data/react-document-editor-qa/`.
The cloud harness also explicitly denies reader and missing/foreign-Origin PUTs,
then proves the saved document is unchanged. Mobile Pilot knowledge and desktop
cloud advanced Pilot screenshots were visually inspected; existing attachments are
real privately stored synthetic PNGs, not fabricated asset IDs.

Docker runtime is **not verified**: `docker info` cannot reach the absent
`dockerDesktopLinuxEngine` daemon pipe. Hosted feature CI, real IAP and Cloud Run
acceptance are **not verified**. The successful baseline Delivery does not imply
feature acceptance. No cloud/provider calls, push, hosted PR, merge, deployment,
master modification or measured hours/costs are part of this work.

Known parity limits are the advanced groups in the matrix, legacy null-section
migration, image management, integrated preview/export and three-way merge. Browser
Intl validates IANA zones for the form; server ZoneInfo/model validation stays final.
In-memory edits/attempts are lost after intentional leave/reload. Canonical protected
example records still require the existing copy workflow; server protection remains
authoritative. PR readiness: **ready for review targeting dev**, subject to normal
hosted gates and the owner-controlled merge/deployment process.

FRONT-003A remains catalog/library/history; B creation; C supported core/section saves;
D integrated preview/image workflows/A4/social/PDF parity is deferred. The broader
architecture ADR stays proposed, with no implied approval of the entire migration.
No backend models, service/repository semantics, storage, auth, IAM/IAP/WIF/Terraform,
Docker recipes, source allowlist, CI/delivery triggers, dependencies or lockfile change.

## Rollback and review

Revert this feature commit, rebuild and use the normal authorized delivery process.
A/B catalog/library/creation and every legacy route remain available. Continue editing
any document at `/documents/demo#edit-draft/{document_id}`. Retain all saved drafts,
snapshots, revisions and image assets; no migration, restoration or deletion is needed.
No automatic merge/deploy/master promotion. [Prepared PR description](front-003c-pr.md).
