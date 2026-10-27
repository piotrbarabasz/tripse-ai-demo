# TRIPSE-PROD-BOOTSTRAP-001: operator-ready production preparation

**2026-10-27 continuation: [PROD-BOOTSTRAP-002](PROD_BOOTSTRAP_002.md) is the
current execution/resume procedure.** The merge already happened: master is
78919b0f17805529fff7a0cfd289ad460c93403b. Run 40550402214 accepted DEV artifact
12753973550, then failed PROD before authentication because all five production
variables were absent. GitHub auto-created production without protections.
Fresh state/resource audits and plans are recorded in the continuation; the
counts below are historical preparation results, not evidence of an apply.
Do not repeat the old PR/merge step or rerun that failed PROD job: its attempt
would advance beyond the accepted artifact. Use the documented separate manual
promotion after bootstrap and explicit approval, preserving strict proof checks.

Prepared 2026-10-27 on clean dev HEAD
`cf94e20a7f53c2d7674d83319704a54e2a92889e`. No apply, GitHub settings write, IAP
enablement, build, deployment, workflow rerun, commit, push or master merge was
performed. Read-only cloud/API checks, local configuration/state preparation,
an exact IAM-member **state import only**, and Terraform plans were performed.

## Verified DEV acceptance and promotion boundary

Run **40523770207** succeeded on **dev**, attempt 1; immutable artifact
**12741609814** is unexpired and contains accepted api_ui_mock cloud_demo proof:

- SHA: cf94e20a7f53c2d7674d83319704a54e2a92889e
- Digest: sha256:8a939ba163b08cb8966e914c1e63371611eb1a59ff116638967c015ea15e36b2
- Source build: c93ce5a8-ef0a-48be-83be-28f4ab211fd1; source_verified=true
- DEV revision: tripse-ai-dev-00006-zk4, 100% traffic, cloud_demo/mock, direct IAP

Artifact metadata was read, not application documents. No DEV object/database
data or application source archive was copied to PROD. The shared image is the
intended release mechanism; PROD must have its own app configuration/data.

**This dev-branch artifact cannot authorize PROD.** At this initial preparation master was
`2c8e79b7b4c521eaf15ce2cf17e09f8b3b830171`. Merge produces a new exact master
commit: CI builds/reuses that SHA, accepts it on DEV, freezes its digest/proof,
then waits for production approval. Production deploys that same digest without
building. Later dev changes cannot substitute their image. Existing code validates
repository/workflow/run/attempt/artifact/job/source verification/mode and master
ancestry; tests preserve rejection of dev/fork/PR evidence. Do not pass artifact
12741609814 to a manual promotion or relabel its source_ref as master.

## Readiness audit: exists, missing, disruption

| Area | Observed state / decision |
|---|---|
| PROD Run | Existing tripse-ai-prod-00001-prh, 100% traffic, image SHA be798fedc1970cdd96ce44bf6c0fae37fe4fce38; ownership/container/secret-reference checks PASS |
| Current access | iapEnabled=false, invokerIamDisabled=true, no service IAM bindings; this is the existing public readonly preview, not ready private PROD |
| PROD URL | https://tripse-ai-prod-64ctpggq3a-lm.a.run.app (confirmed Run URI) |
| PROD runtime | tripse-ai-prod@tripse-ai.iam.gserviceaccount.com already exists; keep it |
| PROD data | Bucket, named Firestore DB, queue and task SA absent in permitted project listings; new state starts empty |
| PROD CI | Provider github-prod and dedicated deploy/probe SAs absent; add in existing shared pool/state |
| GitHub production | Environment absent; no reviewers or deployment branch policy exist |
| master | Branch protection API: Branch not protected; repository rulesets empty |
| GitHub plan | Public repository, admin operator access; required reviewers are supported for public repositories |
| Approval selection | User explicitly selected piotrbarabasz (immutable user ID 72949549), self-review allowed. This is a human pause, not independent two-person approval |
| Builder isolation | Existing shared builder has project-wide roles/cloudbuild.builds.builder, including object read/write across future PROD buckets. DEV CI can actAs this builder: must harden before PROD receives data |
| Default build identity | API reports compute default SA; no project role for it found. Legacy Cloud Build SA retains its historical role, is not current default or a CI actAs target; not changed by this plan. Managed service agents remain trusted project control-plane identities |

