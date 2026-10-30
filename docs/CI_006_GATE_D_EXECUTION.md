# Gate D: controlled DEV deployment result

2026-10-30. **Workflow and DEV functional acceptance: SUCCESS. Scope exception:
the existing deployment recipe made two redundant DEV service IAM-policy writes.**
No further cloud mutations were performed after that exception was discovered in
post-run verification. It must be reviewed before another release. No PROD
deployment, master merge, WIF change, IAP change or IAM grant expansion occurred.

## Approved identity and preflight

The operator explicitly approved DEV only, image publication, synthetic DEV
writes and the existing automatic traffic-recovery mechanism for full SHA
`a171dec346b79203076a22d3455e2205619584c1` on
`ci/ci-006-integration-acceptance`, PR #7. The earlier authentication blocker was
resolved by renewed existing-account access; no account/ADC switch, impersonation
configuration or additional permission was introduced by this execution.

Before the one manual dispatch:

- Local HEAD, remote branch and open/unmerged PR matched the approved SHA.
- Hosted CI `41019455103` was successful for that exact head.
- All 33 previously successful live policy/configuration queries matched the
  Gate D.0 snapshot, including WIF, dedicated builder and DEV/PROD grants.
- The numeric legacy worker's broad project membership remained absent.
- GitHub Development variables passed the existing validator; Development
  Environment settings and the reviewed workflow matched the approved baseline.
- No active non-CI workflow, regional Cloud Run operation or build in the audited
  europe-central2/global scopes was found.
- The current DEV revision and immutable digest passed the actual snapshot and
  previous-revision contracts: `tripse-ai-dev-00031-z2l`, 100% traffic, SHA
  `c3d3e922dae3c8bd15c5a8c78c4b4a51263074cf`, cloud_demo/mock, IAP enabled.
- Its accepted artifact `12882053228` / run `40839099491` and exact-generation
  source proof were independently revalidated read-only as a recovery reference.

Only this dispatch was executed; it was not retried:

```powershell
gh workflow run delivery.yml --repo piotrbarabasz/tripse-ai-demo --ref ci/ci-006-integration-acceptance -f operation=dev -f target_environment=dev -f release_sha=a171dec346b79203076a22d3455e2205619584c1
```

## Workflow and accepted release

