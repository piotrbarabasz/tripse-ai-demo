# CI-005 — release provenance, Cloud Run delivery and recovery hardening

CI-006 integration note (2026-10-29): this is the historical isolated-task report.
The selected implementation is now in the local integration candidate; current
combined validation and outstanding committed-source/hosted/cloud gates are in
[CI-006](CI_006_INTEGRATION_ACCEPTANCE.md). Original measurements below remain
attributed to their original worktree and source, not to a new release SHA.

2026-10-29. **Implementation and offline validation PASS; hosted delivery and live
rollback NOT VERIFIED.** Worktree `D:\Projects\tripse-ai-ci-005`, branch
`ci/ci-005-delivery-hardening`, base `e9731635fcf1dc424ccecebecc0299dafb7936b7`.
This committed base includes CI-001 caching, not the uncommitted CI-002/003/004
workstreams. Those worktrees were inspected and preserved, not merged/cherry-picked.
CI-003 recommends keeping Cloud Build; CI-004 documented blocked live GCP access
and the provenance discovery limit. Their reports were read in their own worktrees.
ADR-0015 remains **proposed**. No commit, push, merge, GCP mutation or deployment.

## Initial findings and preserved architecture

Reviewed ci/deployment/build_proof/deployment_contract/ci_config/parity_smoke/
smoke_auth, CI and Delivery workflows, GitHub Actions Terraform, existing tests,
GITHUB_CICD, DEPLOY_GCP, registry plan, CI-004, the recorded 2026-10-28 release and
ADR-0012/0015. Existing correct behavior remains:

```text
committed SHA -> CI -> allowlisted committed source + baked SHA
 -> Cloud Build --no-cache -> immutable registry SHA tag -> digest
 -> DEV deployment + deployed acceptance -> immutable GitHub artifact
 -> protected master PROD promotion of the same digest, without rebuild
```

PR checks remain credential-free. WIF, separate environment deploy/probe identities,
production Environment, branch/ref policy, concurrency groups, freshness checks,
IAP, private access and exact-source checks are unchanged. No workflow or Terraform
file changes; no Buildx, new registry, database, authentication or storage model.

Findings addressed:

1. Source proof searched only the 1000 most recent successful builds globally.
2. Fresh submission and accepted artifacts already know a Build ID, but the DEV
   verifier did not use it directly.
3. Artifact selection did not compare returned run/artifact IDs with requested IDs;
   runtime revision/traffic metadata, expiry timestamp and strict archive parsing
   needed stronger checks.
4. Previous-revision snapshots did not bind the revision to a resolved registry
   digest/readiness; recovery did not fully recheck revision/environment/privacy.
5. Evidence/output I/O failure after setting `accepted=true` could leave a misleading
   summary; summary I/O could mask the original deployment exception.

## Provenance options and selected solution

| Option | Evaluation |
|---|---|
| A: direct Build ID | Selected for new submissions and accepted DEV rollback. No recency dependency; ID is only a hint until full proof passes |
| B: targeted discovery | Selected for an existing tag without a hint. Filter by SUCCESS, exact result image name and digest before bounded enumeration |
| C: pagination | Reuse gcloud's regional pagination, page size 100 and limit 1000 matching records. No unbounded historical scan or new REST auth client |
| D: durable mapping | Existing release.json already records source_build_id. Retain it and its trust/expiry checks; no new infrastructure or evidence store |

`deployment.build()` returns the submitted ID after success/digest verification;
its existing-tag reuse path returns no hint. `execute()` forwards a fresh hint or
the validated DEV rollback artifact's ID to `build_proof.verify(g, sha, digest, id)`.
The optional fourth argument preserves existing three-argument callers.

Direct lookup performs **one regional `builds describe`**, verifies the returned ID,
project/resource identity where present, SUCCESS, dedicated builder, exact SHA and
digest, approved recipe, generation-pinned source and exact committed source bytes.
`validate_recipe()` and `validate_archive()` remain unchanged. An invalid/missing ID,
permission error, missing archive or failed proof never silently falls back to a
different build or accepts the tag. Old valid builds can be verified without listing
any of the newer unrelated builds. Tests require that direct lookup never lists.

When no hint exists, discovery now uses:

```text
status="SUCCESS" AND results.images.name="IMAGE:SHA" AND results.images.digest="DIGEST"
--region=europe-central2 --page-size=100 --limit=1000
```

The old global-recency sort is removed. It is unnecessary for finding a valid proof
and can force client sorting before limiting. gcloud handles pagination and API
failures. Every candidate is still locally validated, including matching name/digest
in the same output and the single approved image recipe; repeated-field filtering
is an optimization, not authorization. Malformed/partial API results fail closed.

