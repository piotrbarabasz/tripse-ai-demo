# CI-003 — isolated Docker Buildx and cache benchmark

CI-006 integration note (2026-10-29): this is the historical isolated-task report.
The selected implementation is now in the local integration candidate; current
combined validation and outstanding committed-source/hosted/cloud gates are in
[CI-006](CI_006_INTEGRATION_ACCEPTANCE.md). Original measurements below remain
attributed to their original worktree and source, not to a new release SHA.

2026-10-29. **Local benchmark: PASS — 48/48 builds and image smoke checks.**
Local implementation on `ci/ci-003-buildx-benchmark` in
`D:\Projects\tripse-ai-ci-003`. No commit, push, merge, deployment or GCP operation.
ADR-0015 remains **proposed**. Hosted GHA measurements: **Not measured**.

## Existing architecture and baseline

Production remains unchanged: `source_files()` exports an allowlisted committed
archive, `build()` adds `app/_build_version.txt`, and Cloud Build executes the
reviewed single `docker build --network cloudbuild --no-cache -t TAG .` recipe.
An immutable SHA tag resolves to a digest. `build_proof.verify()` matches builder
identity, output digest, recipe and generation-pinned source archive bytes.
DEV acceptance precedes PROD promotion of that same digest; PROD does not rebuild.

Committed baseline: `e9731635fcf1dc424ccecebecc0299dafb7936b7` (`ci 1-2 update`).
Despite that message, its diff contains CI-001, **not CI-002**. CI-001's main
checkout was clean at task start. CI-002 remains an uncommitted patch in its own
worktree at `777e0662da5e57894371529f3af0bdafeb2fed11`. Its local acceptance report
was read there; it is absent from this committed baseline. No changes were copied
from either worktree. Their file fingerprints and Git status are recorded privately
under ignored `local-data/ci-003/protected-worktrees.json` for final comparison.

## Reproducible methodology and equivalence

Run from this checkout with the existing Python dependencies and Linux Docker Engine:

```powershell
.venv/Scripts/python.exe -m scripts.benchmark_buildx run --sha e9731635fcf1dc424ccecebecc0299dafb7936b7 --output local-data/ci-003/new-run --repeats 3
```

Output must be a **new** directory below ignored `local-data/ci-003`. No user data,
credentials, developer directories, generated media or untracked application bytes
are copied. `source_files()` is reused without changing production code. Every
context has the committed source SHA baked into the standard file, plus an input
manifest with every file's SHA-256, original/effective Dockerfile hashes,
requirements hash, base digest, platform and aggregate manifest hash.

These are explicitly synthetic QA contexts, **not immutable Git releases**:

- Only the exported Dockerfile's FROM is frozen to the official linux/amd64
  Python manifest, `python:3.12-slim@sha256:1148dbb014615300fa7e713b2f94f550c0d1c69780c0805f84f093ceee34dd0b`.
  The repository Dockerfile remains unchanged. This prevents a moving tag from
  confounding the comparison observed in CI-002.
- Each repetition adds the same trial comment to requirements in every method and
  variant. It changes the COPY cache key without changing installed packages,
  preventing pre-existing shared Docker cache from satisfying dependency trials.
- `source` appends a fixed harmless comment to `app/main.py` only.
- `dependencies` adds `six==1.17.0` to requirements only. This tests actual pip-layer
  invalidation and installation, rather than an empty change or a cache-key claim.
- Source/dependency variants are each compared with the same base, not cumulatively.
  The baked SHA identifies original application code; manifests identify QA mutations.

Three repetitions are sequential, with all samples retained and medians reported.
Trials run on the same host without parallel benchmark builds. This does not remove
network variation, background host load, page caches or Python package-index variance.
Cold means no reusable RUN/COPY layers, **not** an empty OS/network/Docker content store.
No shared builder/cache is pruned. Smoke-test time is outside measured build time.
The baseline retains its production dependency policy: direct requirements are
pinned, transitive resolutions are not fully locked. Network/index variability
therefore remains a limitation; raw pip logs retain the resolved installation.

