# CI-006 — integration, regression and release acceptance preparation

2026-10-29. **READY FOR REVIEW — Gate A review complete; publication approval pending; Gate B not executed.**
Worktree: `D:\Projects\tripse-ai-ci-integration`.
Branch: `ci/ci-006-integration-acceptance`.
Base HEAD: `e9731635fcf1dc424ccecebecc0299dafb7936b7`.
The candidate remains **uncommitted**. No new release SHA, hosted run, accepted
release artifact or deployed image is claimed. ADR-0015 remains **proposed**.

## Source-of-truth inventory

Actual history, not branch names or commit messages, determines the base:
`777e0662da5e57894371529f3af0bdafeb2fed11` is the earlier common application base.
Its descendant `e973163` (`ci 1-2 update`) contains CI-001's nine-file cache change,
**not CI-002**. There is no committed CI-002–CI-005 implementation to cherry-pick.
Therefore CI-001 is inherited once by creating this worktree at e973163; the other
tasks are integrated through reviewed local patches and selected new source files.

| Source worktree | Branch | HEAD / ancestry | Staged | Unstaged patch bytes | New files |
|---|---|---|---:|---:|---:|
| `D:\Projects\tripse-ai-demo` | `ci/ci-001-python-cache` | e973163, descendant of 777e066 | 0 | 0 | 0 |
| `D:\Projects\tripse-ai-ci-002` | `ci/ci-002-docker-hardening` | 777e066, ancestor of integration base | 0 | 12745 | 2 |
| `D:\Projects\tripse-ai-ci-003` | `ci/ci-003-buildx-benchmark` | e973163 | 0 | 10053 | 5 |
| `D:\Projects\tripse-ai-ci-004` | `ci/ci-004-artifact-registry-audit` | e973163 | 0 | 10620 | 6 |
| `D:\Projects\tripse-ai-ci-005` | `ci/ci-005-delivery-hardening` | e973163 | 0 | 48195 | 4 |

[Inventory with exact full SHAs, Git status, file paths and patch hashes](benchmarks/ci-006-source-inventory.json).
Independent staged/unstaged/combined binary patches and new-file byte captures are
under ignored `local-data/ci-006/source-patches/`. No ignored data, credentials,
virtualenv contents, state, generated media or business data was copied from sources.
Untracked Python captures use `.py.source` suffixes so pytest cannot collect them;
source bytes/hashes remain unchanged. Capturing `git diff` alone was not used.

## Integration sequence and selected files

Non-document tracked changes were applied using checked Git patches in CI-002 →
CI-003 → CI-004 → CI-005 order. New files were verified against captured SHA-256.
Shared documents were reconciled by meaning: CI-005's latest security description
was the starting text, then CI-002/003/004 results and current CI-006 decisions were
incorporated. CSV records were parsed/deduplicated, not blindly concatenated.
Focused checks completed for each selected layer before full regression.

| Task | Included | Excluded / outstanding |
|---|---|---|
| CI-001 | Existing ci.yml/delivery.yml cache, both requirements keys, unconditional install, Python 3.12, SHA pins, tests and report | No duplicate cache patch; hosted cold/warm still unmeasured |
| CI-002 | Dockerfile, both ignore files, five contract cases and measured report | No USER/chown/chmod; previous UID 10001 `/data` failure remains a separate follow-up |
| CI-003 | Manual benchmark helper, tests, report and sanitized measured JSON | Automatic experimental workflow excluded; no GHA/registry cache added to production |
| CI-004 | Offline registry analyzer, 37 tests, synthetic fixture/output, sanitized historical references and report | No delete/apply, cleanup policy, live inventory or IAM changes |
| CI-005 | build_proof.py, ci.py, small deployment.py change, complete existing fixture metadata, 103 new tests and evidence/report | No workflow/WIF/recipe change, live delivery or rollback |
| CI-006 | Two cross-workstream tests, benchmark pin compatibility, worktree-local browser artifacts, reconciled docs/inventory and acceptance runbook | No commit, push, merge, hosted/cloud execution |

