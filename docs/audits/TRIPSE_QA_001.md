# TRIPSE-QA-001 — Reliability audit

Date: 2026-10-28. Branch: `dev`. Audited baseline:
`ecf2f115755c2b208e5bd7e5df97f8bb9c005ec4`.
Working tree was clean before this task. Changes below remain uncommitted.

## Executive summary

Document Studio is suitable for continued **internal DEV testing with synthetic
data after these fixes**, within the documented single-process local JSON or
authenticated GCS configuration. This is a source-level and isolated runtime
assessment, not acceptance of a deployed release or approval for customer data.

Seven defects were reproduced and fixed. The most consequential storage defect
deleted image bytes following an ambiguous, already committed metadata save.
Both document editors also discarded edits entered while a save response was
pending, and cleared their unsaved-change warning. The source Trip editor used
the same unprotected save pattern and now receives the same interaction lock.
Other fixes address stale
navigation, detached filter timers, misleading status retries, malformed section
bindings and multiline print overflow.

Existing coverage is strong for all eight templates, both marketing variants,
snapshot independence, full-state duplication, immutable history, stale revisions,
GCS generation races, access roles, image validation and real browser PDF output.
Passing the original suite did not detect the defects above.

Confirmed limitations remain: local JSON does not coordinate multiple processes;
library pagination scans all metadata; image validation repeatedly downloads the
same image. Live GCP behavior, backup restoration and real customer-data controls
were not verified. No deployment, cloud writes, IAM change, paid service call,
commit or push was performed.

## Scope, architecture and method

Reviewed the recent Document Studio/library changes, models, service/API,
JSON/GCS repositories, assets, library operations, editors, section renderer and
print script, plus `main.py`, `cloud_access.py`, `cloud_runtime.py` and existing
pytest/browser tests. ADR-0011 and ADR-0014 define the access and history contracts;
their proposed status has not been changed. Recent history included the library
implementation/documentation commits `05a1d5e`, `f4c0b6b` and merge `ecf2f11`.

The application uses full document snapshots and optimistic revisions. JSON
archives the previous committed state before atomic replacement, under a shared
in-process lock. GCS archives create-only before a generation-conditioned head
upload; summary metadata travels with that upload. There is no cross-object
transaction. Current history combines the head with older preserved revisions.
Cloud membership and editor/Origin checks precede private routes; local access
checks peer, Host, Origin and proxy headers. Browser editors keep working copies
and submit revision-bearing updates to the same API.

New tests use temporary data, fake cloud adapters and loopback servers. Controlled
faults include exceptions after a real isolated commit, held HTTP responses,
simultaneous writes, invalid payloads, corrupt caches and delayed browser timers.
Suspicions were reproduced before their fixes. Architectural limits were measured
separately rather than changed through a broad persistence redesign.

## Findings

Line ranges refer to the resulting working tree; each row identifies both the
failure mechanism and its executable evidence.

