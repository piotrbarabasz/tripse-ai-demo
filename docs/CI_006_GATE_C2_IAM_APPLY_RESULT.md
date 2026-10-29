# Gate C.2: approved IAM removal result

**IAM REMOVAL APPLIED AND VERIFIED. Gate D remains blocked/pending separate approval and preflight.**

This is the later execution record for the [reviewed saved plan](CI_006_GATE_C2_IAM_PLAN_REVIEW.md).
The original investigation and plan reports remain unchanged historical
checkpoints. The operator explicitly approved application after being shown the
exact target and binary-plan hash, and instructed that the interrupted CI-FIX
request be ignored. This approval covered this IAM removal only.

## Actual change

Completed at **2026-10-29 21:56:34 UTC** using the existing authorized account
`kontakt@protolume.pl`, without account/ADC changes or impersonation.

Terraform applied the existing saved binary with SHA-256:
`34e4ac7ef58fd181fa173a93e7d8625fe5f8864a1a6752b973987680b965c494`.
No replacement plan was generated. Result: **0 added, 0 changed, 1 destroyed**,
exit code 0. The destroyed resource was only this unconditional membership:

| Field | Value |
|---|---|
| Address | `google_project_iam_member.legacy_default_worker[0]` |
| Project | `tripse-ai` |
| Role | `roles/cloudbuild.builds.builder` |
| Member | `serviceAccount:690165197462@cloudbuild.gserviceaccount.com` |

The account itself was not deleted. No replacement grant was added. The
dedicated user-managed builder, Compute default account and Cloud Build service
agent remain distinct and unchanged. No full-policy overwrite was performed.

## Verification

Before apply, the plan, JSON/text exports, imported state, execution module,
provider lock and local backend overlay matched their reviewed hashes.
The six C.2 package hashes and HEAD were checked. Terraform's actual binary
export matched the reviewed JSON hash and passed the existing plan guard again.
All 33 successful live evidence queries from the original collection were
repeated before apply and matched their reviewed snapshots exactly.

After apply the same 33 queries were repeated:

- The project IAM policy, canonicalized only for ordering and its new etag,
  differs solely by removal of the approved member from the approved role.
- The legacy member has no remaining direct project binding in that policy.
- The other 32 evidence results are unchanged: organization IAM, repository,
  source/log/document bucket policies, visible service-account policies,
  dedicated custom roles, effective default-builder constraints, WIF providers,
  IAP policies/settings and DEV/PROD Cloud Run service descriptions and IAM.
- Cloud Run configuration and traffic are therefore unchanged in the observed
  service descriptions. No runtime request, build or restore was executed.
- The isolated local state retains its lineage, now has serial 3 and contains
  zero resources. State SHA-256 after apply:
  `e0c946b6aac702d105ad78c5772e97d182056dd8d6db46d770fe255be774b9aa`.

The state path and `TF_DATA_DIR` remained the reviewed local paths. Production
Terraform state was not adopted or migrated. Authentication was confined to a
short-lived token in the Terraform subprocess environment; exact-token checks
of captured Terraform output and resulting state found no token persistence.

Private, Git-ignored evidence is under
`local-data/phase-b-gate-c2/operator-state/approved-apply/`: authorization record,
`apply.stdout.log`, `apply.stderr.log`, before/after JSON snapshots and
`apply-verification.json`. Original plan/import evidence and the pre-change
local state backup remain in its parent directory. Do not reapply the old plan:
it refers to the pre-removal state.

## Limits and next stage

This proves the exact live IAM delta, not successful execution of a new build
or deployment under the resulting permissions. No Cloud Build submission,
image publication/deletion, deployment, traffic restore, probe impersonation,
WIF/IAP modification, commit or push was performed. Existing C.1/C.2 code and
proposal files remain unchanged; only this new report and ignored evidence
were added during application.

The original investigation's visibility limits remain, including the denied
service-agent IAM-policy read, unaudited external consumers/regions and
deny/PAB/group effects. Repository search found no other numeric legacy-member
Terraform resource; external state ownership was not independently enumerable.
The operator approved the plan with those documented limitations. This does
not establish the absence of all inherited/equivalent privilege paths.

No code changed, so the full 1086-pass suite was not rerun for the IAM apply.
The previous 29-pass guard-test run and this execution's guard validation remain
the relevant local checks. Live post-change build/probe/recovery acceptance has
not been performed. Gate D still requires its own approval, current private
CI-probe health preflight, recovery/write-scope review and SHA/WIF/Environment
recheck. Any restoration of this broad grant requires separate emergency
authorization and a newly reviewed restoration plan; it is not automatic.