Reports [CI-001](CI_001_PYTHON_CACHE.md), [CI-002](CI_002_DOCKER_OPTIMIZATION.md),
[CI-003](CI_003_BUILDX_CACHE_BENCHMARK.md), [CI-004](CI_004_ARTIFACT_REGISTRY_AUDIT.md)
and [CI-005](CI_005_DELIVERY_HARDENING.md) remain as historical isolated-task evidence.
Their original test counts and build measurements do not describe a newly committed
combined release. Shared plan, deployment/CI/CD guide, ADR index/history and worklog
now point here for current integrated state; dated historical worklog rows are retained.

## Conflicts and compatibility decisions

**CI-001 duplicates:** CI-002 was based before CI-001. Its old workflow/docs versions
were not copied over the newer baseline. CI/Delivery workflow bytes equal e973163;
cache remains in all three intended jobs with no authority/trigger changes.

**CI-002 versus CI-003:** CI-002 begins with comments and a pinned Python index;
the original benchmark expected a floating FROM on line one. The retained helper now
reads reviewed instructions, preserves official Python 3.12 digest pins and comments
byte-for-byte, records the actual base and rejects unsupported/multistage recipes.
Historical floating contexts keep the original QA-only freeze for reproducibility.
Tests cover both paths and ensure no pin is stripped. The workflow-specific test was
replaced by an explicit exclusion/production-builder guard because that workflow is
deliberately absent, not weakened to permit extra authority.

**CI-003 disposition:** Option A, retain Cloud Build. Manual tools have value for
reproducing archived measurements and checking context integrity. No benchmark was
rerun here and no new performance gain is inferred. `.github/workflows/buildx-benchmark.yml`
is captured/hashes recorded but is not part of the RC. Its original worktree remains
available; the report's hosted design is explicitly historical.

**CI-002 context versus CI-005 proof:** the allowlist is unchanged. New helpers,
tests, docs and QA data do not enter the application image. Dockerfile/ignore changes
are legitimate new committed source bytes only **after review and commit**. A new
cross-test proves a working-tree archive differing from HEAD cannot masquerade as
that committed SHA. Old releases still validate against their original SHA context,
not today's Dockerfile. No clean-head/source safeguard is bypassed.

**CI-004/CI-005 identity:** the registry analyzer and deployment contract identify
the same existing project/region/repository; no parallel registry/cache namespace
was added. Dry-run classifications remain non-authoritative and `safe_to_delete=false`.

**Evidence compatibility:** the integrated validator rechecked authentic cached
CI-004 DEV/PROD record/API metadata in memory and passed both contracts. No ignored
cache file was copied into the RC and no new GitHub/GCP request was needed. This is
cached-record compatibility, not current live resource availability.

**Documentation:** current sections consistently distinguish selected implementation,
historical measurements, proposed ADR status and outstanding hosted/cloud gates.
The obsolete global 1000-most-recent-build description was replaced by direct lookup
and targeted bounded discovery; matching-candidate limit and PROD trust delegation
remain explicit.

## Local verification

| Check | Result |
|---|---|
| Full integrated Python suite | **1006 PASS**, one existing Starlette/AnyIO warning, final run 58.16 s |
| CI-001 focus | **22 PASS** |
| CI-002 Docker contracts | **5 PASS** |
| Retained CI-003 helper | **15 PASS** |
| CI-004 analyzer | **37 PASS** |
| CI-005 + existing CI/CD focus | **251 PASS** |
| Cross-workstream tests | **2 PASS**, included in total |
| Offline CI/deployment contracts | **PASS**; validates committed base context, not a new combined SHA |
| Existing `make test-container` | **PASS**: linux/amd64, port 8000, readonly, fixture, baked-SHA/write-denial/SIGTERM |
| `make test-browser` | **PASS**, all nine scripts, no external provider requests |
| Viewer browser after artifact-path correction | **PASS**, desktop/mobile and isolated output |
| Additional API/worker/container persistence | **PASS**, details below |
| actionlint 1.7.12, all two workflows | **PASS** |
| `make check`, `git diff --check` | **PASS** |

