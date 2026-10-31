# ARCH-001 documentation reconciliation

Closure snapshot: 2026-10-31, branch `docs/arch-001-foundation`, starting commit
`3921c84`. **Original-source reconciliation complete; documentation ready for PR review.**
Architecture choices remain proposed. This is not implementation or deployment acceptance.

## Sources and authority

| Category | Source | Meaning |
| --- | --- | --- |
| Current implementation | [Current-state audit](current-state-audit.md), linked source code and tests | Verified repository observations, with dated verification limits. The audit was previously stored under the blueprint filename; its technical findings are preserved. |
| Long-term product vision | [Original 446-line blueprint](TRIPSE_ARCHITECTURE_BLUEPRINT.md) | Read in full and renamed unchanged from the committed source. PROPOSED North Star, not an accepted ADR. |
| Proposed architecture decisions | [ADR-0017](../adr/0017-modular-react-typescript-migration.md), [UI](../ui/README.md), [API](../api/README.md) | Reconciled migration proposals with explicit scope differences and open owner decisions below. |
| Approved decisions | Explicit owner acceptance recorded in an ADR | No new approval is recorded here. ADR-0017 stays proposed. A supplied vision, task authorization, implemented behavior or passing test is not evidence that every architecture choice is accepted. Historical ADR statuses/evidence remain intact. |
| Future implementation | [Migration roadmap](migration-roadmap.md) | Commissioned FRONT-001/API-001/FRONT-002/FRONT-003/AI-001 and retained Marketing/AUTO-001 scope are future work, not completed features. |

## Original preservation and review evidence

The user identified the committed source
`docs/architecture/TRIPSE_ARCHITECTURE_BLUEPRINT_446_LINES.md`. At starting commit
`3921c84`, it contains 446 lines and 27,385 bytes. It was renamed to the canonical
blueprint path without editing its contents, encoding, whitespace or line endings.
SHA-256 before/after: `f56d5775bfccdf5259c8c5027e151ef8189d74167cdfadf5e1f1e7cdb696a5ad`.
Validation compares the target bytes with `git show 3921c84:<original path>`.

All sections 0–15 have been read. Sections 1/6/8/9 establish future product/domain
scope; 3/4/7/10 define stack/boundaries; 5/11/15 differ from the commissioned docs/stages;
12–14 define gates and future decisions. Reconciliation is recorded below and reflected
in the roadmap, ADR, UI/API docs and documentation index. No blueprint content is rewritten.

Earlier missing-input observations and test results remain historical in Git/worklog;
they no longer describe the current status. The technical audit remains authoritative
for current code, with its original baseline and validation limits. A supplied vision
is evidence of intended direction, not owner approval of a technology or new scope.

## Stage numbering crosswalk — no silent renumbering

The original ARCH-001 commission combined stages differently from blueprint section 11.
The roadmap retains commissioned IDs for continuity; the owner must confirm the IDs
used when creating implementation issues. Neither scheme represents verified issue IDs.

| Blueprint section 11 | Commissioned roadmap / documentation treatment |
| --- | --- |
| ARCH-001 audit | Covered by this ARCH-001 documentation task and current-state audit; no fresh cloud/master deployment claim. |
| DOCS-001 indexes/templates | Documentation structure/index work covered by ARCH-001; conceptual work package, not a new completed GitHub issue. |
| ADR-FE-001 technology decision | Represented by proposed ADR-0017; ADR-FE-001 is a work label, not a second ADR number or approval. |
| FRONT-001 skeleton/shell | Commissioned FRONT-001; see scope differences below. |
| API-001 client | Commissioned API-001; schema/codegen and Query integration after shell. |
| FRONT-002 Hub/navigation | Hub portion of commissioned FRONT-002. |
| FRONT-003 Trip Planner | Planner portion of commissioned FRONT-002; not commissioned FRONT-003. |
| FRONT-004 Document Studio | Commissioned FRONT-003; do not create duplicate implementation tasks for both IDs. |
| AI-001 first tool workflow | Commissioned AI-001, with a concrete editable-draft outcome retained. |
| AUTO-001 tasks/history/approval | Retained future scope, with dependencies/gates/rollback in roadmap; not implemented or folded into AI-001. |

## Requirement differences and proposed handling