Disruption to approve: closing public preview requires users to log in; legacy
preview-only routes may differ from full cloud_demo. There can be downtime between
enabling private IAP/Invoker enforcement and completing IAP-agent/human/probe IAM.
Builder grant replacement intentionally reduces authority and may affect DEV
builds: pause concurrent delivery and require a fresh DEV build/acceptance after
hardening. Data, runtime/task identities, buckets, DBs and queues on DEV are not
replaced. No production user-data migration is needed from the fixture-only old
preview, and no DEV data migration is permitted.

## Prepared artifacts and exact plan results

| State/root | Saved plan | Reviewed result |
|---|---|---|
| Existing shared CI: infra/gcp/github-actions/terraform.tfstate | prod-bootstrap.tfplan | **20 create, 0 update, 1 delete**; no existing ["dev"] address changes |
| New PROD app: infra/gcp/cloud-demo-prod/terraform.tfstate (not yet created/applied) | prod-app.tfplan | **17 create, 0 update, 0 delete** |
| Existing DEV app: infra/gcp/cloud-demo/terraform.tfstate | prod-bootstrap-dev-baseline.tfplan | **0 changes**; state file checksum unchanged |

Human-safe address/action summaries are in local-data/prod-bootstrap-001/
shared-ci-plan-summary.json, prod-app-plan-summary.json and
dev-baseline-plan-summary.json. Binary plans stay ignored/private; inspect with
Terraform show, never commit state or plans. Do not apply a stale saved plan after
new changes; regenerate and review if anything drifts. No -target or destroy.

The shared CI root still owns one pool and the original DEV provider/resources.
Its existing ignored bootstrap.auto.tfvars now contains [dev,prod]; the tracked
prod-bootstrap.tfvars.example records this required superset. Keep BOTH on all
future plans. This is not a second CI state/pool. Original CI state/vars were
backed up under local-data/prod-bootstrap-001/ci_state.before and ci_vars.before;
original lineage and resource addresses were preserved.

For a reviewable exact removal, the existing builder role member was imported
locally at google_project_iam_member.legacy_builder[0], using import-only
retain_legacy_builder_grant=true and environments=[dev]. The first import using
the expanded environment set failed output evaluation with Invalid index and
left state byte-identical; retry with the import-only dev set succeeded. Import
does not grant/revoke IAM. Final plan uses default retain=false and deletes ONLY
the one old builder project-role member. Never persist retain=true or apply an
import-only configuration. No other role member or builder identity is deleted.

Before any apply, local preparation can be abandoned by removing just that imported
address with terraform state rm and restoring the reviewed dev-only variable set;
that forgets tracking, not IAM. After any apply, never restore old state files or
remove prod from the environment set as a rollback strategy.

### Isolated application state

New root infra/gcp/cloud-demo-prod uses the existing cloud-demo module with fixed
project tripse-ai, project number 690165197462 and environment prod. It does not
copy DEV state. manage_project_apis=false leaves shared project API ownership in
the original DEV app state; default true preserves its resource addresses.

New resources: private/versioned/soft-delete GCS, named Firestore with PITR/delete
protection and five index exclusions, bounded Tasks queue, dedicated task SA,
runtime grants, task actAs/token-mint bindings and service-scoped IAP/Invoker
bindings. Runtime database access is conditioned only on tripse-ai-prod. No new
LIVE provider secret or broad role is granted. Bucket/DB/queue prevent_destroy
remain; never use a DEV backend/state with the PROD root.

### Shared builder hardening is required for data separation

The 20 CI creations consist of 11 PROD CI resources and nine scoped builder IAM
definitions/bindings. Exact builder identity remains tripse-ai-build; it gets:

- project metadata/service use/log write only;
- source object reads and source/log bucket metadata on the two build buckets;
- objectUser only on the existing build-log bucket;
- custom registry push/read on the existing image repository, without delete.

