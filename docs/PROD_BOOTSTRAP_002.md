# TRIPSE-PROD-BOOTSTRAP-002: resume the first private production release

Audit date: 2026-10-27, Europe/Warsaw. Local branch dev,
HEAD f6d96c5899419eadcb8e568cbaf0099001f94a4d. Fetched origin/master is
78919b0f17805529fff7a0cfd289ad460c93403b (PR #1 already merged). At audit start
their file trees were identical. No reset, re-merge or master push is required.
This continuation supersedes the execution order in [BOOTSTRAP-001](PROD_BOOTSTRAP_001.md).

This session performed read-only GitHub/GCP audits, fetched Git refs, generated
local variables and refreshed Terraform plans. No remote settings, IAM, IAP,
application data, Terraform state/import, build, deployment or workflow run was
changed. All mutation blocks below are **operator commands requiring explicit
approval**, not commands executed by Codex. PROD remains **NOT READY**.

## Confirmed failure and accepted evidence

[Run 40550402214](https://github.com/piotrbarabasz/tripse-ai-demo/actions/runs/40550402214)
is push/master, attempt 1, SHA 78919b0f17805529fff7a0cfd289ad460c93403b.
CI and DEV succeeded. PROD job 122356592499 failed in dependency-free configuration:

```text
CI blocked: Missing GitHub Environment variable: DEPLOY_CONFIG_JSON (production).
```

All five required production variables are absent. The first check reports only
the first missing field. The auth step, gcloud installation and promotion step
were skipped. This run is **not a PROD WIF, IAM, IAP or container failure**.
Supplying variables alone would expose the next missing bootstrap gate; it is
not sufficient to authorize credentials in the unprotected environment.

Artifact **12753973550**, unexpired, was downloaded in memory and validated with
the actual `ci.validate_proof(..., production=True)` implementation and attempt-1
DEV job metadata. The overall Delivery failure does not invalidate its successful
DEV acceptance. Exact evidence:

- Master SHA: 78919b0f17805529fff7a0cfd289ad460c93403b.
- Digest: sha256:b6ac3c9bacd7d565df383452b4130064e3237b8ee4fbadd359a7f38108f9a153.
- Source build: 51fd44d5-31ff-434a-926c-71e79ee0b15e, successful reviewed recipe.
- DEV revision: tripse-ai-dev-00008-hmj, 100% traffic, cloud_demo/mock, IAP true.
- Acceptance: api_ui_mock; source_verified=true; accepted=true; run_attempt=1.

Registry digest/immutability, build recipe metadata and receiving DEV digest
match. This continuation read no application documents, database contents or
source archive. Accepted evidence attests the existing source-byte verification.

## Live inventory versus desired state

| Item | Status | Observed / required action |
|---|---|---|
| Master code | PRESENT | Already merged exact SHA above; same tree as initial local dev |
| Accepted master DEV evidence | PRESENT | Original run attempt 1 and immutable artifact validated |
| GitHub production Environment | DIFFERENT | ID 25489284095, created by workflow; protection_rules=[], policy=null, can_admins_bypass=true |
| Reviewer/self-review | MISSING | Configure piotrbarabasz, ID 72949549; self-review allowed by explicit owner choice |
| Production branch policy | MISSING | GET 404 while custom policies disabled; require exactly branch master |
| Master protection | MISSING | Protection API 404; rulesets=[]; strict PR CI/admin enforcement required |
| Five production variables | MISSING | No values; locally generated complete validated cloud_demo/mock bundle |
| PROD Run service/runtime | PRESENT | tripse-ai-prod, existing runtime tripse-ai-prod@tripse-ai.iam.gserviceaccount.com |
| PROD access/mode | DIFFERENT | Public readonly_demo/mock, invokerIamDisabled=true, IAP flag unset/false |
| PROD traffic | PRESENT | 100% tripse-ai-prod-00001-prh; old SHA be798fedc1970cdd96ce44bf6c0fae37fe4fce38 |
| PROD Run/IAP IAM | MISSING | Both policies have no bindings; no reviewed human/probe/task/IAP-agent grants |
| PROD OAuth settings | MISSING | Resource metadata only; no programmaticClients configured |
| Shared WIF pool/DEV provider | PRESENT | Existing Terraform resources retained unchanged by fresh plan |
| github-prod | MISSING | Provider describe returns NOT_FOUND; plan creates strict master/production provider |
| PROD deploy/probe/task SA | MISSING | Absent from complete permitted service account list |
| PROD bucket/DB/queue | MISSING | Complete project/region listings show only DEV resources and build buckets |
| Builder isolation | DIFFERENT | Shared builder still has project-wide roles/cloudbuild.builds.builder |
| IAP service-agent object | UNKNOWN | Direct IAM describe returns PERMISSION_DENIED; active DEV IAP and its existing grant are corroborating evidence, not a successful object read. Do not create duplicate agents or widen operator IAM |
| Inherited/group negative IAM | UNKNOWN | Direct metadata audit/plan does not prove effective denial through every ancestor/group; operator verification remains required |
| PROD WIF token exchange/probe/full acceptance | UNKNOWN | Never exercised; gated after provisioning and production approval |

Actual PROD URI is https://tripse-ai-prod-64ctpggq3a-lm.a.run.app.
The previous public preview will lose anonymous access during the approved
cutover. Expect a maintenance interval until the IAP service-agent/human grants
are applied. Never reopen anonymous access to recover from a failed rollout.

## State reconciliation and fresh plans

All three roots use the default **local backend**; no backend block or cached
remote backend was found. Actual files were inspected before planning:

| Root | Existing state | Lineage / serial before planning |
|---|---|---|
| infra/gcp/github-actions | PRESENT, 21 resource instances | 01fd2f1a-88d6-a0bb-4c2e-faea3e35c2bc / 26 |
| infra/gcp/cloud-demo | PRESENT, 22 instances | c2dc7573-79ff-4c3a-dbb1-54ae74233c30 / 19 |
| infra/gcp/cloud-demo-prod | MISSING, correctly unapplied | No state file; do not seed it from DEV |

The original exact legacy_builder[0] import is already tracked in shared CI.
No import was repeated. Existing CI auto vars contain dev+prod. Keep one pool
and one shared CI state. Separate PROD app root reuses the existing module with
manage_project_apis=false; shared project APIs remain owned by DEV state.

Fresh refreshed plans, not reused historical plans:

| Plan/root | Create | Update | Delete | Use |
|---|---:|---:|---:|---|
| CI prod-bootstrap-002-builder.tfplan | 9 | 0 | 1 | Controlled builder-only first phase with explicit environments=[dev] |
| CI prod-bootstrap-002.tfplan | 20 | 0 | 1 | Full desired-state review snapshot before any apply; **stale after builder apply** |
| PROD app prod-bootstrap-002.tfplan | 17 | 0 | 0 | Empty independent application resources |
| DEV app prod-bootstrap-002.tfplan | 0 | 0 | 0 | Existing application unchanged |

The deletion is ONLY
`google_project_iam_member.legacy_builder[0]`: remove the exact project binding
roles/cloudbuild.builds.builder for tripse-ai-build@tripse-ai.iam.gserviceaccount.com.
No service account, image, bucket, database or other role member is deleted.
Nine replacements scope builder project metadata/logging, build source/log buckets
and registry push permissions. This can affect DEV builds; pause delivery and
exercise a **fresh** DEV build after this phase. Reusing a cached tag is not proof.
After successful builder apply, regenerate the normal dev+prod CI plan: expected
remaining change is **11 creates**, zero updates/deletes, if nothing else drifted.
That expectation is not an already executed post-apply plan.

Exact address/action manifests are saved privately in
local-data/prod-bootstrap-002/{builder,ci,prod,dev}-plan-summary.json. The address
appendix below reproduces them for review. Saved plans and state never go in Git.
State checksums/lineages are recorded in states-before.json; audits in audit.json.
If this workspace is missing or remote changes occurred, re-audit and replan;
do not reconstruct a state, blindly import, or trust these counts by themselves.

## Ordered operator procedure (PowerShell)

Stop on an unexpected result. Read-only preparation can be repeated. Every write
stage requires operator approval for its actual diff, costs and access impact.
After partial completion, inspect current state, regenerate the relevant plan and
review the remaining address/action subset; never reapply a stale saved plan.

### 0. Initialize review context and validate local configuration

Run from the repository root. Use these helpers in one PowerShell session:

```powershell
$ErrorActionPreference = 'Stop'
$prodRepo = 'repos/piotrbarabasz/tripse-ai-demo'
$prodWork = 'local-data/prod-bootstrap-002'
$prodSha = '78919b0f17805529fff7a0cfd289ad460c93403b'
$prodTfCommand = Get-Command terraform -ErrorAction SilentlyContinue
$prodTf = if ($prodTfCommand) { $prodTfCommand.Source } else { Join-Path $env:TEMP 'tripse-cloud-parity-tools/terraform.exe' }
if (-not (Test-Path -LiteralPath $prodTf)) { throw 'Install the reviewed Terraform CLI first' }
function Invoke-ProdTf {
    param([string]$Root, [string[]]$TfArguments)
    & $prodTf "-chdir=$Root" @TfArguments
    if ($LASTEXITCODE -ne 0) { throw "Terraform failed in $Root; stop and inspect" }
}
function Invoke-ProdGh {
    param([string]$Path, [string]$Method = 'GET', [string]$PayloadFile, [switch]$Allow404)
    $prodGhArguments = @('api', '--method', $Method, $Path)
    if ($PayloadFile) { $prodGhArguments += @('--input', $PayloadFile) }
    # Windows PowerShell turns native stderr into ErrorRecords even for handled 404s.
    $prodGhSavedPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $prodGhRaw = & gh @prodGhArguments 2>$null
        $prodGhExit = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prodGhSavedPreference
    }
    $prodGhData = $prodGhRaw | ConvertFrom-Json
    if ($prodGhExit -ne 0) {
        if ($Allow404 -and $prodGhData.status -eq '404') { return $null }
        throw 'GitHub metadata/settings operation failed; credentials and raw stderr suppressed'
    }
    return $prodGhData
}
New-Item -ItemType Directory -Force $prodWork | Out-Null
if (-not (Test-Path "$prodWork/production.variables.json")) {
    .venv/Scripts/python.exe -m scripts.gcp.bootstrap prepare --environment production --mode cloud_demo --input infra/gcp/github-actions/production.cloud_demo.json --output "$prodWork/production.variables.json"
    if ($LASTEXITCODE -ne 0) { throw 'Production variable validation failed' }
}
git status --short
git rev-parse origin/master
Invoke-ProdTf 'infra/gcp/github-actions' @('show', 'prod-bootstrap-002.tfplan')
Invoke-ProdTf 'infra/gcp/cloud-demo-prod' @('show', 'prod-bootstrap-002.tfplan')
Invoke-ProdTf 'infra/gcp/cloud-demo' @('show', 'prod-bootstrap-002.tfplan')
```

Review values privately against the tracked production.cloud_demo.json; do not
dump the variables bundle into Actions logs. It has five variables and no secret
payloads. Own PROD resource/identity names are mandatory. The existing registry
and reviewed public OAuth client ID are the only intentionally shared references.

### 1. Configure GitHub protection before exposing production credentials

**APPROVAL: remote GitHub settings writes.** Current unprotected state is verified.
These commands skip an already configured environment/master rather than blindly
overwriting stronger protection; the checker must verify the result.

```powershell
$prodEnvironment = Invoke-ProdGh "$prodRepo/environments/production"
if (@($prodEnvironment.protection_rules).Count -eq 0 -and $null -eq $prodEnvironment.deployment_branch_policy) {
    $null = Invoke-ProdGh "$prodRepo/environments/production" 'PUT' 'infra/gcp/github-actions/production-environment.json'
}
$prodPolicies = Invoke-ProdGh "$prodRepo/environments/production/deployment-branch-policies?per_page=100"
if (@($prodPolicies.branch_policies).Count -eq 0) {
    $null = Invoke-ProdGh "$prodRepo/environments/production/deployment-branch-policies" 'POST' 'infra/gcp/github-actions/production-branch.json'
} elseif (@($prodPolicies.branch_policies).Count -ne 1 -or $prodPolicies.branch_policies[0].name -cne 'master' -or $prodPolicies.branch_policies[0].type -cne 'branch') {
    throw 'Unexpected production policy; review it instead of adding another branch'
}
$prodMasterProtection = Invoke-ProdGh "$prodRepo/branches/master/protection" -Allow404
if ($null -eq $prodMasterProtection) {
    $null = Invoke-ProdGh "$prodRepo/branches/master/protection" 'PUT' 'infra/gcp/github-actions/master-protection.json'
}
```

In GitHub Settings -> Environments -> production, **disable administrator bypass**.
Verify reviewer piotrbarabasz and allow self-review (the user's explicit choice).
This is a solo-operator pause, not independent two-person approval. Branch policy
must contain only master, no tag/wildcard. Master uses strict required PR CI
`Tests and offline contracts`, pinned to GitHub Actions App 15368, admin enforcement,
no force push/delete; zero independent PR approvals permits the solo owner path.
Do not remove required CI if a check name changes; inspect the PR check first.

```powershell
.venv/Scripts/python.exe -m scripts.gcp.production_readiness --variables-file "$prodWork/production.variables.json"
if ($LASTEXITCODE -ne 0) { throw 'Stop: production approval/branch protections are not verified' }
```

The live Environment GET **does** expose can_admins_bypass. The updated checker
requires explicit false, rejects true/missing, and now verifies this through the
API. Earlier BOOTSTRAP-001 uncertainty about GET visibility is superseded. No
unsupported field is added to the reviewed PUT payload; the toggle is set in UI.

### 2. Controlled builder isolation; DEV build acceptance before proceeding

**APPROVAL: shared builder IAM change and subsequent DEV build/deployment costs.**
Pause concurrent Delivery operations in the Actions UI; do not cancel an in-flight
release midway through its traffic/IAM writes. Record current DEV revision. The
explicit source/log selection is already in merged master and accepted DEV code.
Back up existing local state files privately, never into another Terraform root.

Only use the dev-only builder phase while actual shared state has NO PROD
addresses. If PROD is already tracked after a partial/full apply, skip this plan
and reconcile using dev+prod; otherwise dev-only inputs could propose removals.

```powershell
$prodCiStateAddresses = & $prodTf '-chdir=infra/gcp/github-actions' state list
if ($LASTEXITCODE -ne 0) { throw 'Shared CI state unavailable; do not import or replace it' }
if ($prodCiStateAddresses | Select-String -SimpleMatch '["prod"]') { throw 'PROD already tracked: use the dev+prod reconciliation plan instead' }
if (-not ($prodCiStateAddresses -contains 'google_iam_workload_identity_pool.github')) { throw 'Wrong/missing shared CI state' }
$prodStateBackup = Join-Path $prodWork ('ci-state-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.json')
Copy-Item -LiteralPath 'infra/gcp/github-actions/terraform.tfstate' -Destination $prodStateBackup
'environments = ["dev"]' | Set-Content -Encoding ascii "$prodWork/builder-phase.tfvars"
Invoke-ProdTf 'infra/gcp/github-actions' @('plan', '-input=false', '-var-file=../../../local-data/prod-bootstrap-002/builder-phase.tfvars', '-out=prod-bootstrap-002-builder.tfplan')
Invoke-ProdTf 'infra/gcp/github-actions' @('show', 'prod-bootstrap-002-builder.tfplan')
# STOP for review: expected +9/-1, exact addresses in appendix, no DEV resource changes.
Invoke-ProdTf 'infra/gcp/github-actions' @('apply', 'prod-bootstrap-002-builder.tfplan')
```

After partial builder apply, regenerate/review remaining changes; zero means it
is already applied, not a reason to re-import the revoked member. Persisted CI
auto vars stay dev+prod throughout; never change them to dev-only for later use.

Allow propagation, resume approved Delivery and validate a **new, meaningful,
reviewed DEV SHA build and full api_ui_mock acceptance**. A cached image bypasses
the builder and does not prove restricted source/log/registry permissions. The
real checker/tests/docs improvements in this task can supply that reviewed DEV
commit; no empty commit or repeat merge to master is needed. Operator workflow:

```powershell
# After review of actual git diff, on dev only:
git add scripts/gcp/production_readiness.py tests/test_production_bootstrap.py tests/test_production_resume.py docs/PROD_BOOTSTRAP_001.md docs/PROD_BOOTSTRAP_002.md docs/GITHUB_CICD.md docs/tracking/worklog.csv
git commit -m 'Verify production protections and document first release recovery'
if ($LASTEXITCODE -ne 0) { throw 'Commit failed; inspect working tree' }
git push origin dev
if ($LASTEXITCODE -ne 0) { throw 'DEV push failed' }
gh run list --workflow delivery.yml --branch dev --limit 5
```

Choose/watch the run matching the new exact DEV SHA and require actual new Cloud
Build SUCCESS plus full DEV acceptance. Never restore the broad builder role to
make it pass. If this gate fails, diagnose it and stop PROD preparation. This does
not invalidate the older immutable accepted master image; its evidence remains
separately bound to the original master run/attempt/artifact.

### 3. Maintenance window: private cutover and remaining CI bootstrap

**APPROVAL: PROD access interruption, IAP settings and 11 remaining CI creates.**
Pause concurrent delivery while applying grants/cutting access. Re-read actual
PROD traffic and preserve its old image/revision metadata in private operator
storage. Current known old revision is tripse-ai-prod-00001-prh. No fixture/data
copy is part of this procedure. Existing IAP agent object read was denied; if a
write reports an agent problem, stop and inspect service identity provisioning
with authorized IAM tooling, without granting broader operator/project roles.

```powershell
gcloud run services describe tripse-ai-prod --project=tripse-ai --region=europe-central2 --format=json > "$prodWork/prod-before-cutover.json"
if ($LASTEXITCODE -ne 0) { throw 'Cannot snapshot receiving PROD metadata' }
gcloud run services update tripse-ai-prod --project=tripse-ai --region=europe-central2 --iap --invoker-iam-check
if ($LASTEXITCODE -ne 0) { throw 'Stop: inspect private access flags; never open public access' }
gcloud iap settings set infra/gcp/github-actions/production-iap.yaml --project=tripse-ai --resource-type=cloud-run --region=europe-central2 --service=tripse-ai-prod
if ($LASTEXITCODE -ne 0) { throw 'IAP OAuth configuration failed' }
Invoke-ProdTf 'infra/gcp/github-actions' @('plan', '-input=false', '-var-file=prod-bootstrap.tfvars.example', '-out=prod-bootstrap-002.tfplan')
Invoke-ProdTf 'infra/gcp/github-actions' @('show', 'prod-bootstrap-002.tfplan')
# STOP: after builder phase expected 11 PROD creates only; re-review any partial/drift result.
Invoke-ProdTf 'infra/gcp/github-actions' @('apply', 'prod-bootstrap-002.tfplan')
$prodProvider = gcloud iam workload-identity-pools providers describe github-prod --project=tripse-ai --workload-identity-pool=tripse-github --location=global --format=json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'PROD provider unavailable' }
$prodExpectedTrust = (Get-Content -Raw "$prodWork/prod-wif-condition.txt").Trim()
if ($prodProvider.state -cne 'ACTIVE' -or $prodProvider.disabled -or $prodProvider.attributeCondition.Trim() -cne $prodExpectedTrust) { throw 'Unexpected PROD WIF trust/state' }
```

Also review attributeMapping against the planned provider: google.subject=sub,
repository_id, repository_owner_id, environment, repository, event_name, ref,
workflow_ref. Strict CEL pins immutable repository/owner IDs, immutable production
subject, production environment, master ref, approved delivery.yml and push/manual
events. No PR/DEV subject is permitted. No provider/pool copy or key is needed.

If resuming after cutover, read existing IAP settings before setting again; stop
if they contain unreviewed values rather than overwriting them. Reapplying the
same flags/client allowlist is idempotent but still an approved production write.

### 4. Provision independent empty PROD app resources and verify drift

**APPROVAL: 17 PROD app creates and normal Firestore/PITR/GCS/Tasks costs.**

```powershell
Invoke-ProdTf 'infra/gcp/cloud-demo-prod' @('plan', '-input=false', '-out=prod-bootstrap-002.tfplan')
Invoke-ProdTf 'infra/gcp/cloud-demo-prod' @('show', 'prod-bootstrap-002.tfplan')
# STOP: review 17 isolated creates, no DEV/shared API ownership changes or data copy.
Invoke-ProdTf 'infra/gcp/cloud-demo-prod' @('apply', 'prod-bootstrap-002.tfplan')
Invoke-ProdTf 'infra/gcp/cloud-demo-prod' @('output')
gcloud run services get-iam-policy tripse-ai-prod --project=tripse-ai --region=europe-central2
if ($LASTEXITCODE -ne 0) { throw 'Run policy unavailable' }
gcloud iap web get-iam-policy --project=tripse-ai --resource-type=cloud-run --region=europe-central2 --service=tripse-ai-prod
if ($LASTEXITCODE -ne 0) { throw 'IAP policy unavailable' }
foreach ($prodRoot in @('infra/gcp/github-actions', 'infra/gcp/cloud-demo-prod', 'infra/gcp/cloud-demo')) {
    & $prodTf "-chdir=$prodRoot" plan '-input=false' '-detailed-exitcode'
    if ($LASTEXITCODE -ne 0) { throw "Drift or error in $prodRoot; review before promotion" }
}
```

After partial completion Terraform must reconcile the existing PROD state, not
recreate it. Zero-change plans are required after successful applies. Verify:
private uniform/versioned bucket, DB PITR/delete protection, own bounded queue,
task SA; PROD runtime data access only to PROD; human kontakt@protolume.pl editor;
PROD probe reader; task IAP access and token-mint/actAs grants; IAP service-agent
Run invoker. No DEV identities, allUsers, allAuthenticatedUsers, keys or broad
roles. OAuth ID is a public allowlist identifier shared intentionally, not a
secret or an access grant. Do not change it to the IAP redirect/backend URL.

Check current Run flags and IAP settings again. Authorized effective-IAM negative
checks for DEV/build identities remain necessary; the local operator's lack of
signJwt permission is not grounds to widen IAM. Actual PROD WIF/prerequisite
authenticated /health validation will run before deploy under the approved PROD
deployer. Any failure must stop that release, retaining private access.

### 5. Set five variables idempotently, without overwriting differences

**APPROVAL: production GitHub Environment variable writes.** First recheck
protections; do not use a repo-level variable as a production environment fallback.

```powershell
.venv/Scripts/python.exe -m scripts.gcp.production_readiness --variables-file "$prodWork/production.variables.json"
if ($LASTEXITCODE -ne 0) { throw 'Production protections not ready' }
$prodDesired = Get-Content -Raw "$prodWork/production.variables.json" | ConvertFrom-Json
$prodExisting = Invoke-ProdGh "$prodRepo/environments/production/variables?per_page=100"
foreach ($prodEntry in $prodDesired.PSObject.Properties) {
    $prodMatches = @($prodExisting.variables | Where-Object { $_.name -ceq $prodEntry.Name })
    if ($prodMatches.Count -gt 0) {
        if ($prodMatches[0].value -cne $prodEntry.Value) { throw "Different existing production variable: $($prodEntry.Name); review before changing it" }
        continue
    }
    $prodEntry.Value | gh variable set $prodEntry.Name --env production --repo piotrbarabasz/tripse-ai-demo
    if ($LASTEXITCODE -ne 0) { throw 'Variable write failed; re-read partial result before retrying' }
}
.venv/Scripts/python.exe -m scripts.gcp.bootstrap check --environment production --gcp
if ($LASTEXITCODE -ne 0) { throw 'Production variables/provider/accounts not ready' }
.venv/Scripts/python.exe -m scripts.gcp.production_readiness --variables-file "$prodWork/production.variables.json"
if ($LASTEXITCODE -ne 0) { throw 'Production protection check failed' }
```

STDIN preserves JSON quotes on Windows. Existing equal values are skipped;
different values stop the procedure. Retry after partial writes is safe. The five
names are DEPLOY_CONFIG_JSON, EXPECTED_CLOUD_FEATURE_MODE, DEPLOY_SERVICE_ACCOUNT,
WIF_PROVIDER, CI_PROBE_ACCOUNT. No values or credentials are printed by validation.
These checks prove metadata/configuration, not a successful PROD STS exchange.

### 6. Resume accepted master release by separate manual promotion

**Do not rerun only failed PROD or use Re-run failed jobs on run 40550402214.**
GitHub increments GITHUB_RUN_ATTEMPT on re-runs. `release_proof()` reads the source
run's latest run_attempt, fetches jobs for that attempt, and requires all of:

1. record.run_attempt == source run.run_attempt;
2. exact artifact name dev-accepted-SHA-run-attempt;
3. successful DEV job from the same attempt.

A PROD-only retry advances source run to attempt 2 but retains the attempt-1
artifact, so the strict provenance gate rejects it. This diagnosis is derived
from the actual code, documented GitHub attempt semantics and regression tests;
no test rerun was triggered. Do not relax equality/select arbitrary older jobs.

A **new workflow_dispatch promote** has a new run ID; it references source
40550402214/artifact12753973550 without modifying that source run's attempt.
The existing master workflow skips DEV for operation=promote, runs offline CI,
waits for production approval and deploys the accepted digest without a build.
The original overall run may remain failed because only its DEV job is evidence.

Immediately before dispatch, revalidate through the actual proof implementation.
This Python process reads the existing gh operator credential into memory for
API access only; it never prints/persists it or JWT contents:

```powershell
@'
import os, shutil, subprocess
from scripts.gcp.ci import release_proof
r = subprocess.run([shutil.which("gh"), "auth", "token"], capture_output=True)
if r.returncode:
    raise SystemExit("Operator GitHub authentication unavailable; credential output suppressed")
os.environ["GH_TOKEN"] = r.stdout.decode().strip()
os.environ["CI_EVIDENCE_RUN_ID"] = "40550402214"
os.environ["CI_EVIDENCE_ARTIFACT_ID"] = "12753973550"
try:
    p = release_proof("dev", "78919b0f17805529fff7a0cfd289ad460c93403b", "cloud_demo", production=True)
    assert p["image_digest"] == "sha256:b6ac3c9bacd7d565df383452b4130064e3237b8ee4fbadd359a7f38108f9a153"
    print("Original accepted master evidence PASS; digest matches the reviewed release")
finally:
    os.environ.pop("GH_TOKEN", None)
'@ | .venv/Scripts/python.exe -
if ($LASTEXITCODE -ne 0) { throw 'Evidence changed/expired; stop and investigate instead of bypassing provenance' }
$prodRemoteMaster = Invoke-ProdGh "$prodRepo/git/ref/heads/master"
if ($prodRemoteMaster.object.sha -cne $prodSha) { throw 'Master changed; review promotion policy code and ancestry before using newer master' }
# APPROVAL REQUIRED: starts CI and a gated PROD deployment; no build or DEV deployment.
gh workflow run delivery.yml --repo piotrbarabasz/tripse-ai-demo --ref master -f operation=promote -f target_environment=prod -f release_sha=78919b0f17805529fff7a0cfd289ad460c93403b -f evidence_run_id=40550402214 -f evidence_artifact_id=12753973550
if ($LASTEXITCODE -ne 0) { throw 'Dispatch failed; inspect run list before retrying to avoid duplicates' }
gh run list --repo piotrbarabasz/tripse-ai-demo --workflow delivery.yml --branch master --event workflow_dispatch --limit 5
```

Inspect the newly created run's inputs and ID, then explicitly approve its pending
production deployment as piotrbarabasz. No CLI approval bypass is provided. If the
original source run was already rerun or artifact expired, stop: this artifact
will no longer satisfy strict current proof checks. Obtain a newly accepted
master DEV artifact through the normal approved delivery path; do not rebuild
or rewrite evidence merely to get around provenance checks.

### 7. First private PROD acceptance and recovery gates

All must pass before declaring PROD ready:

- Approved Environment, master-only policy/admin bypass false, protected master.
- Zero-drift shared CI/DEV/PROD app plans and successful fresh DEV build after
  builder hardening; no broad builder role or DEV data access to PROD.
- Actual PROD auth through github-prod -> dedicated PROD deployer, no keys.
- Private IAP/Invoker checks, correct OAuth programmatic allowlist and human/
  reader probe/task memberships; anonymous request denied.
- Source-verified exact accepted master digest above, receiving PROD revision
  and EXPECTED_IMAGE_SHA correct, 100% traffic, authenticated read-only smoke PASS.
- prod-accepted artifact recorded with accepted=true, environment=prod, expected
  SHA/digest/config hash and actual receiving revision. Preserve its run/artifact
  IDs for future accepted-release rollback; no new Cloud Build for promotion.
- DEV remains functional. No DEV data copy; mock mode, no LIVE secrets/provider
  keys. Any human functional upload/mock job is a separately approved tiny PROD
  synthetic canary, not a CI-probe write or paid external provider call.

The actual workflow enforces read-only production smoke; do not claim full human
functional/cost/backup/negative IAM acceptance from /health alone. Record runtime
and task outcomes separately. Native service auth may deny an anonymous request
before the container; a container log entry is not required for this gate.

After release, read traffic/flags privately with gcloud and inspect the new
workflow's result/artifact. A redirect to IAP login is an anonymous denial, not
proof that every authorized human has app access. Use the intended human login.

Rollback preserves data/state and private flags. Before the first accepted PROD
release there is no prior accepted PROD evidence artifact. The known old revision
can be restored **only as explicit private failure recovery**, not an automatic
readonly fallback or accepted cloud_demo:

```powershell
# APPROVAL REQUIRED; only after checking no release is writing traffic concurrently.
gcloud run services update tripse-ai-prod --project=tripse-ai --region=europe-central2 --iap --invoker-iam-check
if ($LASTEXITCODE -ne 0) { throw 'Private flags not verified' }
gcloud run services update-traffic tripse-ai-prod --project=tripse-ai --region=europe-central2 --to-revisions=tripse-ai-prod-00001-prh=100
if ($LASTEXITCODE -ne 0) { throw 'Traffic recovery failed; operator incident response required' }
```

Keep private IAM/IAP and independently created data. Do not destroy GCS/Firestore,
restore DEV state, remove prod from shared state/vars, regrant broad builder roles
or reopen public access. If old code cannot process queued tasks, approve pausing
only the PROD queue; never delete it for rollback. Later accepted PROD rollbacks
use prior PROD evidence and the normal protected manual workflow. Existing
coordinator snapshot/restore retains private flags because cutover is required
before deployment; failure restoration must be verified, never called success.

## Implementation and validation ledger

Changed production_readiness.py to verify actual can_admins_bypass=false, with
regressions for enabled/missing bypass. Added release_proof tests for accepted
master evidence in an overall failed run, separate manual promotion preserving
the original attempt, rejected PROD-only retries, and cross-attempt job evidence.
Deployment, proof predicates, Terraform resources, DEV application and workflow
behavior are unchanged. No new ADR is needed: ADR-0011/0012 already cover these
boundaries; neither is marked accepted by this preparation.

Validation results and exact address differences are appended below. Live PROD
acceptance, IAM propagation, builder-restricted fresh build and private cutover
remain operator gates, not completed outcomes. Normal GCP/Actions/retention costs
apply after approval. No measured cost/time estimate is invented.

Sources: [GitHub re-runs](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs),
[GITHUB_RUN_ATTEMPT](https://docs.github.com/en/actions/reference/workflows-and-actions/variables),
[Environment approvals/admin bypass](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments),
[Environment API](https://docs.github.com/en/rest/deployments/environments).

## Validation results (local, no deployment)

- `make test`: **623 passed**, one existing Starlette/AnyIO deprecation warning.
- Focused PROD readiness/resume regressions: **33 passed**.
- All three Terraform roots: fmt/check and validate PASS; refreshed plans and exact address assertions PASS.
- actionlint 1.7.7, Python compileall, `scripts.gcp.ci offline` and `git diff --check`: PASS.
- PowerShell runbook blocks parsed without executing writes; GitHub helper GET/handled-404 behavior checked against live read-only endpoints.
- Local production config and original accepted master artifact: PASS. Live production readiness check correctly FAILS on missing protections and enabled admin bypass.
- CI and DEV application state file SHA-256 values unchanged; PROD app state still absent. No new imports/state writes.

## Exact fresh plan address/action appendix

### Builder phase (+9/-1)

| Address | Action |
|---|---|
| `google_artifact_registry_repository_iam_member.builder_push` | create |
| `google_project_iam_custom_role.builder_bucket_metadata` | create |
| `google_project_iam_custom_role.builder_metadata` | create |
| `google_project_iam_custom_role.builder_registry` | create |
| `google_project_iam_member.builder_metadata` | create |
| `google_project_iam_member.legacy_builder[0]` | delete |
| `google_storage_bucket_iam_member.builder_bucket_metadata["690165197462-europe-central2-cloudbuild-logs"]` | create |
| `google_storage_bucket_iam_member.builder_bucket_metadata["tripse-ai_europe-central2_cloudbuild"]` | create |
| `google_storage_bucket_iam_member.builder_logs` | create |
| `google_storage_bucket_iam_member.builder_source` | create |

### Remaining PROD CI addresses (11 creates, part of current full +20/-1 snapshot)

| Address | Action |
|---|---|
| `google_artifact_registry_repository_iam_member.read["prod"]` | create |
| `google_cloud_run_v2_service_iam_member.deploy["prod"]` | create |
| `google_cloud_run_v2_service_iam_member.probe_invoker["prod"]` | create |
| `google_iam_workload_identity_pool_provider.github["prod"]` | create |
| `google_iap_web_cloud_run_service_iam_member.probe["prod"]` | create |
| `google_project_iam_member.inspect["prod"]` | create |
| `google_service_account.deploy["prod"]` | create |
| `google_service_account.probe["prod"]` | create |
| `google_service_account_iam_member.federation["prod"]` | create |
| `google_service_account_iam_member.runtime["prod"]` | create |
| `google_service_account_iam_member.sign_probe["prod"]` | create |

### Independent PROD app (+17)

| Address | Action |
|---|---|
| `module.cloud_demo.google_cloud_run_v2_service_iam_member.iap_invoker` | create |
| `module.cloud_demo.google_cloud_tasks_queue.jobs` | create |
| `module.cloud_demo.google_cloud_tasks_queue_iam_member.enqueue` | create |
| `module.cloud_demo.google_firestore_database.jobs` | create |
| `module.cloud_demo.google_firestore_field.unindexed["error"]` | create |
| `module.cloud_demo.google_firestore_field.unindexed["notification"]` | create |
| `module.cloud_demo.google_firestore_field.unindexed["request_text"]` | create |
| `module.cloud_demo.google_firestore_field.unindexed["result_json"]` | create |
| `module.cloud_demo.google_firestore_field.unindexed["stage"]` | create |
| `module.cloud_demo.google_iap_web_cloud_run_service_iam_member.members["user:kontakt@protolume.pl"]` | create |
| `module.cloud_demo.google_iap_web_cloud_run_service_iam_member.task` | create |
| `module.cloud_demo.google_project_iam_member.database_runtime` | create |
| `module.cloud_demo.google_service_account.task` | create |
| `module.cloud_demo.google_service_account_iam_member.runtime_act_as` | create |
| `module.cloud_demo.google_service_account_iam_member.task_token` | create |
| `module.cloud_demo.google_storage_bucket.documents` | create |
| `module.cloud_demo.google_storage_bucket_iam_member.runtime` | create |