Browser QA covered planner/maps doubles, Hub, Document Studio edit/save/reopen and
actual process restart, marketing/trip documents and real browser PDFs, readonly
preview, fake authenticated cloud UI, GT template edit flows and mock chat/worker.
This is local/fake-cloud browser testing, not deployed IAP or Cloud Run acceptance.

Initial full collection found duplicate test modules in private source captures;
renaming captures to non-executable `.py.source` fixed that harness issue without
changing test selection or assertions. Raw failed and final logs remain in ignored
`local-data/ci-006/`. No production regression was hidden or test assertion relaxed.

[Final validation and preservation record](benchmarks/ci-006-local-validation.json)
includes the source/Git checks and the disclosed ignored-output exception.

### Real Linux container acceptance

Docker Desktop 4.81.0, Engine 29.6.1, API 1.55, Linux/amd64 under WSL2,
8 CPUs and 8 304 398 336 B daemon RAM. Integrated pin runs Python 3.12.16.
The additional QA image uses `source_files(e973163…)` plus **only** working-tree
Dockerfile/.dockerignore/.gcloudignore overlays. Application bytes are identical to
that commit. Its baked SHA identifies that unchanged app base; an explicit manifest
identifies QA input bytes. It is marked `release_image=false`, never a Git release.

Image audit verified all 78 app/fixture/requirements file hashes, direct runtime
dependencies, API CMD, worker imports, absence of development packages and required
fixtures. Runtime acceptance used a new labeled SQLite volume and a new synthetic
Document Studio bind directory under this worktree, not Compose's existing volume:

- API `/health`, Hub, five trip fixtures and nine example recipes available.
- Actual worker command `python -m app.worker` completed mock mountain/coast jobs.
- Copied example, edited revision 2, read historical revision 1, uploaded a synthetic
  PNG; normalized asset content was verified.
- Stopped worker, queued another job, stopped/restarted API and worker; completed
  job JSON, queued job, entire draft/history and asset bytes survived. The pending
  job completed after worker restart.
- Effective UID/GID 0/0; writes to `/data`, Document Studio bind and `/tmp` passed.
  No non-root/chown/chmod change was introduced.
- Readonly preview, exact baked app SHA, fixtures, private-route/write denial and
  graceful SIGTERM exit 0 passed. API/worker logs had no PermissionError/Traceback.

Owned containers, network, volume and QA tag were removed after label/ID checks.
Existing volumes and application data were never mounted. Shared build cache was
not pruned. Ignored synthetic evidence/bind/context directories remain locally.

### Worktree preservation and one disclosed isolation incident

Branches, HEADs, Git staged/unstaged/untracked source status and all nonignored source
hashes in the five original worktrees are unchanged. No original reset, stash,
merge, history rewrite or data/volume cleanup occurred.

**Exception:** the first existing viewer browser smoke wrote `desktop.png`,
`mobile.png` and `server.log` to `.venv/viewer-artifacts`. This integration uses the
existing dependency environment via a junction, so those three ignored QA outputs
were written in the shared CI-001 virtualenv directory. Pre-run hashes of those
ignored QA files were not captured; their prior byte contents cannot be asserted
unchanged or reconstructed. No application/business data or source change resulted.
They were left in place rather than guessing a restoration/deletion.

The integration fixes `tests/browser_smoke.py` to write to worktree-local
`local-data/viewer-qa`; the rerun passed and reports that isolated path. This closes
the ongoing test-isolation defect. The preservation claim is therefore explicitly
about source/Git/application data, **not an unqualified claim that every ignored
file in the shared dependency directory was untouched**.

## Security and remaining gates

Production remains Cloud Build → existing Artifact Registry → DEV deployed
acceptance → protected PROD promotion of the accepted digest. WIF, separate deploy/
probe identities, CI-first dependency, global environment locks, full action SHA
pins and master-only production remain byte-identical in workflows/Terraform.