It gets no PROD document bucket, database, task identity or Run authority. Removing
its old project build role removes its project-wide object access. Existing DEV
CI project metadata/build-submit roles are retained; actAs remains DEV runtime/
the shared restricted builder only. A new PROD preflight guard rejects unreviewed
project grants for known DEV builder/runtime/probe/task/deployer principals; only
the planned metadata/submit roles and database-conditioned DEV runtime grant are
accepted. Actual inherited/group/organization deny resolution and negative IAM
drills require authorized operator validation; plans alone are not that drill.

Build client now explicitly validates and selects the existing log bucket as well
as source staging. This avoids requiring builder bucket creation for automatic
regional logs. SDK async/status-only polling, recipe, builder, SHA/digest and source
proof are unchanged. Legacy make gcp-setup no longer reintroduces the broad
project builder grant; it accepts reviewed scoped provisioning or fails closed.

## Prepared GitHub configuration (local, no remote writes)

Ignored directory local-data/prod-bootstrap-001 contains actual validated values:

- production.json and production.variables.json: complete strict cloud_demo/mock,
  private configuration; no placeholders, credentials or secret payloads.
- production-environment.json: required reviewer piotrbarabasz, self-review allowed,
  custom deployment branch policies.
- production-branch.json: exactly branch master.
- master-protection.json: strict PR check Tests and offline contracts pinned to
  observed GitHub Actions App 15368; PR path with zero independent reviews (single
  operator), administrator enforcement, no force push/deletion.
- production-iap.yaml: reviewed programmatic client allowlist value only.

Reproducible nonsecret source versions are also in infra/gcp/github-actions/
production.cloud_demo.json, production-environment.json, production-branch.json,
master-protection.json and production-iap.yaml. These contain no secret or
placeholder. To regenerate the variable bundle in a fresh private output path:

```powershell
New-Item -ItemType Directory -Force local-data/prod-bootstrap-001 | Out-Null
.venv/Scripts/python.exe -m scripts.gcp.bootstrap prepare --environment production --mode cloud_demo --input infra/gcp/github-actions/production.cloud_demo.json --output local-data/prod-bootstrap-001/production.variables.json
```

The helper refuses an existing output: review before choosing another name.
Settings/IAP commands below can use the corresponding reviewed tracked files if
private copies are absent. State backups/plans must be restored from their secure
operator storage or regenerated; never fabricate/clone a DEV app state for PROD.

PROD values: own Run URI, tripse-ai-tripse-ai-prod-documents, database/queue
tripse-ai-prod, own runtime/task/deploy/probe SAs. Human editor is
kontakt@protolume.pl (the accepted DEV human operator); reader is ONLY the PROD CI
probe. No DEV service account is in PROD app access lists or target data bindings.

Prepared OAuth programmatic client ID is the existing reviewed
690165197462-653cuslrjb8nusq758avecpau885tj5r.apps.googleusercontent.com. This
nonsecret client ID is shared, not a secret or authorization grant. IAP access,
task identity, app assertion audience and backend URI remain service-specific.
Do not use the IAP redirect URL as the backend/programmatic audience or copy an
OAuth client secret/token. If a separate OAuth client is required by policy,
create/review it manually and regenerate production variables before applying
settings; no fabricated placeholder is used in the prepared bundle.

## Staged operator execution — no stage has been applied

All settings/IAM/IAP/deploy commands below require the operator's deliberate review
and approval. No automatic pipeline or Terraform apply was initiated here.

### 0. Review plans and configuration

```powershell
$tfCommand = Get-Command terraform -ErrorAction SilentlyContinue
$prodBootstrapTf = if ($tfCommand) { $tfCommand.Source } else { Join-Path $env:TEMP 'tripse-cloud-parity-tools/terraform.exe' }
if (-not (Test-Path -LiteralPath $prodBootstrapTf)) { throw 'Install the reviewed Terraform CLI first' }
& $prodBootstrapTf '-chdir=infra/gcp/github-actions' show 'prod-bootstrap.tfplan'
& $prodBootstrapTf '-chdir=infra/gcp/cloud-demo-prod' show 'prod-app.tfplan'
& $prodBootstrapTf '-chdir=infra/gcp/cloud-demo' show 'prod-bootstrap-dev-baseline.tfplan'
.venv/Scripts/python.exe -m scripts.gcp.production_readiness --variables-file local-data/prod-bootstrap-001/production.variables.json
```

