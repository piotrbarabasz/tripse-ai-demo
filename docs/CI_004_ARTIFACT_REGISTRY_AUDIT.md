# CI-004 — Artifact Registry audit, retention and release safety

CI-006 integration note (2026-10-29): this is the historical isolated-task report.
The selected implementation is now in the local integration candidate; current
combined validation and outstanding committed-source/hosted/cloud gates are in
[CI-006](CI_006_INTEGRATION_ACCEPTANCE.md). Original measurements below remain
attributed to their original worktree and source, not to a new release SHA.

2026-10-29. **Static audit and offline tooling verified; live GCP inventory BLOCKED.**
CI-004 is not fully verified. Worktree `D:\Projects\tripse-ai-ci-004`, branch
`ci/ci-004-artifact-registry-audit`, committed baseline
`e9731635fcf1dc424ccecebecc0299dafb7936b7`. CI-002 and CI-003 remain separate
uncommitted work; neither was merged/copied. CI-003's report was read from its
worktree and its recommendation to retain Cloud Build is preserved.
ADR-0015 remains **proposed**. No commit, push, merge, deployment or infrastructure change.

## Scope and evidence boundaries

Reviewed the CI/CD plan, ADR-0015, CI-003 report, GITHUB_CICD, DEPLOY_GCP, the
2026-10-28 release record, deployment/contract/build_proof/ci modules, delivery
workflow, GitHub Actions Terraform including builder isolation, and existing
deployment/provenance/rollback tests. No application data was read. No container
build/run or volume operation was performed; application data and Docker volumes
were not modified. `make check` only validates Compose configuration.

| Evidence class | What this audit establishes |
|---|---|
| Committed configuration | Static intent and implemented validation at the baseline above |
| Historical release records | Accepted deployment identities recorded on 2026-10-28 |
| Current GitHub observation | Two known artifacts downloadable, unexpired, matching existing `validate_proof()` contracts |
| Current GCP observation | Unavailable: authentication refresh failed before policy retrieval |
| Proposal | Conservative retention classes, manual review, offline helper and cost scenarios; no policy applied |

`gcloud auth list` found an active configured account, and configured project was
`tripse-ai`. The first identity/IAM preflight, `gcloud projects get-iam-policy
tripse-ai --format=json --quiet`, failed with:
`Reauthentication failed. cannot prompt during non-interactive execution.`
No IAM policy was obtained. Consequently effective account roles, including whether
it has broad administrator rights, could not be established. No login, account
switch, impersonation, IAM grant or privilege expansion was attempted. Further GCP
queries were stopped. This is not evidence that the registry is empty or inaccessible
to every identity. A usable, already authorized read-only identity is required.

## Repository configuration and inventory

Static sources: `infra/gcp/github-actions/main.tf`, `builder-isolation.tf`,
`scripts/gcp/deployment.py:repository/setup`, deployment contract image property,
and recorded release evidence. Example env files deliberately leave project blank;
they are not evidence of current live deployment values.

| Property | Reviewed configuration / historical expectation | Current live verification |
|---|---|---|
| Project / number | `tripse-ai` / `690165197462` | Not verified |
| Region | `europe-central2` | Not verified |
| Repository | `tripse-ai`, Docker format | Not verified |
| Repository resource | `projects/tripse-ai/locations/europe-central2/repositories/tripse-ai` | Not verified |
| Release image package | `europe-central2-docker.pkg.dev/tripse-ai/tripse-ai/tripse-ai` | Not verified |
| Tag policy | Full lowercase commit SHA; immutableTags required by existing code | Not verified |
| Cleanup policies / dry-run flag | No cleanup policy declared in reviewed implementation | Unknown; absence in code is not absence live |
| Packages / images / tags | No live inventory obtained | **Not measured**, not zero |
| Timestamps / size distribution / repository sizeBytes | No live metadata obtained | **Not measured** |
| Repository / inherited project IAM | Scoped grants declared; see security section | Not verified |

The bootstrap path creates a Docker repository only if absent; CI-004 did not call
it. Repository IAM resources in Terraform do not establish a live repository's
cleanup state. There is no new registry, cache registry or production Buildx path.

## Release-to-image relationship and rollback holds

Current architecture remains:

```text
committed SHA -> allowlisted source + baked SHA -> Cloud Build ID
 -> generation-pinned source archive -> immutable SHA tag -> image digest
 -> DEV revision + acceptance -> accepted GitHub artifact -> same digest on PROD
```

`build_proof.verify()` checks builder service account, exact single-step
`docker build --network cloudbuild --no-cache -t TAG .` recipe, image digest and
archive bytes against `source_files(SHA)` plus baked SHA. Tag spelling alone is
insufficient. Promotion/rollback additionally checks repository/workflow/ref,
run/attempt/artifact identity, successful environment job, accepted/source_verified
flags, feature mode and evidence expiry. PROD requires master and the approved digest.

