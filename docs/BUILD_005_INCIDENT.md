# TRIPSE-CICD-BUILD-005: restricted CI source staging

Current state - 2026-10-28: private DEV and PROD `cloud_demo` delivery is
accepted in [master run 40614584902](RELEASE_2026_10_28.md). That evidence record
includes artifact IDs, isolated infrastructure, operator-verified IAM/Organization
Policy and state adoption, and remaining acceptance limits. Earlier dated findings
below are historical snapshots, superseded for rollout status. Do not replay
completed bootstrap/import/cutover steps or use old saved plans. Human login,
restore/isolation drills and real customer-data readiness remain unverified.

Follow-up: DEV run 40523770207 at cf94e20a7f53c2d7674d83319704a54e2a92889e
successfully completed deployment and api_ui_mock acceptance; artifact 12741609814
matches the serving digest. This closes the observed DEV submission/acceptance
blocker, without recovering the lost historical stderr. At that date, the next stage was
[PROD bootstrap preparation](PROD_BOOTSTRAP_001.md); no PROD rollout is implied.

2026-10-27, Europe/Warsaw. DEV only; project tripse-ai (690165197462),
europe-central2. Starting clean dev HEAD and failed run source:
`200f7f73351458d9bd182d7b971283e1573114c6`.
[Run 40509727837](https://github.com/piotrbarabasz/tripse-ai-demo/actions/runs/40509727837),
attempt 1, DEV job 122209326773, failed at `2026-10-27T13:24:29Z`:

```text
stage=build.submit; operation=gcloud builds submit; exit 1
```

## Diagnosis and limits of proof

**CONFIRMED contract defect:** the code relied on implicit source staging. The
audited Google SDK first GETs the regional staging bucket, then LISTs buckets
in the project to verify ownership, **before uploading or creating a build**.
The deployed CI inspect role grants buckets.get/getIamPolicy; its build role and
bucket objectCreator/objectViewer bindings do not grant project buckets.list.
The assumed object-only staging contract therefore omitted an actual CLI dependency.
H1's missing buckets.get is contradicted by the actual custom inspect role.

**PROBABLE cause of this incident, not direct historical proof:** the implicit
ownership LIST fails for the restricted CI deployer. The historical stderr was
discarded, the runner SDK version was not logged, and Policy Troubleshooter plus
existing-authority CI impersonation both returned 403 to the local operator.
Exact effective CI access (including group inheritance/deny policies) and the
historical Google error cannot be certified from operator reads alone. No IAM
grant was made to bypass these limits. Audit records available around the failure
show successful GenerateAccessToken and SignJwt, but no Storage/Build denial.
Missing audit records do not prove the absence of those calls.

The correction removes the implicit LIST dependency rather than granting a wider
project role: explicitly select the **same existing source bucket**, and first
validate its API-reported owner project number, exact name and region. This is
a permanent least-privilege staging correction, not a catch-and-continue workaround.
Live resolution still requires an approved new DEV run. The task remains OPEN.

## Submission, identities and data flow

| Responsibility | Identity / resource |
|---|---|
| CLI initiator, source metadata check and archive upload | tripse-ai-dev-ci-deploy@tripse-ai.iam.gserviceaccount.com via GitHub WIF |
| Build execution, source read, image push and build log writes | tripse-ai-build@tripse-ai.iam.gserviceaccount.com (unchanged custom builder) |
| Cloud Build managed orchestration | service-690165197462@gcp-sa-cloudbuild.iam.gserviceaccount.com |
| Staged source | gs://tripse-ai_europe-central2_cloudbuild/source/<unique>.tgz |
| Regional build log bucket | gs://690165197462-europe-central2-cloudbuild-logs |
| Image repository | europe-central2-docker.pkg.dev/tripse-ai/tripse-ai; image tripse-ai, full SHA tag |
| Private runtime | tripse-ai-dev; runtime tripse-ai-dev@tripse-ai.iam.gserviceaccount.com |

The application document bucket/Firestore/Tasks are separate resources/states and
are not build staging. Neither the local operator nor the IAP probe is the build
initiator or builder. An operator's successful metadata request is not a CI test.

1. `source_files` reads `git archive <selected SHA>`, permits only Dockerfile,
   runtime requirements, ignore files, app and selected synthetic fixtures; rejects
   symlinks/traversal and credential/data patterns. CI requires a clean checkout.
2. The script writes those bytes to an isolated temporary directory, injects
   app/_build_version.txt for the selected SHA, and submits that directory. No
   workspace credentials or ignored user data are copied. gcloud applies the
   committed .gcloudignore when producing its uploaded tarball.
3. Implicit old source selection was the project/region default bucket. New code
   directly reads the project number and `storage buckets describe --raw`, then
   passes `--gcs-source-staging-dir` for the same bucket/source prefix.
4. The caller uploads under its CI credentials. Cloud Build executes under the
   explicitly selected builder; its existing project build role supplies source
   object reads, registry push and log-write permissions. Roles/serviceAgent is
   a separate orchestration identity, not a replacement builder.
5. After build completion, digest lookup and `build_proof.verify` validate exact
   builder/recipe, result tag/digest and every generation-pinned archived source
   byte against the committed context plus baked SHA. This check is unchanged.
   No tag overwrite/rebuild-on-PROD or latest tag is introduced.

Effective command shape (placeholders are reviewed nonsecret values, not secrets):

```text
gcloud builds submit <isolated-committed-context>
  --tag=europe-central2-docker.pkg.dev/tripse-ai/tripse-ai/tripse-ai:<full-SHA>
  --region=europe-central2
  --service-account=projects/tripse-ai/serviceAccounts/tripse-ai-build@tripse-ai.iam.gserviceaccount.com
  --gcs-source-staging-dir=gs://tripse-ai_europe-central2_cloudbuild/source
  --default-buckets-behavior=regional-user-owned-bucket
  --timeout=600 --suppress-logs --async --format=json --project=tripse-ai --quiet
```

All old flags are supported in the audited SDK/reference. Timeout is seconds.
`--suppress-logs` suppresses output, but the audited synchronous SDK still creates
a GCS log tailer and performs HTTP reads even with out=None. Configured CI has
no exact log-bucket objectViewer grant. This is a separate confirmed SDK client
dependency that can fail **after** build creation; it does not explain the absence
of a historical build record. The correction uses `--async --format=json`, validates
the returned UUID and polls `builds describe` with existing builds.get authority.
Only SUCCESS permits digest/provenance checks; terminal failure/unknown status
blocks. After 900 seconds, fail without cancelling or resubmitting; the operator
must inspect that existing build. No log-read permission is added and log creation
is unchanged. Regional default behavior selects the user-owned regional log
bucket; explicit source staging overrides only the source choice. `--tag` generates
one gcb-internal Docker step (`docker build --network cloudbuild --no-cache -t ... .`),
matching the existing proof validator. Kaniko/property changes remain unreviewed
and would fail proof; no such option is enabled by this patch.

## Independent hypothesis review

| Hypothesis | Verified evidence / outcome |
|---|---|
| H1 missing source buckets.get | Actual project inspect role includes buckets.get and getIamPolicy. Object roles alone would not suffice, but they are not CI's only grants. H1 as stated is not supported. |
| H2 staging discovery/upload | Google SDK 590.0.1 `submit_util.SetSource`: omitted staging dir sets default_gcs_source=true; StorageClient.CreateBucketIfNotExists GETs, then LISTs(project,prefix) to prevent squatting. Configured CI grants omit LIST. Both source/log buckets exist in europe-central2, uniform access, no retention policy; source owner projectNumber=690165197462. Public-access prevention is inherited, not proof of public access. Existing IAM is not changed. Upload/organization deny or requester policy errors still require actual CI evidence. |
| H3 builder identity | Exact custom builder exists in old successful build records and currently has roles/cloudbuild.builds.builder. Expanded role includes source object read, registry upload and logging write. Service agent has roles/cloudbuild.serviceAgent. CI has builder actAs via the declarative binding and advanced past its actual actAs check. No evidence supports switching accounts or adding broad roles. |
| H4 custom builder logs | Last successful build 9c54ce2d-d425-44cd-9328-a765affb8bad at 2026-10-26T09:39:59Z used the same builder, regional log bucket, LEGACY logging and REGIONAL_USER_OWNED_BUCKET. The bucket still exists and builder's role includes log/GCS writes. This rejects an inherently invalid flag combination; current hidden validation/policy errors are not ruled out without the error. |
| H5 CLI/API/source/quotas | Local Google-distributed SDK 590.0.1 source and official CLI reference support the flags and reviewed Docker recipe. Failed runner version cannot be recovered from available log lines; next build prints only the validated SDK version. No regional build after 26 Oct was returned. No actual CreateBuild error or quota denial was retrieved. Local source allowlist/provenance regressions remain active. No build request was submitted in this investigation. |

## Diagnostic ledger and commands already exercised

- GitHub API metadata and narrowly filtered failed logs: run/SHA/stage above
  confirmed; no private raw output logged. Repository started clean on dev.
- Read exact source and log bucket metadata/IAM, project roles, expanded custom
  inspect/build and builder roles, project parent and organization policy. CI has
  two custom project roles and exact source object grants; no direct CI/public
  organization grant found. Group membership/deny policy evaluation remains open.
- Source bucket raw JSON API GET confirmed projectNumber 690165197462 and region.
  gcloud's standardized describe output omits that owner field, so the new helper
  deliberately uses the documented `--raw` flag. Wrong/missing owner fails closed.
- Read regional build records: latest success 9c54ce2d... dated 26 Oct; no newly
  accepted build from the failed 27 Oct attempt.
- Audit query for CI principal between 13:18 and 13:28 UTC: only successful
  GenerateAccessToken and SignJwt returned, no failed Storage/CreateBuild event.
- Policy Troubleshooter accessTuple queries for exact CI buckets.get/list: HTTP
  403 to the operator; no API enablement/IAM changes attempted.
- Existing-authority generateAccessToken for exact CI identity: HTTP 403; stopped.
  No CI token obtained and no CI Storage test performed. Operator credentials
  were captured in memory only and never used to submit a build.
- Primary SDK code inspected locally: Google-distributed SDK 590.0.1,
  lib/googlecloudsdk/command_lib/builds/submit_util.py (SetSource, Build) and
  lib/googlecloudsdk/api_lib/storage/storage_api.py (CreateBucketIfNotExists).
  Default discovery LIST occurs before staging Upload and Cloud Build Create.
  api_lib/cloudbuild/logs.py also confirms synchronous Stream creates/polls the
  GCS tailer with out=None; suppressing output alone is not a no-log-read contract.
- Actual new `build_source_staging` helper executed read-only as operator: PASS
  for owner/name/region; actual local version parser returns 590.0.1. Not a proof
  of CI authorization. No archive uploaded or build initiated.
- Existing CI Terraform state planned without source/IAM changes. First native
  PowerShell argument attempt failed with “Too many command line arguments”;
  retry using a literal Python subprocess argv succeeded: **0 changes**, plan
  complete. No apply. State/backend preserved; environments remains dev only.

## Code correction and safe one-cycle fallback evidence

- `deployment.build_source_staging`: read existing exact project/bucket metadata;
  enforce name/owner/region before upload. Return the canonical existing prefix.
- `deployment.build`: retain registry reuse/actAs/source/proof behavior; pass the
  explicit staging flag; log only a validated numeric SDK version. Submit once
  asynchronously, validate UUID, wait on Build status metadata, then verify digest.
  No bucket list, bucket create, new builder, log-object read or widened role is
  introduced. No background failure is mistaken for a successful async submission.
- `run`/`CommandError`: for submit (and new staging-metadata failures), classify
  stderr internally into fixed Google/RPC/HTTP categories, static phase labels
  and a fixed set of recognized permission names. No original text, credential
  paths, flags, bearer headers, stdout or stderr fragments are returned/logged.
  Recognition of a permission name is not automatically a proven denied grant.
  CI summary includes the same safe fields; unknown errors stay UNCLASSIFIED.
- Tests model audited default-vs-explicit SDK behavior under restricted CI:
  implicit staging raises buckets.list denial; new submission uses verified explicit
  bucket without LIST. Foreign/missing metadata blocks before submit. These mocks
  do not emulate a real Google server or replace required live validation.
  Additional tests prove queued/working to SUCCESS waits, terminal/unknown failure,
  timeout without cancel/resubmit, invalid-ID suppression and preserved submit flags.

If the corrected run still fails, one cycle should provide the SDK version,
stage, operation, native exit, google_category, submit_phase and recognized_permissions.
For example SOURCE_BUCKET_ACCESS_DENIED/source_bucket_validation differs from
PERMISSION_DENIED/source_upload, INVALID_ARGUMENT/build_log_configuration or
CLI_ARGUMENT_ERROR/client_arguments. Stop on the actual evidence; do not turn a
classification into an automatic IAM grant. Never enable shell tracing/log-http
or upload raw gcloud credential/cache/stderr artifacts to diagnose it.

## Terraform and exact next operator steps

**No Terraform source change or IAM apply required by this correction.** Existing
read metadata and exact object grants are reused. In particular do not add Storage
Admin or project buckets.list merely to satisfy implicit source discovery.
Reviewable local plan: infra/gcp/github-actions/build-005-review.tfplan (ignored),
0 resource changes. Human-safe summary: local-data/BUILD-005-plan-summary.txt.
No PROD resources or workflow were changed.

```powershell
# Review the prepared plan using your installed Terraform; no apply is needed.
terraform '-chdir=infra/gcp/github-actions' show 'build-005-review.tfplan'
# Offline code/contract validation:
.venv/Scripts/python.exe -m pytest tests/test_cloud_build_staging.py tests/test_gcp_command_diagnostics.py -q
git diff --stat
git diff -- scripts/gcp/deployment.py scripts/gcp/ci.py
```

If regeneration is desired, retain the same state/vars and quote native flags:

```powershell
terraform '-chdir=infra/gcp/github-actions' plan '-input=false' '-detailed-exitcode' '-out=build-005-review.tfplan'
```

Stop and investigate any unexpected plan differences; no `-target`, state
replacement, destroy or automatic apply. A code-only update is sufficient to try
the new staging contract. After review/commit on dev, the **operator** may publish
it when ready for normal paid DEV build/deploy/acceptance:

```powershell
git branch --show-current
git status --short
# Stop unless reviewed changes including new tests/docs are committed on dev.
git push origin dev
gh run list --workflow delivery.yml --branch dev --limit 5
gh run watch <NEW_RUN_ID> --exit-status
gh run view <NEW_RUN_ID> --log-failed | Select-String -SimpleMatch 'CI blocked:'
```

Replace the placeholder with the numeric run ID. Old-commit reruns cannot load
this correction. No build/deploy/rerun/push was executed by Codex. Any request for
Codex to perform a controlled real build requires a separate explanation of source
upload, build/registry/log costs and explicit approval before execution.

## Acceptance, remaining risks and handoff

Raw Google error for run 40509727837 and effective CI permission simulation remain
unavailable; historical attribution to buckets.list is probable, not proven.
The source correction is tested locally and removes that dependency while
preserving ownership validation. New source metadata/API/organization denies,
upload, builder/log quota or later acceptance failures could still emerge.
No real WIF/IAP/build/deploy acceptance was rerun here. Require a real new exact-SHA
DEV build, verified source/digest, private cloud_demo mock API/UI acceptance and
trusted release artifact before declaring CI/CD fixed. PROD remains a separate
protected release, not part of this validation.

Next session: inspect current dev HEAD/status and the reviewed BUILD-005 diff,
then the new run's safe fields. Do not replay completed bootstrap, widen IAM or
repeat speculative role changes. [AUTH-004 history](DEV_AUTH_004_INCIDENT.md) and
[ADR-0012](adr/0012-github-actions-delivery.md) retain the architecture; explicit
source configuration/ownership verification is an operational correction, not a
new architecture, so no redundant ADR is created.

## Local validation and changes performed

- `make test`: **590 passed**, one existing Starlette/AnyIO deprecation warning.
- Focused staging/command-diagnostic suites: **51 passed** (including the final
  safe-category-to-job-summary regression); no test invokes a real cloud client.
- Terraform 1.13.5 fmt/validate: both CI identity and cloud-demo modules PASS;
  CI identity plan completed with **0 resource changes**. No Terraform source edit.
- actionlint 1.7.7, Python compileall and Git whitespace checks PASS.
- Current committed source allowlist validated locally: **68 files, 335581 bytes**
  before baked-version injection; no archive uploaded and no contents printed.
- Actual operator-only direct source owner/name/region read and numeric SDK-version
  parsing PASS. This is not effective CI authorization or a real submission test.

Changed production code: deployment.py (explicit verified staging, async status
wait, validated SDK version, fixed error categories), ci.py (safe category summary).
Tests: new test_cloud_build_staging.py plus adapted existing command diagnostic
fixtures. Docs: this incident, AUTH-004/GITHUB_CICD links, ADR-0012 evidence and
tracking. No workflow or Terraform source was changed; no new ADR was needed.

Persistent GCP mutations, Cloud Build submissions, deployments, applies, workflow
reruns, commits and pushes performed by Codex: **none**. Metadata/audit/policy reads,
denied short-lived impersonation attempt and read-only Terraform planning are
listed above. Local plan/summary files are ignored and kept for operator review.
Browser/Docker QA was not repeated for this build-client-only change.

## Primary references

- [gcloud builds submit flags and staging/log defaults](https://docs.cloud.google.com/sdk/gcloud/reference/builds/submit)
- [Raw bucket describe output](https://docs.cloud.google.com/sdk/gcloud/reference/storage/buckets/describe)
- [Cloud Storage permission semantics](https://docs.cloud.google.com/storage/docs/access-control/iam-permissions)
- [Build logs and regional user-owned buckets](https://docs.cloud.google.com/build/docs/securing-builds/store-manage-build-logs)
- [Cloud Build API options](https://docs.cloud.google.com/build/docs/api/reference/rest/v1/projects.builds)
- [Default builder role permissions](https://docs.cloud.google.com/build/docs/cloud-build-service-account)
