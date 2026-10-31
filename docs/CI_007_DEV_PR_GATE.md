# CI-007 — DEV pull request quality gate

2026-10-31. Base: clean dev `b3e4a92`; working branch `ci/ci-007-dev-pr-gate`.
Status: **implemented and validated locally; hosted acceptance pending**.
CI-007 is the user-supplied task label, not a verified GitHub issue number.
Existing [ADR-0012](adr/0012-github-actions-delivery.md) applies; no new architecture
decision, deployment authorization or ADR acceptance is introduced.

## Audit before changes

The source review confirmed all six requested baseline contracts, with no discrepancy:

| Contract at base b3e4a92 | Evidence |
| --- | --- |
| PR CI targets master only | ci.yml pull_request branch filter. |
| Delivery triggers on dev/master pushes and manual dispatch | delivery.yml on section; no PR event or documentation-path exclusion. |
| Delivery reuses CI before deployment | jobs.ci uses ci.yml; dev needs ci; prod needs ci/dev plus explicit success conditions. |
| PR CI is read-only | Workflow/job contents: read; no environment, OIDC scope, cloud auth, secrets or deployment variables; checkout persist-credentials: false. |
| DEV/PROD have separate authorization boundaries | development/production environments, their WIF variable sets and dedicated identities; existing offline tests enforce immutable trust and separation. |
| Production retains master/DEV evidence | Master-only prod condition, successful DEV dependency for pushes, existing accepted proof checks for promotion/rollback. |

Sources reviewed: [CI](../.github/workflows/ci.yml),
[Delivery](../.github/workflows/delivery.yml),
[workflow/security contracts](../tests/test_github_cicd.py),
[integration](../tests/test_ci_integration.py),
[command/cache contracts](../tests/test_ci_python_cache.py),
[production contracts](../tests/test_production_bootstrap.py),
[delivery guide](GITHUB_CICD.md) and [migration roadmap](architecture/migration-roadmap.md).
These observations inspect source and local tests, not current remote GitHub/GCP settings.

## Minimal source change and security

The sole workflow edit is ci.yml pull_request.branches: `[master]` → `[dev, master]`.
workflow_call/workflow_dispatch, the existing job, pinned Actions, permissions, Python
tests, offline contracts, Chromium/browser QA and diff check remain unchanged. No path
exclusions or frontend commands are added; frontend toolchain checks await FRONT-001A.

No pull_request_target or workflow_run handoff, PR environment, WIF authentication,
id-token write permission, secrets/deployment variables or cloud operation is introduced.
Fork PRs run the same unprivileged checks, subject to GitHub's existing approval policy.
Checkout does not persist credentials. No deployment workflow can be called from PR CI.
The existing deployment coordinator also rejects PR contexts before cloud access,
including a PR attempting to present a master ref.

delivery.yml is untouched: its Git source matches the base; checkout CRLF normalization
is accounted for when comparing working bytes with Git blobs. CI's normalized source
diff consists only of the target branch list. No release-proof validation is weakened.

## Events after this change

| Event | Behavior |
| --- | --- |
| PR targeting dev | Existing CI checks only; no deployment. |
| PR targeting master | Existing CI checks only; no deployment. |
| Push/merge to dev | Existing Delivery workflow; DEV deployment after checks and existing authorization. |
| Push/merge to master | Existing master/accepted-DEV/protected-PROD release process. |
| Other feature branch push | No automatic deployment. |

Pre-merge checks do not alter post-merge delivery. Do not merge merely to test PR CI:
a merge into dev can deploy. Existing protected master, WIF, concurrency, evidence and
environment approval requirements remain outside this task's mutation scope.

## Executed local validation

- `.venv/Scripts/python.exe -m pytest -q tests/test_github_cicd.py tests/test_ci_integration.py`:
  **68 passed in 1.10 seconds**.
- `.venv/Scripts/python.exe -m pytest -q tests/test_ci_python_cache.py tests/test_production_bootstrap.py`:
  **52 passed in 1.89 seconds**. Existing commands/pins, cache contracts and production
  identity/proof/security checks remain intact.
- `.venv/Scripts/python.exe -m scripts.gcp.ci offline`: **PASS**, source and preview
  contracts; no cloud credential or deployment used.
- Both workflow files parsed with yaml.BaseLoader; CI exact one-filter delta and
  unchanged Delivery Git source verified. Expanded contracts cover intended PR events,
  absent privileged handoffs/credentials/environments, secure checkout, dependency and
  promotion conditions, and denied PR deployment contexts.

- Scoped Markdown structure/relative-link/heading-fragment checks: **8 changed/new
  Markdown files and 154 local link occurrences PASS**. ADR IDs/YAML, worklog CSV
  structure and intended workflow/test/documentation scope checks passed.
- `git diff --check`: **PASS**.

actionlint was not found on PATH or in checked local tool locations, so was not run.
Full pytest, local browser QA and container builds were not rerun for this trigger-only
change; their existing CI commands are preserved. Local tests do not prove hosted
workflow success, fork approvals, required-check enforcement or deployment acceptance.

## Hosted acceptance and Definition of Done — pending

After review, push the working branch and open a PR targeting dev. Record the actual
PR/head SHA and GitHub run evidence; none is fabricated here. Verify:

1. PR automatically starts workflow CI and job `Tests and offline contracts`.
2. Python tests, offline contracts, Chromium setup, all existing browser QA and diff
   checks finish successfully, with visible PR status checks.
3. This PR event starts no Delivery deployment and uses no cloud authentication,
   privileged environment or OIDC write scope. Inspect the run event/job logs.
4. Existing Delivery file and master/proof/security contracts remain unchanged.

No push/PR/hosted run is performed in this local implementation. The user-defined
Definition of Done requires real successful dev-PR execution, so CI-007 is not marked
complete. Ready for a PR to dev; hosted acceptance is the remaining completion gate.

## Manual GitHub enforcement

An administrator must separately inspect/configure the dev branch protection or ruleset
to require the exact check context emitted by the real PR run, using the GitHub Actions
check source. The job is named `Tests and offline contracts`; verify the actual context
instead of guessing a caller prefix. Select up-to-date-branch policy deliberately and
preserve master/production protections and fork workflow approvals. Default repository
token permissions should remain read-only. YAML does not make a check mandatory.

No remote branch-protection/ruleset setting is changed or claimed verified here. There
are no measured hours/costs or hosted release/approval evidence for CI-007. Rollback of
this change restores only the old CI PR branch filter and matching test/docs; it does
not revert deployments, resources or application data.