CI-005 direct IDs are lookup hints until builder/recipe/digest/generation/source
bytes pass. No-hint discovery is bounded to 1000 matching candidates, not unrelated
recent builds. Missing history/archive fails closed. PROD retains accepted master
DEV/PROD artifact delegation without new Cloud Build/source-read authority.
Artifact identity/expiry and runtime revision/traffic checks, private recovery,
stale-run rejection and original-error preservation are covered by negative tests.

The RC has no committed identity yet. Existing offline SHA tests still read e973163;
working-tree/static/container tests cover local changes but cannot establish exact
production Cloud Build source provenance of an uncommitted candidate. That gate
requires a reviewed commit, then hosted contracts and actual authorized DEV build.

No GCP request, hosted CI/Delivery trigger, registry publication, IAM/IAP/Terraform
mutation, traffic change, deployment or rollback was performed in CI-006. The known
authentication-renewal failure from CI-004/CI-005 remains an open prerequisite;
it was not rechecked or bypassed here. Current registry/IAM/usage/digests/revisions,
human login and real customer-data readiness remain unverified.

## Phase B runbook — procedures only, not executed

### Gate A — review and commit approval

1. Open the integration worktree/branch above. Review `git status --short`,
   `git diff`, **and every untracked file** listed by `git ls-files --others
   --exclude-standard`. Review the three deployment modules and unchanged workflow/
   Terraform diff separately. Inspect source inventory, chosen file disposition,
   QA isolation exception and the matching-candidate/provenance limitations.
2. Confirm no local-data, .venv, credentials, state, logs, generated PDFs/media or
   business data is staged. `docs/benchmarks` contains intentionally versioned,
   sanitized evidence metadata, not raw build caches or media; review each JSON.
3. Only after operator approval, stage the explicit reviewed RC files, inspect
   `git diff --cached --name-only`, `--stat` and `--check`, then create the reviewed
   commit. Do not stage the private source-capture bundle. No automatic commit is
   performed by this task.
4. Record the full new SHA, require a clean Git status, rerun full/focused tests,
   offline contracts and container checks from that committed SHA. Verify the
   committed allowlist matches reviewed Docker/context bytes. This is still local
   source validation, not live Cloud Build archive acceptance.

### Gate B — feature PR and GitHub-hosted CI

After separate publication approval, from this worktree only:

```powershell
git push -u origin ci/ci-006-integration-acceptance
gh pr create --base master --head ci/ci-006-integration-acceptance --title "Integrate CI-001 through CI-005" --body-file REVIEWED_PR_BODY_FILE
gh pr checks PR_NUMBER --watch
```

Do **not** push dev/master, dispatch Delivery or merge the PR merely to run tests:
those refs/merge can trigger real deployment. PR CI targets master and has only
contents:read, no cloud auth/id-token authority. Record committed SHA, PR/run/attempt
IDs, runner/tool versions and every required check result. Verify unconditional
installs and both dependency cache keys; collect actual pip hit/miss and native
setup/install/test/browser durations across equivalent runs. First run is not
automatically cold because default-branch fallback caches may exist. Do not delete
caches or invent performance gains. No experimental Buildx workflow is published.

### Gate C — authorized read-only GCP/GitHub audit

After operator authentication renewal using already approved metadata-reader access,
run only read operations. If a permission is missing, record the gap and stop that
check; do not grant roles, switch to administrator credentials or apply Terraform.

