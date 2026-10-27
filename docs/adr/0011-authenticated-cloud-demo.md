---
id: ADR-0011
title: "Authenticated cloud_demo with shared modules and durable adapters"
status: proposed
date: 2026-10-26
author: "Codex — implementation proposal"
area: "application composition, access, storage, asynchronous jobs, deployment"
related_tasks: [CLOUD-PARITY-001, TRIPSE-PROD-BOOTSTRAP-001]
related_prs: []
supersedes: [ADR-0009]
---

# ADR-0011: Authenticated cloud_demo

Implementation: prepared and tested offline; no GCP rollout. Owner acceptance of
this ADR and customer-data production readiness have not been established.

2026-10-27 operational evidence: DEV run 40523770207 accepted private cloud_demo
at cf94e20a7f53c2d7674d83319704a54e2a92889e, artifact 12741609814. This supersedes
the original offline-only note for exercised DEV gates; backup/restart/isolation
drills and production acceptance are not inferred. PROD_BOOTSTRAP-001 prepares a
separate empty PROD state/root, independent bucket/database/task/runtime IAM, and
leaves shared project APIs in the original DEV state. See
[production bootstrap](../PROD_BOOTSTRAP_001.md). No PROD apply or rollout occurred;
the ADR remains proposed without formal owner acceptance.

## 1. Context and problem

Code evidence: `main.create_app` previously selected a different application in
Cloud Run. ADR-0009 intentionally omitted editors, uploads, SQLite jobs and chat.
The CLOUD-PARITY-001 request authorizes shared authenticated demo functionality,
without deploying or exposing private documents anonymously.

## 2. Alternatives considered

Retain preview only (insufficient functional parity); copy modules into preview
(divergence); mount a bucket as JSON/SQLite disk (incorrect locking/durability);
introduce Cloud SQL and a separate full application (larger operational scope).
Chosen: existing routers/domain/UI with GCS and Firestore/Tasks adapters. No
additional load balancer is required for direct Cloud Run IAP.

## 3. Decision

Keep `local`, `readonly_demo`, and opt-in `cloud_demo`. This supersedes the
cloud-only-preview restriction in ADR-0009, retaining its public preview as an
independent supported mode. ADR-0010 still governs publication of that preview.
ADR-0002/0005/0007/0008 remain the LOCAL decisions; this adds cloud boundaries.

Verify IAP ES256 assertions against Google keys with exact service audience,
issuer, subject, email, issued-at and expiry. Explicit readers/editors; only
editors may write, with exact configured Origin. All private HTML, static files,
API and images require membership. `/health` has no private data and supports
container probes. Only the dedicated verified task account may invoke processing.

Use private separate DEV/PROD buckets, named databases, queues and task identities.
GCS JSON overlays use generation preconditions; image bytes use the existing
decode/re-encode validation and private API responses. Fixtures remain read-only.
No bucket mounts, local persistence or SQLite worker in Cloud Run.

Firestore jobs store owner, dedup identity, status, lease/fence, result, token hash
and simulator outbox. Cloud Tasks delivery uses deterministic task names and OIDC
through the reviewed IAP OAuth client. Three processing attempts; queue delivery
retries are separately bounded. Terminal writes are fenced and messages derived
from the committed job, avoiding a second notification side effect. Interrupted
dispatch has an explicit operator recovery command. Only mock generation is
enabled; LIVE remains fail-closed pending the controls listed in the audit.

## 4. Rationale and evidence limits

**Documented requirement:** CLOUD-PARITY-001 and existing confidentiality rules.
**Code evidence:** shared `document_router`, `hub_router`, `demo_router`,
`viewer_router` and `worker.generate_job_result`; adapters in `cloud_runtime`,
`cloud_jobs`, `cloud_access` and `document_studio/cloud_storage`.
**Inference:** this is a smaller operational addition than Cloud SQL for a small
authenticated mock demo. No performance or price advantage has been measured.
**Unconfirmed:** deployed IAM/OAuth, backup restore, real multi-instance behavior,
customer acceptance and suitability for real personal data.

## 5. Positive and negative consequences

One UI/domain implementation and independent local operation. Cross-instance CAS
and durable jobs replace ephemeral files. More cloud services, OAuth provisioning,
retry monitoring, SDK dependencies and restoration procedures must be maintained.
Cloud viewer tokens additionally require their owner's IAP identity; they are
not public sharing links. Demo members share document overlays within an
environment; jobs and conversations are private to their principal.

## 6. Technical debt and limitations

See the OPEN/BLOCKED register in [the parity audit](../CLOUD_PARITY_AUDIT.md).
No real WAHA session, automatic dispatch reconciler, real customer-data approval,
or LIVE activation. Per-owner job/conversation queries currently suit a small
demo; retention/pagination and admission quotas need work before scaling. An
operator recovers exhausted queue delivery; this is not unattended job recovery.
GCS versioning/soft delete and Firestore PITR are configured, but a restore drill
and independent backup access controls remain operator gates.

## 7. Cost impact

Cloud Run, GCS operations/bytes/version retention, Firestore operations/indexes/
PITR, Tasks/retries, OAuth/IAP setup, logging, backups and maintenance are separate
cost areas. Optional Maps JavaScript has its own budget. OpenAI/Places/Routes are
disabled. No measured hours, API prices or billed amounts are available.

## 8. Links, tasks, PR and acceptance

Task: CLOUD-PARITY-001. PR/commit: none created for this change. Acceptance:
not recorded; `proposed` is deliberate. Sources and run instructions:
[audit](../CLOUD_PARITY_AUDIT.md), [deployment](../DEPLOY_GCP.md),
[Studio](../DOCUMENT_STUDIO.md), [Hub](../HUB.md).
Google references are linked in the audit and deployment instructions.

## 9. Reconsideration criteria

Revisit for real customer data, unauthenticated sharing, non-Google identities,
LIVE billing, large result sizes, high conversation volume, unattended recovery,
or a requirement for transactional writes across multiple Studio documents.

## Change history

| Date | Author | Change and reason | Task |
|---|---|---|---|
| 2026-10-26 | Codex | New cloud parity proposal; preserve preview and LOCAL contracts | CLOUD-PARITY-001 |
