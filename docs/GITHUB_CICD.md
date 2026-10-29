# GITHUB-CICD-001 — GitHub Actions delivery

Current state - 2026-10-28: private DEV and PROD `cloud_demo` delivery is
accepted in [master run 40614584902](RELEASE_2026_10_28.md). That evidence record
includes artifact IDs, isolated infrastructure, operator-verified IAM/Organization
Policy and state adoption, and remaining acceptance limits. Earlier dated findings
below are historical snapshots, superseded for rollout status. Do not replay
completed bootstrap/import/cutover steps or use old saved plans. Human login,
restore/isolation drills and real customer-data readiness remain unverified.

## Proposed registry/cache improvements

[TRIPSE CI-001–CI-005 plan](ARTIFACT_REGISTRY_CICD_PLAN.md) and
[ADR-0015](adr/0015-registry-build-cache-evolution.md) describe improvements over
this existing pipeline. CI-001 is implemented locally on `ci/ci-001-python-cache`:
native pip caching in CI/DEV/PROD, both requirements as cache inputs, unchanged
per-job virtualenv installation and a safe cache/native-timing summary.
[Measurements and validation](CI_001_PYTHON_CACHE.md): local tests PASS; the new
workflow has not run on GitHub and no performance gain is claimed. CI-002–CI-005
remain proposals; ADR-0015 remains proposed. Artifact Registry and Cloud Build already
exist in the recorded architecture. Buildx is an optional isolated benchmark,
not a replacement activated by the plan. Immutable release tags, provenance and
DEV-to-PROD digest promotion remain unchanged. Do not replay registry bootstrap.

## Historical bootstrap and incident timeline

2026-10-27 historical result: master was merged; run 40550402214 accepted DEV artifact
12753973550 then failed PROD before auth because all five Environment variables
were missing. Follow [PROD-BOOTSTRAP-002](PROD_BOOTSTRAP_002.md) for the audit at that date,
protections, staged plans and separate manual promotion. Do not repeat the merge
or rerun only failed PROD: strict source run-attempt provenance would reject its
older artifact. Older dated notes below retain the incident/preparation history.

2026-10-27: DEV run 40523770207 is accepted. Continue with the
[operator-ready PROD bootstrap plans and approval/cutover runbook](PROD_BOOTSTRAP_001.md).
The accepted artifact is from dev, not eligible master release evidence. PROD is
still the public readonly baseline; no production bootstrap was applied by Codex.

BUILD-005: [source staging diagnosis, code correction and zero-change IAM plan](BUILD_005_INCIDENT.md).
CI explicitly stages to the existing verified project/region source bucket rather
than using implicit SDK project-wide bucket discovery. No IAM widening; actual
new DEV build/acceptance remains an operator gate.

2026-10-27: [DEV IAP 401 incident, verified bootstrap history and session handoff](DEV_AUTH_004_INCIDENT.md).
Operator bootstrap and WIF exchange now pass; authenticated preflight health
still blocks the first cloud_demo rollout. AUTH-004 corrects JWT URL scope and
adds safe response classifications; no successful live fix or PROD readiness is
claimed. This dated update supersedes older pending-bootstrap statements below.

TRIPSE-WIF-AUTH-003: [DEV immutable-subject diagnosis and reviewed recovery](WIF_AUTH_003.md).
GitHub repo settings use immutable subjects; the former DEV condition expected
the legacy subject. The DEV-only declarative correction and temporary safe claim
diagnostic preserve all trust checks; applying/verifying it remains operator work.

## CI-CD-FIX-002: dev/master bootstrap correction

Follow the [Windows operator setup and first-run procedure](CICD_BOOTSTRAP.md).
That guide documents operator setup; the remaining sections retain the original
architecture and recovery details. Automatic deployment is now dev/master only.