The last check currently fails because production is absent; it validates local
variables first without printing values. Review all five variables and human
membership. This is not an instruction to run an operator token as CI.

### 1. Configure GitHub protections before any master release

Review JSON first. These explicit operator commands CREATE/UPDATE settings:

```powershell
gh api --method PUT repos/piotrbarabasz/tripse-ai-demo/environments/production --input local-data/prod-bootstrap-001/production-environment.json
if ($LASTEXITCODE -ne 0) { throw 'Production Environment setup failed' }
gh api --method POST repos/piotrbarabasz/tripse-ai-demo/environments/production/deployment-branch-policies --input local-data/prod-bootstrap-001/production-branch.json
if ($LASTEXITCODE -ne 0) { throw 'Master-only deployment policy failed' }
gh api --method PUT repos/piotrbarabasz/tripse-ai-demo/branches/master/protection --input local-data/prod-bootstrap-001/master-protection.json
if ($LASTEXITCODE -ne 0) { throw 'Master protection failed' }
```

Do not blindly repeat create/update if settings now exist: re-read/review them and
merge intent rather than overwriting someone else's changes. In Settings ->
Environments -> production, disable administrator bypass. BOOTSTRAP-002 observed
can_admins_bypass in live GET metadata and now requires explicit false in the
CLI checker; use the UI to change it and re-read the API to verify.
Confirm reviewer piotrbarabasz, self-review allowed and only master (not wildcard/
tag). Public repo supports required reviewers. This is a single-owner human gate;
it does not claim independent approval. Verify the exact direct PR CI check name
when the first PR runs; do not drop required CI to unblock a name mismatch.

### 2. Publish reviewed code on dev; validate explicit log selection

Commit reviewed code/new files on dev, then the operator may push dev and watch
its normal CI/DEV build. This requires approval for ordinary build/runtime costs;
Codex did not do it. Do this before changing the builder's live authority so its
new explicit log destination is in the delivery code. Do not merge master yet.

### 3. Maintenance window: privatize the existing preview and apply CI plan

Pause concurrent Delivery operations (UI/approved workflow disable). Keep the
known old PROD revision/image. **Cutover commands below change availability**:

```powershell
gcloud run services update tripse-ai-prod --region=europe-central2 --project=tripse-ai --iap --invoker-iam-check
if ($LASTEXITCODE -ne 0) { throw 'Stop: verify private access flags before proceeding' }
gcloud iap settings set local-data/prod-bootstrap-001/production-iap.yaml --resource-type=cloud-run --region=europe-central2 --service=tripse-ai-prod --project=tripse-ai
if ($LASTEXITCODE -ne 0) { throw 'Stop: review IAP programmatic configuration' }
& $prodBootstrapTf '-chdir=infra/gcp/github-actions' apply 'prod-bootstrap.tfplan'
if ($LASTEXITCODE -ne 0) { throw 'Stop: inspect partial IAM result; never restore broad roles blindly' }
```

This closes anonymous access to the old fixture preview; do not re-open it as a
fallback. IAP-agent Run invoker and human access are applied by the app plan next,
so an interim denial/downtime is expected. The CI plan replaces builder permissions
and creates PROD identities/provider; it does not deploy any image or copy data.
Read back the new provider before using it:

```powershell
$expectedProdTrust = (Get-Content -Raw local-data/prod-bootstrap-001/prod-wif-condition.txt).Trim()
$actualProdTrust = gcloud iam workload-identity-pools providers describe github-prod --workload-identity-pool=tripse-github --location=global --project=tripse-ai --format='value(attributeCondition)'
if ($LASTEXITCODE -ne 0 -or $actualProdTrust.Trim() -ne $expectedProdTrust) { throw 'PROD WIF trust differs from the reviewed plan' }
```

If live state changed since preparation, regenerate/review the plan first:

```powershell
& $prodBootstrapTf '-chdir=infra/gcp/github-actions' plan '-input=false' '-var-file=prod-bootstrap.tfvars.example' '-out=prod-bootstrap.tfplan'
```

