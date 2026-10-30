# Controlled DEV verification of the IAM-write fix

2026-10-30. **PASS: 0 SetIamPolicy, DEV PASS, PROD SKIPPED.**

The operator authorized one DEV-only Delivery run for full release SHA
`844621cd229b70e6b48b2bd16f97c46485e91ae8`. No automatic redeployment, IAM repair,
rollback, master merge, commit or push was performed in this verification.
This is the live follow-up to the [Gate D incident and patch analysis](CI_006_GATE_D_EXECUTION.md).

## Preflight and single dispatch

PR #7 was open/unmerged, the release was its current feature-branch HEAD and the
worktree was clean. The published content matched the reviewed four-file patch.
Hosted [CI 41043426579](https://github.com/piotrbarabasz/tripse-ai-demo/actions/runs/41043426579)
was allowed to finish and succeeded before any dispatch.

All 33 live policy/configuration reads matched the previous accepted DEV baseline:
dedicated builder grants, DEV/PROD isolation, WIF, IAP, invoker IAM and scoped
source/log/registry permissions were unchanged. DEV had no public members and
retained its unconditional IAP service-agent invoker grant. Development variables
passed the existing validator; Environment settings matched the reviewed baseline.
No competing Delivery run, regional Cloud Run operation or build in the audited
europe-central2/global scopes was active.

Recovery metadata and the authentic prior accepted artifact were checked:
SHA `a171dec346b79203076a22d3455e2205619584c1`, revision
`tripse-ai-dev-00032-blr`, 100% traffic, digest
`sha256:f02348dc58788091799a65f6fd1b5fa05a84e4b7b97b718d77d5b72d6b8b29be`,
accepted artifact `12969672196` from run `41038476349`.

Executed once:

```powershell
gh workflow run delivery.yml --repo piotrbarabasz/tripse-ai-demo --ref ci/ci-006-integration-acceptance -f operation=dev -f target_environment=dev -f release_sha=844621cd229b70e6b48b2bd16f97c46485e91ae8
```

## Workflow and release identity

[Delivery 41044398730, attempt 1](https://github.com/piotrbarabasz/tripse-ai-demo/actions/runs/41044398730)
ran on the exact approved SHA, with event workflow_dispatch and the feature ref.

| Job | Job ID | Result |
|---|---|---|
| ci / Tests and offline contracts | 124024800876 | SUCCESS: 1142 pytest passed, one existing Windows-only skip and one existing warning; offline contracts and browser QA passed |
| DEV deployment | 124026344789 | SUCCESS; authenticated API/UI mock acceptance and immutable release artifact |
| PROD deployment | 124028009051 | SKIPPED |

| Release field | Verified value |
|---|---|
| SHA | `844621cd229b70e6b48b2bd16f97c46485e91ae8` |
| Digest | `sha256:bf23aece14f83a4d105b819a9052262991794a34b9d393885e7cb9a885230403` |
| Cloud Build | `49b0c65c-49dc-45b1-8162-9778353da640`, SUCCESS |
| Build worker | `tripse-ai-build@tripse-ai.iam.gserviceaccount.com` |
| SDK recorded by the deployment | 591.0.0 |
| DEV revision | `tripse-ai-dev-00033-r9k`, Ready, 100% traffic |
| Accepted artifact | `12971459532`, `dev-accepted-844621cd229b70e6b48b2bd16f97c46485e91ae8-41044398730-1` |

The real authenticated serving-revision IAP health gate succeeded before Cloud
Build createTime `2026-10-30T11:01:57.773478189Z`. The fixed success message is
present in the job logs. The new release then passed API/UI mock acceptance:
private runtime checks, Studio trip revision/conflict checks, draft/preview and
internal-note checks, image/campaign operations, mock jobs, simulator deduplication,
expired viewers and authenticated browser assertions. The actual synthetic Studio
trip marker printed by the run is `8ccd0208914a4f1c97d944e8fe605e3e`.

The uploaded artifact was independently downloaded and validated through
`ci.release_proof` (run/attempt/job/ref/expiry/archive contracts). Its SHA, digest
and revision match live metadata. Separate `build_proof.verify` validated the
actual builder recipe and exact generation-pinned source bytes. The immutable
revision digest/readiness contract passed independently. No token values were
printed or included in the report.

## Actual Cloud Audit Logs count

Scope: Cloud Run Admin Activity for the DEV service, **all principals**, from
`2026-10-30T10:56:14.443894Z` through `2026-10-30T11:04:15Z` — starting before
dispatch and ending after workflow completion (`11:04:10Z`). The query was:

```text
log_id("cloudaudit.googleapis.com/activity")
AND protoPayload.serviceName="run.googleapis.com"
AND protoPayload.resourceName:"tripse-ai-dev"
AND timestamp>="2026-10-30T10:56:14.443894Z"
AND timestamp<="2026-10-30T11:04:15Z"
```

The result was read three times with a limit of 10,000; every read returned just
two service-update entries, so the query was not truncated. Both were from the
DEV deployer; one is explicitly attributable to command/gcloud.run.deploy.
The known previous deployment's two SetIamPolicy events were also retrieved as
a positive control before dispatch, confirming audit access/filter visibility.

| Read time UTC | All returned entries | Exact `google.cloud.run.v1.Services.SetIamPolicy` | Any method containing `SetIamPolicy` |
|---|---:|---:|---:|
| 11:05:25 | 2 | **0** | **0** |
| 11:05:57 | 2 | **0** | **0** |
| 11:06:29 | 2 | **0** | **0** |

This is measured runtime evidence for this deployment, not an inference from unit
tests or an empty log query alone. It is bounded to the recorded interval and
reads; it does not assert zero calls for bootstrap, PROD or automatic recovery.

## Policy, access and PROD comparison

The post-run 33-read comparison found **only the expected DEV service-description
change**. DEV IAM policy bindings, version **and etag are exactly identical** to
the pre-dispatch policy. IAP remains enabled, Invoker IAM checks remain enabled,
there is no allUsers/allAuthenticatedUsers member, and the IAP service-agent grant
is intact. Other inspected IAM policies, WIF and IAP policies/settings are unchanged.

The full PROD service description and IAM policy are exactly identical before
and after. PROD remains on SHA `c3d3e922dae3c8bd15c5a8c78c4b4a51263074cf`,
revision `tripse-ai-prod-00007-xsd`, 100% traffic; its job was skipped.

Recovery was **not triggered**. The previous a171dec snapshot and accepted evidence
remain the recovery reference; no live restore or synthetic-data cleanup was tested.
Synthetic acceptance writes remain in DEV according to the documented persistence
contracts. No extra deployment or IAM write was used to achieve the result.

Private evidence resides in `local-data/iam-write-verification/`: authorization,
preflight, before snapshots, dispatch request/result, monitor history, health/build
ordering, and `post-run/` policy snapshots, release artifact, source proof, logs,
audit filter, three raw audit reads and audit summary. This report is local and
uncommitted; the tested application/workflow source remains the approved SHA.
