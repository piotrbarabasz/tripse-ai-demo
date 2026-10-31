# Incremental migration roadmap

ARCH-001 proposal, 2026-10-31. Only the documentation stage is performed here.
Stage IDs below come from the user request; they are not invented GitHub issue numbers.
Owner acceptance of [ADR-0017](../adr/0017-modular-react-typescript-migration.md) and
each stage's scope is separate from implementation or deployment acceptance.

The [original blueprint](TRIPSE_ARCHITECTURE_BLUEPRINT.md) has been read and reconciled
with the [current-state audit](current-state-audit.md). This roadmap retains the task IDs
commissioned for ARCH-001; blueprint section 11 uses different IDs for Planner and Studio.
Use the [stage crosswalk and owner decisions](reconciliation.md) before creating future
tasks. Documentation reconciliation is complete; architecture acceptance is still pending.

## Shared gates

Every implementation stage keeps old URLs, endpoint payloads/statuses, authentication,
IAP/Origin rules, readonly fixture isolation and demo labels. Use synthetic data and
mock providers for local regression. Run existing pytest and offline contracts plus
relevant browser/PDF tests; add focused tests for new boundaries. Record commands and
limitations. Deployment, cloud changes and master merges need separate authorization.

Retain legacy modules/routes throughout. Rollback removes the new entry/feature or
links users back to the legacy page; never restores old data over new document saves.
Avoid storage/schema migration in these stages. A later authorized release can use
existing accepted-image rollback procedures; this task does not execute them.

## ARCH-001 — architecture and documentation

- Dependencies: source audit on dev; existing ADR/worklog conventions.
- Scope: preserved current-state audit and original target vision, UI/API architecture, proposed ADR,
  incremental stages and current implementation/verification boundaries.
- Acceptance: all requested docs exist; source-linked claims distinguish current code
  from proposals; ADR remains proposed; risks/approvals and FRONT-001 scope explicit.
- Regression: documentation links/structure, ADR YAML/numbering, worklog CSV,
  git diff --check and existing relevant tests where supported. No runtime changes.
- Rollback: revert only ARCH-001 documentation additions/index/tracking edits.

## FRONT-001 — React foundation and app shell

**FRONT-001B implementation update:** compiled private FastAPI `/app` serving,
read-only health UI, pinned multi-stage image recipe and versioned frontend source
provenance are now implemented. Local compiled browser and offline cloud/IAP-double
checks pass. Docker daemon and hosted Cloud Run acceptance are unavailable in this
session; the combined stage is not declared fully deployment-accepted. Current
evidence and rollback: [integration guide](../ui/front-001b-integration.md).

**2026-10-31 scope update:** the commissioned FRONT-001A request splits this combined
stage. A implements only the standalone React bootstrap, responsive shell, informative
Hub, five module placeholders, legacy anchors and local build/CI checks. B retains
FastAPI `/app` assets/fallback, image packaging, provenance, IAP/CSP/Host/Origin
integration, read-only `/health` PoC and compiled/hosted acceptance. No part of B is
claimed complete by A. See [exact split and recommended B scope](../../frontend/README.md)
and [local evidence](../ui/front-001a-validation.md). The requirements below describe
the combined stage; ADR-0017 remains proposed and future full Hub/Planner work remains
FRONT-002. The original blueprint and historical ARCH-001 audit remain unchanged.

- Dependencies: ARCH-001 and owner agreement on ADR-0017 stack/entry/packaging;
  CI-007 dev-PR CI gate hosted acceptance and any required-check configuration before
  relying on mandatory PR enforcement. Local source change alone does not verify
  GitHub execution or branch protection. No API-001 dependency.
- Exact scope: create frontend/ with pinned React/TypeScript/Vite, React Router,
  Tailwind and only shell-required shadcn/ui primitives; lockfile, strict type checking,
  documented install/dev/build commands. Add bootstrap, providers only as needed,
  accessible responsive shell/navigation, error boundary and app not-found state.
  Use real links to existing Hub, Planner and Studio. Include the blueprint section 15
  PoC: one bounded, read-only same-origin GET `/health`, with loading/error states and
  response validation; no mutation or business workflow. This thin PoC is not the
  generated API client or TanStack Query integration, which remain in API-001.