| Blueprint requirement | Current implementation / earlier draft | Reconciled treatment and owner decision |
| --- | --- | --- |
| Sections 3.2/6: React/TS/Vite, Router, Tailwind/shadcn, Query and OpenAPI | No frontend packages/build exist; ADR-0017 proposes this core stack | Keep proposed; FRONT-001 PoC and dependency/accessibility/maintenance evidence precede acceptance. |
| Sections 3.2/6: React Hook Form + Zod; conditional React Flow | Earlier migration draft omitted these preferences | Retain form preference in UI strategy/ADR for the first substantial forms; Zod is UX-only. Flow requires an actual diagram requirement. No shell-only speculative installs, Redux or graph orchestrator. Owner accepts exact libraries/versions later. |
| Section 6: dashboard/trips/marketing/automations modules and components/ui/layout/api/hooks | Earlier draft had hub/planner/documents/assistant and shared/* | Map dashboard→hub and initial trips→planner, components/ui→shared/ui, layout→app shell, api→shared/api; hooks stay feature-owned. Retain Marketing/Automations as future features. Owner confirms naming/domain ownership before implementation. |
| Sections 7/15: initial App Shell plus new Hub; one safe endpoint PoC | Earlier FRONT-001 had shell/legacy links and excluded all API reads; full Hub scheduled later | Include one bounded read-only GET /health PoC with response validation, auth/error/loading/cancel handling. Keep full Hub in commissioned FRONT-002; shell landing/navigation in FRONT-001. This narrower Hub split needs owner confirmation; original first-phase requirement remains visible. |
| Sections 1/6: full Trip Catalog, editing and reuse | Planner jobs and Studio trips are separate models/stores; FRONT-002 covers planner/status only | Preserve future catalog/reuse and explicit conversion work. Do not cast TripPlan into Studio Trip or imply the workflow exists. Owner scopes conversion, source ownership and catalog behavior separately. |
| Sections 1/6: Marketing workspace | Existing campaign/marketing.collection capabilities are inside Studio; earlier feature tree omitted Marketing | FRONT-003 preserves current campaign/render/PDF parity. Dedicated Marketing workspace is retained future work with acceptance/rollback; no claim of automated publication. Owner defines independent workspace scope/task. |
| Sections 1/9/11: Automations UI, unified job history/retry/approval | SQLite worker and Firestore/Tasks exist; no general workflow dashboard or approval engine | Retain AUTO-001 panel after stable actor-scoped job/tool contracts. Keep queued/running/completed/failed compatible; no replacement queue, DAG engine or database justified by UI migration alone. |
| Section 8: first tool creates an editable document draft from an existing trip | Earlier AI-001 could stop at a read-only/mock scaffold | AI-001 must complete an authorized synthetic persisted draft with ID/revision/missing-field report; read-only scaffold is interim. Start with an existing Studio trip. Raw planner-result conversion is separate. No customer send. |
| Section 8: read vs draft/write vs external/high-impact permissions | Earlier proposal broadly confirmed consequential writes | Keep tool classes explicit. External/high-impact always requires separate authority/confirmation; precise draft-save confirmation UX and retention are owner decisions. Conservative mock-first policy is not proof that those choices are accepted. |
| Sections 5/15: docs/README and uppercase future document names | ARCH-001 uses architecture.md, contracts.md, routing.md and migration-roadmap.md | Add docs/README navigation and map proposed document responsibilities to current files. Keep optional domain/security/infra/feature expansion future; no bulk historical moves or fake implemented documents. |
| Section 7: new endpoint versioning and possible SSE | Existing APIs and polling are current contracts | Preserve old endpoints; agree /api/v1 or other standard only for new contracts. SSE needs product/auth/reconnect justification; no blanket URL versioning or streaming retrofit. |
| Sections 2/9/10/12: backend/storage/auth/print and same-origin hosting | Verified audit matches these preservation requirements | Reuse FastAPI/Pydantic, independent snapshots/CAS, renderers/print, current queues/storage and IAP/Origin boundaries. No runtime or GCP change in ARCH-001. Frame compatibility and strict release provenance remain implementation gates. |

## Unresolved decisions — future gates, not missing documentation

- Owner acceptance of ADR-0017 core stack, PoC results, dependency ownership/versions,
  form-library adoption, module naming and initial same-service packaging.
- Canonical issue numbering and the full-Hub timing difference above; confirm before
  issuing FRONT-001/002/003 work to avoid confusing blueprint FRONT-003/004.
- Trip Catalog/conversion rules, dedicated Marketing scope and AUTO-001 permissions,
  approval/retry/audit UX. Future storage/workflow engines require evidence, not assumption.
- Assistant placement (panel/full-screen), first tool's draft-write confirmation,
  conversation/result/audit retention and cost caps; live cloud AI remains a separate gate.
- New endpoint versioning, any SSE, eventual customer identity/tenancy and future hosting
  changes require separate decisions. None blocks documentation PR review.

## Historical documentation gaps

`docs/DOC_TEMPLATES_006.md` is absent from this working tree and local Git history
for that path. The [coverage audit](../audits/DOC_TEMPLATES_006_COVERAGE.md) explicitly
describes a pre-implementation snapshot; it is not the missing post-implementation
report. Do not relabel it as acceptance evidence.

Current navigation can use verified existing sources: [Studio instructions](../DOCUMENT_STUDIO.md),
[fixture/CLI guidance](../../demo-fixtures/README.md),
[example manifest](../../demo-fixtures/gt-v1/examples.json) and the coverage audit.
Historical references to the missing report remain explicitly labeled as unavailable
plain-text paths, with adjacent working navigation where useful. No report or historical
acceptance result is fabricated. Earlier worklog and validation snapshots are retained.

## PR and merge considerations

Recommended PR target: `docs/arch-001-foundation` → `dev`. Original restoration and
source reconciliation are complete. No documentation blocker remains for PR review;
the future architecture decisions above remain explicit review items, not accepted
implementation scope. Do not target protected master. No PR is created here.

[CI](../../.github/workflows/ci.yml) now checks PRs targeting dev and master in the
CI-007 source change; hosted execution and mandatory-check enforcement remain separate.
[Delivery](../../.github/workflows/delivery.yml) runs on pushes to dev/master and calls
CI before the DEV job. There is no documentation-path exclusion: merging even this
documentation-only branch into dev creates a qualifying push and can trigger DEV
deployment, subject to workflow success and environment controls. This review does not
authorize that deployment. Coordinate merge timing and existing delivery authorization
with the owner; do not treat a documentation merge as operationally inert.

[CI-007](../CI_007_DEV_PR_GATE.md) implements the separately proposed PR trigger
extension with read-only CI permissions and no deployment credentials. Delivery
triggers, IAM/WIF, environment approvals, protected branches and promotion authorization
remain unchanged. ARCH-001 itself changed no workflow; its historical validation below
remains a dated snapshot, not proof of CI-007 hosted acceptance.

## Historical final-review validation (before original restoration)

2026-10-31, Windows, existing Python virtual environment:

- Scoped Markdown structure and relative-file/heading-fragment checks: 24 changed/new
  Markdown files and 290 relative link occurrences passed. Bare unavailable historical
  paths are explicitly labeled, not active broken links. No configured Markdown linter
  was found; these were ad hoc structural checks, not a full Markdown lint suite.
- All 17 ADRs passed YAML metadata/ID/unique-number checks; the registry is one contiguous
  four-column table and its next-number hint is ADR-0018. ADR-0017 remains proposed.
- Audit preservation check: every section from `Current system` onward is identical to
  the technical audit in starting commit `71f59fa`; only title/provenance changed.
- `.venv/Scripts/python.exe -m scripts.gcp.ci offline`: PASS; no cloud credentials or
  deployment used.
- `.venv/Scripts/python.exe -m pytest -q tests/test_github_cicd.py tests/test_ci_integration.py`:
  66 passed in 1.13 seconds.
- `git diff --check`: PASS. Tracked/untracked change scope is documentation only.

The earlier 1143-test result remains a historical ARCH-001 result, not a new run.
Full pytest, browser/PDF/container QA, live providers, hosted IAP and deployments were
not rerun in that earlier pass. It left original-source reconciliation incomplete;
the closure above and validation below supersede that limitation without rewriting
the earlier evidence or worklog observations.

## Closure validation — 2026-10-31

- `.venv/Scripts/python.exe -m scripts.gcp.ci offline`: PASS; source and preview
  contracts checked without cloud credentials or deployment.
- `.venv/Scripts/python.exe -m pytest -q tests/test_github_cicd.py tests/test_ci_integration.py`:
  **66 passed in 1.23 seconds**.
- Markdown structure/local-link/heading-fragment checks: **18 Markdown files and 252
  relative link occurrences PASS**. All 17 ADRs passed YAML/unique numbering/nine-section
  checks; registry table and next-number hint passed. Exact blueprint/audit preservation,
  worklog CSV, CI trigger notes and documentation-only scope checks passed.
- `git diff --check`: **PASS**. Original blueprint whitespace remains untouched;
  preservation compares bytes, not normalized text or line count alone.

No repository-configured Markdown linter was found; structural/link checks are ad hoc
and offline. Full pytest, browser/PDF/container QA, actual React builds, hosted IAP,
LIVE providers and deployments are not rerun for documentation-only closure. The
earlier 1143-test result remains historical. Documentation completion does not claim
implementation of any new route, module, tool or frontend dependency.