Measured host: Windows 11 build 22631, Docker Desktop 4.81.0, Engine 29.6.1,
Linux/amd64 under WSL2, 8 daemon CPUs, 8 304 398 336 B daemon RAM.
Buildx `v0.35.0-desktop.2` (`b554ce1decd8b509893b1e7c6227eabfb923d094`),
BuildKit v0.31.1 in both Docker and isolated builders; Python 3.12.16.
The exported original Dockerfile hash is
`90f7c9901655ccf9128174685fa5e7fd351afa17fc0c3df92cdfe48c3ed68af9`,
effective frozen-base Dockerfile hash
`c33b0a95fef29fbc7adb311519ba06b294c6b3a30fcb9e15dd41128a160462f0`.
Requirements and complete context hashes vary by recorded trial/variant; each
method within the same trial uses the identical corresponding context.

| Method | Cold | Warm / source / dependencies |
|---|---|---|
| `docker build --no-cache` | Cache disabled | Cache disabled in each scenario |
| Regular `docker build` | Forced `--no-cache` with unique trial requirements | Same daemon; cache permitted; tested before no-cache variants |
| Buildx internal | New disposable docker-container builder | Same builder within trial, no external import/export |
| Buildx local external | New builder exports `mode=max` to new local cache | New builder for **each** probe imports the seed, exports to a separate destination |

Buildx uses `--load` for an inspectable local application image. Load/export overhead
is included in total wall time. Internal builders and cache directories are isolated;
no registry-backed cache, release namespace or image publication is used. BuildKit
is pinned to `moby/buildkit:v0.31.1@sha256:2caaaf9bc673a82d5b0a87824f8375e6b2b36b55001dad611230516c724e9fba`.
Builder bootstrap/pull durations are recorded separately, not hidden in cache-hit times.

`results.json` records success, measured wall time, image inspect size, cache hits,
dependency/import/export vertex spans and runtime checks. Raw JSON progress handles
both Docker's wrapped `vertexes` and Buildx's flat events. Import/export spans are
included in wall time and can overlap other work; their sum is **not** additional
end-to-end latency. Missing spans use null / **Not measured**, not zero.
In particular, an `importing cache manifest` vertex measures manifest lookup,
not all lazy blob downloads. Exclusive total network cache-transfer overhead and
network byte counts are **Not measured**; blob retrieval may appear during other
vertices. The reported import-plus-export span must not be called a complete
network-transfer measurement or subtracted from wall time to claim a speedup.

An initial `run-01` was rejected and interrupted: preceding no-cache dependency
builds had populated the shared Docker cache, making the cached dependency test
invalid. Its logs and exclusion reason were retained. Corrected trials use the
trial comment and ordering above; no application or production checks were weakened.

## Results

Final series `run-02`, session `b41c955780`: **48/48 builds successful**, all image
audits/runtime smoke checks PASS; identical materialized base layers across every
sample. Each cell is the median of three runs, in seconds:

| Scenario | Docker `--no-cache` | Regular Docker local cache | Buildx internal | Buildx local external | GHA cache |
|---|---:|---:|---:|---:|---|
| Cold | 24.675 | 24.152 | 36.512 | 36.325 | Not measured |
| Warm | 22.761 | 1.633 | 7.686 | 21.662 | Not measured |
| Source-only change | 23.568 | 1.747 | 9.733 | 21.286 | Not measured |
| Dependencies changed | 22.909 | 22.697 | 29.778 | 40.222 | Not measured |

Regular Docker is already BuildKit-backed on this host. These results compare
cache/driver/output strategies, not a legacy builder with a new compiler. Warm
internal cache is useful locally; a separate Buildx docker-container builder plus
`--load` did not outperform existing Docker behavior. External local cache restored
correctly, but its complete warm/source builds remained much slower than reusing
the same daemon. This does not establish any production Cloud Build speedup.

