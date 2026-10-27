# CI-CD-FIX-002: Windows operator setup

2026-10-27 status: DEV environment/WIF and application resources have been
bootstrapped by the operator. WIF works; authenticated health 401 blocks rollout.
Do not repeat resource creation to fix authentication. Continue from the
[AUTH-004 incident ledger and handoff](DEV_AUTH_004_INCIDENT.md). Historical
validation observations below describe their original dates.

Code changes are prepared on `dev`. This procedure is operator-invoked; no part
was executed to mutate GitHub/GCP in implementation. See [architecture, evidence
and recovery](GITHUB_CICD.md) and [application bootstrap](DEPLOY_GCP.md).

## A. GitHub Environments (manual settings, no cloud deployment)

Create repository Settings -> Environments -> `development` and `production`.
Allow development from dev/master and only branches approved for explicit manual
dispatch. Restrict production to master; require a human reviewer and disable
protection bypass where available. Verify the repository/account plan supports
required reviewers: unsupported approval protection is a blocker, not something
YAML can bypass. For a single operator, prevent-self-review needs another reviewer.
Protect master with PR CI/review, no force pushes/deletion and review of workflow,
deployment and infrastructure changes. Default Actions token stays read-only.

## B–C. Generate validated nonsecret configuration (local files only)

From the repository root, with local dependencies installed:

```powershell
gh auth login
gh auth status
New-Item -ItemType Directory -Force local-data/cicd-bootstrap | Out-Null
Copy-Item infra/gcp/github-actions/development.cloud_demo.json.example local-data/cicd-bootstrap/development.json
code local-data/cicd-bootstrap/development.json
```

Review every field. Replace OAuth `REPLACE`, approved human membership and reviewed
Run origin. Keep DEV probe in editors; retain `cloud_demo`, public access `false`,
and planning `mock`. Never put API credentials, OAuth secrets, human session tokens
or service-account keys here. LIVE OpenAI/Google providers remain disabled.

```powershell
.venv/Scripts/python.exe -m scripts.gcp.bootstrap prepare --environment development --mode cloud_demo --input local-data/cicd-bootstrap/development.json --output local-data/cicd-bootstrap/development.variables.json
if ($LASTEXITCODE -ne 0) { throw 'Correct config before continuing' }
$devVariables = Get-Content -Raw local-data/cicd-bootstrap/development.variables.json | ConvertFrom-Json
```

The helper validates the full deployment contract, rejects placeholders and
cross-environment identities, creates only a local ignored nonsecret bundle and
refuses to overwrite an existing output. For a revision choose a new output name.
It never writes GitHub variables or creates infrastructure. Compare its exact
provider/account names to the reviewed Terraform outputs before using them.

Under development -> Environment variables add these five names with the matching
properties of `$devVariables`: `DEPLOY_CONFIG_JSON`, `EXPECTED_CLOUD_FEATURE_MODE`,
`WIF_PROVIDER`, `DEPLOY_SERVICE_ACCOUNT`, `CI_PROBE_ACCOUNT`. Copy one property at
a time without printing the bundle:

```powershell
$devVariables.DEPLOY_CONFIG_JSON | Set-Clipboard
# Paste into DEPLOY_CONFIG_JSON; repeat for the other four properties.
.venv/Scripts/python.exe -m scripts.gcp.bootstrap check --environment development
if ($LASTEXITCODE -ne 0) { throw 'Fix missing or invalid GitHub settings' }
```

`check` uses read-only paginated `gh api` with an authenticated operator who can
read repository Environments/variables. It prints READY / MISSING / INVALID, never
values. 403/404 can mean insufficient visibility. READY for variables alone is
not proof of GCP readiness. For production repeat using its separate example,
`--environment production`, PROD identities/resources and a probe in readers.
The five required settings are ordinary nonsecret GitHub Environment variables;
no GCP permanent key or human token belongs in GitHub Secrets.

## D–E. GCP bootstrap (manual IAM/resources; can incur costs)