- Routing: serve compiled same-origin assets and bounded `/app` navigation fallback
  only in local/cloud_demo, preserving guards. Verify `/app` and deep-link refresh,
  404 missing chunks, unknown APIs and readonly absence. Keep `/` and legacy URLs.
  No public Caddy allowlist expansion or auth/header relaxation.
- Packaging: add deterministic frontend build and copy output into existing Python
  image; deliberately update release source allowlist, recipe/manifest validation and
  build tests to include exact frontend sources/lock/config. Document loopback-only
  dev setup. No cloud resource, deployment or independent hosting changes.
- Acceptance: clean install, typecheck and production build succeed; shell works with
  JS loading and deep links under existing security headers; mode/Host/Origin/IAP denial
  matrix passes; compiled image starts API/worker as before; release provenance accepts
  intended inputs and rejects unexpected inputs. PoC health success/failure/cancellation
  and authentication/session expiry are handled without bypassing existing policies.
  Validate Vite base, hashed chunk/cache busting and CSP. No secrets in built assets.
- Regression: existing pytest/offline provenance/container checks plus shell browser
  smoke in local/mock and mocked cloud compositions. Legacy Hub/planner/Studio/viewer
  and readonly browser smoke stay green; hosted IAP evidence is a later authorized gate.
- Rollback: remove `/app` registration/build integration and frontend source additions
  together; use unchanged legacy routes. Revert recipe/provenance changes as one unit.
- Excluded: migrated Hub/planner/map/editor/library UI, generated API client or query
  hooks, assistant, authentication redesign, print CSS/pagination changes, new storage,
  root-route cutover and deployment. TanStack Query belongs to API-001.
  React Hook Form/Zod are preferred for later form-heavy features; React Flow is
  conditional on a justified diagram requirement. Do not install them for an empty shell.
  The blueprint section 7 first-phase Hub is scoped here to shell landing/navigation;
  full Hub migration remains FRONT-002. Owner confirmation of this split is outstanding.

## API-001 — API client and contracts

**2026-10-31 implementation:** offline isolated OpenAPI export, pinned TypeScript/Zod
generation, runtime gap guards, same-origin transport and TanStack Query provider/
conventions implemented without business-screen migration or backend changes.
Schema/wire/client drift checks join the existing unprivileged PR checks.
[Current contract gaps and validation evidence](../api/api-001.md) distinguish
local source acceptance from hosted CI/IAP/container acceptance.

- Dependencies: FRONT-001 build/type tooling; ARCH-001 contract inventory.
- Scope: offline OpenAPI export, deterministic schema/client generation, typed transport
  wrappers for JSON/HTML/raw bytes, supplemental runtime checks for schema gaps,
  TanStack Query provider and bounded query/mutation conventions. Follow
  [contracts](../api/contracts.md); preserve server APIs.
- Acceptance: generated artifacts reproduce from isolated local/mock composition;
  schema drift check passes; weak responses are explicitly covered; 401/403/404/409/
  413/422/503, timeout/cancel, cloud idempotency versus local non-idempotency and binary/
  HTML responses tested. No automatic write retries or public cloud OpenAPI route.
- Regression: existing backend/security suites plus synthetic adapter contract checks;
  FRONT-001 shell/legacy smoke. No screen migration required.
- Rollback: remove unused client/query integration; legacy fetch paths remain intact;
  no API/data rollback needed.

## FRONT-002 — Hub and Trip Planner migration

**2026-10-31 implementation:** operational `/app/planner` form, trusted authenticated
runtime capabilities, explicit submission/retry semantics, bounded status polling
and narrow validated result/viewer projection; Hub Planner card now available.
Legacy Planner/viewer and Studio remain intact. API-001 is reused and its 401 cache
clearing now exposes a session-failure flag to mounted React observers. No storage,
maps implementation, auth mechanism or deployment change.
See [implementation, validation, limits and rollback](../ui/front-002-planner.md).