| Method | Cold pip vertex, median s | Dependency-change pip vertex, median s | Warm hits | Source hits | Dependency-change hits |
|---|---:|---:|---|---|---|
| Docker no cache | 15.131 | 14.800 | 0/3 | 0/3 | 0/3 |
| Regular Docker cache | 15.440 | 14.636 | 3/3 | 3/3 | 0/3 |
| Buildx internal | 15.608 | 15.372 | 3/3 | 3/3 | 0/3 |
| Buildx local external | 14.503 | 14.461 | 3/3 | 3/3 | 0/3 |

Warm cached pip spans have a median of 0.000 s. External source-change cached pip
vertices have a median span of **10.566 s despite 3/3 cache hits**: this is a cached
vertex/materialization span, not execution of pip installation. Cache flags and raw
progress distinguish these observations; durations alone do not prove a cache miss.

| External local cache scenario | Import manifest span, median s | Export span, median s | Sum of spans, median s |
|---|---:|---:|---:|
| Cold | Not applicable: no import | 2.012 | 2.012 |
| Warm | 0.021 | 2.054 | 2.072 |
| Source-only | 0.020 | 2.202 | 2.228 |
| Dependencies | 0.019 | 1.995 | 2.013 |

The median of a sum need not equal the sum of medians. These spans exclude an
exclusive attribution of lazy blob transfers, as explained above. Each fresh
builder bootstrap took **2.920–3.693 s**, median **3.228 s**, outside build wall time.

Image inspect `.Size` ranged **76 098 350–76 123 773 B** across all variants and
methods. This is the daemon's raw image size counter, not physical incremental
disk consumption; small metadata/compression differences do not prove an image
optimization. Dependency variants intentionally install one additional package.
All **78** application/fixture/requirements files per image matched its exact QA
context manifest. Individual sizes, samples, input hashes, environment and medians:
[machine-readable evidence](benchmarks/ci-003-local-2026-10-29.json).

Raw progress, full manifests, contexts and cache stores are retained locally in
ignored `local-data/ci-003/run-02/`. To recheck completeness, cache invalidation,
materialized bases and medians from raw logs:

```powershell
.venv/Scripts/python.exe -m scripts.benchmark_buildx summary --output local-data/ci-003/run-02
```

GHA cache and Cloud Build build-only timings remain **Not measured**.

## Validation and cleanup

- `make test`: **853 passed**, one existing Starlette/AnyIO deprecation warning;
  pytest elapsed 85.28 s. Includes nine benchmark-specific tests for committed
  context integrity, deterministic mutations/trial isolation, progress formats,
  median aggregation, rejection of false cache evidence and workflow trust policy.
- `python -m scripts.gcp.ci offline`: **PASS**, no cloud credentials or deployment.
- `make test-container`: **PASS**, existing linux/amd64 preview contract including
  port 8000, readonly filesystem, baked SHA, fixtures, write denial and SIGTERM 0.
- `actionlint` **1.7.12**, checksum-verified official Windows binary: **PASS** for
  the new workflow. `make check` and `git diff --check`: **PASS**.
- Final fingerprint/status comparison: CI-001 and CI-002 worktrees **unchanged**.
  All original Docker volumes remain. No owned benchmark container, tag, builder
  or builder volume remains, including the excluded initial series and worker probe.
  Shared Docker cache was not pruned; ignored QA contexts/cache/logs remain.
- Dockerfile, both ignore files, requirements, Compose, `scripts/gcp/`, existing
  CI/DEV/PROD workflows and Terraform have **no diff against the committed baseline**.

Checks ran after the timed matrix. Full raw validation logs and cleanup evidence
are under ignored `local-data/ci-003/`; exit codes and cleanup assertions also
appear in the linked machine-readable evidence. No hosted/cloud acceptance is claimed.

## Historical hosted experiment — excluded from CI-006

CI-006 deliberately excludes `.github/workflows/buildx-benchmark.yml`. Its original
source is preserved in the CI-003 worktree and hashed in the integration inventory.
The following hosted design/pins are historical, not an enabled release-candidate
workflow or instructions to publish one. GHA results remain Not measured.