```powershell
gcloud artifacts repositories describe tripse-ai --project=tripse-ai --location=europe-central2 --format=json
gcloud artifacts repositories get-iam-policy tripse-ai --project=tripse-ai --location=europe-central2 --format=json
gcloud artifacts docker images list europe-central2-docker.pkg.dev/tripse-ai/tripse-ai --project=tripse-ai --include-tags --format=json
gcloud run services describe tripse-ai-dev --project=tripse-ai --region=europe-central2 --format='json(metadata.name,metadata.labels,metadata.annotations,status.traffic,status.latestReadyRevisionName,spec.template.spec.containers.image)'
gcloud run services describe tripse-ai-prod --project=tripse-ai --region=europe-central2 --format='json(metadata.name,metadata.labels,metadata.annotations,status.traffic,status.latestReadyRevisionName,spec.template.spec.containers.image)'
gcloud projects get-iam-policy tripse-ai --format=json
gcloud iam workload-identity-pools providers describe github-dev --workload-identity-pool=tripse-github --location=global --project=tripse-ai --format=json
gcloud iam workload-identity-pools providers describe github-prod --workload-identity-pool=tripse-github --location=global --project=tripse-ai --format=json
```

Reconcile CI-004: immutable tags, cleanup settings/dry-run flag, sizeBytes, complete
image/tag pagination, inherited IAM, builder and Cloud Run image access, all receiving/
tagged/zero-traffic revisions and approved rollback references. Resolve relevant build
IDs with regional `builds describe`, exact archive generation and accepted artifacts;
check direct lookup versus the documented result image/digest server filter. Inspect
only build-source object metadata/bytes where authorized, never application storage.
Use the offline analyzer on a complete captured snapshot; no deletion/apply is allowed.

Read GitHub Environment/reviewer/deployment-branch and branch-protection settings;
code alone cannot prove current protections. Validate current artifact availability,
expiry/run-attempt identity and source/evidence retention. Historical release IDs in
CI-004 are references to check, not assumptions about today's active services.

### Gate D — separately authorized controlled DEV acceptance

Stop until explicit DEV authorization. Require Gates A–C, clean reviewed SHA,
reviewed cloud_demo config, private origin, correct WIF/deploy/probe identities,
fresh snapshot and usable prior recovery proof. Confirm development Environment
and WIF permit the selected dispatch ref; **do not widen policy if they do not**.

If authorized under existing rules, the operator may dispatch the existing Delivery
workflow on the feature ref with operation=dev and the full reviewed SHA:

```powershell
gh workflow run delivery.yml --ref ci/ci-006-integration-acceptance -f operation=dev -f target_environment=dev -f release_sha=REVIEWED_FULL_SHA
```

Record run/attempt, submitted Build ID, immutable SHA tag, resolved digest, exact
generation-pinned source proof, ready revision/traffic, private access and deployed
API/browser acceptance. Capture the accepted artifact ID. No paid provider or real
customer data is needed. A feature-branch DEV artifact is **not** valid PROD proof.
Failure means no accepted release; inspect recovery verification and preserve the
original error. An unsuccessful restoration requires a separately authorized incident
response, not an improvised public-access or source-proof bypass.

### Gate E — separately authorized protected master/PROD release

Do not merge until separately authorized for the real master-triggered release.
A merge/master push triggers CI → DEV → protected PROD. A merge may create a new
SHA; it needs its **own accepted master DEV record**. Never substitute the feature
artifact or a different digest. Confirm production Environment/reviewer protection
before merge/approval. Approve promotion only after master DEV acceptance and
independent evidence/digest checks. PROD promotes that digest without rebuilding.

For an authorized manual resume, use a new master dispatch with operation=promote,
full approved SHA and accepted master DEV run/artifact IDs. Do not rerun only PROD
in a way that changes the source attempt and invalidates its old artifact. Record
PROD readiness, exact digest/receiving revision, 100% traffic, private health/smoke,
artifact ID/run attempt and a verified rollback reference. Only completed independent
Gates B–E can establish release **ACCEPTED**; this report does not do so.

Only after separate production authorization, the manual-resume command is:

```powershell
gh workflow run delivery.yml --ref master -f operation=promote -f release_sha=APPROVED_MASTER_FULL_SHA -f evidence_run_id=ACCEPTED_MASTER_DEV_RUN_ID -f evidence_artifact_id=ACCEPTED_MASTER_DEV_ARTIFACT_ID
```

### Rollback procedure — separate approval required