- Dependencies: FRONT-001, API-001 and accepted shell/routing contracts.
- Scope: `/app` Hub and `/app/planner` vertical workflows: mock/live labels, request,
  durable progress polling, errors and link to existing token viewer. Preserve legacy
  viewer/maps and simulator; an in-app map/viewer rewrite needs separately bounded scope.
- Acceptance: synthetic request completes via existing worker/queue; failures/timeouts
  render safely; duplicate clicks, unmount and terminal polling handled; readonly gets
  no create path; editor/reader and idempotency behavior match existing APIs. No implied
  automatic planner-to-Studio conversion. Legacy `/hub` and `/planner` still work.
- Regression: planner, viewer, hub, demo and cloud auth suites; browser API-worker-viewer
  flow with mock map/no browser key and responsive/keyboard checks. No live paid calls
  assumed verified by mock tests.
- Rollback: remove new feature navigation or `/app/planner`; link to `/planner` and
  `/hub`. Existing jobs/viewer tokens remain valid; do not delete them.

## FRONT-003 — Document Studio migration

**2026-10-31 FRONT-003A implementation:** `/app/documents` now provides the real
eight-template catalog, server-filtered/paginated saved library, metadata/details
and revision history with safe legacy/new-tab preview links. This increment is
read-only: no React creation, editing or library mutations. Existing Studio and
PDF rendering remain unchanged. [A evidence and recommended B/C/D boundaries](../ui/front-003a-documents.md)
separate catalog/library acceptance from the full migration described below.

- Dependencies: API-001, accepted FRONT-002 coexistence and snapshot/conflict parity.
- Scope: migrate one workflow at a time: catalog/source picker and examples → library/
  history → source editors → snapshot/section editing and preview controls. Reuse server
  validation, template registry, rendering and browser print; preserve eight template
  IDs, marketing variants, sections, provenance and private asset handling.
  This includes existing campaign/marketing.collection parity, not the entire future
  Marketing workspace or automated publication. Blueprint FRONT-004 maps to this task.
- Acceptance: synthetic create/edit/save/reload/duplicate/archive/restore/status/history,
  image rights/upload/crop and stale-revision conflict pass. Preserve null/empty sections,
  immutable snapshots and operation IDs; dirty navigation and stale preview cancellation
  work. Cloud reader cannot write. Test history preview against DENY/IAP constraints;
  use permitted separate windows without weakening policies. No default cutover until
  feature parity is accepted.
- Regression: full document/service/library/sections/source tests; browser creation,
  section, history, marketing and all-template tests; actual PDF text/order/bounds,
  long-content pagination, image persistence, A4/social and invalid-export gates.
  Baseline fixtures and existing print pages stay available for comparison.
- Rollback: route users to `/documents/demo` with existing saved IDs/hashes where
  supported. Keep revisions/assets and server schemas unchanged; rollback UI only.

## AI-001 — assistant foundation and tool orchestration

- Dependencies: API-001; FRONT-002 for planner tools; FRONT-003 and its acceptance before
  document writes. Read-only/mock foundation can proceed after API-001 independently
  of unfinished document screens. Owner-approved tool/confirmation/retention policy.
- Scope: assistant feature and server orchestrator with explicit typed allowlist,
  actor-scoped domain operations, mock provider/tool execution, bounded steps and safe
  audit metadata. [Assistant proposal](../api/assistant-integration.md) defines limits.
  First vertical workflow, per blueprint section 8: create an editable document draft
  from an existing permitted Studio trip, returning ID, revision and missing-field
  warnings; never send to a customer. A raw planner result needs a separately scoped
  planner-to-Studio adapter before it can be used as a source.