On 2026-10-29 read-only GitHub queries and in-memory ZIP inspection revalidated
the two known historical records using **unchanged** `ci.validate_proof()`:

| Field | DEV historical record | PROD historical record |
|---|---|---|
| Run / attempt | 40614584902 / 1 | 40614584902 / 1 |
| Artifact ID | 12784708088 | 12784523829 |
| Expired now? / expiry | false / 2027-01-26T01:21:51Z | false / 2027-01-26T01:21:51Z |
| Receiving revision | `tripse-ai-dev-00014-9jb` | `tripse-ai-prod-00004-gg5` |
| Previous SHA recorded | `71419ec4f55cf97ac8f0fc4ec3cee1145dcf4d5b` | `c87377d331220d54ee3be27dee3c2eba69cc6649` |

Both identify SHA `3f55a25276a7e92ce74b3e0c70460d4e967a0138`, Cloud Build
`379950bf-7772-464a-9f16-47bc02472efb`, and digest
`sha256:c9fdd47b93a49c3fbf27a5810c01f6d974fcd8faa3598950185d290a1a690566`.
See [sanitized read-only evidence](benchmarks/ci-004-historical-release-evidence.json)
and [original record](RELEASE_2026_10_28.md).

**Neither current DEV nor current PROD digest is established by those records.**
Registry existence, current traffic, zero-traffic/tagged revisions, source object
generation/content and the Cloud Build record were not reverified through GCP.
The two previous SHAs are unresolved recovery references, not confirmed usable
rollback images: their digest and own accepted artifacts must be mapped first.
Do not discard them because they are absent from today's active traffic.

Conservative holds include the recorded accepted digest, both previous SHAs, every
currently serving/tagged revision once inventoried, and every approved rollback
target. This audit does not enumerate all historical accepted releases. No actual
image has been declared unreferenced or eligible for deletion.