Starting branch/HEAD: clean `dev`, `2c8e79b7b4c521eaf15ce2cf17e09f8b3b830171`.
Reported master run `40327554050` reached an empty JSON parser because required
GitHub variables were absent. Read-only inspection during this fix confirmed
`development` exists with all five variables missing; `production` does not exist.
Template/Terraform files do not provision those settings. New early validation
reports the setting/location before dependencies or credentials, with a safe step
summary. No cloud mode fallback is permitted. The operator helper prepares local
nonsecret config and checks GitHub/GCP metadata without changing remote settings.
Real bootstrap and runner acceptance remain OPEN; no push, merge, deploy or IAM
mutation was performed by this fix.

Original GITHUB-CICD-001 preparation on 2026-10-26: no workflow was pushed/activated, no IAM or billable resource
was provisioned, no Cloud Build submitted, and no DEV/PROD deployment performed
in this implementation. Real Actions/WIF/IAP acceptance is a bootstrap gate.

## Historical GITHUB-CICD-001 audit baseline and the preview problem

Remote `master`, local HEAD and the committed cloud source were
`3729ee53292ea29f96284358b3d2d3473297c390`; working tree was clean before this task.
Read-only service inspection during this task found DEV revision
`tripse-ai-dev-00005-hqb` running that SHA in **readonly_demo/mock**, now with IAP
enabled. PROD revision `tripse-ai-prod-00001-prh` runs
`be798fedc1970cdd96ce44bf6c0fae37fe4fce38`, readonly_demo/mock, without IAP enabled.
These are observed baseline facts, not deployments made by this work.

Existing `deployment.py` builds a committed allowlisted archive, injects baked
SHA, reuses immutable tags, pins a digest and deploys through manual Make targets.
Existing cloud_demo smoke uses a human-provided token and does not test writes.
The CLI preflight assumed an interactive active account. No Actions workflows
existed. The new layer reuses `build`, `deploy`, `smoke`, `deployed_state`, strict
configuration and existing parity checks. It does not duplicate image/deploy logic.

Configuration is explicit: an environment's `EXPECTED_CLOUD_FEATURE_MODE` must
match its validated JSON. No default to readonly is allowed. Changing code alone
still does not change feature mode. Missing resources/auth block deployment.

## Events and trust boundaries

| Event | Tests | Cloud access | Result |
|---|---|---|---|
| PR to master, including fork PR | CI + offline/image source + all browser smoke | none | no deployment |
| Push to dev | same CI first | development WIF only | build exact SHA, deploy DEV, deployed acceptance |
| Push to master / merge commit | same CI first | development, then approved production | exact master SHA accepted on DEV; same digest promoted |
| Other branch push | none (optional independent CI) | none | no automatic deployment |
| Dispatch `dev` | CI first | development | selected full SHA or dispatch commit on DEV |
| Dispatch `promote` from master | CI first + accepted DEV proof | protected production | selected prior master SHA/digest; no build |
| Dispatch `rollback` | CI first + prior successful target proof | selected environment | accepted prior image; PROD dispatch must be master |

`ci.yml` has only `contents: read` and no cloud authentication/environment.
It is reusable by Delivery, and PRs cannot inherit credentials. No
`pull_request_target`, `workflow_run` privilege handoff or credential-bearing
checkout of arbitrary PR code is used. Delivery jobs receive only read contents,
read Actions evidence and `id-token: write`. All third-party Actions are pinned
to full upstream commit SHAs. Action versions were resolved during implementation;
upgrades require review. No personal/reusable human token is a GitHub Secret.

Repository branch pushes are trusted DEV code: anyone allowed to push can execute
code with DEV deployer authority. Restrict repository write access accordingly.
The security boundary for PROD is enforced both by GitHub protection and GCP WIF;
the Python guard is an additional check, not the sole authorization mechanism.

## Shared DEV, freshness and immutable proof

All dev/master/manual DEV jobs use **one** concurrency group
`tripse-dev-global`, including build, deployment, acceptance and artifact upload.
No in-progress deploy is canceled. GitHub may replace an older pending job;
FIFO is not assumed. Before mutation the coordinator checks the current remote
branch head for push events and compares the workflow's sequence with the target
service's `github-run-number` label. A slow/stale run cannot overwrite a newer
deployment. An older rerun must be replaced with a new manual dispatch if a
newer sequence has already reached that service. A newer failed attempt also
blocks older pending attempts conservatively. Intentional rollback gets a new
manual run number; it never resets the freshness watermark.