Follow [declarative resources and least privilege](DEPLOY_GCP.md#declarative-resources-and-least-privilege).
Existing owned Run service, immutable registry, builder/runtime identities and
Cloud Build source bucket are prerequisites. Bootstrap DEV private versioned GCS,
named Firestore with PITR, bounded Tasks queue/task identity and scoped IAM with
`infra/gcp/cloud-demo`, a separate private DEV state and reviewed
`dev.tfvars.example`. Configure direct IAP, custom OAuth/programmatic client,
approved human/task access and exact Run origin. Never copy DEV user data to PROD.

Then review the [CI identity Terraform plan procedure](GITHUB_CICD.md#one-time-operator-bootstrap-checklist)
for `environments=["dev"]`. This is a separate shared CI state; do not create a
second WIF pool. Import matching existing resources and authorize apply separately.
No workflow bootstraps its own WIF. Check DEV push trust allows only dev/master;
manual dispatch remains explicit. The module grants dedicated deploy/probe roles,
not application data resources. Do not create SA JSON keys or broad owner grants.

After provisioning, approve DEV probe as application editor and service IAP
accessor (CI Terraform grants its IAP/Run roles). Verify runtime storage/database/
queue IAM, task actAs/token minting, IAP invoker enforcement and Tasks OAuth
programmatic client. Full Document Studio must remain private.

```powershell
.venv/Scripts/python.exe -m scripts.gcp.bootstrap check --environment development --gcp
if ($LASTEXITCODE -ne 0) { throw 'Review bootstrap or metadata permissions' }
```

This uses the operator gcloud session for read-only provider/account existence and
state. It does not prove policy/IAM drift, all app resources or actual runner WIF.
CI separately obtains keyless credentials and verifies private GCS/Firestore/Tasks,
runtime/probe/task identities, IAM, direct IAP and usable probe authorization
before build/deploy. Missing setup blocks without readonly fallback.

Before PROD release bootstrap separate PROD app resources and configuration,
then add prod alongside dev in the **same CI identity state**. Review every IAM
binding/plan. No apply, cloud deployment or provisioning was performed by this fix.

## F. First DEV run (actual deployment and costs)

Finish bootstrap/checks first. Use VS Code Source Control to review and commit
the intended changes, including new files, on dev. Then the operator runs:

```powershell
git switch dev
git status --short
# Stop if intended changes have not been committed.
git push origin dev
gh run list --workflow delivery.yml --branch dev --limit 5
gh run watch <DEV_RUN_ID> --exit-status
```

Replace `<DEV_RUN_ID>` with the numeric ID listed by gh. Alternatively, after
the updated workflow is available, explicitly dispatch:

```powershell
gh workflow run delivery.yml --ref dev -f operation=dev
```

Inspect summary/artifact for exact pushed SHA, digest, receiving revision/100%
traffic, `cloud_demo`, URL, real API/UI acceptance and previous SHA. Missing config
now fails before dependency installation/Chromium and WIF. Passing offline CI is
not actual cloud acceptance. Other feature pushes do not deploy automatically.

## G–H. PR dev -> master and approved release

```powershell
gh pr create --base master --head dev --title 'Release reviewed dev changes' --body 'Review DEV acceptance and immutable release metadata before merging.'
```

PR runs tests only, with no WIF identity or deployment. Review CI/changes and merge
through protected GitHub UI. This fix does not create that PR, merge or push.
The new **master merge SHA**, not the old dev SHA, must pass CI -> build/reuse ->
DEV acceptance -> trusted immutable proof -> production approval. Inspect proof
under Actions -> Delivery -> Review deployments, then approve deliberately. PROD
gets the same digest, with read-only smoke. Failed CI/DEV never authorizes PROD.
Later DEV changes cannot alter the frozen accepted master artifact.

## I. Diagnose failure without exposing credentials

| Stage | Check |
|---|---|
| Missing variable | Summary gives exact name and Settings -> Environments location; run bootstrap check |
| Malformed JSON | Correct local JSON; prepare a new bundle; parser never prints input |
| Invalid runtime schema/identity | Compare target/mode/private access with template and Terraform outputs |
| IAM/WIF auth | Review claims, event/ref/environment, impersonation and IAM propagation; never substitute keys/human tokens |
| GCP preflight/bootstrap | Distinguish missing resources from denied metadata/probe access; check IAP/OAuth and app IAM |
| Application deployment/acceptance | Inspect release/recovery summary; failed run has no accepted artifact |

The config summary gives actionable errors without a traceback. The read-only
helper cannot fix missing infrastructure. Coordinate terminal operations with
Actions locks; GitHub concurrency cannot serialize a separate operator terminal.

## J. Controlled rollback and recovery (actual deployment and costs)

Actions -> Delivery -> Run workflow: choose master for PROD, operation `rollback`,
target dev/prod, prior **accepted target-environment** SHA, successful evidence run
ID and immutable artifact ID. PROD still requires approval; no rebuild/data restore.
Promotion uses `promote` plus trusted master DEV evidence. Expired/untrusted proof
blocks. See [recovery policy](GITHUB_CICD.md#manual-release-rollback-and-recovery-runbook)
for private prior-traffic restoration and manual recovery if verification fails.

Real runner WIF/IAP acceptance and first DEV/PROD delivery remain operator gates.
Budget Actions/browser/artifacts, build/registry, Run, GCS, Firestore/PITR and Tasks
synthetic acceptance traffic. No billed amounts/hours or successful bootstrap are
claimed merely because the modules exist.

## Validation record for this fix

2026-10-26: `make test` **473 passed**, including 40 new bootstrap/configuration
regressions and expanded runtime/probe prerequisite cases. One existing
Starlette/AnyIO deprecation warning remains. Actionlint 1.7.7 workflow validation,
Terraform 1.13.5 fmt/schema validation (Google 8.8.1), offline source/runtime
contracts and Git whitespace checks passed. The dependency-free path was also
tested under Python `-S` (no site packages). Operator checks read GitHub metadata
only: development exists with all five settings missing, production absent.
Browser/Docker QA was not repeated for this workflow/helper-only fix; the CI
workflow retains browser tests. No real runner delivery, cloud build submit,
Terraform apply, IAM change, deployment, merge or push was performed.
