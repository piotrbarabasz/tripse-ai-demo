# FRONT-002: React Hub and Planner

Implementation on `feature/front-002-hub-planner`, based on `origin/dev`
`18058a0` (merged API-001 PR #13 and FRONT-001B), 2026-10-31.
The base commit's [DEV Delivery run](https://github.com/piotrbarabasz/tripse-ai-demo/actions/runs/41209758392)
was in progress at the initial audit and subsequently completed successfully.
The preceding dev delivery also succeeded. This task uses local/mock and offline
cloud validation; it does not rely on or claim hosted acceptance of these changes.

## Screens and actions

`/app` keeps the existing shell and five module cards. Planner is marked available:
its primary action opens `/app/planner`, its secondary action opens `/planner`.
Document Studio remains in `/documents/demo`; Marketing, Automations and Assistant
remain planned. No metrics, saved-trip catalog or new business data are fabricated.

`/app/planner` now provides a labeled Polish description form, character count,
server-confirmed MOCK/LIVE mode, existing mock examples, submission status, real job
progress, safe errors, manual status refresh and a completed-plan viewer action.
Descriptions are trimmed and require 1–10,000 Unicode code points, matching
Pydantic's character count rather than JavaScript's UTF-16 length. HTML maxlength is
deliberately not used to incorrectly truncate emoji/surrogate pairs. An invalid
description focuses the textarea and references a visible validation message.

Mock examples come from the existing `/api/demo/scenarios` response, guarded at
runtime and requested only after the capability confirms mock mode. They are the
existing Karkonosze, Ojców and Trójmiasto scenarios from `app/demo_data.py`, never
invented offerings. Choosing one fills the form without creating a job. Live mode
does not fetch mock examples. Mode copy describes illustrative data versus provider
suggestions/estimates; neither runtime mode nor a completed status implies that
all travel facts, opening hours, access or reservations are verified.

Form, examples and create action lock during submission and while an accepted job
is tracked. A synchronous guard prevents duplicate POSTs before React's pending
render, including repeated submit events in StrictMode. Mutations use API-001's
`createTripMutation`/`createTrip`, zero retry and a caller AbortSignal. No mount,
refetch, navigation or manual status refresh submits a job. Unmount aborts the
client request; it cannot undo a request already accepted by the server.

A network, timeout, unavailable/other server failure or malformed acceptance is
treated as ambiguous. The UI says a job may already exist and disables ordinary
resubmission. A separate explicit decision can retry the same operation or start
a new one. Cloud retry retains its original UUID and frozen description; a new
intent receives a new UUID. Local retry displays its duplication risk and sends
no idempotency header. No automatically replayed offline mutation is introduced.

Accepted UUIDs remain in component memory. `jobQuery` supplies the API-001 read,
1500ms interval and consumed AbortSignal. Progress supports queued/running/completed/
failed. A two-minute observation window bounds polling; expiry pauses reads and
offers a manual GET refresh with a fresh window. Terminal state, unmount, auth or
other read error stops polling. Manual refresh only reads the existing job; it never
creates one. No server cancellation endpoint is invented. Job error text and raw
HTTP/provider messages are not rendered. 401 clears caches, disables queries and
shows a persistent session-expired message; 403 remains a permission failure.

On completion, **Otwórz plan i mapę** is a full-page link to the existing token viewer.
The Planner does not embed HTML, maps or private assets. A separate explicit
**Zaplanuj kolejną podróż** action returns the form to an editable state. Legacy
Planner and Hub fallback links remain available throughout.

## Exact API contracts

Only one new route is introduced:

```http
GET /api/workspace/capabilities
Cache-Control: private, no-store
Content-Type: application/json

{
  "runtime_mode": "local",
  "can_create_trip": true,
  "planning_mode": "mock"
}
```

`WorkspaceCapabilities` is a strict Pydantic model with forbidden extra fields:
runtime_mode local/cloud_demo, boolean can_create_trip, planning_mode mock/live.
It contains no actor identity, credential, infrastructure name or provider key.
The local route uses the existing `local_only` guard (loopback peer/Host, same-origin
and proxy-header restrictions). Cloud uses the existing verified IAP/membership
boundary and `authenticated_demo`; write capability is taken from server-derived
`request.state.can_edit`. Client-supplied role/capability headers cannot change it.
Cloud always reports mock. Local mode reflects the API process's configured
PLANNING_MODE, default live as in the existing application; invalid values fail 503.
API and worker must use the same existing environment composition. Results are
independently checked for their actual mock/live flags. No new local auth scheme
is added. Readonly composition returns before registration and has no new endpoint.

An unknown/unavailable/malformed capability disables creation. It is never inferred
from health, hostname, Vite environment, a query parameter or user input. The hint is
not authorization: existing cloud POST membership/editor/Origin enforcement remains
the authority even if permissions change after the GET. Tests cover readers,
anonymous/forged/task identities, wrong Host, missing/null/foreign write Origin and
cross-site access. Existing create/status behavior and legacy routes are unchanged.

Existing operations remain:

| Operation | FRONT-002 use |
| --- | --- |
| POST `/api/trips` | Generated TripRequest and 202 TripAccepted; cloud UUID header only, no local equivalence claim. |
| GET `/api/trips/{trip_id}` | Generated TripStatus, opaque result/null; no global TripPlan assertion. |
| GET `/api/demo/scenarios` | Minimal scenarios id/name/text projection; existing mock-only availability. |
| `/trip/{token}` | Existing full-page viewer, unchanged; browser requests its existing `/api/viewer/{token}`. |

The schema and generated TypeScript/Zod code were regenerated using the existing
offline API-001 scripts. The artifact now has 40 paths and 45 component schemas.
`scripts.export_api_fixtures` now also captures capabilities, the existing scenarios
catalog and a synthetic `worker.generate_job_result` mock result with fixed viewer
token/expiry. It calls the pure result helper in a temporary mock composition; it
does not start the worker loop. Python checks fixture drift; TypeScript validates
the actual captured result and capability shapes.

`completedResultSchema` projects only viewer_url, viewer_expires_at, is_mock,
generation_mode, verification_status and optional warnings. Contradictory mode flags
are rejected. Extra fields are discarded; raw warning text is not rendered, only an
indicator to review the viewer's existing warnings. This is not full TripPlan or
Studio Trip coverage. No Planner-to-Studio conversion is added.

Viewer links must be exact root-relative `/trip/{token}` paths or absolute HTTP(S)
URLs whose origin equals the current browser origin. Token format is exactly
`[A-Za-z0-9_-]{43}`. Protocol-relative links, external origins, credentials, unexpected
paths, dot segments, escaped tokens, queries, fragments, whitespace and backslashes
are rejected. A finite future viewer expiry is required. The URL is projected to a
relative path, checked again on click and removed when its known expiry passes.
Malformed/missing/expired links show a safe fallback instead. If the server has
already invalidated a token or its clock differs, the existing viewer still enforces
expiry/access and displays its existing 404 page; no client check bypasses that.

Local setup must keep the API/worker `PUBLIC_BASE_URL` equal to the actual browser
origin, including protocol/hostname/port. The default is `http://localhost:8000`;
opening the SPA under `127.0.0.1` requires configuring that origin instead. The client
does not rewrite an absolute link from another origin to bypass this requirement.

## Session and source safety

API-001's immediate cache clearing on 401 could leave mounted React queries showing
pending after their error entry was removed. A small observable boolean per
QueryClient now records session failure while clearing private query/mutation data.
Planner observers disable themselves and show the safe session-expired message.
The flag carries no identity or payload and lasts only for that in-memory client;
sign-in plus a full page reload creates a fresh client. No localStorage,
sessionStorage, persisted private cache or credential handling is added.

Strict SPA CSP and Zod jitless initialization remain intact. New production files
are `.ts`, `.tsx` and `.css` under frontend/src, already included by FRONT-001B's
versioned source allowlist; backend code stays under app. Provenance tests explicitly
include the Planner and projection sources alongside generated code. No allowlist,
Docker recipe, pinned build inputs, release-promotion rule, deployment trigger,
IAM/IAP/WIF, Terraform or GCP resource is changed. The new browser smoke is added to
the existing `scripts/dev.py` test-browser list, so current CI runs it without a new
privileged job or workflow change.

## Commands and evidence

Use the existing Python environment and Node 24.18.0/npm 11. No dependency was added
or repinned for FRONT-002.

```sh
python -m scripts.export_openapi
python -m scripts.export_api_fixtures
npm --prefix frontend ci
npm --prefix frontend run api:generate
python -m scripts.export_openapi --check
python -m scripts.export_api_fixtures --check
npm --prefix frontend run api:check
npm --prefix frontend run typecheck
npm --prefix frontend run lint
npm --prefix frontend test
npm --prefix frontend run build
python -m pytest -q
python tests/browser_react_planner_smoke.py
python scripts/dev.py test-browser
python -m scripts.gcp.ci offline
git diff --check
```

On Windows use `.venv/Scripts/python.exe`; CI uses `.venv/bin/python`. Browser QA
uses temporary application storage and mock providers. Screenshots are gitignored
under `local-data/react-planner-qa/`:

- hub-desktop.png; planner-tablet.png; planner-mobile.png
- planner-queued.png; planner-completed-mobile.png; planner-completed-desktop.png
- existing-viewer.png; cloud-editor.png; cloud-reader.png

The new browser smoke submits through the real local API, starts the actual mock
worker after observing queued, polls to completed and opens the existing mock map
viewer. It checks one POST per intent, no terminal/unmount background reads, keyboard
example selection, 320/390/768/1024 widths, strict CSP and no external requests.
Offline cloud uses existing TestClient IAP/storage/task doubles and the real routes,
checking editor creation, generated operation UUID, completion/viewer and reader
denial. It does not establish hosted IAP or real Cloud Tasks acceptance. Unit tests
separately exercise the two-minute hard polling cap, errors/timeouts, manual refresh,
session clearing and unsafe/expired result links.

Final local results on 2026-10-31:

- Clean `npm ci`: passed; npm audit: zero findings. No package/lock changes.
- `api:check`, TypeScript, ESLint, 162 Vitest/RTL tests and production build: passed.
  Vite reports the unsuppressed chunk-size advisory noted below (506.28 kB minified,
  155.13 kB gzip); the build succeeds.
- Full Python regression: **1,240 passed** in 157.80s, one existing Starlette/AnyIO
  BlockingPortal deprecation warning.
- Focused capability/generation/provenance/Makefile suite: 67 passed. Final
  Makefile/CI/source/historical-release regression check: 100 passed.
- OpenAPI, wire fixture and generated-client drift checks passed. Offline source/
  preview contracts passed; the committed-branch check is repeated after commit.
- New real API/worker React Planner smoke passed locally and with offline cloud
  doubles. The complete **11-script** `scripts/dev.py test-browser` command passed,
  including the legacy Hub/Planner/viewer, Studio/catalog/library/history/source/
  creation/reliability scenarios, marketing and trip-document PDFs, readonly preview,
  authenticated cloud, GT template matrix and mock worker/simulator/delivery flow.
  It made no external provider calls. Desktop/mobile/cloud screenshots were inspected.
- Changed documentation links and whitespace checks passed.
- Base PR #13's [Tests and offline contracts](https://github.com/piotrbarabasz/tripse-ai-demo/actions/runs/41209553296/job/124561481212)
  and the base DEV Delivery run succeeded. These are base-branch results; no hosted
  run is claimed for this unpushed feature branch.
- Docker runtime acceptance remains unavailable: `docker info` failed because the
  `dockerDesktopLinuxEngine` daemon pipe is absent. Existing Python Docker/source
  contract tests passed. No actual Docker image build/start or hosted IAP/live
  provider acceptance is claimed.

Local source acceptance is complete and the branch is ready for a review PR to dev.

## Remaining limits and rollback

This is a one-request Planner workflow. There is no saved-trip catalog, persisted
resume after navigation/reload, job cancellation, plan editing, embedded map, Studio
conversion or migrated Studio screen. Unknown completed result contracts fail
safely. LIVE presentation is tested with synthetic responses only; no paid provider
or live planning request is executed. An ambiguous local create can still duplicate
if the user explicitly elects to retry; the UI states that risk. Existing legacy
screens, jobs, worker, tokens and storage keep their contracts.

The current eager bundle emits Vite's >500 kB minified chunk advisory. The limit is
not raised or suppressed; feature/vendor splitting can be a separate measured
performance task. No new runtime is introduced. Docker daemon/hosted acceptance
are separate checks and are not implied by local source tests.

To roll back, revert the FRONT-002 commit as one unit: restore the Planner placeholder
and Hub links, remove the capability route, new projection/session UI integration,
regenerated additions and new browser registration, retaining API-001. Rebuild the
existing image through the unchanged release process when separately authorized.
Route users to `/planner`, `/hub` and `/documents/demo`. Do not restore or delete any
database, job, revision, image or viewer token. `/` and `/hub` were never redirected
to React; existing jobs remain accessible through their existing viewer links.

PR target: `dev`. Prepared title/body: [FRONT-002 PR description](front-002-pr.md).
Do not create, merge, push or deploy automatically. Hosted branch CI and deployment
acceptance remain separate from local PR readiness.