PROD uses an independent `tripse-prod-global` lock and never reads "whatever is
on DEV now" as release evidence. DEV may change to another dev commit while
master waits for human approval. The immutable accepted artifact still records
the exact tested master digest and mode. Promotion checks GitHub API metadata:
repository, workflow path, event, master ref, policy commit, job success, run ID,
attempt, artifact ID/name/expiry, source SHA, mode and acceptance type. The chosen
SHA must remain an ancestor of `origin/master`, and its registry digest must
equal the proof. A feature/PR artifact, arbitrary artifact name, offline-only
result, expired artifact or failed acceptance cannot authorize PROD.

An immutable tag by itself is insufficient: a branch deployer can submit builds
to the shared registry. Before issuing DEV acceptance proof, the coordinator
also verifies an authoritative successful Cloud Build, the reviewed single
Google Docker builder command (without environment/entrypoint/secret overrides),
the existing builder identity, and **every actual source byte** from the
generation-pinned source archive against the selected committed context plus
baked SHA. A pre-created misleading SHA tag or altered recipe cannot be promoted
by a trusted master run. Promotion/rollback proof requires `source_verified=true`
and records the source build ID; DEV rollback also rechecks actual build source.
The scan covers the most recent 1,000 successful regional builds; missing/expired
source or an unrecognized new builder recipe blocks rather than weakening proof.
For very old evidence, an operator must review source retention and recovery.

Only `release.json` is uploaded, with 90-day retention. It contains no credentials
or document content. Every successful deployment publishes branch/ref, SHA,
digest, revision, 100% traffic, environment, mode, URL, acceptance, previous SHA,
config hash and rollback guidance in the job summary. Keep its artifact ID and
run ID. Older releases with expired proof require separate operator recovery;
CI does not silently trust an unverified archived file. A rerun of only PROD
after the originating run attempt changed may require rerunning the whole release
to produce a new proof; do not bypass attempt checks.

## Keyless WIF and IAP probes

`google-github-actions/auth` creates temporary external-account credentials through
GitHub OIDC and impersonates separate DEV/PROD CI deployers. No service account
key JSON exists. Generated `gha-creds-*.json` files are ignored by Git, Docker
and gcloud; builds use committed archives instead of the credential-bearing
workspace. `online_preflight` tests usable access-token credentials, including
noninteractive WIF, rather than requiring `gcloud auth login`.

| Identity | Authority |
|---|---|
| `tripse-ai-dev-ci-deploy` | metadata checks, selected DEV service deployment/IAM/traffic, repository reader, Cloud Build submit/wait, source upload, actAs DEV runtime/builder, sign DEV probe |
| `tripse-ai-prod-ci-deploy` | metadata checks, selected PROD service deployment/IAM/traffic, repository reader, actAs PROD runtime, sign PROD probe; no build grant |
| `tripse-ai-dev-ci-probe` | DEV Run invoker + IAP accessor + explicit application editor; no GCS/Firestore IAM data role |
| `tripse-ai-prod-ci-probe` | PROD Run invoker + IAP accessor + explicit application reader; no GCS/Firestore IAM data role |
| Existing builder / app runtime / task identities | retained; not replaced by CI deployers |

The manual module `infra/gcp/github-actions` defines the pool/providers, accounts
and scoped grants. Trust is restricted to repository ID **1430252241**, owner ID
**72949549**, exact `piotrbarabasz/tripse-ai-demo`, push/dispatch events, exact
environment subject and Delivery workflow ref. DEV automatic push trust allows
only dev/master; explicit dispatch can select a repository branch. Production additionally requires
`refs/heads/master`. The pool is exclusive to this repository; do not add broader
providers that could mint the same environment attribute. Ownership transfer,
renaming or workflow path changes deliberately require trust review.