Preserve the previous accepted target-environment record, full SHA/digest, source
Build ID/archive generation, ready revision, traffic and artifact/run/attempt/expiry.
Verify its remaining availability and schema compatibility before authorizing a
real rollback. PROD dispatch must be master and use accepted master PROD proof;
DEV rollback requires its accepted DEV proof and full direct source verification.
Use a new authorized Delivery dispatch with operation=rollback, target environment,
prior full SHA and its accepted run/artifact IDs; never reset the freshness watermark.
Verify actual traffic, revision/digest, private IAP/invoker policy and health before
declaring recovery successful. No database/document/Tasks/schema restoration is implied.
No live rollback drill or manual traffic/IAM operation is authorized by CI-006.

For a separately approved PROD rollback, fill the prior accepted **PROD** reference,
not the DEV promotion artifact:

```powershell
gh workflow run delivery.yml --ref master -f operation=rollback -f target_environment=prod -f release_sha=APPROVED_PRIOR_FULL_SHA -f evidence_run_id=ACCEPTED_PRIOR_PROD_RUN_ID -f evidence_artifact_id=ACCEPTED_PRIOR_PROD_ARTIFACT_ID
```

## Readiness assessment

The combined local implementation is **READY FOR REVIEW**, with the QA-output
isolation incident explicitly disclosed above and fixed for future runs. There is
no unresolved critical local code/test blocker. It is **not ACCEPTED**: commit,
hosted CI, current read-only cloud audit and separately authorized DEV/PROD acceptance
are outstanding. Original branch/history/source changes remain preserved; shared
ignored QA output preservation has the stated exception. The Phase B Gate A review
below supersedes the earlier documentation-only status. Publication still requires
explicit operator approval.

## Phase B — Gate A release candidate review (2026-10-29)

The current branch remains `ci/ci-006-integration-acceptance`, at full base HEAD
`e9731635fcf1dc424ccecebecc0299dafb7936b7`. The index is empty. There is no new
integration commit SHA, PR, hosted run/job ID or hosted cache measurement yet.
Gate B has not run; cloud deployment is not verified. ADR-0015 remains proposed.

The complete candidate inventory, including untracked source/evidence files, is
[the Gate A review record](benchmarks/ci-006-gate-a-review.json). It identifies every
file proposed for the commit, not only the tracked diff. Generated QA outputs,
Python caches, the shared virtualenv, `data/` and `local-data/` remain ignored and
outside the commit. Candidate content was inspected for credentials, private
application data, databases, Terraform state and generated media. Pattern scans
supplemented source and evidence review; no actual credentials or private data
were found. Published historical identifiers and synthetic fixtures are evidence,
not new release acceptance. No unresolved critical issue was found.

All 16 distinct implementation files covered by the previous source/adaptation
hashes still match Phase A. Workflows, application code, Compose, dependencies,
infrastructure, deployment contract and source allowlist have no diff from the
integration base. CI-001 is already in that base, so its workflow change will not
appear in this commit's diff. Relative to current remote master, the workflow
differences are CI-001 cache/step naming/summaries only; event filters, permissions,
WIF, Environment bindings and deployment concurrency are unchanged.

Specific review: both pip dependency keys and unconditional installs remain;
the pinned Python 3.12 base/restricted context remain; Buildx is manual-only and
the experimental workflow is absent. Registry analysis has no network/auth/delete
capability and never declares an image safe to delete. Exact recipe and committed
source-byte verification remain mandatory for DEV. PROD delegates to accepted
master DEV evidence and promotes its digest without rebuilding, as before.
Failure paths retain `accepted=false`, remove their own partial evidence where
possible, preserve the original exception and verify private recovery. Tests do
not establish current live IAM, Environment protection settings or GCP state.

### Gate A repeated local validation

Same Windows PowerShell/GNU Make and shared Python dependency environment as
Phase A; no installation or dependency change. Logs and generated browser outputs
are isolated under this integration worktree. All commands returned exit 0.