Automatic failed-deployment recovery restores recorded previous revision traffic
and verifies old health while retaining private access. Manual accepted-release
rollback selects a SHA and target-environment artifact and rechecks provenance.
Neither restores application storage/schema. Keeping a running revision is not a
substitute for retaining redeployment evidence and source artifacts. Cloud Run
imports images at deployment and retains the serving revision's copy; this does
not satisfy TRIPSE's separate registry/source-proof gates for future releases.
[Cloud Run image lifecycle and deploy permissions](https://docs.cloud.google.com/run/docs/deploying).

## Retention strategy — proposed, not applied

Immutable tagged artifacts cannot be deleted by cleanup policies. Keep rules take
precedence when an artifact matches both keep and delete rules. Configuring even
server-side cleanup dry-run changes repository configuration, so **no such dry-run
policy was installed**. The supplied tool is an offline classification exercise,
not a claim about the Cloud cleanup service's observed behavior.
[Official cleanup semantics](https://docs.cloud.google.com/artifact-registry/docs/repositories/cleanup-policy).

| Class | Retention decision |
|---|---|
| Protected | Retain active DEV/PROD, traffic/tagged revisions, approved rollback references and failure-recovery targets, even with incomplete proof |
| Historically retained | Retain accepted/historically significant evidence references; expired evidence requires investigation, not deletion |
| Unclassified | Retain unknown provenance, incomplete inventory/references, missing artifacts or unresolved previous SHAs |
| Potential cleanup candidate | Only untagged >=90 days with reviewed provenance, complete reference checks and no holds; operator investigation/approval still required |

The 90-day candidate age is a conservative **proposal**, not a configured policy or
an entitlement to delete. Immutable SHA-tagged releases remain retained regardless
of age/count. Do not disable immutability or move tags to implement retention.
Revisit low-cost storage growth before considering a different release contract.

Recovery depends on the intersection of image availability, accepted artifact,
Cloud Build metadata and exact source-object generation. Workflow artifacts request
90-day retention; known artifacts currently expire 2027-01-26. Build source bucket
`tripse-ai_europe-central2_cloudbuild` and log bucket
`690165197462-europe-central2-cloudbuild-logs` have scoped IAM declarations, but their
live lifecycle/retention/soft-delete settings were not read. No build history or
source retention period is assumed. Preserve evidence at least for the approved
rollback horizon; archive/reverification design requires separate review before
any change to accepted evidence behavior.

An additional code limit matters: `build_proof.verify()` searches the most recent
**1000 successful builds**. An old retained image/source can fall outside that
lookup window. Merely retaining images indefinitely does not guarantee indefinite
rollback. CI-005 should test this boundary and design any reviewed fix without
accepting unverified tags or weakening recipe/archive checks.

## Storage and costs

Actual repository bytes, image/tag counts, monthly growth, billing currency and
charges are **Not measured**. Do not substitute CI-003 local image sizes or sums
of image sizes for billable repository storage. Shared layers make these different
quantities. Prefer repository `sizeBytes`, time-series samples and actual billing
export when available. [Repository metadata](https://docs.cloud.google.com/artifact-registry/docs/reference/rest/v1/projects.locations.repositories).

Pricing checked 2026-10-29: USD **$0.000136986/GiB-hour**, first **0.5 GiB-month**
free across the billing account, not per repository/project. At an assumed 730 h,
this is approximately $0.10/GiB-month. Currency-specific SKUs, taxes, scanning,
egress, build/source/log storage and discounts are excluded.
[Official pricing](https://cloud.google.com/artifact-registry/pricing).

Illustrations only; free allowance available here could be 0–0.5 GiB:

| Assumed total storage | Monthly USD estimate, 730 h |
|---|---:|
| 1 GiB | $0.05–0.10 |
| 5 GiB | $0.45–0.50 |
| 10 GiB | $0.95–1.00 |

Formula: `730 × 0.000136986 × max(0, GiB − available_account_free_GiB)`.
Example growth assumption of 30 images/month × **50 MiB new unique bytes/image**
adds 1.465 GiB/month and about $0.146/month to subsequent storage run rate before
remaining free allowance. This is not an observed release rate or realized cost;
first-month accrued cost depends on upload times. Another 1 GiB of billable build
cache would add about $0.10/month. No registry-backed cache was introduced.
No measured savings or deletion-benefit estimate is claimed.

## Security and IAM observations

| Responsibility | Static evidence and remaining check |
|---|---|
| GitHub | WIF trust binds immutable repo/owner IDs, environment, allowed event/ref and delivery workflow; production is master-only. No CI-004 workflow/auth changes |
| DEV deployer | Repository reader; DEV-only build submission and actAs builder; target-service Run admin and scoped source bucket access |
| PROD deployer | Reader and target-service admin; no declared build submission/builder actAs; accepted digest promotion |
| Builder | `tripseBuildRegistryPush` scoped to existing repo; upload/download and tag metadata, **no versions.delete/repository.update**. Project metadata/logging role; scoped build source/log buckets |
| Legacy grants | Terraform defaults `retain_legacy_builder_grant=false`; current absence of broad builder role is unverified. Existing PROD prerequisite checks detect unreviewed DEV/builder project roles |
| Runtime identities | App runtime access is separate from builder/deployer; do not grant registry writer to application SAs for an audit |
| Cloud Run image import | Inspect Cloud Run service agent and deployer repository access/inherited project grants separately from application runtime SA. No current pull permission was verified |
| Operator | Use already configured read-only metadata access. Effective operator roles unknown after auth failure; no admin fallback or IAM expansion |

No live excessive grant is asserted without policy evidence. Repository IAM alone
does not reveal inherited project/folder/organization grants or deny policies.
Review those with existing authorized read access; if unavailable mark incomplete.
Do not run Terraform setup/import/plan/apply to answer an inventory question.

## Minimal offline tool and dry-run result

`scripts/gcp/registry_audit.py` uses only the standard library and captured JSON.
It has no network/cloud client, token reader, provisioning, delete or apply mode.
It merges tags for the same full image URI, keeps identical digests in different
packages separate, validates recorded page-token chains, timestamps/sizes and
repository identity, and reports incomplete evidence conservatively. Supplied
reference/review annotations are operator assertions, **not production proof**.
Reference review must include OCI index/child-manifest and signature/referrer
relationships; this small analyzer does not resolve that graph automatically.
Unknown relationships remain unclassified, never inferred disposable from no traffic.
Output has `production_acceptance=false` and `safe_to_delete=false` for every row.
An expired/missing artifact never removes an active/rollback hold.

```powershell
.venv/Scripts/python.exe -m scripts.gcp.registry_audit --snapshot tests/fixtures/registry_audit/synthetic.json --output local-data/ci-004/new-synthetic-report.json
```

Output must not already exist and cannot overwrite the input. Exit 0 means a
complete **supplied snapshot**, exit 1 means incomplete audit evidence, exit 2
invalid input/CLI; none authorizes a destructive action. Partial pagination is
not returned as a complete empty inventory. Known references missing from the
inventory remain unresolved and block all candidate classifications.

The committed fixture is **synthetic only**: 6 images, 4 tags, 1 package; result
2 protected, 1 historically retained, 2 unclassified and 1 potential candidate.
There are **zero safe-to-delete recommendations**. It includes shared DEV/PROD
reference, expired rollback and historical evidence, unknown provenance and an
old reviewed untagged candidate. [Synthetic output](benchmarks/ci-004-synthetic-dry-run.json)
is not a GCP inventory, usage measurement or deletion plan.

## Operator read-only procedure

After separately restoring authorized **read-only** access, use the reviewed
project/region explicitly. If permissions fail, stop that check and record the
gap; do not request broader grants or use administrator credentials for this tool.
The following are metadata-only examples, **not commands executed by this audit**:

```powershell
gcloud artifacts repositories describe tripse-ai --project=tripse-ai --location=europe-central2 --format=json
gcloud artifacts repositories get-iam-policy tripse-ai --project=tripse-ai --location=europe-central2 --format=json
gcloud artifacts docker images list europe-central2-docker.pkg.dev/tripse-ai/tripse-ai --project=tripse-ai --include-tags --format=json
gcloud run services describe tripse-ai-dev --project=tripse-ai --region=europe-central2 --format='json(metadata.name,status.traffic,status.latestReadyRevisionName,spec.template.spec.containers.image)'
gcloud run services describe tripse-ai-prod --project=tripse-ai --region=europe-central2 --format='json(metadata.name,status.traffic,status.latestReadyRevisionName,spec.template.spec.containers.image)'
gcloud run revisions list --service=tripse-ai-dev --project=tripse-ai --region=europe-central2 --format='json(metadata.name,metadata.creationTimestamp,status.imageDigest,spec.containers.image)'
gcloud run revisions list --service=tripse-ai-prod --project=tripse-ai --region=europe-central2 --format='json(metadata.name,metadata.creationTimestamp,status.imageDigest,spec.containers.image)'
gcloud builds describe 379950bf-7772-464a-9f16-47bc02472efb --project=tripse-ai --region=europe-central2 --format='json(id,status,images,results.images,sourceProvenance.resolvedStorageSource,serviceAccount)'
gcloud storage buckets describe gs://tripse-ai_europe-central2_cloudbuild --format=json
```

Capture create/update times, tags/digests, repository sizeBytes, cleanupPolicies and
cleanupPolicyDryRun. Inspect build-source object **metadata for its exact generation**
once resolved; do not enumerate or read application buckets/Firestore. List all
revisions, including zero-traffic/tagged ones, and all approved rollback artifacts.
Resolve both previous SHAs above. Preserve build identity/source references before
artifact expiry. Inventory projections above do not replace full production proof.

For the helper, use the REST Repository and DockerImage schemas, not an assumed
gcloud flattened-list shape. Save each DockerImage list response in this wrapper:

```json
{"request_page_token":"", "response":{"dockerImages":[], "nextPageToken":"NEXT_IF_PRESENT"}}
```

Follow every nextPageToken with a matching request_page_token; only the last response
may omit/empty nextPageToken. Record failures as an error page or snapshot errors.
The fixture documents the full envelope: observed_at, repository, image_pages,
references, reviews, coverage. Use actual capture time; remove `synthetic` for operator
snapshots. Start all coverage flags false; mark registry/services/revisions/
release_evidence/rollback/build_sources true only after complete current checks.
Do not fill unknown fields with zero or invent a digest from a tag/SHA. Keep sanitized
metadata in ignored local-data; never store bearer tokens, credentials or app data.
[DockerImages list API](https://docs.cloud.google.com/artifact-registry/docs/reference/rest/v1/projects.locations.repositories.dockerImages/list).

## Validation, risks and next step

`make test`: **881 passed**, one existing Starlette/AnyIO warning, 63.63 s.
Includes 37 new synthetic inventory tests: empty/multi-tag/shared-digest cases,
DEV/PROD/rollback references, expired/missing proof, unknown provenance, pagination,
partial failures, unexpected metadata, immutable tags, coverage gaps and CLI
overwrite/apply rejection. Existing image/source provenance and deployment/rollback
tests ran unchanged. Offline CI/deployment contracts and `make check`: **PASS**.
`git diff --check`, documentation links and proposed ADR status: **PASS**.
Final file-hash and Git-status comparison confirms CI-001, CI-002 and CI-003
worktrees are unchanged. Production deployment modules, workflows, Terraform,
Dockerfile, Compose and dependency files have no diff against the baseline.

Live inventory/usage/IAM, actual cleanup configuration/behavior, complete rollback
set, source-generation availability and current DEV/PROD digests remain unverified.
Known GitHub artifacts passed current availability and record-contract checks;
that cannot close those GCP gaps. All actual images stay on hold pending inventory.

Recommended CI-005 scope, **not implemented**: validate current Cloud Run revision
and traffic against digest and evidence; test stale/expired/missing/tampered
run-attempt artifacts, failed-deploy recovery, exact-digest manual rollback and the
1000-build proof lookup boundary. Confirm source/evidence retention meets the
agreed rollback horizon. Begin with read-only/offline contracts; any actual deploy,
rollback drill or live configuration change needs its separate authorized task.