Cloud_demo probes use IAM Credentials `signJwt`: issuer/subject is the dedicated
probe account, audience is the reviewed HTTPS service origin plus `/*` for the
multi-path IAP JWT suite, lifetime 10 minutes. A bare URL scopes only that exact
URL and cannot authorize `/health` or private paths (AUTH-004 correction).
IAP supports this service-account flow without a reusable human session or local
private key. For private preview, `generateIdToken` explicitly targets the Run
origin and includes email. Tokens remain in process memory; they are not printed,
passed on argv, stored in dotenv, uploaded or exposed to third-party browser
requests. The probe must be separately approved in IAP AND application lists.
The task service account is not used as a human/application probe.

This CI flow does not remove the existing cloud task caller's OAuth/OIDC setup.
Cloud Tasks still needs the configured client audience and programmatic access.
Missing signing permission, IAP membership, valid assertion, or private anonymous
denial blocks PROD. There is no authentication bypass to make tests pass.

Sources: [Google auth Action](https://github.com/google-github-actions/auth),
[IAP service-account authentication](https://docs.cloud.google.com/iap/docs/authentication-howto),
[GitHub concurrency](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax).

## Runtime prerequisite checks and acceptance

Before build/deploy the coordinator verifies fixed project `tripse-ai`, region
`europe-central2`, target service, explicit mode, immutable registry and existing
service ownership. Cloud_demo additionally requires the private versioned uniform
bucket, correct named Firestore database with PITR/delete protection, enabled
bounded queue, task identity, scoped runtime storage/database/queue/actAs IAM,
direct IAP with invoker enforcement and exact origin, approved application/task
IAP membership, Tasks programmatic client and a usable keyless probe credential.
Checks only read resources. They never enable APIs, create infrastructure or
silently fall back to fixture preview. Custom IAM role names/permissions were
checked against current predefined role metadata; real resource-scope/WIF
permission propagation must still be tested during bootstrap.

DEV cloud_demo then runs the existing authenticated API acceptance with explicitly
synthetic persisted data: 15-day trip, update/conflict 409, private offer/pilot,
campaign previews, raster upload/private read, mock planner/job/viewer, simulator
dedup/response and invalid/expired token. Headless Chromium checks the actual
authenticated Hub and editor showing that 15-day record and simulator controls.
External browser traffic is blocked, so Maps/OpenAI/WAHA incur no provider calls.
Tests leave labelled synthetic data for inspection; plan retention and cleanup as
a separate reviewed task because the application intentionally has no bulk-delete
API. They do incur ordinary GCP infrastructure operations. PROD smoke is read-only.

`deployed_state` now checks latest-created = latest-ready, exactly 100% traffic to
that revision and the **receiving revision's** resolved digest, not only a service
template/tag. It rechecks after acceptance before issuing proof. The simple
`/health` response is never treated as full cloud_demo acceptance.

## One-time operator bootstrap checklist

Nothing in this section was executed against GCP/GitHub during implementation.
Follow in order; do not apply Terraform on every push.

1. Review/commit these workflow and script changes. Configure repository rules
   before allowing deployment jobs. No push was made by this implementation.
2. Create GitHub Environments **development** and **production**. Restrict
   production deployments to master, add required reviewers, disable admin bypass
   where appropriate. Enable prevent-self-review if a second maintainer can
   approve; a single-operator project must choose an available approval policy
   rather than permanently locking itself out. An environment name in YAML does
   **not** itself create required-reviewer protection.
3. Protect master with PR review, the actual PR CI check, no force push/deletion,
   and required CODEOWNERS review of `.github/workflows`, `scripts/gcp`, `infra/gcp`
   and deployment dependencies. Select the exact check name published by the
   first PR workflow (`Tests and offline contracts`); caller workflows can add a
   job-name prefix. Restrict repository write/admin access and fork workflow
   approvals. Set the repository's default token permission to read-only.
4. Complete the application DEV bootstrap in [DEPLOY_GCP.md](DEPLOY_GCP.md):
   private GCS/Firestore/Tasks, IAP, human/task membership, OAuth and budgets.
   These data resources are separate from the CI identity module. Current code
   cannot obtain parity merely by changing CLOUD_FEATURE_MODE.
5. Review a **manual** CI bootstrap Terraform plan for `infra/gcp/github-actions`
   with `environments=["dev"]`. Use a secured dedicated CI-bootstrap state. It
   expects existing app resources, builder/runtime identities and Cloud Build
   source bucket; it does not create the app buckets/databases/queues. After
   separate approval apply it. Do not create SA keys. Inspect output `environments`.
6. In GitHub environment **development**, add the non-secret variables below.
   Add the DEV CI probe to application editors and IAP. Runtime fields are
   literal strings, not shell interpolation. No human token or provider API key
   should be a GitHub Secret. API keys remain pinned Secret Manager references.
7. Exercise a dev-branch push, then inspect summary/proof and actual DEV
   revision/mode/digest. Exercise missing-resource/auth negative tests, two branch
   pushes with stale-job rejection, a failure with traffic restore, and full
   authenticated acceptance. No production activation until this passes.
8. Extend the **same CI bootstrap state** to `environments=["dev","prod"]` after
   approval. Do not create a second copy of the shared WIF pool or remove DEV
   from the configured set. Bootstrap app PROD resources/IAP separately, then
   configure the protected **production** environment. Confirm the production
   deployer has no builder actAs or build-create grant.
9. Run a master release, inspect its DEV proof, approve production deliberately,
   and verify same digest/expected mode/traffic/URL. Record acceptance externally.
   Test manual promotion and rollback with valid and invalid proof artifacts.

PowerShell examples for the manual identity bootstrap (review before executing;
creates IAM/WIF, not an application deployment):

```powershell
gcloud auth application-default login
gcloud auth application-default set-quota-project tripse-ai
terraform -chdir=infra/gcp/github-actions init
terraform -chdir=infra/gcp/github-actions validate
'environments = ["dev"]' | Set-Content -Encoding ascii infra/gcp/github-actions/bootstrap.auto.tfvars
terraform -chdir=infra/gcp/github-actions plan -out=dev-bootstrap.tfplan
# STOP: operator review of this exact plan and state location.
terraform -chdir=infra/gcp/github-actions apply dev-bootstrap.tfplan
terraform -chdir=infra/gcp/github-actions output -json environments
```

For enabling PROD later, change that private file to
`environments = ["dev", "prod"]` and generate/review a new plan in the
same state. Using a file avoids native argument quoting differences in Windows
PowerShell. The module is additive but IAM is powerful; inspect every binding
and import matching preexisting resources where required. No workflow has IAM
bootstrap authority. Keep state/tfvars/plan files private and backed up.

### GitHub Environment variables

| Variable | development | production |
|---|---|---|
| `WIF_PROVIDER` | Terraform development output | Terraform production output |
| `DEPLOY_SERVICE_ACCOUNT` | `tripse-ai-dev-ci-deploy@tripse-ai.iam.gserviceaccount.com` | `tripse-ai-prod-ci-deploy@tripse-ai.iam.gserviceaccount.com` |
| `CI_PROBE_ACCOUNT` | `tripse-ai-dev-ci-probe@tripse-ai.iam.gserviceaccount.com` | `tripse-ai-prod-ci-probe@tripse-ai.iam.gserviceaccount.com` |
| `EXPECTED_CLOUD_FEATURE_MODE` | explicit `cloud_demo` or deliberately `readonly_demo` | same accepted mode for promotion |
| `DEPLOY_CONFIG_JSON` | complete DEV non-secret schema | complete PROD non-secret schema |

Cloud templates are in `infra/gcp/github-actions/*.cloud_demo.json.example`.
Replace the OAuth placeholder with the approved client ID and review users.
For preview use the fields in the existing `.env.*.example` as a JSON object of
strings, excluding cloud-only fields. Neither mode is selected implicitly.
`GCP_BROWSER_MAPS_SECRET` may reference only a pinned environment-specific secret
version; its payload is never an Actions variable. No live cloud mode is enabled.

At runtime validated dotenv files are generated under `RUNNER_TEMP`, never in
committed source. Because legacy `load_pair` validates both environments, each
job gets a **validation-only private readonly sibling stub** with the same
project/registry, not the other environment's true config. The selected target
is checked independently. This prevents development jobs accessing production
variables or secrets. A mode mismatch between DEV proof and production variables
blocks promotion instead of reverting to preview.

## Manual release, rollback and recovery runbook

In Actions → Delivery → Run workflow:

- DEV: choose branch, `operation=dev`, optional full `release_sha`.
- PROD promotion: choose **master**, `operation=promote`, accepted master SHA,
  DEV evidence run ID and exact artifact ID. Required production approval applies.
- Rollback: `operation=rollback`, target dev/prod, prior accepted SHA and the
  **target environment's** successful evidence run/artifact IDs. PROD must use
  master and production approval. No build is performed for promotion/rollback.

The old Make interface remains available to an operator: `make deploy-dev`,
`make deploy-prod TAG=... CONFIRM=prod`, `make gcp-rollback ENV=... TAG=...
CONFIRM=rollback`, with the appropriate reviewed CONFIG_DIR. Coordinate/pause
Actions before a manual CLI mutation: GitHub's lock cannot serialize a separate
terminal. Use `make gcp-ci PYTHON=...` only with the explicit CI environment; it
is not a replacement for interactive bootstrap.

If deploy or acceptance fails after mutation, the coordinator attempts to restore
the previous recorded revision traffic, restores IAP if it protected the previous
service or its mode was cloud_demo, and keeps invoker authentication **private**. It verifies old health
SHA/mode and traffic before stating restoration was verified. Failure remains a
failed job in every case; no accepted artifact is created, and automatic PROD
cannot proceed. If restore verification also fails, inspect the summary and
restore the recorded known-good revision/config through the operator runbook.
There is no storage deletion/schema migration and no speculative automatic
rollback to an arbitrary SHA. Public preview access is not automatically reopened
after failure: an operator may restore that access only after confirming the
old readonly surface. This is the explicit fail-closed availability tradeoff.

Troubleshooting:

- Config/mode error: fix environment variables; do not add fallback defaults.
- WIF denied: inspect numeric repo/owner ID, event, exact workflow ref,
  environment and provider/account output. Wait for IAM propagation; no JSON key.
- Probe denied: check TokenCreator on the dedicated probe, its Run/IAP role and
  application reader/editor list. Never use the task identity or a human refresh
  token to bypass the test.
- Missing storage/Tasks/PITR/IAM: run the approved one-time infrastructure process,
  not an automatic Terraform apply from a feature push.
- Stale sequence: start a new manual dispatch after inspecting the current
  deployment; do not edit the label backwards or approve stale PROD evidence.
- Expired/mismatched proof: rerun DEV acceptance for the intended master SHA.
- Keep a last-known-good artifact/run/revision and do not rotate/delete state or
  data as a reaction to a code deployment failure.

## Validation limits and costs

Implementation validation on 2026-10-26: `make test` **431 passed** (one existing
Starlette/AnyIO deprecation warning); all eight local browser smoke scripts
passed; offline CI contract passed; actionlint 1.7.7 passed; Terraform 1.13.5
backend-free init, fmt and validate with Google provider 8.8.1 passed; Git diff
whitespace check passed. Both example cloud configs pass the strict schema.
Read-only source-proof verification against the existing DEV image passed for
build `9c54ce2d-d425-44cd-9328-a765affb8bad`, including the complete archived source
and build recipe. None of these checks submitted a build or deployed a service.

Local workflow/policy tests, actionlint and backend-free Terraform validation are
recorded in the worklog. Provider schema validation does not prove WIF claims,
resource-level permission propagation, IAP network behavior or GitHub reviewer
settings. Actual runner WIF refresh, Cloud Build upload/poll and authenticated
DEV/PROD acceptance remain OPEN until operator bootstrap and controlled runs.
No full CI/CD success or cloud parity is claimed here.

Cost categories: Actions runner/browser minutes and artifact retention, Cloud
Build/Artifact Registry, Cloud Run, GCS/Firestore operations and backup retention,
Tasks dispatch/retries, IAM/OAuth maintenance and monitoring. DEV acceptance writes
synthetic data and triggers real mock tasks, so it has infrastructure cost even
without paid AI/Maps. There is no workload admission quota or unlimited-cost
guarantee. Set approved budgets/alerts and operational retention; no prices,
hours or billed amounts were invented.