Never remove dev from bootstrap.auto.tfvars or use -target. If recreating this
workspace, import the legacy exact member only if not already tracked, using
import-only retain=true and environments=[dev]; then plan default retain=false.
Avoid PowerShell quote pitfalls by passing import arguments via Python subprocess
argv or a private import-only tfvars file; the prepared workspace already did it.

### 4. Prove DEV still works after builder hardening

Allow IAM propagation, resume Delivery and run an explicitly approved new DEV
build/acceptance. Use a new reviewed dev commit (a reused SHA image does not exercise
builder source/log/registry permissions). Inspect same builder identity, explicit
source/log buckets, successful status, exact-source proof and full DEV acceptance.
Do not proceed to storing PROD data if this fails. Diagnose the specific safe
operation/Google category; do not restore project Storage Admin/Editor/build role.

### 5. Apply empty PROD app resources and verify private IAP membership

```powershell
& $prodBootstrapTf '-chdir=infra/gcp/cloud-demo-prod' plan '-input=false' '-out=prod-app.tfplan'
if ($LASTEXITCODE -ne 0) { throw 'Review refreshed PROD app plan' }
& $prodBootstrapTf '-chdir=infra/gcp/cloud-demo-prod' show 'prod-app.tfplan'
# Stop unless the operator approves exactly 17 isolated creates and no DEV/API changes.
& $prodBootstrapTf '-chdir=infra/gcp/cloud-demo-prod' apply 'prod-app.tfplan'
if ($LASTEXITCODE -ne 0) { throw 'Stop: inspect PROD bootstrap before release' }
& $prodBootstrapTf '-chdir=infra/gcp/cloud-demo-prod' output
gcloud iap web get-iam-policy --resource-type=cloud-run --region=europe-central2 --service=tripse-ai-prod --project=tripse-ai
gcloud run services get-iam-policy tripse-ai-prod --region=europe-central2 --project=tripse-ai
```

Review exact human/probe/task membership and IAP service agent invoker; no allUsers
or DEV identity. Verify private versioned/soft-delete bucket, named DB PITR/delete
protection, own queue/SA, runtime DB condition, task actAs and scoped token minting.
Perform negative access review for DEV principals (including builder/default build
identities) using authorized IAM tooling; no broad grant to enable diagnostics.
No object/collection is copied from DEV. APIs remain owned by original DEV state.
User-managed backups, restore drills, cost alerts/retention and approved synthetic
PROD canary remain operational work; mock mode does not make infrastructure free.

### 6. Set production variables and verify approval protections

Require empty variables for the first write; never silently overwrite existing
values. These values are nonsecret but should not be dumped into logs:

```powershell
$existing = gh api repos/piotrbarabasz/tripse-ai-demo/environments/production/variables | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $existing.total_count -ne 0) { throw 'Review existing production variables before writing' }
$prodVariables = Get-Content -Raw local-data/prod-bootstrap-001/production.variables.json | ConvertFrom-Json
foreach ($entry in $prodVariables.PSObject.Properties) {
    $entry.Value | gh variable set $entry.Name --env production --repo piotrbarabasz/tripse-ai-demo
    if ($LASTEXITCODE -ne 0) { throw 'Variable write failed; review partial configuration' }
}
.venv/Scripts/python.exe -m scripts.gcp.bootstrap check --environment production --gcp
if ($LASTEXITCODE -ne 0) { throw 'Production config/identity metadata not ready' }
.venv/Scripts/python.exe -m scripts.gcp.production_readiness --variables-file local-data/prod-bootstrap-001/production.variables.json
if ($LASTEXITCODE -ne 0) { throw 'Production approval/branch protection not ready' }
```

STDIN preserves JSON quotes in Windows PowerShell; no secrets/values are printed.
The readiness helper is read-only and operator-invoked, not a runner admin-permission
dependency. API checks must PASS, including explicit administrator bypass false.
Signed probe access/prerequisites will be checked under actual PROD WIF by delivery.

### 7. PR dev -> master, exact master DEV acceptance, then human PROD approval

```powershell
gh pr create --base master --head dev --title 'Bootstrap reviewed private production release' --body 'Review PROD plans, isolation and approval gates. Production uses the exact accepted master DEV digest without rebuilding.'
```