| Check | Result | Wall time |
|---|---|---:|
| `make test` | 1006 passed; one existing Starlette/AnyIO deprecation warning | 62.34 s (pytest 61.10 s) |
| `.venv/Scripts/python.exe -m scripts.gcp.ci offline` | Committed base source/deployment contracts PASS | 3.52 s |
| `make test-browser` | All 9 browser scripts PASS, including actual PDF/restart and mock/readonly flows | 242.72 s |
| `make test-container` | Actual Linux/amd64 container, readiness, port 8000, readonly filesystem, fixtures, write denial, baked synthetic SHA and graceful SIGTERM exit 0 | 14.01 s |
| actionlint 1.7.12, both workflows | PASS | 0.12 s |
| `make check` | Diff whitespace and Compose configuration PASS | 0.72 s |
| `git diff --check` | PASS | 0.19 s |

Docker preflight: Engine/CLI 29.6.1, Linux x86_64, 8 CPUs, daemon RAM
8,304,390,144 bytes; existing Docker Desktop Linux engine was accessible.
No Desktop configuration change. The existing container smoke uses a disposable
context/image/container, synthetic baked SHA, no existing volume or data mounts,
and removes its own image/container. This is local runtime QA, not release-image
provenance or Cloud Run acceptance. The more extensive API/worker persistence
exercise above remains Phase A evidence and was not repeated at Gate A.
All four existing named Docker volumes remain present.

Only acceptance documentation/shared status text and the new Gate A evidence
record changed during this review; implementation bytes stayed unchanged.
The final documentation delta passed `make check` and `git diff --check` again.
Offline source validation still targets the actual committed base; it cannot
verify a not-yet-created RC SHA. Revalidation against the new full SHA is mandatory
after the approved commit and before publication. No hosted cache timing exists.

### Actual GitHub trigger review

Read the current remote master workflow files and workflow-directory listing
through the GitHub connector. There are exactly two workflows: CI and Delivery.
Remote blob IDs: CI `627c822c70323d8994431a6c987ebf1902374854`, Delivery
`a0f469eb76d5e9bd4df0763f6a75d5a010324700`.

| Event | Expected execution from reviewed definitions |
|---|---|
| Push integration feature branch | Neither workflow starts automatically |
| Open PR targeting master | CI only: pytest, offline contracts and browser QA; contents:read; no WIF/cloud authentication |
| Update PR targeting master | Same CI on synchronize; reopened PR also runs CI |
| Merge PR into master | Master push starts Delivery: CI, then DEV, then eligible PROD subject to production Environment gating; merge is forbidden in this task |
| Push dev/master or manually dispatch Delivery | Can start deployment; forbidden in this task |

Hosted CI does not run `make test-container`, actionlint or `make check` in its
current definition. Container execution and those checks remain local-only;
pytest covers static container, provenance, evidence, audit and rollback contracts.
No hosted timing or cold/warm improvement is inferred from local validation.

### Concrete publication proposal — approval pending

Commit message: `ci: integrate CI-001 through CI-005 improvements`.
Remote: `origin` (`https://github.com/piotrbarabasz/tripse-ai-demo.git`).
Publish only `ci/ci-006-integration-acceptance`, then create a PR targeting `master`
and observe credential-free CI. Do not merge, dispatch Delivery or push dev/master.
A draft PR body is prepared under ignored `local-data/phase-b-gate-a/pr-body.md`.

Sections 5–6 of the Phase B operator task explicitly require approval after Gate A
and before staging/committing/publication. Until approval, keep all candidate
files unstaged. After approval, record the actual new SHA, verify the committed
allowlist/provenance contracts, then publish only the reviewed feature branch.
PR/run IDs, cache outcomes and timings remain pending Gate B. Gates C–E remain
separately unauthorized: read-only GCP audit, DEV acceptance and protected PROD.

Original source worktree file hashes, branch/HEAD and complete Git status were
rechecked against the Phase A inventory. The earlier three ignored shared
`.venv/viewer-artifacts` files still have unverified pre-incident contents; no
remediation was attempted. Current browser outputs are worktree-local.
