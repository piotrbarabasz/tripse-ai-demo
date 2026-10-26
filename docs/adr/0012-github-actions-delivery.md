---
id: ADR-0012
title: "GitHub Actions delivery with WIF and immutable DEV acceptance"
status: proposed
date: 2026-10-26
author: "Codex — implementation proposal"
area: "CI/CD, IAM, release evidence, rollback"
related_tasks: [GITHUB-CICD-001]
related_prs: []
supersedes: []
---

# ADR-0012: GitHub Actions delivery

Implementation: workflow/scripts/tests prepared locally; no push, IAM apply or
cloud deployment. Owner acceptance and real runner acceptance remain unrecorded.

## 1. Context and problem

The manual pipeline already builds committed SHA archives, pins digests and
supports preview and cloud_demo. Actual DEV was running new code in readonly
mode, illustrating why source/build/deploy and functional acceptance must be
separate milestones. The user requests branch DEV delivery, approved master PROD
promotion, credential-free PR CI and keyless noninteractive authentication.

## 2. Alternatives considered

Permanent service-account JSON (rejected), human IAP session secrets (rejected),
duplicating gcloud deployment in YAML (rejected), per-branch DEV locks (incorrect
for one shared service), promoting whatever tag/DEV revision is current (racy).
Chosen: WIF, existing Python deployment functions, one DEV mutex, immutable
GitHub acceptance proof and independently protected PROD.

## 3. Decision

Use reusable unprivileged `ci.yml` for PRs and Delivery's test dependency.
`delivery.yml` handles dev/master pushes and explicit deploy/promote/rollback
dispatches. PROD is master-only, a protected GitHub environment and a separate
restricted WIF identity. Pushes execute trusted repository code on DEV; fork PRs
never receive cloud identity. Actions are pinned to full upstream SHAs.

Reuse `deployment.py` build/deploy/smoke contracts. Generate strict non-secret
config outside source; require explicit expected mode/project/service/region and
preexisting private app infrastructure. Keyless probe credentials are signed by
IAM Credentials for a dedicated environment account, with no human token/key.
Readiness failures block rather than enabling infrastructure or falling back.

An immutable SHA tag alone does not prove its source when DEV branches can submit
builds. Trusted acceptance verifies the actual successful Cloud Build recipe,
builder identity and generation-pinned source archive against every committed
image-context byte. Release proof records that verification and the build ID.

Keep one cross-branch DEV lock through acceptance/artifact upload and reject stale
sequence/head runs. Freeze tested SHA/digest/mode/revision/run provenance in an
immutable artifact. PROD verifies trusted master workflow/job evidence, digest
and branch ancestry, then deploys that exact image without building. DEV can move
to another dev release during approval without changing the frozen proof.

CI-CD-FIX-002 narrows automatic DEV delivery to dev/master, while keeping explicit
manual branch deployment. GCP trust enforces the same push restriction. Validate
all five GitHub Environment settings with a dependency-free check before package
installation and authentication, then run the full runtime schema. An operator-only
read-only bootstrap checker and exclusively created local nonsecret config bundle
make setup reviewable; neither helper provisions GitHub/WIF/resources. Terraform
application/IAM and GitHub approval protection remain separate manual gates.

## 4. Rationale and evidence

**Requirement:** GITHUB-CICD-001. **Code evidence:** workflow dependencies, explicit
permissions/environments, `scripts/gcp/ci.py`, `smoke_auth.py`, resource checks,
receiving-revision digest checks and manual WIF Terraform. **Inference:** this
reduces deployment ambiguity without redesigning the app/storage. **Unconfirmed:**
real WIF claims/refresh, scoped IAM, runner IAP and reviewer configuration; local
tests cannot prove those operational boundaries.

## 5. Consequences

Feature branches share DEV deliberately; accepted master proof remains stable.
CI account scope and artifact provenance become part of release security.
There is more bootstrap and synthetic-data/retention maintenance. An expired
artifact or stale rerun fails closed and requires a new acceptance run.

## 6. Debt and limitations

Required reviewers and branch protection cannot be guaranteed by YAML and must
be configured by an operator. Real app infrastructure remains a prerequisite.
GitHub locks cannot serialize a separate operator terminal. No automatic schema
changes or data restores. Failed releases attempt prior traffic restoration and
keep access private; restoration failure is explicit and never recorded as an
accepted release. Public preview restoration after failure needs operator review.
Full backup/restart/negative IAM drills remain acceptance tasks.

## 7. Cost impact

Actions/browser minutes and artifacts, Cloud Build/Registry, runtime, storage,
Firestore/Tasks and operations/monitoring. Synthetic acceptance has infrastructure
cost without OpenAI/Maps calls. No hours, amounts or measured savings supplied.

## 8. Related work and acceptance

[Runbook/bootstrap](../GITHUB_CICD.md), [deployment](../DEPLOY_GCP.md),
[parity](../CLOUD_PARITY_AUDIT.md), [ADR-0011](0011-authenticated-cloud-demo.md).
Task GITHUB-CICD-001; no commit/PR created for this change, no owner acceptance
recorded. This extends ADR-0011 and preserves ADR-0010's public-preview rules;
it does not supersede the app's storage/auth decisions or remove manual Make.

## 9. Reconsideration

TRIPSE-WIF-AUTH-003 audits the repository's immutable OIDC subject setting and
corrects only the DEV subject contract, preserving exact owner/repository IDs,
environment/event/ref/workflow checks. DEV mappings cover all condition claims.
Temporary selected-claim diagnostics cannot authorize access and must be disabled
after successful operator verification. PROD policy remains unchanged and requires
separate review. See [incident runbook](../WIF_AUTH_003.md); no automatic apply.

Untrusted branch deployments, private runner requirements, artifact retention
beyond 90 days, multi-project tenants, live paid planning, canary traffic or
automated data migration/restore require renewed design and acceptance.

## Change history

| Date | Author | Change | Task |
|---|---|---|---|
| 2026-10-26 | Codex | Proposed WIF delivery and tested-release evidence; no activation | GITHUB-CICD-001 |
| 2026-10-26 | Codex | Narrow automatic pushes to dev/master; early safe config diagnostics and operator bootstrap/check; no remote mutation | CI-CD-FIX-002 |
| 2026-10-26 | Codex | DEV immutable subject correction and temporary safe OIDC diagnostics; PROD unchanged; no apply/deployment | TRIPSE-WIF-AUTH-003 |