| ID | Severity | Files / lines | Reproduction, observed and expected behavior | Evidence / status |
| --- | --- | --- | --- | --- |
| QA-001 | P0 — integrity | `app/document_studio/assets.py:75–106` | Upload an image; let repository metadata save commit, then raise `StorageError` before returning. Cleanup deleted the image although its metadata remained in the library, making a published asset unreadable. Expected: an uncertain result must not destroy potentially committed data. | `test_ambiguous_asset_metadata_commit_keeps_referenced_bytes`, JSON and fake GCS: both failed before fix, both pass now. Fixed: preserve immutable bytes on ambiguous storage errors. A definite failure can leave an orphan; no automatic deletion is attempted for an uncertain commit. |
| QA-002 | P1 — lost edits | `frontend/trip-editor.js:103–110`, `frontend/marketing-editor.js:97–105`, `frontend/studio.js:122–134` under `app/document_studio/` | Hold a successful PUT response after commit; enter more text; release the response. Both document editors replaced their model and set dirty=false. Navigation gave no warning and the late text was absent on reopen. The source Trip save path also lacked interaction protection. Expected: prevent concurrent editing or retain those edits as dirty. | Original browser reproduction confirmed loss in `offer.private` and `marketing.collection`; a separate held-response source Trip test failed its interaction-lock assertion. `reliability_qa.py` now verifies document-editor keyboard protection, failure unlock/retry/reload, and the source Trip lock/committed state. Fixed with `inert` during the full save/refresh interval; `finally` clears it on errors. |
| QA-003 | P1 — wrong view | `frontend/studio.js:183–222`, `frontend/trip-editor.js:120–132`, `frontend/marketing-editor.js:133–142` | Hold document GET; navigate to library; release GET. The old editor replaced the library while the URL still pointed to it. Expected: only the latest navigation may render. | Browser failed with missing `#library-view` after delayed response; passes after fix. Route generation checks discard obsolete reads/errors. Editor initialization keeps intermediate results local and checks route currency after asynchronous asset loading. The regression directly holds the document GET; exhaustive permutations of asset/legacy-init responses are not claimed. |
| QA-004 | P1 — misleading mutation result | `app/document_studio/library.py:86–92` | Set status ready with operation UUID K/base revision 1; resend K/revision 1 requesting in_review. API logic accepted it as a retry and returned ready as success. Expected: a different requested outcome must conflict. | `test_status_retry_with_changed_payload_is_not_reported_as_success` failed before fix. Fixed: status retry matching includes the requested target state; the changed request now conflicts. No schema migration required. |
| QA-005 | P1 — invalid saved/preview state | `app/document_studio/sections.py:38–43` | Change a default advanced logistics section to kind source, clear logistics, retain its dynamic role. Model validation accepted it; rendering looked for that role in static bindings and raised StopIteration/HTTP 500. The update path could also save that state. Expected: reject unsupported source binding without committing it. | `test_source_section_cannot_bind_to_dynamic_logistics_role` reproduced the exception. Fixed: source roles must belong to static template bindings. Preview and PUT now return 422; head stays revision 1. |
| QA-006 | P1 — valid data cannot print | `app/document_studio/rendering/trip_documents.py:10–30` | Add 160 short newline-separated lines to a 15-day document. Character-only chunks produced oversized blocks: two layout errors and disabled print, despite complete valid stored text. Expected: paginate this ordinary multiline text without loss. | New chunk regression failed; browser reproduced layout errors before fix. Fixed: chunks also bound explicit line breaks, preserving every character. Chromium now enables print; PDF has 14 pages and text extraction finds all line IDs 0–159. |
| QA-007 | P1 — library stuck loading | `app/document_studio/frontend/library.js:11–15` | Type a search then immediately reset filters; hold reset response until the old debounce fires. Old detached form incremented global sequence, invalidating the new form's response. Expected: reset displays current results. | Browser regression observed zero cards after release, then passes with two documents after fix. Detached roots now return before changing request sequence. |
| QA-008 | P1 — known unsupported deployment limit | `app/document_studio/repository.py:16,38,78–123` | Two processes load revision 1, synchronize before replacing head, then perform serialized physical replacements. Both report revision 2; only one title survives and history is [2,1]. Expected cross-process CAS is not provided by an RLock. | Confirmed in `reliability_experiments.py`. **Not changed:** ADR-0014 explicitly limits local JSON to one process. Experiment disables disposable summary-cache writes to isolate head coordination. Do not run several API workers against the same local root. GCS and same-process instance races have separate passing CAS tests. |
| QA-009 | P2 — measured scaling limit | `app/document_studio/library.py:63–84`, `cloud_storage.py:148–159` | Query limit=25 over 100/1000 synthetic metadata records. All 100/1000 rows are scanned before filtering/sorting/slicing. Expected current contract provides pagination of results, not bounded backend query work. | Confirmed below; no full-document reads for metadata-bearing objects. **Deferred design limit**, already described in ADR-0014. No Firestore or indexing feature added. |
| QA-010 | P2 — redundant image I/O | `app/document_studio/sections.py:53–65`, `assets.py:34–41` | Validate 20 image sections referring to one image. Each calls AssetStore.get, which reads private GCS bytes. | Experiment counts 20 binary adapter reads for one validation. UI validation and preview are separate requests, so repeated work can compound. **Deferred:** consider metadata-only existence validation or request-scoped deduplication after profiling. No cache with new invalidation semantics introduced. |

## Test execution and coverage

### Baseline and regression

| Execution | Measured result |
| --- | --- |
| Baseline `.venv/Scripts/python.exe -m pytest -q` | **699 passed, 0 failed, 0 skipped**, 43.45 s; one pre-existing Starlette/AnyIO deprecation warning. |
| New backend file `tests/test_reliability_audit.py` | **25 passed**, 2.91 s on the focused run. Includes parameterized local/fake-GCS paths. |
| Complete regression | **724 passed, 0 failed, 0 skipped**, 45.38 s on the final complete run before extending the same save lock to the source Trip form; that extension is covered by the final Studio browser rerun. |
| `tests/browser_document_studio_smoke.py` | PASS, including existing catalogue and library QA plus the new reliability module. Covers eight IDs, both marketing variants, typed sections, images/crops, dirty navigation, history, restart, mobile and PDF text. |
| `tests/browser_cloud_demo_smoke.py` | PASS through real cloud routers with injected storage/auth boundaries; no external calls. |
| `tests/browser_trip_documents_smoke.py` | PASS; six actual PDFs, 2/10/15-day programs, long copy, Polish text, internal-data isolation, revision and restart. |
| `tests/browser_marketing_smoke.py` | PASS; eight actual PDFs, 1/3/8 trips, both variants, A4/social, images, order, crops and restart. |
| `python -m scripts.gcp.ci offline` | PASS; no credentials or deployment. |
| `node --check` for four changed JS files | PASS. |

