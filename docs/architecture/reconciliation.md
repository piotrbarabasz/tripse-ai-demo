# ARCH-001 documentation reconciliation

Final-review snapshot: 2026-10-31, branch `docs/arch-001-foundation`, starting commit
`71f59fa`. **Incomplete: original blueprint input required before PR readiness.**

## Sources and authority

| Category | Source | Meaning |
| --- | --- | --- |
| Current implementation | [Current-state audit](current-state-audit.md), linked source code and tests | Verified repository observations, with dated verification limits. The audit was previously stored under the blueprint filename; its technical findings are preserved. |
| Long-term product vision | Original user-authored 446-line `TRIPSE_ARCHITECTURE_BLUEPRINT.md` | Required input, unavailable in this review session. The canonical destination is `docs/architecture/TRIPSE_ARCHITECTURE_BLUEPRINT.md`; no placeholder or reconstructed vision is substituted. |
| Proposed architecture decisions | [ADR-0017](../adr/0017-modular-react-typescript-migration.md), [UI](../ui/README.md), [API](../api/README.md) | ARCH-001 migration proposals. Must be reconciled against the original vision before final review completion. |
| Approved decisions | Explicit owner acceptance recorded in an ADR | No new approval is recorded here. ADR-0017 stays proposed. A supplied vision, task authorization, implemented behavior or passing test is not evidence that every architecture choice is accepted. Historical ADR statuses/evidence remain intact. |
| Future implementation | [Migration roadmap](migration-roadmap.md) | FRONT-001, API-001, FRONT-002, FRONT-003 and AI-001 are future tasks, not completed features. |

The original was not recovered from the repository (including ignored files), reachable
Git history, unreachable Git blobs, checked VS Code history/backups, project directories,
Downloads/Desktop/Documents locations or the two local TRIPSE documentation ZIPs.
The user reports that the original was removed; these checks have not recovered those
bytes or established when/how that occurred. The only blueprint version found in Git
is the ARCH-001 technical audit. A local path was requested; original restoration still
requires the actual source. Line count alone cannot establish a candidate's provenance.

## Reconciliation still required

Restore the original text at its canonical destination without rewriting its product
requirements. Add navigation and commentary in this reconciliation document. Read it
in full, then record each conflict or scope difference with source section references,
current code evidence, proposed handling, affected stage and owner decision required.
Do not infer contradictions from a summary or remove requirements to match the audit.

The following are known current constraints to compare with the original; they are
**not asserted conflicts with an unread document**:

| Current constraint | Provisional migration handling | Owner review after source restoration |
| --- | --- | --- |
| Vanilla JS UI and modular FastAPI | Proposed React shell at `/app`; keep legacy routes | Check target UI/module boundaries and eventual cutover requirements. |
| Python HTML/CSS rendering and browser print; no server export queue | Preserve renderers/PDF gates during Studio migration | Identify any longer-term export/archive requirements without claiming them implemented. |
| Separate planner and Studio models/stores | Explicit future adapter if conversion is required | Preserve desired end-to-end product workflows and schedule their missing implementation. |
| IAP reader/editor/task separation; cloud mock restrictions | Retain all current boundaries | Identify any future identity/tenancy/live-AI requirements as separately reviewed work. |
| Single existing Cloud Run image and strict release-source provenance | Proposed initial same-service packaging | Compare any eventual hosting/deployment design and keep later evolution explicit. |
| No general assistant tool orchestrator | Proposed mock-first domain tools in AI-001 | Compare assistant capabilities, confirmation and retention requirements. |

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

Recommended eventual PR: `docs/arch-001-foundation` → `dev`, after original restoration
and reconciliation. Do not target protected master for this task. No PR is created here.

[CI](../../.github/workflows/ci.yml) checks PRs targeting master only.
[Delivery](../../.github/workflows/delivery.yml) runs on pushes to dev/master and calls
CI before the DEV job. There is no documentation-path exclusion: merging even this
documentation-only branch into dev creates a qualifying push and can trigger DEV
deployment, subject to workflow success and environment controls. This review does not
authorize that deployment. Coordinate merge timing and existing delivery authorization
with the owner; do not treat a documentation merge as operationally inert.

Propose a separate CI change for PR targets `[dev, master]`, retaining read-only CI
permissions and no deployment credentials. Delivery triggers, IAM/WIF, environment
approvals, protected branches and promotion authorization remain unchanged. This task
does not modify any workflow or add a deployment-skipping mechanism.

## Final-review validation executed

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
not rerun for this documentation reconciliation. Comparison with the original vision
cannot pass until that source is recovered; ARCH-001 final review is not complete.
