# Gate C.1 — rollback compatibility, legacy IAM and DEV readiness

2026-10-29. **BLOCKED for Gate D approval: unresolved legacy build-time IAM exposure.**
Historical source compatibility has a focused, locally validated Option A patch.
DEV recovery and feature-ref eligibility are independently qualified below; this
does not authorize a dispatch. The compatibility patch remains uncommitted and
unpublished for separate security review. No infrastructure change was made.

Worktree: `D:\Projects\tripse-ai-ci-integration`; reviewed local/remote HEAD
`c8fec8777cd6f77b88418216de8cd506035ff031`; [PR #7](https://github.com/piotrbarabasz/tripse-ai-demo/pull/7)
remains open/unmerged. Its hosted success covers that SHA, not this new patch.
The pre-existing Gate C documentation changes were preserved byte-for-byte.
This report supplements [Gate C](CI_006_GATE_C_READ_ONLY_AUDIT.md), rather than
rewriting its recorded observations. Raw evidence remains ignored locally under
`local-data/phase-b-gate-c1/` and the original Gate C directory.

## 1. Exact historical failure and trust evidence

Target: `497ea150b158bd10ec347e8bdc2b6b44dc94d2a4`.
Important scope correction: Gate C's rejection was in the standalone source
audit/current source verifier. **No failed PROD rollback was executed or observed.**
The current PROD coordinator intentionally delegates source trust to accepted
master PROD evidence for rollback; it does not call Cloud Build/source verification
under the PROD identity. That existing authority boundary remains unchanged.

| Stage / rule | Expected | Observed / conclusion |
|---|---|---|
| Accepted PROD evidence | Trusted repository, Delivery/master, exact run/attempt/job and immutable artifact, unexpired, accepted/source_verified, smoke | Artifact `12853705896`, run `40770794487`, attempt 1, master policy SHA equals target; current production parser/proof validation PASS |
| Digest | Accepted digest must identify the retained image | `sha256:4bf16a5a8fc9aafa11576e8e91444e6ca4c8ac773c64e7c8df342e409771b2e6`; present under the immutable target tag |
| Cloud Build | Successful reviewed builder/recipe/SHA/digest | Build `23f06da9-270d-4250-bdc8-670c37bd3267`, SUCCESS, dedicated `tripse-ai-build`, all recipe checks PASS |
| Source availability | Exact immutable object generation | `source/1793222622.621063-7752a488b68545e299accf95b4072e90.tgz`, generation `1793222623879833` in the reviewed source bucket; readable |
| Current source rule before patch | Current `source_files(target)` plus baked target SHA; exact names/types/bytes | Rejects five extra legacy fixture files in `validate_archive`, surfaced as `invalid_source_archive_bytes` |
| Historical committed rule | Four root inputs, app, legacy trips/campaigns and the Iceland preset | Archive exactly matches that commit's original context; common files are unchanged |
| Retained revision | Correct service/digest/SHA/mode and Ready | `tripse-ai-prod-00006-5mb` passes current snapshot/revision contract; zero traffic is expected for a superseded revision |

Actual recipe is the reviewed single gcb-internal step:
`docker build --network cloudbuild --no-cache -t IMAGE:FULL_TARGET_SHA .`.
No builder, recipe, run/attempt, expiry, environment, schema, SHA/digest or missing
archive failure caused this source-audit rejection. The current GitHub artifact
still expires at `2027-01-26T21:18:07Z` and passed live validation during C.1.

The five historical additions are:

- `demo-fixtures/campaigns/demo-northern-journeys.json`
- `demo-fixtures/document-presets/iceland.json`
- `demo-fixtures/trips/demo-canada.json`
- `demo-fixtures/trips/demo-iceland.json`
- `demo-fixtures/trips/demo-norway.json`

This is a historical context interpretation regression for source verification,
not evidence of tampering and not proof that the PROD coordinator itself would
reject the artifact. Current build-context strictness is intentional; applying
the new fixture layout retroactively to this trusted old context is the mismatch.

## 2. Selected remediation: Option A, one explicit historical policy

The local patch in `scripts/gcp/build_proof.py` adds code-owned policy
`legacy-fixtures-497ea150-v1` for **only the exact target SHA**. It additionally
binds the precise repository image, Build ID, digest and a canonical manifest:

`59284ce900e3e41c080117c485a4469810ef4e24bc629fbef1d7aec2a3228cd7`

The manifest hashes a sorted list of all 75 expected committed file names and
their content hashes; baked SHA is separately required, yielding 76 archive
files. It was derived independently from the immutable commit, its historical
contract, accepted master PROD evidence and the actual trusted build archive.
The policy's fixed five additions are read from that exact Git commit and undergo
the same filename/credential checks as current source. Any manifest drift fails
before cloud lookup. No SHA prefix, ancestry range, runtime flag, artifact policy
claim or archive-supplied allowlist can activate it. Unsupported old releases
remain under the current strict policy; this does not approve the other 22 old
context failures or the three missing qualifying proofs from Gate C.

New-build `deployment.source_files()` membership is unchanged. Its existing safety
checks were factored into `validate_source_file()` for shared use. Portable POSIX/
Windows absolute, drive and backslash/traversal rejection was strengthened during
negative testing. Secret detection patterns were retained, not weakened.
`validate_recipe`, `validate_archive`, CI evidence authorization, PROD delegation,
workflows, WIF, Terraform, dependencies, Dockerfile and application code are unchanged.

A source proof does **not** authorize rollback: the separate accepted PROD
artifact/run/attempt/ref/job/expiry/acceptance checks still apply. PROD gets no new
source-read permission and does not rebuild. Rebuilding the historical SHA with
a different Build ID does not receive this exception.

The real generation-pinned archive passes the patched verifier, and the real
accepted PROD artifact separately passes existing `release_proof`. Retained
revision checks also pass. This establishes source/evidence compatibility, not
permission for live PROD rollback or application-data/schema recovery.

Code rollback: reverse only this C.1 patch in build_proof/deployment and its new
tests after review. That restores strict rejection of this historical context;
it does not change a service, artifact, IAM policy or stored data. No reset/clean
of the integration worktree or other worktrees is appropriate.

## 3. Validation and review boundary

| Check | Result |
|---|---|
| New deterministic historical/authorization/feature-ref cases | 51 PASS |
| Focused historical + existing provenance/rollback/DEV-PROD/deployment/bootstrap tests | 301 PASS, one existing warning, 3.18 s pytest |
| `make test` | 1057 PASS, one existing Starlette/AnyIO warning, 54.03 s pytest |
| Offline committed-source deployment contracts | PASS, no cloud operation |
| `make check`, `git diff --check` | PASS |
| Read-only real target source/artifact/revision validation | PASS |

Negative cases cover untrusted policy declarations/other SHAs, wrong image/digest/
Build ID, builder/project/status/recipe/generation changes, extra/missing/changed/
duplicate/symlink archive entries, baked SHA and manifest drift, secrets and
unsafe paths, expired/unaccepted/wrong-run/attempt/ref/workflow/repository evidence,
and every PROD operation attempted from the feature ref. Existing tests remain.
Initial test-only fixture-tag and Windows absolute-path failures were corrected;
the full final suite then passed. Their summary and final logs remain ignored
locally; the original failure output is retained in the session transcript.

Browser/container checks were not repeated: no app, schema, dependencies, Docker
recipe/runtime or storage implementation changed. Existing Gate A runtime evidence
is historical; C.1 does not claim a new container/deployment acceptance. Offline
source export uses actual committed HEAD; the security patch has no release SHA
or hosted validation yet. Separate review and authorized publication/new hosted
checks are required before treating a patched SHA as a reviewed candidate.

## 4. Legacy IAM: exact finding, dependency analysis and operator proposal

| Identity | Meaning |
|---|---|
| `690165197462@cloudbuild.gserviceaccount.com` | Legacy default worker; direct, unconditional project-level `roles/cloudbuild.builds.builder` grant observed live |
| `tripse-ai-build@tripse-ai.iam.gserviceaccount.com` | Restricted user-managed worker explicitly used by all 29 inspected regional builds |
| `690165197462-compute@developer.gserviceaccount.com` | Current default reported by Cloud Build in europe-central2 and global |
| `service-690165197462@gcp-sa-cloudbuild.iam.gserviceaccount.com` | Separate Google Cloud Build service agent; do not confuse it with either worker |

The live legacy role contains project-wide storage object get/list/create/update/
delete. DEV's custom role includes `cloudbuild.builds.create`. Effective
`cloudbuild.useBuildServiceAccount` and `cloudbuild.useComputeServiceAccount` both
report enforce=true; a Compute default is not proof that legacy use is disabled.
Google explicitly warns that builds.create can enable legacy-account build-time
privileges ([Cloud Build IAM permissions](https://docs.cloud.google.com/build/docs/iam-roles-permissions),
[default account behavior](https://docs.cloud.google.com/build/docs/cloud-build-service-account-updates)).

Thus there is a credible build-time privilege exposure for a principal that can
run feature-ref code and submit builds. The restricted explicit recipe and source
proof reject an unauthorized release after the fact; they are not a cloud IAM
boundary preventing side effects of an arbitrary build. No exploit build,
legacy-account impersonation or data-access test was executed. Deny/PAB effects
and full effective exploitability are not asserted; this risk is not closed by
the dedicated-builder project-policy check alone.

Complete pagination found 29 successful europe-central2 builds, all explicitly
using the restricted worker; global has zero builds. Both audited scopes have
zero triggers. No observed TRIPSE build depends on the numeric legacy worker.
Other regions, external tools and future callers remain dependency-review items.
The dedicated worker still has the intended scoped source/log/registry grants.

`retain_legacy_builder_grant` defaults false but targets **tripse-ai-build**, not
the numeric legacy principal above. It cannot remove this finding. Setting it
true would reintroduce broad permissions on the restricted worker. No Terraform
state was treated as live policy evidence, and no Terraform file was changed.

Operator-controlled infrastructure proposal, requiring separate approval:

1. Preserve the exact current binding, policy etag and effective org-policy
   baseline; finish dependency inventory for any other build regions/callers.
2. Keep the existing restricted worker and its scoped permissions; add no new
   privileges and do not transfer the broad role to Compute or the CI deployer.
3. Remove only the numeric legacy worker's broad project binding through a
   separately reviewed additive IAM/member change. Review restriction of legacy
   availability as a separate policy action if needed; do not widen WIF.
4. Re-read project/bucket/custom-role policies, confirm the worker and Google
   service agent remain intact, and re-run read-only preflight. A future separately
   authorized DEV build can validate real dependency behavior; C.1 cannot do so.
5. If an unobserved dependency breaks, stop feature dispatches and review the
   missing operation. Any IAM rollback requires explicit approval: restore only
   the exact prior binding/condition temporarily, never overwrite the whole policy,
   and time-box the reopened exposure. Prefer a documented scoped correction after
   identifying the dependency. No IAM rollback is automatic or executed here.

Risk of removal is failure of an undiscovered legacy-identity consumer, not loss
of the dedicated identity. Do not delete accounts, revoke service-agent roles,
rotate keys or apply Terraform as part of this repository patch.

## 5. Storage discrepancy: current bytes independently reconciled

Fresh repository `sizeBytes` remains **1,014,190,112**. File metadata pagination
returned **214 unique content-addressed files across 3 terminal pages**; the sum
of their sizeBytes is **exactly 1,014,190,112**. No file contents/image layers were
downloaded for this measurement. Current image inventory remains complete at 29.

The 29 per-image calculated sizes sum to 2,198,248,257 bytes and reuse stored
content, so they must not be substituted for unique repository bytes. All observed
image media types are Docker schema-2 manifests; no OCI index multiplier was
established. Expanded/uncompressed root filesystems were not measured. File/image
metadata definitions are distinct ([Files](https://docs.cloud.google.com/artifact-registry/docs/reference/rest/v1/projects.locations.repositories.files),
[DockerImage](https://docs.cloud.google.com/artifact-registry/docs/reference/rest/v1/projects.locations.repositories.dockerImages)).

Monitoring still returns 6,968,578,841 bytes at `08:07:19.930Z`, many hours older
than these GETs. Its descriptor says repository bytes, GAUGE, sample period 60 s,
ingest delay 120 s. This is not rounding, and compression or layer sharing alone
does not prove why two repository counters differ. Current GET/file accounting
is internally consistent; the historical metric emission/backend discrepancy
remains unexplained. Do not call it a billing/configuration defect without
time-aligned evidence. Billing integrates usage across time/account; no billing
export was queried. A later read-only metric/billing comparison is appropriate,
not an image push to provoke metrics. All images remain protected; no retention
or deletion action is proposed from these measurements.

## 6. Independent DEV eligibility and recovery

Fresh live DEV WIF condition matches the reviewed dev-oidc-policy.json exactly;
provider/pool are active. It binds repository/owner IDs, development subject,
event/ref and exact Delivery workflow ref. The exact branch
`refs/heads/ci/ci-006-integration-acceptance` satisfies the manual-dispatch prefix.
Current GitHub development Environment has no branch-policy restriction. No
Terraform assumption substituted for these live reads, and no policy was widened.

For workflow_dispatch, operation=dev, target_environment=dev, reviewed SHA:

| Job | Result from reviewed workflow conditions |
|---|---|
| Credential-free CI | Runs first |
| DEV | Runs only after CI success, in development Environment/global DEV lock |
| PROD | Skipped: required top-level master-ref conjunct is false; operation=dev also satisfies neither promote nor PROD rollback |

Independent coordinator tests allow the manual feature DEV path and reject
feature-ref DEV/promote/rollback attempts targeting PROD before any simulated
deployment. Workflow conditions/permissions and the coordinator were not changed.
An arbitrary SHA cannot substitute for a checked-out clean reviewed release;
future dispatch must verify remote branch/workflow SHA again.

Current DEV recovery baseline is `c3d3e922dae3c8bd15c5a8c78c4b4a51263074cf`, digest
`sha256:b4a86311712ace6ff894a346c465a74ecda4272a38b5599821f4d8d8c36ac28f`, receiving
revision `tripse-ai-dev-00031-z2l`, 100% traffic. Fresh snapshot and previous-revision
validators pass, as do full source proof and current accepted DEV artifact
`12882053228` / run `40839099491` / build `8061fc93-dcfe-470b-a65f-5112b8607b58`.
IAP/invoker policy and probe signing/IAP memberships were read; no public invoker.
The existing qualified older DEV references remain in Gate C evidence.

Automatic restoration validates snapshot identity/digest/readiness and freshness,
retains invoker IAM/IAP, restores the named revision traffic, then verifies private
health SHA/mode/environment, exact traffic and private policy. Failures never
turn a deployment into an accepted release; failure/recovery tests pass. No live
restore was invoked. An own-user authenticated GET /health returned IAP HTTP 401:
that does not establish CI-probe failure or success. Probe signJwt/real private
health remains a future preflight check before build, with no unauthorized
impersonation performed here. That preflight must fail closed if authentication
does not work; a traffic snapshot alone is not an end-to-end recovery drill.

DEV bucket is private/uniform/versioned, retains 20 newer object versions and
has seven-day soft delete. Firestore is the correct regional native DEV database
with PITR, delete protection and seven-day version retention. These are metadata
checks, not data restoration tests. Application and requirements have no diff
between deployed c3d3 and reviewed c8fec87, and this patch changes no schema/storage
implementation. Traffic rollback preserves existing GCS/Firestore/Tasks state;
it does not reverse data or queued work. Gate D's synthetic writes still require
explicit approval. Historical PROD compatibility is separate from this DEV baseline.

## 7. Gate D checklist and decision

- Verified: reviewed remote c8fec87/PR preserved, existing hosted checks pass;
  live feature-ref WIF/Environment eligibility, DEV-only job path and PROD skip;
  current DEV source/artifact/snapshot identity; storage protection metadata;
  synthetic recovery/failure/authorization contracts; complete local validation.
- Blocking: close the documented legacy IAM exposure through separately approved
  infrastructure review/remediation and verify the resulting boundary. No critical
  risk is waived merely because the normal recipe selects the dedicated worker.
- Pending: CI-probe authentication/health preflight and explicit acceptance of the
  recovery/data-write plan; this is not an observed live recovery drill.
- Choose the release scope: original reviewed c8fec87 can be evaluated for a
  DEV-only experiment after IAM closure without this historical policy patch.
  Including the patch requires separate security review, an authorized new commit,
  a newly reviewed full SHA and hosted CI; old hosted success does not cover it.
- Pending: explicit Gate D authorization. Do not merge or use master as a shortcut.
  A feature DEV artifact cannot authorize PROD. PROD history/retention/schema and
  deployment/rollback approval remain separate gates even after source compatibility.

No Cloud Build submission, Delivery dispatch, image publication, merge/push,
GCP IAM/WIF/Terraform/traffic/retention modification, live rollback or production
data operation occurred. The only cloud HTTP application request was the read-only
own-user DEV health check noted above. Raw tokens were never printed/persisted.
Stop for local security review; Gate D and production remain unauthorized.