Browser scripts print aggregate acceptance outcomes, not pytest test counts.
Their individual total wall times were not instrumented. Browser suites were run
as regression after targeted fixes; the baseline number above refers to pytest.

An intermediate complete run failed only the existing browser inventory contract
because the new helper initially used a `browser_` prefix. The helper was renamed
to `reliability_qa.py` and integrated into the existing Studio browser entry point.
No CI/CD configuration or inventory assertion was relaxed.

### Independent new checks

- Actual threads and separate repository instances: one successful update, one
  conflict, head revision 2 and exact immutable revision 1 in both storage modes.
- Lost response after committed archive, restore, status and duplicate: replaying
  the same operation returns the committed result without extra copies/revisions.
- Corrupt/missing-shaped/stale local metadata cache: validated head repairs the
  summary; a corrupt authoritative document is not silently replaced by fixtures.
- Pre-library document without sections/authorship/status fields: open, duplicate,
  archive, restore and edit without inventing old history or authors, both stores.
- All four library mutations reject reader, stranger and anonymous writes;
  historical reads/previews reject unauthorized identities. Wrong Origin and Host
  remain denied. Existing tests cover signed IAP claim failures and local proxy
  boundaries; these were not replaced with a fake UI-only check.
- Manipulated client/public previews for all four offer types and both marketing
  variants: injected internal day notes do not appear in rendered output; HTML in
  title is escaped. This checks renderer projection, not prevention of an editor
  deliberately copying sensitive text into a public free-text field.
- Real browser delayed saves, save failure/retry/reload, delayed navigation,
  filter/reset timer and a generated, text-verified multiline PDF.

Existing tests independently retain full lifecycle and snapshot/section-order,
hidden-section, image/crop, long-text, archive edit denial and status/export checks.
They also inject GCS faults before history, before head and after head commit;
ensure failed CAS never archives a losing candidate; and exercise local failed
replace/retry and immutable-history corruption.

## Measured experiments

Run `python tests/reliability_experiments.py` with the project virtual environment.
All data is synthetic; temporary documents are deleted by TemporaryDirectory.
Ignored artifacts are in `local-data/reliability-audit/`.

| Fake-GCS metadata size | Rows returned | Rows scanned | Full document reads | Median of 5 runs | Summary JSON bytes |
| --- | --- | --- | --- | --- | --- |
| 100 | 25 | 100 | 0 | 54.61 ms | 55,300 |
| 1000 | 25 | 1000 | 0 | 559.55 ms | 553,000 |

These are local Python/fake-adapter measurements, **not cloud latency or cost
estimates**. Other runs under concurrent test load were slower; the linear work
and bytes scanned are the meaningful observations. Missing cloud metadata requires
validated full-document fallback, so legacy-heavy libraries cost more reads.

The two-process reproduction returned process A/revision 2 and process B/revision
2, with process B as final head. The winner is scheduling-dependent; the unsafe
double success is the finding. Shared-root caches can also race in unsupported
multi-process operation; cache writes are disabled in the isolated head experiment.

The image experiment measured 20 binary downloads for 20 references to one image.
The new Chromium PDF has 14 pages and all 160 exact numeric line identifiers.

## Answers to the eight review questions

1. **Revision consistency:** supported local single-process writes and fake-GCS
   generation races preserve the previous committed state. Immutable collisions
   must equal it. Failed head writes can leave a redundant previous snapshot;
   they do not publish losing candidate content as history. Local multi-process
   coordination is explicitly absent and reproduced in QA-008.
2. **Ambiguous retries:** library actions are recoverable with the same operation
   ID/base revision. QA-004 fixes changed-status misidentification. Plain draft
   PUT and image creation do not have durable global request deduplication; after
   lost success, reread head/library. An old PUT revision conflicts rather than
   overwriting newer data. Upload retry can create another image, and resetting a
   browser session loses its in-memory pending operation key.
3. **Metadata reliability:** malformed/missing/stale local cache recovers from
   validated data; malformed/missing cloud summary falls back to stored JSON.
   Authoritative corruption fails the listing rather than making up data. A
   manually altered but schema-valid summary with a matching local stamp, or
   out-of-band GCS custom-metadata edits, is trusted; detecting such changes is
   not guaranteed. Normal GCS application writes attach summary and bytes together.