- Acceptance: tool schema/authorization, injection, replay, conflict, cancellation and
  partial-failure cases pass; user confirms consequential writes against exact arguments
  and revision. No arbitrary tools or live-cloud provider enablement. Existing mock
  cloud startup restrictions and readonly absence remain enforced.
  A read-only mock scaffold is an interim milestone, not completion of AI-001: the
  authorized draft workflow must pass synthetic persistence/duplicate/conflict tests.
- Regression: existing planner/document/auth suites plus synthetic orchestration tests;
  assistant browser failure/retry/confirmation flows without paid calls. Live provider,
  human IAP and cost validation remain separately authorized/unverified.
- Rollback: disable/remove assistant route/tool registration and navigation; use
  existing manual workflows. Preserve completed jobs/documents; no compensating delete.

## Retained future product scope — not implemented

Blueprint sections 1, 6, 9 and 11 also retain Trip Catalog/reuse, a dedicated Marketing
workspace, Automations and shared operational history. They are not deleted by the
smaller commissioned stages. Marketing needs its own later scoped task; no task ID is
invented here. Its initial dependency is API-001 plus accepted campaign/document parity;
acceptance must cover campaign composition, snapshots, rights, permissions and failure
states. Regression includes existing marketing/browser/PDF cases; rollback returns to
legacy campaign workflows without deleting saved data. External publication stays gated.

Blueprint AUTO-001 is future scope after stable job/tool contracts and approval policy:
task history/results/errors, safe retry and explicit approval/audit presentation. It
does not imply a new workflow engine. Acceptance requires actor-scoped visibility,
idempotent replay, denied unauthorized approvals and partial-failure recovery; regress
existing queue/auth/idempotency cases. Rollback disables the panel, retaining jobs and
audit records. UI-free backend operations must remain usable from manual workflows.
Neither Marketing nor AUTO-001 is part of FRONT-001 or claimed complete in ARCH-001.

## CI-007 — separate DEV PR quality gate

[CI-007](../CI_007_DEV_PR_GATE.md) implements the separate source change to check PRs
targeting dev and master using the existing read-only pipeline and no deployment
credentials. Previously the PR trigger targeted master only, as recorded by the
dated ARCH-001 audit. Hosted success and required branch checks are separate acceptance
items; do not claim enforcement from YAML alone. Delivery still runs on dev/master
pushes. Frontend install/type/build and schema drift checks remain later toolchain
work, after FRONT-001A establishes it; none are added by CI-007. No delivery trigger,
protected master policy or environment authorization changes are made.

Delivery has no documentation-path exclusion. Merging this branch into dev creates a
push that can run DEV deployment after CI and existing environment controls. Recommend
an eventual documentation PR to dev, with owner coordination
of merge/delivery timing. No PR, merge, deployment or workflow change is authorized by
this documentation review. See [merge considerations](reconciliation.md).

## ARCH-001 validation record

The following records the initial documentation pass at `71f59fa`. Final-review
checks and completed original-source reconciliation are recorded in reconciliation.md;
historical link findings below describe the earlier state, before navigation cleanup.

Executed on 2026-10-31 in the existing Windows Python 3.12 virtual environment:

- `.venv/Scripts/python.exe -m pytest -q`: **1143 passed**, one existing Starlette/
  AnyIO BlockingPortal deprecation warning, 62.70 seconds.
- `.venv/Scripts/python.exe -m scripts.gcp.ci offline`: **PASS**, offline source and
  preview contracts; no cloud credentials or deployment used.

Scoped Markdown structure/local-link checks passed across 18 new/modified Markdown
files; ADR metadata/nine sections and worklog CSV structure passed. Two pre-existing
links remain unresolved: root README and document-system README reference the missing
`docs/DOC_TEMPLATES_006.md`. New links resolve; historical references were not fabricated
or redirected. `git diff --check` passed after final whitespace cleanup.

Historical test results in other documents do not count as this task's verification.
Dedicated browser/PDF/container scripts are not rerun for
this documentation-only change. No GCP deployment, hosted IAP/browser acceptance,
live provider calls or new React build is performed here. No repository-configured
Markdown linter was found; scoped structural/local-link checks are used instead.
