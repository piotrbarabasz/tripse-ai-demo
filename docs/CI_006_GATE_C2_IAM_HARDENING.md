# Gate C.2 — Cloud Build IAM hardening and DEV readiness

2026-10-29. **READY FOR IAM CHANGE APPROVAL — proposal only; Gate D is not approved.**
The precise proposed cloud change is removal of one unconditional legacy-worker
IAM member. No IAM/state mutation, build, deployment or publication occurred.
An isolated Terraform module, offline plan guard and operator procedure are ready
for review. A real imported-state removal plan still requires separate approval.

Worktree: `D:\Projects\tripse-ai-ci-integration`; branch
`ci/ci-006-integration-acceptance`; reviewed HEAD
`c8fec8777cd6f77b88418216de8cd506035ff031`.
[PR #7](https://github.com/piotrbarabasz/tripse-ai-demo/pull/7) remains open/unmerged
at that SHA. Its hosted CI success does not cover these uncommitted changes.
The [Gate C](CI_006_GATE_C_READ_ONLY_AUDIT.md) and [C.1](CI_006_GATE_C1_REMEDIATION.md)
reports, C.1 source/tests and its remediation.patch were preserved byte-for-byte.
Reverse patch check confirmed C.1 was already applied; it was not applied again.

## 1. Evidence scope and current identities

Existing-account read-only gcloud access succeeded. Current project/organization,
service-account, custom/predefined role, repository, source/log/document bucket,
Cloud Run, WIF and IAP policies were captured under ignored
`local-data/phase-b-gate-c2/`. Tokens and raw JWTs were never persisted or printed.
No state file or Terraform state was used as evidence of live IAM.

| Principal | Current role and boundary |
|---|---|
| `690165197462@cloudbuild.gserviceaccount.com` | Google-owned legacy worker. Direct unconditional project `roles/cloudbuild.builds.builder`; broad storage/registry/build permissions |
| `tripse-ai-build@tripse-ai.iam.gserviceaccount.com` | User-managed explicit worker. Project metadata/logging; source reader; dedicated log object user; repository-scoped push |
| `tripse-ai-dev-ci-deploy@tripse-ai.iam.gserviceaccount.com` | DEV WIF identity. Inspect + build submit; actAs dedicated worker and DEV runtime; DEV service admin; DEV probe signing; source create/read; registry reader |
| `tripse-ai-prod-ci-deploy@tripse-ai.iam.gserviceaccount.com` | PROD WIF identity. Inspect/registry reader, PROD service admin/runtime actAs/probe signing; no observed build-submit or source-object reader grant |
| `service-690165197462@gcp-sa-cloudbuild.iam.gserviceaccount.com` | Cloud Build service agent, with separate platform-orchestration role. Not the legacy worker; must remain intact |
| `690165197462-compute@developer.gserviceaccount.com` | Current default returned by Cloud Build. No direct SA policy bindings or project role grant were found in the inspected policies |
| `tripse-ai-dev-ci-probe` / `tripse-ai-prod-ci-probe` | Separate probe identities, own-environment IAP/Run access and matching deployer token-creator binding |
| `tripse-ai-dev` / `tripse-ai-prod` | Runtime identities. Environment document-bucket object access and database-conditioned Firestore user roles |

Dedicated worker/deploy/probe/runtime accounts are present and enabled. The project
is directly under the inspected organization, with no intermediate folder. No
additional named worker/CI grants were found in its readable organization policy.
Allow policies do not constitute a complete deny/PAB/group/effective-permission
simulation; there was no impersonation or attack build.

**Permission gap:** direct IAM-policy inspection of the Cloud Build service agent
was denied with `iam.serviceAccounts.getIamPolicy`. Its project platform-role
binding is readable, but absence of separate impersonation bindings on that
Google-managed identity is not proven. No privilege was added to obtain this read.
This does not prevent reviewing/removing a different, precisely identified worker
grant, but it remains an explicit limit on the wider impersonation analysis.

## 2. Capability map and scope of the broad grant

- Build submission: DEV has custom `tripseCiBuild` (create/get/list/service usage).
  PROD has no such grant. The legacy worker and service agent have platform/build
  capabilities in their own predefined roles; they are not GitHub WIF identities.
- User-managed worker selection requires actAs. DEV's observed actAs covers the
  dedicated builder and DEV runtime, not arbitrary PROD/Compute accounts. Its DEV
  runtime authority already permits DEV data access indirectly through deployment.
- Source objects: DEV creator/viewer and worker viewer are scoped to the approved
  source bucket. PROD does not gain source-object access for accepted promotions.
- Logs: worker objectUser and bucket metadata are scoped to the existing build-log
  bucket. That permits log-object writes, not project-wide application storage.
- Image publication: worker `tripseBuildRegistryPush` is scoped to repository
  `tripse-ai`; its live definition has no delete permission. Deployers are readers.
- Application data: runtime document grants are environment-specific and Firestore
  grants are database-conditioned. The legacy worker's unconditional project role
  includes storage object get/list/create/update/delete at the allow-policy level,
  potentially covering PROD documents; no application object was read to test it.
- Cloud Run and IAM: each deployer has run.admin only on its target service,
  including service update/setIamPolicy, and its own runtime/probe bindings.
  The worker roles do not give project IAM mutation or Cloud Run admin. A human
  project Owner can alter project IAM; that is distinct from CI workload authority.
- The Cloud Build service agent has broad managed platform permissions, including
  token/storage/registry orchestration. Its role is not the deletion target and
  must not be reassigned to the worker or deployers.

Live dedicated-worker custom role definitions and source/log/registry bindings
match the intended scoped permissions. The existing production-isolation check
passes for the dedicated identities but does not establish legacy-account safety.

`retain_legacy_builder_grant` in the existing bootstrap targets the **user-managed
tripse-ai-build** worker. Its default false does not manage the numeric legacy
account. Toggling it true would add broad authority to the wrong identity. No
existing Terraform or WIF definition was changed to implement this cleanup.

## 3. Actual execution identity and threat model

Complete fresh REST pagination found 29 successful europe-central2 builds, all
recording the dedicated user-managed serviceAccount; global has zero builds.
Both inspected trigger scopes are empty. Current accepted builds and the C.1
historical target were independently re-described and their full source verified.
No observed TRIPSE build uses the legacy worker. Other regions/external tools are
operator dependency-review items before applying a cleanup.

`deployment.build()` explicitly passes the dedicated account and owned source/log
buckets. Its new-submit/wait path never retries without the selected identity.
Existing-tag reuse returns no new build and still requires provenance checks;
that lookup is not a fallback to a default worker. Metadata is consistent with
this explicit configuration; original API request traces were not reconstructed.

Cloud Build currently reports Compute as the default. Effective useBuildServiceAccount
and useComputeServiceAccount policies both report enforced. Therefore **builds.create
alone is not proof of arbitrary service-account impersonation**, nor proof that
omitting the account would select the legacy worker in this project. User-managed
selection is separately bounded by actAs; no arbitrary PROD identity path was
demonstrated. Google nevertheless documents legacy-account build-time escalation
risks ([IAM permissions](https://docs.cloud.google.com/build/docs/iam-roles-permissions),
[user-managed workers](https://docs.cloud.google.com/build/docs/securing-builds/configure-user-specified-service-accounts),
[default selection](https://docs.cloud.google.com/build/docs/cloud-build-service-account-updates)).

Confirmed facts are the broad legacy authority, feature-ref DEV WIF/build-submit
capability, live actAs scopes, explicit limited normal worker and current default.
Legacy selection/exploitation through a different build configuration remains
unexercised; no create/dry-run build request or legacy impersonation was attempted.
If a caller can execute using the legacy identity, its inherited storage authority
is material. Source/recipe verification can reject a release later but cannot
undo build-time data access. The proposed cleanup removes this unused observed
authority without claiming all possible platform escalation paths are proven closed.

## 4. Exact proposed infrastructure change

| Field | Planned value |
|---|---|
| Project | `tripse-ai` |
| Principal | `serviceAccount:690165197462@cloudbuild.gserviceaccount.com` |
| Role | `roles/cloudbuild.builds.builder` |
| Condition | None — existing unconditional binding |
| Action | Remove only this member, retaining other policy members |
| Added privileges/accounts | None |
| Other cloud changes | None |

New isolated module: `infra/gcp/legacy-default-builder-cleanup/`. It contains one
non-authoritative google_project_iam_member, default retain=false, using the same
import/removal convention and locked provider as the existing bootstrap. It has
no shared backend, WIF, accounts, service, bucket, role or repository resources.
The current bootstrap module and its legacy variable remain unchanged.

The intended result is the same limited worker with sufficient source/log/registry
permissions and metadata output, while the unused numeric worker loses its broad
project role. Current policies and 29 successful builds support that dependency
assessment; no new build was submitted to claim post-removal execution success.
The old default account is not deleted, no broad replacement role is given to
Compute, and the Cloud Build service agent is not altered.

## 5. Operator change and recovery sequence

The [module procedure](../infra/gcp/legacy-default-builder-cleanup/README.md) gives
exact commands, target address, isolated local state path and stop conditions.
Gate C.2 forbids state mutations, so no live-state import or removal plan was run.
Backend ownership, competing state/automation and other-region consumers must be
reviewed before executing the proposed isolated adoption.

1. Obtain approval for a new isolated local state, state-only import and plan.
   Use the current authorized account without ADC/account changes or persisted
   tokens; do not point at application/bootstrap state or copy production state.
2. Adopt only the existing member at
   `google_project_iam_member.legacy_default_worker[0]` with temporary retain=true.
   Never apply a retain=true creation plan. If the member is absent, stop/re-audit.
3. Plan retain=false and require exactly 0 additions, 0 updates and 1 deletion
   of that unconditional member. No account/service-agent/WIF/data changes.
4. Export JSON from the exact saved binary plan. The new offline
   `scripts.gcp.legacy_builder_plan` guard rejects missing/additional/wrong IAM
   targets, conditions, creates/replacements, moves/imports, drift/unknown/deferred
   or non-applyable plans. Its output still requires operator approval and never
   executes cloud actions. Keep binary/JSON/module hashes with the fresh policy
   evidence; the guard alone does not authenticate the binary or current IAM.
5. Seek separate approval for that actual saved plan before operator apply. Then
   re-read all affected/scoped policies, confirm no equivalent legacy broad grant
   remains and all dedicated/service-agent/WIF/immutable-tag/source-proof contracts
   remain. A changed plan or drift requires review again, not auto-approval.

Removal could break an undiscovered legacy consumer; it is not expected to affect
the explicitly selected worker. If a dependency fails, stop feature dispatches and
diagnose it. Any emergency restoration requires a separate human-reviewed plan
adding only the exact prior member, explicit approval and a time limit. Do not
overwrite project IAM, grant a broad role to the dedicated worker/Compute, or
weaken the deletion-only guard to accept a restoration. No recovery action was run.
Default count=0 is a cleanup operation after import, not a continuous denial of
grants added outside Terraform; follow-up IAM ownership/rechecks remain necessary.

## 6. DEV IAP 401 root cause

The manual request was reproduced using only the existing user identity and
GET /health. Sanitized observations show:

| Hypothesis | Evidence |
|---|---|
| Missing credentials | No: a nonempty Bearer user ID token was attached |
| Expired token | Returned token expiry was in the future |
| Wrong origin/service | No: URL matched current DEV PUBLIC_BASE_URL |
| Wrong audience | **Confirmed:** token aud matched neither configured IAP client nor allowed programmatic clients; IAP response explicitly reported invalid JWT audience |
| Missing user IAP membership | Not the observed cause: active user has direct IAP accessor binding |
| Backend Run invoker absent | IAP service agent has Run invoker on DEV |
| Application /health failure | Not established: iap_generated=true and 401 occurred before the application |
| CI probe identity broken | Not established: no CI probe token/request was made |

This is a manual credential/audience mismatch. No raw token, claims payload, body
or secret was retained; only booleans, audience hash and fixed classifications.
Do not add the gcloud client to IAP or make DEV public to force this request through.

The actual code path is different: `smoke_auth.probe_token` requires the dedicated
environment probe, uses the runner's WIF access token to sign a short-lived
service-account JWT, with iss/sub=probe and aud=origin/*, and keeps it in memory.
The caller has the observed matching probe token-creator binding and the probe
has IAP/Run membership. OAuth user ID-token client audiences and this service JWT
URL audience must not be conflated ([IAP guidance](https://docs.cloud.google.com/iap/docs/authentication-howto)).
`parity_smoke` disallows redirects/credential forwarding and verifies authenticated
health/runtime fields. Synthetic probe/recovery tests passed. No signJwt,
impersonation, service-account key, IAP change or GCP fixture write was performed.
A successful current CI-probe request remains a future authorized preflight check.

## 7. DEV-only eligibility, recovery and C.1 preservation

Live DEV WIF binds exact repository/owner IDs, development subject/environment
and Delivery workflow ref. Manual dispatch accepts refs/heads/ and therefore the
exact integration branch; production remains production/master-only. No WIF was
widened. Current development Environment settings were re-read: no branch restriction.
DEV variables match the live provider, deployer, probe, mode, origin and IAP client;
mock planning and DEV project/environment match. The WIF pool is active. These
settings must still be re-read immediately before a future dispatch.
The reviewed workflow runs CI first, then DEV on manual operation=dev/target=dev.
PROD is skipped both by the mandatory master-ref conjunct and operation mismatch.
Passing offline tests does not execute a job or approve a deployment.

Current DEV baseline remains c3d3e922…, digest b4a86311…, revision
`tripse-ai-dev-00031-z2l`, 100% traffic, cloud_demo/mock and matching runtime identity.
Fresh snapshot, exact current source proof, retained revision and private access
metadata checks passed. No public invoker binding was found. Current service,
source/archive and registry identity are distinct from the undeployed c8fec87 RC.

Restoration validates prior SHA/digest/revision/readiness/ownership/origin and
freshness; retains invoker IAM/IAP; restores named traffic; checks private health
SHA/mode/environment, traffic and IAM again; and never accepts a failed release.
Those safeguards were tested synthetically. A real traffic restore was not run,
so no end-to-end restore claim is made. Read-only metadata/source readiness and
the corrected manual-401 interpretation do not waive CI-probe runtime preflight.

C.1 compatibility was revalidated against the real immutable historical archive
and authentic PROD artifact, still bound to exact SHA 497ea150…, Build ID
23f06da9…, digest 4bf16a5a… and trusted manifest. Unsupported history/malicious
variants remain rejected. C.1 source/tests/report/patch hashes are unchanged;
neither it nor C.2 was committed or published. No PROD rollback occurred.

## 8. Tests, verification and remaining gates

| Evidence/check | Result |
|---|---|
| Focused identity/WIF/IAM/provenance/probe/recovery suites | 330 PASS, one existing warning, 3.22 s pytest |
| make test | 1086 PASS, one existing warning, 54.83 s pytest |
| Offline committed-source contracts, make check, diff check | PASS |
| Terraform fmt | PASS |
| Terraform init -backend=false -lockfile=readonly + validate | PASS in isolated disposable directory; no live backend or state |
| Real historical source/artifact and current DEV source/snapshot | PASS, read-only |
| Actual Terraform removal plan / import / apply | NOT RUN; requires state adoption approval |
| New build / CI-probe request / live restore | NOT RUN |

29 new synthetic plan cases reject missing/excessive grants, wrong worker/Compute/
service-agent targets, authoritative binding resources, conditional/different
project/role changes, unsafe actions, malformed/duplicate fields and incomplete
plans. Existing source, secret detection, negative provenance, WIF and missing/
excessive dedicated-IAM tests remain intact. No app/dependency/Docker runtime
change requires new browser/container execution. Raw evidence/logs remain ignored.

**Decision: READY FOR IAM CHANGE APPROVAL**, starting with approved isolated state
adoption and production of the actual one-member removal plan. A confirmed exploit
is not claimed, and removal of an unused broad grant does not certify every
platform permission path. Direct service-agent policy, other consumers/regions,
deny/PAB effects and post-change operation remain explicit review limits.

**Gate D remains blocked/pending** IAM resolution/recheck, current CI-probe private
health preflight, accepted recovery/write scope, exact SHA/WIF/Environment recheck
and separate deployment approval. If the C.1/C.2 patches are to be included in a
release, they require security review, authorized commit/publication, a new full
SHA and hosted CI. Existing c8fec87 hosted success is not inherited by local edits.

No Cloud Build submission, deploy/rollback/traffic operation, grant change, state
import/mutation, Terraform apply, WIF/IAP/retention change, image push/deletion,
production data operation or remote publication occurred. Stop for operator
approval of the next stage; no approval is inferred from these local checks.
