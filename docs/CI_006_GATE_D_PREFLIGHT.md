# Gate D preflight after IAM hardening

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