4. **Editor reliability:** QA-002/003/007 reproduce and fix actual loss and stale
   UI races. Existing dirty guards and new failed-save recovery pass. Exhaustive
   save/upload/preview/navigation interleavings and long browser memory-soak
   sessions have not been tested; no claim of complete race freedom is made.
5. **Confidentiality:** tested membership, role, Origin/Host, historical access,
   public/client projections and escaped output held. Private routes remain
   shared among approved readers; there is no new per-document/client ACL.
6. **Legacy compatibility:** absent additive fields load with defaults, authors
   stay unknown and sections remain legacy unless initialized explicitly. New
   lifecycle regressions pass locally and in fake GCS. Unknown future schema or
   corrupt storage fails validation; no destructive automatic migration occurs.
7. **Output correctness:** QA-006 confirms valid data could fail print preparation.
   The new multiline case and existing long-copy/PDF suites pass after fix.
   Arbitrarily wide tables, huge titles and every maximum-size combination are
   not guaranteed printable. Layout/image failures block export rather than
   silently claiming successful complete output. Historical preview uses the
   current renderer; PDFs/renderer binaries are not immutable archived artifacts.
8. **Recovery:** archive-before-head plus CAS permits retry after an uncommitted
   write. After uncertain commit, inspect current state. QA-001 preserves image
   bytes rather than executing destructive rollback of an uncertain commit.
   This can leave orphan objects; cleanup/retention is separate future work.

## Changed files

| File | Change |
| --- | --- |
| `app/document_studio/assets.py` | Preserve image bytes after ambiguous metadata persistence errors. |
| `app/document_studio/library.py` | Include requested status in retry matching. |
| `app/document_studio/sections.py` | Reject unsupported source-role bindings. |
| `app/document_studio/rendering/trip_documents.py` | Bound newline density in text chunks without dropping characters. |
| `app/document_studio/frontend/trip-editor.js` | Lock editing during save; discard obsolete async initialization. |
| `app/document_studio/frontend/marketing-editor.js` | Same save and initialization protections. |
| `app/document_studio/frontend/studio.js` | Only latest navigation may render async results/errors; protect the source Trip save interval. |
| `app/document_studio/frontend/library.js` | Ignore detached-view loads before sequence mutation. |
| `tests/test_reliability_audit.py` | 25 focused adversarial/regression cases. |
| `tests/reliability_qa.py` | Isolated real-browser delayed-response, recovery, filter and PDF checks. |
| `tests/reliability_experiments.py` | Reproducible process-limit, metadata scan and image-I/O measurements. |
| `tests/browser_document_studio_smoke.py` | Invoke reliability checks from the established browser entry point. |
| `docs/audits/TRIPSE_QA_001.md` | This evidence and findings report. |

No dependencies, authentication policy, infrastructure or CI/CD configuration
changed. No unrelated pre-existing working-tree edits existed to move or overwrite.

## Remaining risks and recommendation

**Continued internal DEV testing with synthetic data: yes, with these changes.**
Use one local API process per JSON root, or the authenticated GCS adapter. The
baseline and regression tests, isolated fault injection and actual browser/PDF
checks support this conclusion. Keep revision conflicts visible; reread after an
uncertain write. The measured P2 issues are acceptable for a small internal demo,
not evidence of capacity at customer scale.

**Real customer data: not approved by this audit.** Required acceptance work is:

- Demonstrate backup restoration, retention and deletion procedures for documents,
  history and image bytes, including orphan recovery and integrity checks.
- Verify the deployed build's real IAP/roles, bucket access and DEV/PROD isolation,
  multi-instance generation races, restart behavior and ambiguous network recovery
  through separately authorized integration tests.
- Confirm which employees may read internal pilot material and whether the shared
  membership model is acceptable. Define approval, personal-data handling and
  source verification procedures; a typed source string/status is not evidence
  of factual business confirmation.
- Validate representative real document lengths, assets and PDF layouts, then
  measure cloud latency/volume with an agreed dataset and expected usage. Address
  QA-009/010 if those measurements exceed operational limits.
- Close remaining browser interleaving/soak coverage and decide how ordinary PUT
  and upload clients should recover from uncertain success without misleading the
  operator. Durable global idempotency would be a separate product/storage design.

Unverified hypotheses include upload completion during a separate save, preview
response timing during rapid document switching, prolonged browser memory growth,
and external storage corruption/permissions changes. They are not counted as
confirmed vulnerabilities. No live infrastructure tests or integration approval
are inferred from the passing simulated cloud suite.