The manual helper/tests and measured local evidence are retained for reproducibility.
For future committed CI-002 inputs it preserves the existing Python digest and
leading comments byte-for-byte; historical floating inputs retain the original
QA-only freeze. It rejects unsupported/multi-stage recipes instead of stripping pins.
Rebenchmarking is optional operator work, not part of production delivery.

In the original experiment, `.github/workflows/buildx-benchmark.yml` was separate from CI/DEV/PROD delivery.
It runs on pushes to **only** `ci/ci-003-buildx-benchmark`, or manual dispatch on
that branch once GitHub makes dispatch available. This supports testing a newly
added workflow before default-branch merge. Nothing was pushed or dispatched here.

The job requires the exact repository and feature ref, has only `contents: read`,
and has no production Environment, WIF, id-token permission, GCP login, registry
login, release tag, deployment or release evidence. No PR or pull_request_target
trigger exists. Fork/untrusted PR code cannot enter this workflow's export path.
If a future PR trigger is added, it requires a fresh trust review and an import-only
or disabled cache policy; never export PR-produced layers to trusted scopes.

Twelve serial jobs cover three repetitions of four scenarios. Each creates a new
seed and probe builder. The cold seed exports GHA cache; warm/source/dependency
probes import it from a fresh daemon. Cold probes use no cache import and force
`--no-cache`. Each export uses `type=gha,version=2,mode=max,timeout=5m` with scope:
`ci003-v1-RUNID-ATTEMPT-REPEAT-SCENARIO-amd64`, and a separate `-probe` destination.
This avoids accidental cross-run and production cache reuse. It tests within-run
transfer, **not** cache longevity or cross-run eviction behavior.

Current supported action tags were resolved with `git ls-remote`; their immutable
action.yml files were inspected (all use Node 24). Full pins:

| Action | Verified tag | Full commit |
|---|---|---|
| actions/checkout | v6 | d23441a48e516b6c34aea4fa41551a30e30af803 |
| docker/setup-buildx-action | v4 | f87e5991a6d7451dcb8d9637bfbc97413f497069 |
| docker/build-push-action | v7 | c3c9e263c25d99ce0380d002d59b67737d91b0dc |
| actions/upload-artifact | v7 | cf430e030ddbb5b0abf93d22962f4752f3646cd9 |

Setup selects Buildx v0.35.0 (verified upstream tag
`151a92201622eeb80e19bdd9681af2266772875f`) and the pinned BuildKit above; defaults
for insecure builder entitlements are cleared. The build action supplies GitHub's
runtime cache URL/token; no token is printed or baked into the context. GHA v2
requires Buildx >=0.21 and BuildKit >=0.20; selected versions meet that requirement.
Actual hosted service access, runner execution and v2 transfer are still unverified.

After a separately authorized push, collect all native action/step times and
downloadable `.dockerbuild` records, plus uploaded input manifests, image/runtime
evidence and metadata. Use BuildKit vertex timings to separate pip work, cache
restore/save and image load from total step duration. Report every successful and
failed sample and median across all three equivalent repetitions. Compare only
within a runner class; retain OS, CPU, RAM, Docker and builder versions from artifacts.
Do not substitute local transfer times for GHA measurements.
A matched hosted internal-cache/no-cache comparison should accompany any future
production decision; this prepared workflow measures cold seed/probe and GHA
import/export, not a complete migration or cross-provider controlled experiment.

GitHub's cache quota, eviction and service throttling can turn a nominal warm run
into a miss or failed export. Timeout/export failures remain failures (`ignore-error`
is not enabled). Unique scopes reduce collisions but consume storage; serial jobs
bound traffic. Export permission comes from GitHub's runtime cache service and event
trust, not from granting cloud or release permissions. Cache is an acceleration
input, never source/provenance evidence. Do not place secrets in caches: cache access
is broader than secret access and can include forks under other trigger policies.