Operator reviews/merges the protected PR when ready. No merge is performed here.
The master run first tests/builds/accepts its **own** SHA on DEV. Before approving
Actions -> Delivery -> Review deployments, inspect master evidence run/artifact
ID, digest, cloud_demo/mock, source proof and DEV acceptance. Approval by
piotrbarabasz then releases production credentials; no PROD build is executed.
Read-only PROD smoke must confirm exact digest/SHA, receiving revision, 100%
traffic, private routes and anonymous denial. Human editor can then perform an
explicitly approved tiny synthetic PROD mock job/upload/read/delete-retention
acceptance using independent data; PROD CI probe remains read-only. Do not call
this accepted PROD merely because Terraform or /health passed.

## Rollback and recovery (private only)

- Before any apply: keep saved plan/backup; abandon local state import/config
  changes only with a current manifest check. No remote rollback is needed yet.
- After resource apply: do not destroy/recreate databases/buckets, restore DEV
  state, remove prod from CI config, regrant broad builder IAM or reopen public
  Run. Fix a reviewed specific grant/policy if needed; keep data intact.
- During cutover/first release there is no historical accepted PROD artifact.
  Coordinator failure restoration retains private IAP/Invoker and marks failure.
  Operator may restore old known revision traffic as a temporary private fixture
  surface; this is not cloud_demo acceptance or a silent mode fallback:

```powershell
gcloud run services update tripse-ai-prod --region=europe-central2 --project=tripse-ai --iap --invoker-iam-check
gcloud run services update-traffic tripse-ai-prod --region=europe-central2 --project=tripse-ai --to-revisions=tripse-ai-prod-00001-prh=100
```

  Inspect health privately and preserve the recorded image; request explicit
  approval for these writes. If tasks exist and old code cannot handle them,
  pause only the PROD queue after review, never delete its data/queue to rollback.
- After an accepted PROD release exists, use existing manual rollback from master
  with the prior PROD evidence run/artifact/SHA and production approval. Reuse its
  digest; no rebuild/data restore. Coordinate manual traffic writes with Actions
  concurrency locks and follow [GITHUB_CICD recovery](GITHUB_CICD.md).

## Local verification results

- `make test`: **618 passed**, one existing Starlette/AnyIO deprecation warning.
- Terraform fmt/check and validate: PASS for shared CI, existing DEV app and new
  PROD app roots; workflow actionlint 1.7.7 and Python compileall: PASS.
- Three actual refreshed Terraform plans: CI +20/-1, PROD app +17, DEV app zero
  changes. The only deletion is the imported legacy builder IAM member; existing
  DEV CI resource addresses are unchanged. DEV app state checksum is unchanged.
- Local strict production variables validation: PASS. Read-only GitHub readiness
  check correctly blocks because production is absent; remote protection changes,
  PROD WIF exchange and PROD acceptance have not been tested or performed.
- `git diff --check`: PASS. Reviewable code/docs patch is saved privately at
  `local-data/TRIPSE-PROD-BOOTSTRAP-001.patch`; state/plans/backups are excluded.

## Costs, limitations and resume point

Applies create Firestore/PITR, versioned GCS, queue and IAM; subsequent builds,
runtime and synthetic acceptance incur normal GCP/Actions/registry/log retention
costs. No money/time estimate was invented. These are reviewed plans, not proven
live builder hardening, WIF PROD auth, IAP PROD probe or application acceptance.
Inherited/group IAM and actual propagation/negative-access drills remain gates.

Next session: start with this runbook, actual git status, the three plan summaries
and current state manifests. Existing CI state includes the imported legacy member;
do not import it again or create another pool. PROD app root is unapplied; DEV data
state was verified unchanged. Current accepted dev artifact is not master proof.
Check live protections before any merge and require operator approval for every
mutation stage. Preserve private config bundles and avoid logging tokens/secrets.

References: [GitHub environment protection](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments),
[branch protection API](https://docs.github.com/en/rest/branches/branch-protection),
[user-managed build identities](https://docs.cloud.google.com/build/docs/securing-builds/configure-user-specified-service-accounts),
[IAP setup](https://docs.cloud.google.com/run/docs/securing/identity-aware-proxy-cloud-run).