[Delivery run 41038476349, attempt 1](https://github.com/piotrbarabasz/tripse-ai-demo/actions/runs/41038476349)
recorded the exact approved head and feature branch with event workflow_dispatch.

| Job | Job ID | Result |
|---|---|---|
| ci / Tests and offline contracts | 124005090154 | SUCCESS: 1124 pytest passed, one existing Windows-only skip, one existing warning; offline contracts and browser QA passed |
| DEV deployment | 124006998513 | SUCCESS, acceptance `api_ui_mock`, immutable release artifact uploaded |
| PROD deployment | 124008817628 | SKIPPED |

The mandatory DEV IAP gate succeeded after WIF, at **10:13:32 UTC**. Its fixed
success message is present in the completed logs. It checked GET /health against
the **previously serving** revision identity using the existing dedicated probe's
keyless JWT. The build/deploy step began at 10:13:51 UTC; Cloud Build's authoritative
createTime is **10:14:28.931196423 UTC**. Thus the authenticated health gate passed
before the build was submitted. Tokens/claims were not printed in this report.

| Release field | Verified value |
|---|---|
| Image/policy SHA | `a171dec346b79203076a22d3455e2205619584c1` |
| Image digest | `sha256:f02348dc58788091799a65f6fd1b5fa05a84e4b7b97b718d77d5b72d6b8b29be` |
| Cloud Build ID | `fa88c70d-02a3-466a-88a4-af31f4688117` — SUCCESS |
| Actual build worker | `tripse-ai-build@tripse-ai.iam.gserviceaccount.com` |
| Registry image | `europe-central2-docker.pkg.dev/tripse-ai/tripse-ai/tripse-ai` |
| DEV revision | `tripse-ai-dev-00032-blr` — Ready, 100% traffic |
| DEV origin | `https://tripse-ai-dev-64ctpggq3a-lm.a.run.app` |
| Runtime | dev / cloud_demo / mock, `tripse-ai-dev@tripse-ai.iam.gserviceaccount.com` |
| Accepted artifact | `12969672196`, `dev-accepted-a171dec346b79203076a22d3455e2205619584c1-41038476349-1` |

The artifact was independently downloaded and passed `ci.release_proof` with
run/attempt/job/ref/expiry/archive checks. Its SHA, digest and revision match live
metadata. A separate post-run `build_proof.verify` passed the recorded build recipe,
dedicated worker and exact generation-pinned source bytes. This is actual
post-hardening Cloud Build execution, not an offline permission simulation.

## DEV tests and recovery

The pinned coordinator completed authenticated API/UI mock acceptance, including
private health/runtime checks, Studio trip create/update/stale-revision rejection,
two document drafts/previews, internal-note protection, synthetic PNG upload/read,
campaign previews, mock planner processing, simulator deduplication/conversation,
expired viewer handling and authenticated browser checks. Any failed assertion
would have prevented accepted release evidence. CI's browser suite also passed.

The Studio synthetic trip printed by the actual run is
`5881fdb1876a4e849d02345e6bf8337f`. The accepted API path creates the six GCS object
names, three Firestore jobs and normally three task names described in the
[Gate D.0 write inventory](CI_006_GATE_D_PREFLIGHT.md). Completion is evidenced by
the accepted `api_ui_mock` record and successful pinned code; this report does
not claim a separate exhaustive enumeration of every persisted object/job.
No test cleanup or container restart experiment was performed. Synthetic data
persists according to the existing storage contracts.

**Recovery was not triggered:** deployment/acceptance succeeded and no automatic
traffic restore was needed. The preserved previous reference remains c3d3e922,
digest `sha256:b4a86311712ace6ff894a346c465a74ecda4272a38b5599821f4d8d8c36ac28f`,
revision `tripse-ai-dev-00031-z2l`. Metadata/source/evidence checks passed, but this
run does not prove a live restoration or application-data rollback.

## Scope exception: redundant SetIamPolicy calls

Post-run comparison found changes only in the DEV service description and its
IAM policy etag. **The DEV IAM bindings and policy version are identical before
and after.** Project IAM, all other scoped policy/configuration snapshots, WIF,
IAP and the full PROD service description remain unchanged.

Cloud Audit Logs nevertheless record two
`google.cloud.run.v1.Services.SetIamPolicy` calls on DEV by
`tripse-ai-dev-ci-deploy@tripse-ai.iam.gserviceaccount.com`, at **10:15:44.029172 UTC**
and **10:15:45.988443 UTC**. Both logged request policies contain the same bindings
as the pre-deployment policy. No grant addition/removal or public invoker resulted.
The existing gcloud deployment recipe includes private-access/IAP flags; the exact
client-internal cause of the two calls was not instrumented independently.

These are still IAM-policy writes, despite unchanged effective grants, and do
not satisfy a literal no-IAM-write requirement. That behavior was missed in the
pre-deployment review. It was discovered after the successful workflow completed;
no further cloud mutation, rerun, compensating IAM write or manual rollback was
attempted. The next release must explicitly address this behavior through a
separately reviewed change or an explicitly revised operational scope. The local
report does not authorize either remediation or another deployment.

## Final state and evidence

- **DEV:** accepted approved SHA/digest, Ready revision `00032-blr`, 100% traffic;
  private IAP and invoker bindings retained.
- **PROD:** unchanged full service metadata, SHA
  `c3d3e922dae3c8bd15c5a8c78c4b4a51263074cf`, revision
  `tripse-ai-prod-00007-xsd`, 100% traffic. PROD job skipped.
- **Git:** no merge, commit or push as part of Gate D execution. This new report
  is local and uncommitted. Application, workflow and Terraform source remain at
  the approved SHA; no repair or security bypass was introduced.

Private evidence is under
`local-data/gate-d-approved-run/resume-1/`: preflight-PASS, dispatch request/result,
selected run, monitor snapshots, health/build ordering, original recovery evidence,
and `post-run/` accepted release, verified build, workflow logs, policy comparisons
and IAM audit entries. Raw credentials, Terraform state and unrelated application
data are not part of this report or a publication.

## Follow-up — redundant IAM writes patch prepared, 2026-10-30

**Prepared only: no commit/push, build, deployment, rollback or cloud mutation.**
The working-tree baseline is `7b23184b386ddeb16e9978dc076e8c9a29758090`, whose
only change after the deployed a171dec was publication of this incident report.

The audit user-agent identifies **gcloud 591.0.0**, with both calls belonging to
the same `gcloud.run.deploy` invocation. The exact 591.0.0 core sources were
downloaded from [Google's official component archive](https://dl.google.com/dl/cloudsdk/channels/rapid/components/google-cloud-sdk-core-20261026202537.tar.gz),
verified against the official component-manifest SHA-256
`0485899fd0e2897d5eea2e868e4fc3babc3b8440f0435cd5d202cfe1a5b672a3`,
and inspected without installing/updating the local SDK (590.0.1).

Confirmed SDK behavior:

- `--no-allow-unauthenticated` supplies false to `_HandleAllowUnauthenticated`,
  which calls `AddOrRemoveIamPolicyBinding` to remove allUsers/run.invoker.
- `--iap` supplies true to `_HandleIap`, which calls
  `_AddIamPolicyBindingWithRetry` for the IAP service-agent invoker grant.
- The shared binding helper always sends `SetIamPolicy`, even when removal finds
  no binding or addition finds the member already present. This explains two
  writes of equivalent policies. Audit entries alone do not identify which
  individual call came from which handler; that ordering is inferred from the
  matching SDK implementation, not a per-handler runtime trace.
- `--invoker-iam-check` sets the service's invoker-check annotation through
  `InvokerIamChange`; it is not either binding-reconciliation trigger. It is
  retained. For an existing service, omitting allow-unauthenticated avoids the
  new-service prompt, and omitting IAP leaves its current state unchanged.
  See also the [official deploy flag reference](https://docs.cloud.google.com/sdk/gcloud/reference/run/deploy).

The minimal patch affects only DEV cloud_demo: normal deployment now requires
an existing private service, enabled IAP/Invoker checks, no allUsers or
allAuthenticatedUsers member under any role/condition, and the correct project's
unconditional IAP service-agent run.invoker grant. Missing service/bootstrap or
invalid security state fails before any mutation, rather than repairing grants.
Only after those reads succeed are `--no-allow-unauthenticated` and `--iap`
omitted. Invoker checks, pinned image/runtime identity, provenance, smoke,
recovery and WIF checks remain. PROD and readonly command flags/behavior are
unchanged, including explicit security configuration on their existing paths.

Read-only live verification confirms DEV remains private with IAP enabled,
Invoker checks enabled, the service-agent grant intact and the same IAM policy
as after Gate D. PROD service/IAM and DEV/PROD WIF match their prior snapshots.
The patch has not been deployed to establish those results.

Validation: **16 new regression cases; 343 focused tests PASS; full suite 1143
PASS** (one existing deprecation warning), offline contracts, make check and
git diff --check PASS. The existing cloud deployment test now separately covers
private existing DEV and both existing/new PROD flag contracts, preserving its
image, secret, private-smoke and no-publication assertions. An additional private
offline execution of the actual SDK handlers with fake binding helpers produces
two reconciliation requests for the old flags and zero for the verified-existing
DEV path; it makes no network or GCP calls.

**Limitation:** these tests confirm command construction, rejection of unsafe
state and SDK handler behavior. A claim of zero live SetIamPolicy calls still
requires a separately authorized DEV deployment and Cloud Audit Logs review.
No such deployment or authorization is inferred here. Proposed commit:
`fix(ci): preserve private DEV IAM during image deployment`.
Private source/audit checks and logs remain in `local-data/iam-write-fix/`.
