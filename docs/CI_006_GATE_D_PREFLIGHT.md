# Gate D preflight after IAM hardening

## Current-status addendum — Gate D.0, 2026-10-30 (Europe/Warsaw)

**PREPARED FOR COMMIT REVIEW. No commit, push, Delivery dispatch or deployment
was performed in Gate D.0. Actual CI-probe authentication and post-IAM-change
Cloud Build execution are still unverified.** The historical report below is
preserved; its references to c8fec87 and unpublished C.1 describe its earlier
checkpoint, not the current candidate.

### Current published candidate and security evidence

PR #7 is open/unmerged. Local HEAD, remote feature branch and PR head all match
**`86adcdbebf86cf1e7e4ef00b22febfa6a6bb3083`**. This published commit includes
C.1/C.2 and their tests/reports. [Hosted CI run 40964945914](https://github.com/piotrbarabasz/tripse-ai-demo/actions/runs/40964945914)
passed for that exact head: 1085 passed, one existing Windows-only skip and one
deprecation warning on Ubuntu; offline source contracts and browser QA passed.
This hosted result does not cover the uncommitted Gate D.0 changes described here.

Fresh read-only GCP evidence repeated all 33 previously successful policy/config
queries: all match the post-apply snapshots. The numeric legacy worker has no
direct project binding. The dedicated builder still has only its scoped metadata,
source-reader, log-writer and repository-publisher grants; the Cloud Build service
agent role and DEV/PROD isolation are preserved. No new build was submitted.
The previously denied service-agent own-policy read remains an evidence limit,
not proof of absent impersonation bindings; no new permissions were requested.

Published C.1 still binds its historical exception to the exact 497ea150 full SHA,
build, image, digest, fixed fixture paths and trusted manifest. Shared path/secret
checks, normal new-build allowlist, clean-head checks and accepted-release
provenance requirements remain unchanged and fail closed. The deletion-only C.2
guard remains separate from release authorization. No Terraform/IAM changes are
part of Gate D.0. Evidence and validation logs stay ignored in `local-data/gate-d0/`.

### New DEV-only pre-deployment health gate

The DEV job now runs `.venv/bin/python -m scripts.gcp.ci dev-health` after the
existing WIF authentication and setup-gcloud, before browser installation and
`make gcp-ci`. It has no conditional skip or continue-on-error. PROD steps,
authorization conditions, WIF, IAM, dispatch inputs and concurrency are unchanged.

The new action validates the existing DEV configuration and dedicated deployer,
then uses metadata reads to identify the single 100% receiving DEV revision,
its Ready state, immutable image digest, SHA, environment and mode. It requires
IAP enabled, invoker checks enabled and no public service invoker binding.
It uses the existing `smoke_auth.probe_token` keyless signJwt contract for
`tripse-ai-dev-ci-probe@tripse-ai.iam.gserviceaccount.com`; JWT aud is the exact
reviewed origin plus `/*`, with a 600-second lifetime. The only application
request is authenticated **GET `/health`**, with redirects refused.

The response must be a JSON object with status=ok, environment=dev,
feature_mode=cloud_demo, generation_mode=mock, storage=gcs_firestore,
service=tripse-ai-dev and image_version equal to the **currently serving**
revision's SHA. It intentionally does not expect the undeployed new RC SHA.
Unknown/missing values, split traffic, invalid revision/digest, failed signing,
401/403, redirects, network errors and malformed responses stop the step and
therefore the job before image publication or Cloud Run mutation.
Errors are reduced to a fixed safe message; access/JWT tokens and response bodies
are never printed, passed in argv or persisted. Configuration files under the
existing runner temp config directory contain no tokens. No cloud-writing
application endpoint, acceptance method or release coordinator is called by
`dev-health`. The existing coordinator's own prerequisites/probe check remains.

This gate is intentionally for the currently configured cloud_demo DEV rollout.
A different/readonly current mode is rejected for operator review rather than
silently accepted as a bootstrap transition. The live DEV is already cloud_demo;
the existing feature-branch DEV dispatch remains eligible.

Required signing and resource-read grants are already observed on the DEV
deployer. No authentication bypass or permission addition is needed in the design.
The local user's missing signJwt grant from the earlier investigation is not
substituted for the actual WIF runner. No real probe JWT or health request was
executed here, so successful authentication is still a future runtime result.

### Exact synthetic DEV acceptance write inventory (not executed)

This inventory follows `ci.execute`, `Acceptance.writes`, Document Studio's API/
GCS adapter and `CloudJobs`. Acceptance runs **after** deployment and is distinct
from the new GET-only gate. The live DEV configuration names bucket
`tripse-ai-tripse-ai-dev-documents`, Firestore database `tripse-ai-dev` and queue
`projects/tripse-ai/locations/europe-central2/queues/tripse-ai-dev`.

| Target | Intended writes for one successful acceptance run |
|---|---|
| GCS `documents/trips/<uuid4hex>.json` | One new 15-day trip, title `CLOUD-PARITY synthetic DEV <8 hex>`, data_origin=synthetic_test, day titles `Synthetic day N`, internal marker `PARITY_PRIVATE_OPS`. One successful PUT advances it from revision 1 to 2. A repeated stale PUT must return 409 without another successful write. |
| GCS `documents/drafts/<uuid4hex>.json` | Two new draft snapshots: `offer.private` and `pilot.basic`, sourced from that synthetic trip. Draft title/data_origin inherit the synthetic source; the client-facing offer must not expose the internal marker. No draft update or revision-archive operation is requested. |
| GCS `images/<asset uuid4hex>` | One sanitized 32x20 blue PNG, uploaded as `synthetic.png` with rights_confirmed=true; immutable binary create uses generation-match 0. |
| GCS `documents/assets/<asset uuid4hex>.json` | One asset metadata object for that image. |
| GCS `documents/campaigns/<uuid4hex>.json` | One new campaign with the synthetic trip's title, data_origin=synthetic_test and references to that trip and uploaded image. |
| Firestore `jobs/<trip_id>` in DEV database | Three distinct jobs: one `/api/trips` mock plan, one simulator message, and one expired-viewer simulator case. Creation, dispatched flag, processing lease/attempt/status, mock result_json, viewer hash/expiry and notification are transactional updates to each job. The duplicate simulator request reuses the same job. |
| DEV Cloud Tasks | Normally three named tasks, one per distinct job: `<queue>/tasks/<trip_id>`, POST to DEV `/internal/jobs/<trip_id>` with `{}` body and existing dedicated task-account OIDC/IAP audience. Redelivery/retries may repeat processing requests; this suite does not invoke operator recovery or create recovery-suffix tasks. |
| Document Studio storage | The trip, two drafts, campaign and asset metadata above are the actual durable Studio records. Cloud mode uses GCS, not SQLite or `/app/local-data/document-studio`; no PDF export or persisted preview is requested. |

That is **six distinct GCS object names**, with a second generation of the trip
object; previews render/read existing records without persisting extra drafts.
There are three Firestore job documents and normally three unique task names,
not one task/document per duplicate HTTP request. Partial failure can leave a
subset of these objects, including unreferenced image bytes after an ambiguous
storage result. Existing asset error handling is unchanged; no destructive
cleanup has been added.

Studio IDs come from fresh UUID4 hex values. Planner idempotency uses a fresh
UUID; simulator conversation and message IDs are fresh UUIDs. Cloud job IDs are
UUID5-derived from the verified caller's owner hash and planner/demo event key;
the demo key includes conversation and message ID. The duplicate request has
the same key; the expired case has a new message ID. Job request text is the
first built-in demo scenario: **Firestore jobs have no synthetic_test field or
CLOUD-PARITY title**. Their unique IDs, owner and conversation/event context are
the identifiers; do not rely on a text prefix to discover every test job.

Trip and campaign synthetic markers are visible in the shared DEV Studio library;
drafts inherit the synthetic origin. Studio is shared among approved DEV editors,
so accumulation and accidental later manual edits are real risks. Create-only
checks and GCS generation/revision CAS protect against overwriting an existing
record on collision; the intentional PUT addresses only the newly created trip.
Firestore owner/event isolation and idempotency avoid reusing existing jobs.
These are collision controls, not permission to erase records after acceptance.

GCS objects/versions and Firestore jobs survive container restart and traffic
rollback; this suite deletes none of them and defines no automatic expiry for
them. Viewer expiry makes links inaccessible without deleting job data.
Cloud Tasks follows its configured dispatch/retry lifecycle; it is not a durable
audit store. Mock jobs do not call paid AI or real WhatsApp. Browser acceptance
visits the hub, existing synthetic trip and chat without submitting forms;
third-party requests are blocked. No such writes or browser acceptance occurred
in Gate D.0, and no data-cleanup behavior was introduced.

### Review, validation and publication checkpoint

Prepared scope: four files only — DEV workflow (one mandatory step), `ci.py`
(DEV-only action and serving-health validation), new
`tests/test_dev_health_preflight.py`, and this current-status addendum.
The historical report, published C.1/C.2 implementation and other worktrees are
preserved. Proposed commit: **`ci: verify serving DEV identity through IAP before release`**.
If separately approved, commit/push goes to `ci/ci-006-integration-acceptance`
and updates existing PR #7; it starts credential-free PR CI, not Delivery.

| Final local validation | Result |
|---|---|
| New DEV health preflight tests | 39 PASS |
| Focused probe/IAP, workflow, delivery, historical and bootstrap contracts | 336 PASS, 2.39 s |
| Full `make test PYTHON=.venv/Scripts/python.exe` | 1125 PASS, 62.27 s pytest; one existing Starlette/AnyIO deprecation warning |
| `python -m scripts.gcp.ci offline` | PASS |
| actionlint v1.7.12, both workflows | PASS; official Windows asset checksum verified; optional shellcheck/pyflakes not installed/enabled |
| `make check` and `git diff --check` | PASS; existing LF/CRLF advisory only |
| Actual WIF/probe authentication / post-change Cloud Build | NOT RUN / NOT RUN |

The new tests
exercise real keyless/HTTP request construction with synthetic transports,
identity mismatches, absent fields, redirect/auth/network failures, metadata
and privacy failures, wrong targets, no coordinator entry and workflow order.
No existing security assertions were weakened.

### Exact intended path and separate Gate D approval

After commit/push approval and successful hosted CI, obtain the **new full SHA**
from PR #7. It does not exist yet; 86adcdb is the published baseline, not a SHA
containing this new health gate. Return the new SHA and hosted result for separate
deployment authorization. The intended path is manual Delivery on the feature
branch, operation=dev and target_environment=dev, with release_sha explicitly
equal to the approved new SHA. Development Environment/WIF identity and global
DEV concurrency stay unchanged. PROD remains excluded by master-ref and operation
conditions; no merge to master is part of either approval.

Documentation-only command template; **not executed**:

```powershell
$approvedDevSha = 'REPLACE_WITH_NEW_PUBLISHED_40_HEX_SHA'
if ($approvedDevSha -cnotmatch '^[0-9a-f]{40}$') { throw 'A reviewed full SHA is required' }
$remoteDevSha = gh api repos/piotrbarabasz/tripse-ai-demo/git/ref/heads/ci/ci-006-integration-acceptance --jq .object.sha
if ($LASTEXITCODE -ne 0 -or $remoteDevSha -cne $approvedDevSha) { throw 'Approved candidate differs from branch head' }
gh workflow run delivery.yml --repo piotrbarabasz/tripse-ai-demo --ref ci/ci-006-integration-acceptance -f operation=dev -f target_environment=dev -f "release_sha=$approvedDevSha"
```

Publication approval authorizes no cloud mutation. A later separate Gate D approval
must cover the exact new SHA, Cloud Build image publication, DEV Cloud Run
deployment, the synthetic writes listed above, and the existing automatic
traffic-recovery behavior. It must explicitly exclude PROD deployment and master
merge. Recheck the branch/workflow SHA and Environment/WIF immediately before
dispatch and inspect the selected run identity; do not accept a moved branch as
the approved policy. The signed health gate must pass before build in that run.
Automatic recovery, if needed after a later failed deployment, restores verified
traffic/private access and checks prior health; it does not undo synthetic data
writes. A mocked recovery test is not a live restoration drill.

**STOP: publication approval required now. Gate D requires its own later approval.**

## Historical preflight snapshot — 2026-10-29 (preserved)

2026-10-29, approximately 22:01–22:04 UTC. **PARTIALLY READY. Gate D was not executed.**

IAM hardening and recovery metadata pass. Two prerequisites remain: publication
and hosted CI for the recommended new candidate, and a real CI-probe private
health check. No deployable SHA containing the local C.1 patch exists yet.
This report does not authorize a workflow dispatch or expand the prior IAM approval.

Worktree: `D:\Projects\tripse-ai-ci-integration`; branch
`ci/ci-006-integration-acceptance`; local/published PR #7 HEAD:
`c8fec8777cd6f77b88418216de8cd506035ff031`.
PR [#7](https://github.com/piotrbarabasz/tripse-ai-demo/pull/7) remains open/unmerged.
The [IAM application record](CI_006_GATE_C2_IAM_APPLY_RESULT.md) supersedes the
proposal-only status in the unchanged C.2 investigation and plan checkpoints.

## 1. Post-change IAM and build identity

All 33 previously successful GCP evidence queries were repeated and matched
their post-apply snapshots exactly. The service-agent policy read was retried
separately. Twenty-two explicit live binding/configuration assertions passed.
Raw evidence is ignored under `local-data/phase-b-gate-d-preflight/`.

| Live evidence | Result |
|---|---|
| Numeric legacy worker | No direct project binding for `serviceAccount:690165197462@cloudbuild.gserviceaccount.com`; removed broad role remains absent |
| Dedicated worker | `tripse-ai-build@tripse-ai.iam.gserviceaccount.com`; project role only `projects/tripse-ai/roles/tripseBuildMetadata` |
| Worker metadata role | `resourcemanager.projects.get`, `serviceusage.services.use`, `logging.logEntries.create` |
| Source bucket | Worker objectViewer plus bucket metadata on `tripse-ai_europe-central2_cloudbuild`; DEV source creator/viewer retained |
| Log bucket | Worker objectUser plus bucket metadata on `690165197462-europe-central2-cloudbuild-logs` |
| Artifact Registry | Worker custom push role only on repository `tripse-ai`; 10 permissions including upload/download and tag create/update, no delete; deployers remain readers |
| Cloud Build default | Compute default account `690165197462-compute@developer.gserviceaccount.com`, distinct from the explicitly selected worker |
| Current accepted build | `8061fc93-dcfe-470b-a65f-5112b8607b58`, dedicated worker explicitly recorded in `serviceAccount` |
| Source provenance | Current DEV generation-pinned source downloaded and verified against exact committed allowlist and baked SHA; recipe/worker/digest checks PASS |
| Service agent | Project `roles/cloudbuild.serviceAgent` retained on `service-690165197462@gcp-sa-cloudbuild.iam.gserviceaccount.com` |

The dedicated worker is still explicitly selected by `deployment.build()`;
the default account response does not override that recipe. No new build was
submitted, so post-hardening build execution is not empirically demonstrated.
Live custom-role definitions and scoped bindings support the permission analysis;
Terraform declarations alone were not treated as proof of deployed permissions.

The service agent's own IAM policy is still denied with
`iam.serviceAccounts.getIamPolicy`. Its project orchestration role is observable;
absence of direct impersonation grants on that identity cannot be asserted.
No privileges were added to obtain evidence. Organization policy, scoped grants,
WIF and DEV/PROD service metadata show no unexpected changes since apply.
Deny/PAB/group effects and unaudited external consumers remain visibility limits.

## 2. Probe authentication and IAP

The live DEV origin is `https://tripse-ai-dev-64ctpggq3a-lm.a.run.app`.
The configured IAP OAuth audience/programmatic client is
`690165197462-653cuslrjb8nusq758avecpau885tj5r.apps.googleusercontent.com`;
it matches the development configuration and live IAP programmatic allowlist.

The CI path uses `tripse-ai-dev-ci-probe@tripse-ai.iam.gserviceaccount.com`.
The DEV deployer has Token Creator on that probe account. The probe has IAP
accessor and Cloud Run invoker on DEV. IAP is enabled, invoker checks remain
enabled and no `allUsers` or `allAuthenticatedUsers` service binding exists.
The IAP service agent's Run invoker grant is retained.

`smoke_auth.probe_token` obtains the runner's access token in memory, calls
IAM Credentials `signJwt`, and uses iss/sub=probe, aud=origin+`/*`, exp=iat+600.
The request carries `Authorization: Bearer <in-memory JWT>`; the health client
rejects redirects. A signed service-account JWT uses the protected URL audience,
whereas the configured OAuth client audience applies to the OAuth token path.
This distinction matches [Google's IAP authentication guidance](https://docs.cloud.google.com/iap/docs/authentication-howto).
The prior own-user ID-token 401 had a wrong audience and is not a failed CI probe.

**Real authentication remains pending.** A read-only `testIamPermissions` on the
DEV probe returned no `iam.serviceAccounts.signJwt` for the existing local caller
`kontakt@protolume.pl`. No JWT was minted, no privilege expansion or account/ADC
change was attempted, and no authenticated health GET was possible through that
same probe path. We did not try signing as the DEV deployer or bypass IAP.
The local caller is not the WIF runner: its missing signing permission does not
prove the deployer's observed scoped signing grant is ineffective.

Without invoking a workflow, the actual GitHub OIDC exchange cannot be reproduced
here. The existing coordinator performs the real signed-probe `/health` check
in `prerequisites()` before building. This must pass in a separately authorized
run; static IAM checks and mocked tests do not substitute for it. No successful
live private health result is claimed by this preflight.

## 3. Release candidate consistency and recommendation

The published SHA is `c8fec8777cd6f77b88418216de8cd506035ff031`.
[Hosted CI run 40900716604](https://github.com/piotrbarabasz/tripse-ai-demo/actions/runs/40900716604),
job/check `123541912593`, is successful on that exact SHA. Only PR CI is listed
for it; no Delivery run has executed for this candidate.

The current working tree has unpublished source changes in `build_proof.py`
and `deployment.py`, new `test_historical_provenance.py`, the C.2 offline plan
guard/tests and isolated cleanup module, and the prior reports. None is covered
by that published SHA's hosted success. The existing C.1 patch is already applied;
its reverse-check and recorded hashes are preserved. It was not reapplied.

C.1 adds one trust-anchored historical exception for full SHA `497ea150…`, exact
Build ID, digest and manifest, with five fixed fixture paths and shared secret/
path scanning. It changes source-verification security contracts; it does not
change runtime schema or data. PROD promotion/rollback still requires authentic
accepted PROD evidence. The normal new-build allowlist remains unchanged.

**Recommend B: review and publish a new RC containing C.1, then rerun hosted CI.**
C.1 is not technically needed to validate the current DEV recovery SHA: its
source and artifact pass without the historical exception. Option A is possible
only as an explicitly narrower experiment on the existing published candidate,
excluding every local patch. B is safer for acceptance of the final intended
release tooling: code, policy tests, hosted CI and subsequent release approval
will refer to one reviewed commit rather than accepting local code that was
never executed in GitHub. The new commit SHA cannot be identified before an
authorized commit exists; it must not be invented or replaced silently by c8fec87.

No automatic commit/push occurred. Security review, selection of publication
contents, commit/push approval and successful hosted CI are prerequisites to B.
The new full SHA must replace the candidate identity in the next approval request.

## 4. DEV-only workflow and proposed command

The live Delivery workflow is active and `workflow_dispatch` exists on master.
The RC workflow fetched from GitHub matches the local workflow. Its triggers
are push to dev/master and manual dispatch; no scheduled, PR or workflow_run
release trigger was found. Pushes to dev/master can automatically release, so
candidate publication must remain on the feature branch. Recent Delivery runs
are existing dev/master push runs; none was triggered by this investigation.

- Proposed dispatch ref: `ci/ci-006-integration-acceptance` (a branch, not a tag).
  Live DEV WIF binds immutable repository/owner IDs, development subject and
  environment, exact Delivery workflow_ref and refs/heads/ for manual dispatch.
  It permits this feature branch but is not exclusive to this one branch.
- Development Environment has no reviewers or branch restrictions and allows
  admin bypass. The operator approval is therefore an external checkpoint,
  not an enforced GitHub reviewer gate. Variables match provider/deployer/probe,
  project/dev, cloud_demo/mock, private origin and IAP audience.
- DEV needs successful CI; concurrency `tripse-dev-global`, cancel-in-progress=false.
  DEV deployer retains inspected build-submit/metadata, source create/read,
  dedicated-worker/runtime actAs, probe signing and DEV-service admin grants.
- PROD requires master ref, successful CI and promote/PROD-rollback operation
  (or the matching master push success path). Feature ref + operation=dev makes
  PROD false on both ref and operation checks. PROD concurrency is separate.
- Live PROD WIF requires production/master/exact workflow; production Environment
  has a required reviewer, bypass disabled and the sole custom branch policy
  `master`. Self-review is not prevented. These are observed settings, not new
  guarantees created by this task.

**Documented alternative A only; not executed or approved by this report:**

```powershell
gh workflow run delivery.yml --repo piotrbarabasz/tripse-ai-demo --ref ci/ci-006-integration-acceptance -f operation=dev -f target_environment=dev -f release_sha=c8fec8777cd6f77b88418216de8cd506035ff031
```

This is the exact command for the currently published candidate if the operator
explicitly selects A and accepts exclusion of all local patches. Before any
dispatch, re-read the branch head and require the approved workflow/policy SHA;
the branch is mutable even though release_sha is explicit. For recommended B,
use the same ref/operation/target fields with **the newly published, reviewed,
hosted-CI-successful full SHA** in release_sha. There is no executable, exact B
command yet. Stop rather than using an unknown SHA or dispatching the older A
candidate under a claim that C.1 is included.

## 5. Recovery readiness and data scope

Fresh `ci.snapshot`, `validate_snapshot` and `verify_previous_revision` checks
passed against read-only service, revision and registry metadata:

| Recovery field | Observed value |
|---|---|
| Current DEV SHA | `c3d3e922dae3c8bd15c5a8c78c4b4a51263074cf` |
| Digest | `sha256:b4a86311712ace6ff894a346c465a74ecda4272a38b5599821f4d8d8c36ac28f` |
| Receiving revision | `tripse-ai-dev-00031-z2l`, Ready, 100% traffic |
| Runtime identity | `tripse-ai-dev@tripse-ai.iam.gserviceaccount.com` |
| Mode / environment | cloud_demo / dev; mock planning |
| Access | IAP enabled, private invoker policy retained |
| Freshness sequence | 37 from current service's GitHub run label |
| Accepted evidence | DEV run `40839099491`, artifact `12882053228` |
| Source proof | Build `8061fc93-dcfe-470b-a65f-5112b8607b58`, exact-byte current policy PASS |

The authentic accepted artifact was downloaded and passed current run/attempt/
job/ref/expiry and archive validation; its digest/revision match the fresh
snapshot. GitHub metadata and deployed evidence refer to c3d3, not the undeployed
c8fec87 candidate. Earlier qualified older DEV targets are historical evidence;
the freshly checked automatic-recovery target for a future release is c3d3.

Recovery runs as the DEV deployer, which retains DEV service admin, own-runtime
actAs and own-probe signing. It validates ownership, snapshot identity, digest,
Ready revision and freshness; restores the named traffic allocation; then checks
private health identity, exact traffic and invoker/IAP state. Failure does not
create accepted release evidence. These contracts are tested, not a live restore.
No traffic change or rollback was executed. Snapshot readiness does not prove
application-state recovery or a working private probe.

A later controlled cloud_demo acceptance includes application writes; this task
authorized none. Before Gate D approve the existing acceptance fixture/write
scope and data compatibility explicitly. Traffic rollback preserves document,
Firestore and Tasks state; it is not a database/schema restore or fixture cleanup.

## 6. Validation, preservation and approval boundary

| Check performed in this preflight | Result |
|---|---|
| `make test PYTHON=.venv/Scripts/python.exe` | 1086 PASS, 57.87 s pytest; one existing Starlette/AnyIO deprecation warning |
| Historical negative/source, DEV/PROD/WIF, provenance and recovery contracts | Included unchanged in full suite |
| `python -m scripts.gcp.ci offline` | PASS; committed-source/preview contracts, no cloud credentials used by command |
| `make check` / `git diff --check` | PASS; existing LF/CRLF Git advisory only |
| Post-apply IAM comparison / explicit live contracts | No unexpected differences / 22 PASS |
| Current DEV revision, accepted artifact and source proof | PASS, read-only |
| Real CI-probe/WIF health / post-hardening new build / live restore | PENDING / NOT RUN / NOT RUN |

No application, workflow, Terraform or existing report was edited. The only new
tracked-scope deliverable is this report; evidence is ignored. All pre-existing
dirty file hashes, C.1 patch and other five worktrees are preserved. No commit,
push, merge, dispatch, build, IAM/WIF/IAP mutation, deployment or data write occurred.
Full diffs, before/after preservation checks and current evidence are local-only.
One preliminary artifact-list lookup used an incorrect run and returned an error;
it was not used as evidence. The correct run/artifact above was independently
retrieved and validated, with the failed lookup retained in private logs.

**Stop here.** Request separate Gate D authorization only for an explicitly
chosen, exact published candidate and agreed DEV data/recovery scope. For the
recommended B path, first obtain review/publication approval and new hosted CI;
then return that SHA for Gate D approval. This report is not a recommendation
to execute the alternative A command now. The real WIF/probe check must succeed
before build in any later authorized experiment; pending authentication evidence
is not converted into a successful preflight by local tests.
