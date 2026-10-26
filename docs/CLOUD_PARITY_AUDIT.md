# CLOUD-PARITY-001 — audit and delivery matrix

GITHUB-CICD-001 update (2026-10-26): CI/CD now has prepared workflows, explicit
mode/resource/IAP gates, keyless probes and recorded deployed acceptance before
PROD. See [GitHub runbook](GITHUB_CICD.md) and [ADR-0012](adr/0012-github-actions-delivery.md).
This does not close the existing real-GCP parity, IAM, restart/restore or LIVE
gates. No deployment was performed in the CI/CD implementation task.

Date: 2026-10-26. Evidence: this checkout, not a live inspection of GCP.
Existing DEV/PROD configuration selects `readonly_demo`; deployed revisions,
IAM, billing and data durability have not been independently verified.
No deployment, promotion, paid API call or cloud resource mutation is authorized
by this task. PROD is a client demonstration, not approved for real customer data.

## Target architecture and stage dependencies

One FastAPI composition and existing Hub, document editors, chat and viewer.
`local` uses the existing localhost policy, JSON/images and SQLite worker.
`readonly_demo` retains its separate, deliberately minimal public route surface.
`cloud_demo` uses verified IAP assertions, explicit reader/editor membership,
same-origin writes, private GCS document/image adapters and Firestore jobs.
Cloud Tasks invokes an authenticated processing route; it never starts the
SQLite worker. Existing domain models, rendering, snapshots and validation stay shared.

Dependency order: audit → access policy + shared composition → GCS repository
and binary assets → Document Studio → durable jobs + task delivery → planner,
viewer and isolated simulator → deployment validation → DEV acceptance → manual
promotion of the tested digest. LIVE is a separate gated step after quotas,
rate limits, Secret Manager and cost controls. No automatic migration of local data.

## Baseline module audit

| Module / local functions and endpoints | Cloud baseline / reason / intentionality | Required change and dependencies | Security and cost exposure | Priority |
|---|---|---|---|---|
| `main.py`, `hub.py`, `hub_frontend`, `static/module-nav.*`: `/hub`, module links | Separate preview Hub; full routers intentionally omitted by `CloudSettings` | Shared router factories with injected policy and dependencies; retain preview tests | Authenticate all private routes and static assets; Cloud Run CPU/memory/requests | P0 |
| `document_studio/api.py`, `service.py`, models and frontend: `/documents/demo`, `/api/document-studio/*`, trips/campaigns/drafts, 10–15 day trips, offer/pilot, A4/social, browser PDF | Marketing fixtures only; intentional public confidentiality boundary | Reuse complete router and UI with IAP policy; GCS storage first | Pilot/internal fields remain private; offer whitelist unchanged; no server PDF fee | P0 |
| `repository.py`: JSON overlays, fixtures, revisions, draft snapshots, 409 | No editable cloud repository; intentional ephemeral disk avoidance | Private environment bucket, generation-match CAS, immutable image blobs, read-only packaged fixtures | Lost-update protection across instances; GCS storage/operations/version retention | P0 |
| `assets.py`: validated raster upload, metadata stripping, private content route | Upload absent; filesystem paths and FileResponse cannot persist in Cloud Run | Byte-oriented adapter and response; same validator; private bucket | Upload limits/decompression checks; authenticated reads; GCS bytes/operations/egress | P0 |
| `db.py`, `worker.py`: SQLite jobs/status/token hashes, dedup and outbox | No cloud worker or jobs; intentionally prohibited | Firestore transactions + Cloud Tasks; lease fencing, bounded attempts, durable dispatch recovery | User/environment ownership; no shared SQLite; Firestore reads/writes and Tasks requests | P1 |
| `planning.py`, `planning_providers.py`, `demo_data.py`: POST `/api/trips` 202, GET `/api/trips/{id}`, mock/live | Static scenarios; intentional absence of durable queue, not missing UI | Reuse generation functions, durable job adapter, protected processing endpoint | Existing day/place limits unchanged; mock never constructs AI clients; live OpenAI/Places/Routes costs | P1 |
| `viewer.py`, `static/viewer.*`, `demo-map.js`: `/trip/{token}`, `/api/viewer/{token}` | Schematic preview only; intentional token persistence gap | Durable hashed tokens/expiry and existing viewer; separate optional browser map key | Private owner-scoped token reads; no server key in browser; Maps JS can incur charges independently of AI | P1 |
| `demo.py`, `static/demo.*`: `/demo/chat`, scenarios/messages/conversations | Unavailable; intentionally avoids ephemeral SQL state | Repository methods instead of SQL in routes; durable user-scoped conversation/dedup/outbox | Authenticated simulator, no real WAHA session; Firestore/Tasks costs | P1 |
| `waha.py`, `messaging.py`: real webhook/HMAC, sender filter, session transport | Disabled intentionally | Keep real integration separate; evaluate WAHA persistent session hosting or Business Platform | Do not register real webhook in cloud_demo; external WhatsApp provider/session costs unknown | P2 / separate assessment |
| `Dockerfile`, `compose.yaml`, `scripts/dev.py`, Makefile | One image; local volumes/worker; immutable cloud build and manual targets | Preserve local commands; cloud SDK dependencies lazy; no bucket mounts | No credentials/data in image; build/registry costs; no GCP needed for local | P0 |
| `scripts/gcp/*`, `infra/gcp/*` | Two services, same project/region, SHA/digest, promotion/rollback, preview-only public smoke | Explicit mode contract, private IAP configuration, declarative separate resources; authenticated smoke before rollout | Public publication remains preview-only; narrow runtime IAM and secret references; no automatic apply | P0–P1 |
| `docs/adr`, tracking, local/cloud pytest and browser smoke | ADR-0009/0010 describe public preview; no authenticated parity evidence | New proposed ADR, preserve history, separate preview and authenticated tests | Record untested cloud boundaries and real measured costs only | P0 |

