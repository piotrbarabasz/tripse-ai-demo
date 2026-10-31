# CI-006 Phase B Gate C — live read-only audit

2026-10-29. **GATE C PARTIALLY VERIFIED.** Authentication was restored. Current
resources, receiving release/source identity and readable IAM/WIF were verified.
Historical provenance compatibility, PROD rollback readiness and guaranteed
retention remain unresolved. Gate D was not executed or authorized.

Reviewed HEAD: `c8fec8777cd6f77b88418216de8cd506035ff031`.
Branch: `ci/ci-006-integration-acceptance`; [PR #7](https://github.com/piotrbarabasz/tripse-ai-demo/pull/7).
The RC is **not deployed**. This is a local, uncommitted report; no commit, push
or PR modification was made. ADR-0015 remains proposed.

## Authentication, scope and evidence

The 15:47:42 UTC probe failed with reauthentication required and all cloud queries
stopped. After the operator's continuation, the same active account/project was
checked; at 15:52:02 UTC `gcloud projects describe tripse-ai` succeeded. No account
switch, ADC change, impersonation, IAM grant or credential/key creation occurred.
Existing-account tokens were captured only in process memory for GET requests,
never printed or persisted. No application data or document objects were read.

Raw and sanitized observations, page chains and diagnostics remain only in ignored
`local-data/phase-b-gate-c/resume-2026-10-29/`: `analysis-summary.json`,
`provenance-results.json`, `github-release-evidence.json`, `live-snapshot.json`,
`live-retention-dry-run.json`, and per-resource captures. The initial blocked
report/results are retained there. Historical documents, current GitHub metadata
and live GCP observations are separate evidence categories.

## GitHub preflight

PR #7 remains open and unmerged at the reviewed SHA. Required check
`Tests and offline contracts` and final run `40900716604`/job `123541912593` passed.
Master requires this context with strict/up-to-date checks and zero mandatory
approvals. No reviews, review requests or review threads were returned. Only PR
CI is associated with this head; no unexpected Delivery execution was observed.
No GitHub setting, branch, workflow or PR was modified.

The current development Environment reports no protection rules and
`deployment_branch_policy=null`. Its separate custom branch-policy endpoint
returned 404; this does not establish a missing Environment. The successful
Environment GET is the evidence for its current branch-policy setting.

## Registry and complete inventory

Project `tripse-ai`, region `europe-central2`, repository `tripse-ai`:

| Observation | Live result |
|---|---|
| Format / mode | DOCKER / STANDARD_REPOSITORY |
| Immutable tags | true |
| Packages / versions / Docker images / tags | 1 / 29 / 29 / 29 |
| Untagged images | 0 |
| Cleanup policies | No policies returned by v1 repository GET |
| Cleanup dry-run flag | Omitted; not evidence that dry-run is enabled |
| Current v1 `sizeBytes` | 1,014,190,112 bytes (0.944538 GiB) |
| Sum of image sizes | 2,198,248,257 bytes; not billable repository storage |
| Vulnerability scanning | SCANNING_DISABLED; scanning API not enabled |

Images, packages, versions and tags were collected through v1 REST GETs with page
size 100 and retained request/response token chains. Each returned one terminal
page with no next token. Completeness was not inferred from gcloud's include-tags
display. SHA/digest/tag links, timestamps and sizes are retained in the snapshot.
All 29 images are referenced by retained revisions. No deletion/policy is authorized.

## Current DEV and PROD

Both services are ready, with 100% traffic to the listed latest ready revision:

| Environment | Receiving revision | Accepted artifact |
|---|---|---:|
| DEV | `tripse-ai-dev-00031-z2l` | 12882053228 |
| PROD | `tripse-ai-prod-00007-xsd` | 12882995327 |

Both currently identify:

- Source `c3d3e922dae3c8bd15c5a8c78c4b4a51263074cf`.
- Digest `sha256:b4a86311712ace6ff894a346c465a74ecda4272a38b5599821f4d8d8c36ac28f`.
- Accepted master Delivery run `40839099491`, attempt 1.
- Cloud Build `8061fc93-dcfe-470b-a65f-5112b8607b58`.
- Correct APP_ENV, mock planning, cloud_demo mode, ownership/environment labels,
  and separate `tripse-ai-dev` / `tripse-ai-prod` runtime service accounts.

Complete v2 revision pagination returned 31 DEV and 7 PROD revisions, all with
succeeded Ready conditions: 2 receiving and 36 zero-traffic revisions. Image,
environment, readiness and receiving status are retained for every revision.
Readiness alone is not recoverability or permission to change traffic.

Ingress is ALL, **not network-internal-only**. Both services report IAP enabled.
Invoker IAM disablement is absent/default false under the existing production
check. Service/project/organization readable allow policies have no public
allUsers/allAuthenticatedUsers bindings. IAP membership is limited to named users
and dedicated environment probe/task principals; the configured programmatic
client is present. No HTTP health test, signJwt, impersonation, human login test,
mock job or document write was performed.

The 2026-10-28 record's `3f55a252…` / `c9fdd47b…` release is historical, not today's
receiving image. The CI-002 pinned Dockerfile and integration RC are not claimed
deployed: live provenance is checked against the actual deployed SHA.

## Release evidence and exact provenance

Complete GitHub artifact pagination returned 32 accepted-release artifacts.
All 32 passed the current strict ZIP/JSON and run/attempt/job/ref/identity/expiry
metadata contracts. Listed artifacts are unexpired, with expiry dates between
2027-01-25 and 2027-01-27. This does not prove that no older artifact was deleted.

Current accepted records match live SHA, digest, revision, 100% traffic and Build
ID. Current build status, dedicated builder and exact approved recipe passed;
the generation-pinned archive was read and compared byte-for-byte with committed
allowlisted source plus baked SHA:

`gs://tripse-ai_europe-central2_cloudbuild/source/1793261173.446354-ced57aa0663a4e2fb5fc0396531b623f.tgz#1793261174920447`

The object is readable (157,221 bytes). Direct Build ID verification passed.
Separate no-hint targeted SUCCESS/image/digest discovery returned one candidate
and verified that same build/source. Page size 100 and the bound of 1000 matching
candidates were retained; the bound was not hit. No source bytes were normalized.

All 29 retained image tags were assessed with the production validator:

- **3 full current-policy proofs PASS:** current `c3d3e922…`, `777e0662…` (build
  `2ce6332e-86b1-4c30-a9af-b059d1bd7fb7`), and `eb89487d…` (build
  `36659b5c-387c-4894-860c-82e57915ba79`).
- **23 archive/context checks rejected.** They remain unverified under the
  reviewed current allowlist. No security assertion was relaxed.
- **3 targeted lookups returned no qualifying build:** `3729ee53…`, `b9c43a5f…`,
  `be798fed…`; no available accepted artifact supplied their Build ID. This does
  not mean the candidate bound was exhausted or an old build never existed.

The first Windows-native verification exposed Git archive CRLF conversion; its
failed results were retained. The successful run used process-local Git options
`core.autocrlf=false` and `core.eol=lf` to reproduce Linux production archive
semantics. No persistent config/worktree or downloaded bytes changed. The missing
local c3d3 commit object was fetched read-only without checkout/branch movement.
No application or validator code was changed for this audit.

## Rollback readiness and retention

Two DEV references have passing metadata, full source proof and current retained
revision contract (exact digest, Ready, APP_ENV and mode):

| SHA | Artifact | Retained revision |
|---|---:|---|
| `777e0662da5e57894371529f3af0bdafeb2fed11` | 12882430721 | `tripse-ai-dev-00030-9tr` |
| `eb89487d5e3859ec4b387646b9bc668772777dda` | 12880754593 | `tripse-ai-dev-00029-xsc` |

Snapshot/previous-revision validators ran read-only, without health requests or
traffic changes. These are qualified references, not a completed rollback drill
or a guarantee of application data/schema compatibility.

**The recorded previous PROD target fails current policy:**
`497ea150b158bd10ec347e8bdc2b6b44dc94d2a4`, artifact `12853705896`, run
`40770794487`, build `23f06da9-270d-4250-bdc8-670c37bd3267`. Its source archive
contains five extra legacy demo fixture files; common files match exactly.
That commit's original broader fixture allowlist was inspected read-only, and
exact-byte verification against that historical committed allowlist passes.
This establishes a **policy compatibility gap**, not evidence of source tampering.
Current-policy rejection was not overridden. No older distinct PROD release
obtained full current-policy proof in this audit. Owner review and a separately
scoped compatibility resolution are required before declaring that rollback ready.

Across accepted records, 27 previous SHA references resolve to retained tags; two
(`3729ee53…`, `be798fed…`) have no available accepted artifact. Unknown references
remain retained. Workflow artifact retention is configured for 90 days. The source
bucket has no returned lifecycle deletion/locked retention policy and has seven-day
soft delete. That does not guarantee a 90-day source retention horizon. Present
readability and artifact expiry do not establish future recoverability.

The existing analyzer consumed actual REST image pages, a real observation
timestamp, all current/zero-traffic/accepted/previous references, and explicitly
incomplete rollback/build-source coverage. Result: `complete=false`, **29 protected
images and every `safe_to_delete=false`**. Its incomplete-coverage diagnostic is
retained. No cleanup candidate is authorized; outputs remain ignored locally.

## IAM/WIF and remaining security findings

Readable project/organization/repository/service/source-log-document-bucket/
service-account/custom-role policies were compared with Terraform. Both WIF
providers and the pool are active. Live DEV trust binds exact repository/owner
IDs, development subject/environment and workflow ref; pushes are dev/master,
manual dispatch allows `refs/heads/`. Live PROD requires production/master.

Dedicated runtime/deploy/probe/builder identities are present and enabled. DEV
alone has the custom build-submit role and actAs binding on the dedicated builder.
Deployers have repository reader and target-service admin; probes have scoped
invoker/IAP/signing bindings. The dedicated builder has metadata/logging,
source-reader/log-bucket and registry push grants. Its actual push role has no
delete permission. Document-bucket direct runtime grants are environment-specific;
database user grants are database-conditioned. The existing project-level
production-isolation validator passed on live policy.

**Separate retained broad grant:** the legacy default Cloud Build account
`690165197462@cloudbuild.gserviceaccount.com` has project-wide
`roles/cloudbuild.builds.builder`. The live role includes storage object
get/list/create/update/delete. It is not the dedicated builder used by the verified
release. Record it for owner review; do not infer CI exploitability/impersonation
reachability or remove it automatically. The existing audit user has project
Owner; no privilege was added and no account switched.

These are readable allow-policy observations, not full effective-permission
simulation: group membership, deny/PAB effects and impersonation paths were not
exercised. No IAP, IAM, Environment or trust settings were changed.

## Storage and cost assumptions

Current v1 repository GET: **1,014,190,112 bytes / 0.944538 GiB**. Monitoring's latest
size sample is **6,968,578,841 bytes at 08:07:19 UTC**, older and inconsistent with
that GET. The discrepancy is retained, not silently reconciled. Image-size sums
double-count shared storage and are not the billed repository size.

The [official Artifact Registry price](https://cloud.google.com/artifact-registry/pricing?hl=en)
is $0.000136986/GiB-hour, approximately $0.10/GiB-month at 730 hours. If the GET
size remains constant, registry storage alone is approximately **$0.044–$0.094/month**,
depending on availability of the billing account's shared 0.5 GiB allowance.
This is a scenario from a point-in-time counter, not a measured bill. The stale
Monitoring discrepancy requires reconciliation. Build usage, transfer, source/log
storage, taxes/currency and other billing components were not measured.

## Remaining gates and safest proposed DEV path

Gate C is not fully verified: resolve historical source-policy/PROD rollback
compatibility, missing older proofs, the desired retention horizon, legacy broad
grant review and storage-counter discrepancy. Current receiving release/source
and private access settings are verified; deployment acceptance of the new RC is not.

After separately authorized review/resolution and explicit Gate D approval, use
the existing **manual DEV-only Delivery on the integration feature ref**, rather
than a dev/master push or PR merge. Current development Environment and live DEV
WIF permit this ref shape. Recheck the remote branch is still exactly
`c8fec8777cd6f77b88418216de8cd506035ff031`, then select operation `dev`, target `dev`
and that full release SHA in the existing workflow. PROD requires master, so this
feature-ref dispatch does not promote PROD. Do not widen trust if it changes.

Before that future action, capture current c3d3 DEV revision/digest and qualified
source/evidence recovery reference, verify private cloud_demo/mock configuration,
and approve the workflow's synthetic document/job writes. Require exact new
build/source proof, authenticated acceptance and an immutable DEV record. A
feature DEV artifact is not master provenance for later PROD promotion.

No dispatch, Cloud Build submission, image push, merge/publication, IAM/Terraform/
IAP change, deployment, traffic change, rollback or application-data operation
occurred. Original worktrees and the prior ignored QA-output limitation remain
preserved. Stop here; this report does not authorize Gate D or production.