Filtering semantics were checked against Google's documented supported fields and
the installed **SDK 590.0.1**. Its Cloud Build backend rewrites both fields into the
server filter, leaving **no client filter**, and passes it to the regional list API.
[Recorded offline rewrite](benchmarks/ci-005-filter-semantics.json).
This proves the installed CLI translation, not a successful live service query.
[Official filter syntax](https://docs.cloud.google.com/build/docs/view-build-results),
[regional list API](https://docs.cloud.google.com/build/docs/api/reference/rest/v1/projects.locations.builds/list),
[regional direct lookup](https://docs.cloud.google.com/build/docs/api/reference/rest/v1/projects.locations.builds/get).

The remaining 1000 bound is on **matching candidate records**, not the most recent
unrelated builds. If no candidate proves the release, the diagnostic explicitly
requires an exact Build ID for older history. More than 1000 same-image/digest
candidates can still require a direct hint. Missing permanently deleted build
metadata/source bytes cannot be recovered by this change; validation fails closed.
No fabricated mapping, tag-only proof or relaxed recipe is provided.

## PROD trust boundary and compatibility

PROD still consumes a validated accepted master DEV artifact for promotion, or an
accepted master PROD artifact for manual PROD rollback. It does not submit builds,
scan Cloud Build or gain source-bucket access. CI-005 does **not** add a new live
source-archive verification requirement to PROD: the original accepted DEV proof
delegation remains the existing authorization boundary. An arbitrary caller Build
ID cannot authorize PROD; the artifact/run/job/ref/mode/digest relationship must pass.
Direct full source verification is performed in DEV before emitting accepted proof.

This distinction avoids breaking the existing scoped PROD IAM. Continuous live
reverification of old build/source availability on PROD would require a separately
reviewed permission/design change, outside this task. Do not claim this offline
patch proves current availability of every historical source object.

The release recipe remains exactly `build --network cloudbuild --no-cache -t TAG .`;
no IAM/WIF/Terraform or image namespace changes. Existing published release fields
are retained; no schema version/migration or artifact reinterpretation is introduced.
Real legacy records already contain the required runtime fields. Incomplete external
or synthetic records missing expiry/runtime identity now fail rather than receiving
inferred values. Historical expired artifacts still fail.

## Release evidence checks

- Requested run/artifact IDs must match the returned integer identities.
- Repository, Delivery workflow, event/ref, policy SHA, image SHA/digest, source
  Build ID, environment, mode, accepted/source_verified flags and successful job
  from the exact attempt remain bound. PROD still requires master.
- Artifact `expired` must explicitly be false and its timezone-aware expiry must
  be in the future. Conflicting workflow-run head identity is rejected.
- Runtime metadata must identify the reviewed project/region/service, a revision
  of that environment and one 100% traffic allocation to that exact revision.
- ZIP bytes are capped at 2 MB, release.json at 64 KB; exactly one named
  release.json is allowed. Encrypted/symlink/extra-member/malformed archives, invalid
  JSON, duplicate keys and nonstandard NaN constants are rejected with fixed errors.
- GitHub pagination validates shape/count and fails on incomplete results or its
  existing page bound. A partial list does not become accepted evidence.
- Artifact redirects never forward the GitHub bearer token. Download errors omit
  signed URLs and raw bodies. Expired/missing artifacts get distinct diagnostics.

New/retained negative tests cover wrong repo/workflow/branch/SHA/digest/Build ID,
run/attempt/artifact identity, failed acceptance/job, wrong environment/mode,
missing source verification, expired/missing artifacts, conflicting runtime metadata
and oversized/malformed evidence. Overall source workflow failure is still allowed
when the independently accepted DEV job succeeded, preserving manual promotion
after a failed PROD job. Rerunning an old source attempt does not validate its old artifact.

Cached authentic DEV/PROD records from CI-004 passed the strengthened `validate_proof()`
without modification. This is an **offline compatibility check of cached records**,
not a fresh GitHub availability or live GCP check.

## Recovery changes and tests

Snapshot now binds a single receiving revision to the expected environment/service,
SHA, mode, ready status and canonical image digest, cross-checked against the
immutable registry SHA tag. Traffic is copied so later response mutation cannot
rewrite the snapshot. If the prior tag/image is unavailable or mismatched, snapshot
creation fails **before deployment**, rather than promising an unverifiable fallback.

Before recovery mutation, validate the snapshot/origin/traffic and re-read the
selected revision. Check current service ownership, origin and freshness. Restore
the exact traffic allocation with invoker IAM enabled; preserve existing IAP and
never emit `--no-iap` during recovery. Then verify health SHA/mode/environment,
actual traffic, ownership/origin, freshness, revision digest/readiness and absence
of public invoker bindings. A newer concurrent release blocks recovery success.

| Scenario | Offline result / guarantee |
|---|---|
| Valid cloud_demo and readonly recovery | PASS; exact traffic and health, IAP retained |
| Missing/wrong/unready revision or wrong digest | Rejected before mutation |
| Invalid snapshot, service, origin or traffic | Rejected; no guessed restoration |
| Traffic command or authentication failure | Recovery fails; never accepted |
| Wrong restored SHA/mode/environment or health failure | Recovery fails |
| Wrong actual traffic, disabled IAP/invoker check, public IAM | Recovery fails |
| Newer run before/during recovery | Stale attempt rejected |
| Original deploy failure plus restore failure | Original exception re-raised; summary explicitly says recovery NOT verified |
| Output/evidence I/O failure after runtime acceptance | accepted reset false; own partial evidence removed; recovery attempted |
| Summary I/O failure during failure handling | Original outcome retained; fixed diagnostic only |
| Existing release.json at invocation start | Fail before deployment; prior evidence untouched |
| Digest changes in final post-acceptance verification | Rejected and recovery attempted |

No destructive data restoration exists. Firestore, GCS documents, Tasks, schemas and
provider side effects are not rolled back. A failed recovery produces no accepted
release file; successful traffic restoration still leaves the deployment FAILED.

## Diagnostics

Reuse existing fixed command stages. Build/registry/source errors retain safe
operation/stage/exit-code and recognized Google category; source-archive and image
lookup phases are distinguished. Provenance rejection has fixed categories for
invalid hint, missing/conflicting record, invalid recipe, archive bytes or exhausted
discovery. Evidence and recovery failures use fixed messages. No raw stderr, tokens,
authorization headers, credentials, signed URLs, secret values or document bodies
are appended to summaries. Recovery exceptions do not replace the original failure.

## Validation and live status

- **947 pytest PASS**, one existing Starlette/AnyIO warning; final run 55.22 s.
- **103 new tests**; focused CI/CD set **251 PASS** (2.34 s), including existing
  deployment/source-proof/bootstrap/resume/diagnostics tests. No existing test was
  removed or weakened. Legacy fixtures were completed with real runtime identity,
  expiry and revision metadata; original behavioral assertions remain.
- Existing offline source/preview/deployment contracts and `make check`: **PASS**.
- `git diff --check`, documentation links and protected-file comparisons: **PASS**.
  CI-001–CI-004 tracked/untracked source hashes and Git status are unchanged.
  [Validation record](benchmarks/ci-005-offline-validation.json) records counts,
  checks, cached compatibility and final implementation hashes.
- Workflow files unchanged; no workflow actionlint requirement introduced.
- Initial new-test harness failure was pytest placing a multi-megabyte payload in
  Windows' test-name environment variable. Short explicit test IDs fixed the harness;
  the oversized payload and its rejection assertion remain tested.

Optional read-only `gcloud projects describe tripse-ai --format=value(projectId)
--quiet` failed with exit 1: `Reauthentication failed. cannot prompt during
non-interactive execution.` No interactive login, account/config change, IAM
expansion or bypass was attempted. Live source lookup/filtering, current registry
and Cloud Run state, WIF execution, hosted CI and actual recovery remain **NOT VERIFIED**.
No live deployment/traffic/rollback test is authorized or was executed.

## Operator acceptance and rollback of this patch

Read-only acceptance after separately restoring already authorized credentials:

```powershell
gcloud projects describe tripse-ai --format='value(projectId)' --quiet
gcloud builds describe 379950bf-7772-464a-9f16-47bc02472efb --project=tripse-ai --region=europe-central2 --format=json
gcloud artifacts docker images describe europe-central2-docker.pkg.dev/tripse-ai/tripse-ai/tripse-ai:3f55a25276a7e92ce74b3e0c70460d4e967a0138 --project=tripse-ai --format='value(image_summary.digest)'
gcloud run services describe tripse-ai-dev --project=tripse-ai --region=europe-central2 --format='json(metadata.name,status.traffic,status.latestReadyRevisionName,spec.template.spec.containers.image)'
gcloud run services describe tripse-ai-prod --project=tripse-ai --region=europe-central2 --format='json(metadata.name,status.traffic,status.latestReadyRevisionName,spec.template.spec.containers.image)'
```

These known IDs are historical checks, not assumed current state. Test the exact
server filter against known metadata and compare with direct describe. Under the
existing DEV read identity and reviewed config, call `build_proof.verify(g, sha,
digest, build_id)` for a retained committed release to verify the source generation
and bytes without deploying. It reads the **build-source** archive, never application
buckets. Keep credential-bearing/raw metadata out of published logs. Stop on missing
permissions; no new IAM grant is part of CI-005. Revalidate artifact metadata and
expiry with the existing GitHub proof path before planning any controlled release.

CI-005 code rollback: review/revert only this branch's patch in build_proof.py,
ci.py and the small build-return/diagnostic change in deployment.py, together with
its tests/docs. Do not reset other worktrees or invoke a Cloud Run rollback.
There is no infrastructure/schema migration. Reverting restores the old recency
limitation; it must not be used to accept a release rejected by source proof.

## Separate integration and release-acceptance phase

Propose a new task to review/reconcile CI-001–CI-005 worktrees, choose an explicit
committed combined base, resolve documentation/implementation overlaps, run the
combined tests/offline contracts/container acceptance, execute hosted CI, complete
read-only GCP/IAM/inventory/evidence checks and prepare controlled DEV/PROD acceptance
with rollback criteria. Any deployment or actual rollback drill requires that task's
explicit authorization. CI-005 performs **none of that integration or deployment**.
