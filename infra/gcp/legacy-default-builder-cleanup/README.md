# Operator-only legacy default worker cleanup

**Execution update:** the separately approved import/plan and exact saved-plan
apply have since completed; see the [application result](../../../docs/CI_006_GATE_C2_IAM_APPLY_RESULT.md).
The legacy membership is absent. The procedure below records the original
proposal; do not repeat import/apply or regrant the member. Operational state and
saved plans remain private and are not distributed with this module.

**Proposal only. No import, plan against live state, apply or IAM change was run
in Gate C.2.** Review [the C.2 report](../../../docs/CI_006_GATE_C2_IAM_HARDENING.md)
before authorization. This isolated module manages only the unconditional member:

- Project: `tripse-ai`
- Role: `roles/cloudbuild.builds.builder`
- Member: `serviceAccount:690165197462@cloudbuild.gserviceaccount.com`
- Address: `google_project_iam_member.legacy_default_worker[0]`

It uses the existing repository's import-then-remove member-resource convention
and the identical locked Google provider 8.8.1. It does not share the application
or GitHub bootstrap state. No WIF, account, repository, bucket or service is managed
here. `google_project_iam_member` preserves other members; there is no authoritative
project/role policy resource. Default retain=false cannot remove an unimported
binding: **an empty no-op plan is not a successful cleanup**.

## Preconditions requiring owner review

Confirm the live principal/role/scope/condition and preserve its etag. Confirm no
other state/automation owns this same binding; reconcile that owner first if it
does. Recheck dependency inventory beyond the audited europe-central2/global
builds/triggers. Preserve the dedicated builder, Compute default and Google
service agent, all scoped source/log/registry grants, DEV/PROD identities and WIF.

Proposed state backend is a **new isolated local state** at:
`D:\Projects\tripse-ai-ci-integration\local-data\phase-b-gate-c2\operator-state\legacy-default-builder.tfstate`.
It has not been created/adopted. The owner must approve that location and backup/
access ownership before import. Never copy existing production state or point
this procedure at a shared backend. Do not run state move/rm or migration commands.
The state and saved plans are operational metadata and must stay ignored/private.

Use the existing authorized account. Terraform requires its own valid provider
authentication; the operator may capture a short-lived `gcloud auth print-access-token`
result directly into `GOOGLE_OAUTH_ACCESS_TOKEN` in the process environment without
printing it. Do not paste it, store it, use shell tracing, change accounts/ADC or
create keys. Clear that temporary environment variable after the operation. Use
an isolated `TF_DATA_DIR` under the same ignored operator directory, not another
module's initialized backend/provider directory.

## Phase 1 — separately approved state import and plan, no IAM mutation

The following are command templates for an operator in the integration root.
They were **not executed**. Set `$iamStatePath` to the approved absolute local
state path above and create its owned directory. Initialize only this module:

```powershell
terraform -chdir=infra/gcp/legacy-default-builder-cleanup init -input=false -lockfile=readonly

terraform -chdir=infra/gcp/legacy-default-builder-cleanup import -input=false "-state=$iamStatePath" -var=retain_legacy_default_worker_grant=true 'google_project_iam_member.legacy_default_worker[0]' 'tripse-ai roles/cloudbuild.builds.builder serviceAccount:690165197462@cloudbuild.gserviceaccount.com'

terraform -chdir=infra/gcp/legacy-default-builder-cleanup plan -input=false "-state=$iamStatePath" -var=retain_legacy_default_worker_grant=false -out=REVIEWED_ABSOLUTE_PRIVATE_PLAN_PATH
```

The temporary true value is for adopting the existing binding, **never approval
to create/regrant it**. If import reports the member absent, stop and re-audit;
do not apply a retain=true plan to recreate it. Do not copy this flag to the
existing bootstrap `retain_legacy_builder_grant`: that targets a different account.

Export JSON from that exact saved binary plan using `terraform show -json`,
writing UTF-8 (PowerShell `Set-Content -Encoding utf8`, not the Windows UTF-16 `>`
default). Then run from the repository root:

```powershell
.venv/Scripts/python.exe -m scripts.gcp.legacy_builder_plan --plan-json REVIEWED_PRIVATE_PLAN_JSON_PATH
```

Require exactly **0 additions, 0 updates, 1 member deletion**, with the exact
address/project/role/member above and no condition, drift, import/move/deferred
changes, replacements, other resources or outputs. The offline guard rejects
wrong/extra/missing actions, but it does not establish that a JSON file belongs
to a binary plan, current IAM safety or operator authorization. Keep their hashes,
module/lock hashes, fresh policy evidence and a human-reviewed Terraform display
together. Stop if anything differs. No credentials belong in the package.

## Phase 2 — separate approval of the exact saved plan, then operator apply

Return the actual plan and evidence for approval; the expected shape here is not
an already approved real plan. Only after explicit IAM-change approval may the
operator apply **that exact saved binary plan**, verifying its hash immediately
beforehand. Do not regenerate/auto-approve a replacement plan or apply retain=true.
This changes one IAM member; no account is deleted and no role is transferred.

Re-read IAM and confirm the unconditional legacy broad grant is absent, no
equivalent remaining project/inherited/resource grants were introduced, and all
dedicated builder/deployer/probe/service-agent source/log/registry bindings remain.
Verify immutable tags, source proof, WIF and service traffic/config are unchanged.
An empty module after removal does not continuously enforce absence of grants
added outside Terraform; post-change inspection and ownership remain necessary.

No Cloud Build, deployment, probe impersonation or live restore is part of this
IAM approval. A separately approved DEV experiment must still pass preflight and
acceptance. Gate D is not approved by a passing cleanup plan.

## Recovery — separate emergency authorization

If a previously unidentified legacy consumer fails, stop feature dispatches and
identify the missing dependency. Do not add broad roles to the dedicated builder
or Compute account and do not remove the Cloud Build service agent.

If the owner explicitly authorizes restoring the previous risk temporarily,
prepare a **separate** retain=true restoration plan against this same isolated
state: it should add only the exact previous unconditional legacy member. Human
review, a new approved binary-plan hash and a time limit are required. The cleanup
guard deliberately rejects this addition and must not be weakened to authorize
recovery. Prefer scoped permissions for a proven dependency when separately
reviewed. After temporary restoration, resolve the dependency and obtain approval
for a new removal plan; never overwrite the full project IAM policy.