Sources checked for current behavior:
[GHA backend](https://docs.docker.com/build/cache/backends/gha/),
[API v2 requirements](https://docs.docker.com/build/ci/github-actions/cache/),
[local backend](https://docs.docker.com/build/cache/backends/local/),
[GitHub cache trust/eviction](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching),
[service limits](https://docs.github.com/en/actions/reference/limits).

## Historical Cloud Build comparison

Read-only GitHub metadata for accepted run **40614584902**, dated 2026-10-28:
CI checks 169 s, DEV deployment 253 s, PROD deployment 100 s. These are whole job
intervals, including installation/auth/verification/acceptance and potentially
other overhead; **none is a Cloud Build-only duration**. The existing release
record identifies Cloud Build `379950bf-7772-464a-9f16-47bc02472efb`, but contains
no start/finish or dependency-layer timings. No new GCP operation was performed
to obtain them. Historical Cloud Build build-only duration, layer duration and
cost therefore remain **Not measured**. No cross-environment speedup is inferred.

## Correctness, supply chain and integration blockers

Every successful local sample loads an amd64 image and checks exact CMD, Python
3.12, exact direct production requirement versions, API and worker imports, required
fixture JSON, and SHA-256 equality of **all** `/app` files with its QA manifest.
Development packages pytest/Playwright/pypdf/PyMuPDF are excluded by the audit.
Readonly API runs with tmpfs `/tmp`, no application volume, dropped capabilities,
mock planning, synthetic source SHA, `/health`, collection preview and SIGTERM exit 0.
This verifies worker import compatibility; the benchmark does not repeat CI-002's
full API/worker persistent job matrix for every image. Existing tests cover that code.
One retained QA base image additionally ran the real `python -m app.worker`
entrypoint with a **new tmpfs `/data`**, network disabled and no volume/bind mount:
mock startup log and SIGTERM exit 0 **PASS**. Its container and extra QA tag were removed.

Only owned tags, containers and uniquely named builder resources are removed. QA
contexts, local cache directories, raw logs and manifests remain ignored as evidence.
No existing application data or named volume is mounted. No ownership/chmod change,
daemon setting change or global cache/volume prune occurs. Docker's shared build
cache retains newly generated entries; physical disk savings are not claimed.

A Buildx output cannot satisfy current production proof: it has no accepted Cloud
Build ID, dedicated Cloud Build service-account identity, prescribed one-step recipe
or generation-pinned GCS source archive. The QA FROM/requirements/source overlays
also intentionally differ from committed release bytes. `--load` is for local QA;
its image config/manifest and handling of attestations cannot stand in for the
published immutable digest or trusted release.json. Neither a hit nor a pinned
action establishes trusted source provenance.

Any future migration would require a separately reviewed trusted-builder identity,
event/ref and cache trust policy, exact committed context verification, digest-bound
source attestations, accepted evidence schema/verifier, reproducibility/tamper tests,
and DEV acceptance before unchanged-digest PROD promotion. It must reject feature/PR
evidence for PROD and preserve rollback evidence. CI-003 changes none of these checks.

## Operational overhead and recommendation

**Option A — retain existing Cloud Build.** Local cache measurements alone cannot
establish a production benefit across different runners/networks, and hosted GHA
and build-only Cloud Build comparisons are missing. No production cache integration
or builder migration is justified by this experiment. The local observations can
guide a future reviewed measurement task without weakening the release recipe.

This benchmark itself adds maintenance of four action pins, Buildx/BuildKit pins,
base digest, fixture/runtime checks, result parsing, cache quota and timeout behavior.
A local run creates 15 disposable builder instances and runs 48 builds plus smoke
checks. A hosted run schedules 12 jobs, 24 builds and up to 24 GHA export scopes;
runner minutes, transfer time, cache storage/eviction and failure rate need actual
hosted measurement. No invented monetary saving or engineering-hour estimate is used.
Local cache directories accumulate evidence until explicitly reviewed for cleanup.

CI-004 remains the separately authorized registry inventory/retention/cost audit,
including protection of active/rollback images and release evidence. CI-005 remains
the separately reviewed coordinator/acceptance and recovery work from the plan.
Neither is implemented by this task. Disable/remove this isolated workflow to roll
back the experiment; production delivery is unchanged.