## Acceptance matrix

`LOCAL` means the existing functional contract. DEV/PROD columns below describe
the target cloud_demo acceptance; they do not assert deployment success.

| Scenario | LOCAL | DEV cloud_demo | PROD cloud_demo |
|---|---|---|---|
| Hub and existing editors | localhost policy | IAP reader/editor | same after manual acceptance |
| 10–15 day document trip, campaigns, offer/pilot, PDF | JSON + browser | GCS + same UI/browser | separate PROD bucket |
| Save/read across process restart | disk overlay | bucket generation CAS | independent bucket + backup |
| Photo upload/read; two editors conflict 409 | local validator/files | same validator; bytes; CAS | same, private assets |
| Simulator send/progress/dedup/new conversation | SQLite + worker | owner-scoped Firestore + Tasks | separate database/queue |
| Mock job 202/poll/result | SQLite + worker | durable lease/task | same; mock default |
| Viewer valid/invalid/expired token | hashed token + expiry | owner + token + expiry | same |
| Map | schematic mock; configured Google live | optional explicit browser key | separately approved key |
| Anonymous editing/private reads | denied for Studio | denied for entire app | denied |
| DEV/PROD isolation | separate local path | environment database/bucket/queue | distinct resources and IAM |
| Paid API calls in mock | forbidden | forbidden AI/server Maps; browser Maps opt-in | same |
| Public readonly preview | independent tests | remains selectable | existing service unchanged |

## Infrastructure, access and costs

Direct Cloud Run IAP supports the `run.app` URL without a separate load balancer:
[Cloud Run IAP](https://docs.cloud.google.com/run/docs/securing/identity-aware-proxy-cloud-run).
External Google accounts require the external OAuth configuration and explicit
IAP membership. A user outside Google Workspace can use a Google account;
non-Google identities require a separately validated Identity Platform/federation
setup. Do not promise arbitrary email/password login.

Validate the signed assertion, including signature, issuer, audience and expiry;
unsigned identity headers are not proof:
[signed headers](https://docs.cloud.google.com/iap/docs/signed-headers-howto).
Cloud Run audience: `/projects/PROJECT_NUMBER/locations/europe-central2/services/SERVICE`.
Task OIDC access through IAP needs an explicitly configured OAuth client and
programmatic access allowlist, plus IAP membership for the dedicated task account:
[programmatic authentication](https://docs.cloud.google.com/iap/docs/authentication-howto).
This boundary must be tested on DEV before enabling jobs or accepting cloud parity.

No amounts or hours are estimated here. Cloud Run depends on request duration,
CPU/memory, concurrency and minimum instances; Storage on bytes, operations,
location, retention and egress; Firestore on documents, operations, indexes,
backups and retention; Tasks on task traffic/retries. IAP/OAuth pricing and any
Identity Platform additions must be checked for the selected identity setup.
OpenAI and server Maps are separate live budgets; Maps JavaScript has its own
usage and referrer restrictions even for mock coordinates. Logging volume,
backup storage, restore exercises, operator maintenance and Artifact Registry /
Cloud Build are additional costs. Use billing export and measured DEV traffic
for an estimate; no invented zero-cost assumptions.

## Delivery evidence and remaining gates

Implementation and test results are recorded here as stages complete. Real GCP
IAP/OAuth/IAM, multi-instance persistence/retries, browser acceptance on DEV,
backup restoration and PROD promotion remain unverified until operator-run tests.

### Prepared implementation

| Stage | Repository result | Validation / remaining gate |
|---|---|---|
| 1 audit, architecture, dependency and acceptance matrix | Implemented in this document | Checkout evidence; no claim about deployed GCP state |
| 2 shared application | Existing Hub, Studio, viewer, planner and demo router factories reused; preview stays separate | LOCAL and preview regressions tested |
| 3 authorization | IAP ES256 verification, exact audience/issuer/time/subject; explicit reader/editor lists, Host/Origin checks, private assets and dedicated task identity | Real OAuth/IAP and external-user DEV acceptance OPEN |
| 4–5 Studio persistence/UI | GCS generation CAS, read-only fixture overlay, unchanged document models/snapshots/revisions, validated binary uploads/private responses | Fake GCS multi-writer race and app reconstruction PASS; real restart/restore OPEN |
| 6 planner/queue/viewer | Firestore transaction adapter, named OIDC Tasks, 202/status, fenced leases and bounded processing attempts, owner-scoped hashed viewer tokens | Offline adapter flows PASS; real Tasks through IAP OPEN |
| 7 simulator | Same router/UI; user-scoped durable job/conversation/outbox, stable message IDs, retry/dedup/new conversation | Offline browser/API PASS; real DEV delivery/restart OPEN |
| 8 LIVE | Deliberately rejected by runtime/deployment validation; no server provider keys in cloud mock modes | OPEN: admission quotas, per-user limits/rate limiting, budget controls, secret injection and paid-operation decision |
| 9 deployment | Opt-in private mode, IAP flag, explicit OAuth smoke token, optional pinned browser key secret, additive Terraform resources | Provider validation PASS; resource provisioning and live preflight OPEN |
| 10 tests | Independent preview tests retained; new cloud API/storage/jobs/access and browser suites; controlled DEV smoke prepared | Offline PASS; DEV/PROD acceptance not executed |
| 11 documentation | ADR-0011; ADR-0009 superseded with historical text preserved; deployment/Hub/Studio/tracking updated | No fabricated hours, costs, PR or commit |
| 12 rollout | DEV-only operator sequence; separate manual tested-digest promotion and mode-aware rollback | BLOCKED by explicit requirement for a separate operator deployment decision; no cloud mutation performed |

POST `/api/trips` preserves the existing JSON-only contract and additionally
supports an optional `Idempotency-Key` UUID in cloud_demo; the shared frontend
supplies/reuses it for ambiguous submission retries. Viewer tokens require the owning user's
IAP identity in cloud_demo. Cloud simulator message IDs are stable opaque strings
(`job:ack`, `job:result`) so completion of an earlier job cannot renumber messages.
These are deliberate access/retry differences, not claims of byte-identical APIs.

### Real WhatsApp assessment (separate substage)

Current `waha.py` verifies webhook HMAC, filters configured senders/session,
routes supported intents and atomically deduplicates events with local jobs.
`worker.py` and `messaging.py` maintain acknowledgement/result retry state. In
Compose, WAHA WEBJS has a dedicated persistent `waha_sessions` volume; this state
and a stable owning process are prerequisites, unlike the stateless simulator.
Cloud demo registers no WAHA webhook or transport and does not start WEBJS.

Keeping WAHA would require a separately assessed persistent host/session backup,
webhook authentication/routing, sender consent/authorization, session recovery,
operational monitoring and provider policy review. The optional official
WhatsApp Business Platform path would require an approved business account,
phone setup, webhook verification, message/consent/template policy analysis and
a new transport adapter. Neither option is implemented or costed here; no real
message was sent. The simulator deliberately uses no WAHA credentials/session.

### OPEN / BLOCKED register

| Item | Status | Concrete reason / next evidence |
|---|---|---|
| Actual DEV/PROD functional parity | OPEN | No deployment or live inspection; operator-run staged acceptance must establish it |
| IAP/OAuth for operator, TRIPSE and external Google accounts | OPEN | Organization/consent/programmatic client settings and actual identities not validated; Console bootstrap needed |
| Non-Google identities | OPEN | No Identity Platform/federation adapter configured or tested; external email alone is insufficient |
| Tasks OIDC → direct IAP → handler | OPEN | Requires OAuth client allowlist, task-agent IAM and real DEV dispatch; fake adapter tests cannot establish that boundary |
| Cross-environment IAM denial | OPEN | Naming/isolation validation exists, but IAM must be tested with actual runtime credentials against the other environment |
| Real restart/multi-instance concurrency, backup restore | OPEN | Fake stores exercise reconstruction/CAS; GCS versioning/soft delete and Firestore PITR have not been provisioned or restored |
| Unattended dispatch reconciliation | OPEN | Firestore commit and enqueue are not atomic; failed dispatch uses client idempotent retry or explicit operator recovery; no scheduled reconciler |
| Large-volume conversations, retention and admission quotas | OPEN | Current owner query is intended for small demo volume; pagination/quotas/retention need measurement and implementation before scaling |
| LIVE DEV activation | OPEN | Runtime remains mock-only until rate limiting, quotas, budget controls, secrets and approved paid tests are delivered |
| Real Google Maps API behavior/billing | OPEN | Optional browser path checked with SDK double only; key restrictions and any paid smoke need separate operator decision |
| Real WhatsApp | OPEN | No Cloud Run WAHA session; hosting/session durability and Business Platform/provider assessment remain a separate substage |
| Deployment and PROD promotion | BLOCKED | User explicitly requires a separate operator decision and manual promotion of an accepted digest; neither was performed |
| Real customer-data readiness | BLOCKED | Security/durability/restore acceptance has not been completed; PROD remains only a demonstration |

### Verification evidence (2026-10-26)

- Final `make test`: **369 passed**, one existing Starlette/AnyIO deprecation
  warning. `docker compose config --quiet`, Terraform checks and `git diff --check`
  passed. Baseline before changes: 311 pytest tests passed. No existing readonly preview
  tests were removed; the source packaging assertion now permits only the reviewed
  fictional Iceland preset required by the authenticated editor.
- New tests cover real ES256 signature/claim rejection, fake GCS generation races,
  private validated assets, 15-day trips/offer/pilot/campaign snapshots and restart
  reconstruction, optional idempotency keys, queue failures, ownership, stable
  outbox IDs, expired tokens, bounded crash retries and stale-processor fencing.
  The real Firestore SDK is tested at a fake protobuf RPC boundary, including
  automatic transaction retry with a fresh concurrent snapshot and exhausted
  retries translated to storage errors. Cloud Tasks request/OIDC shape and
  private deployment/secret-alias handling have offline tests.
- `make test-browser`: all eight scripts passed. LOCAL checks include actual API
  process restarts, images and browser PDFs; public preview retains its own
  read-only/browser checks. The authenticated cloud harness intercepts all
  requests against real routers and fake cloud stores; it checks Hub, 15-day
  edit/save/reload, offer/pilot editing and PDFs, mock planner/viewer and
  simulator/dedup/new conversation. The optional Maps JavaScript path uses an
  intercepted SDK double and fake key. No Maps/OpenAI/WAHA requests ran.
- Terraform 1.13.5 + locked Google provider 8.8.1: backend-free initialization,
  `fmt -check` and `validate` passed. No `plan`, `apply`, import or cloud resource
  request was executed. Provider initialization only downloaded tooling.
- Existing DEV offline preflight and PROD deploy dry-run passed using Make. Those
  commands explicitly reported no GCP calls or mutations; cloud_demo configuration
  isolation is separately exercised by its contract tests.
- `make test-container` was attempted but did not build an image: the Docker
  daemon was unavailable. Docker Desktop was started for the check, but its
  Linux-engine API returned HTTP 500. Container image/runtime/SIGTERM verification
  for these changes is **BLOCKED** until the local engine is healthy. This does
  not invalidate Python/browser results and is not reported as a passing build.
- No GCP deployment, live DEV smoke, external login test, IAM denial test,
  backup restoration, PROD promotion or paid API test ran. No commit/PR created.

Test totals and exact final command results are recorded in the tracking worklog;
the acceptance matrix still requires real DEV evidence before cloud parity is done.
