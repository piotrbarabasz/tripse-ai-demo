# Gate C.2 follow-up: imported state and real removal plan

**READY FOR IAM CHANGE APPROVAL. No apply has been performed. Gate D remains blocked.**

This supplements the [C.2 investigation](CI_006_GATE_C2_IAM_HARDENING.md)
and [operator procedure](../infra/gcp/legacy-default-builder-cleanup/README.md).
Their statements that import/plan were not run describe the original proposal
checkpoint. They are preserved unchanged; this report records the later,
separately authorized Phase 1 execution on 2026-10-29, completed at 20:22:57 UTC.
The operator's continuation followed an explicit request to approve only isolated
state import and preparation of a deletion plan. It did not authorize IAM changes.

## Scope and actual result

Worktree: `D:\Projects\tripse-ai-ci-integration`; branch
`ci/ci-006-integration-acceptance`; HEAD
`c8fec8777cd6f77b88418216de8cd506035ff031`.

| Check | Actual result |
|---|---|
| Terraform / locked Google provider | 1.16.6 / 8.8.1 |
| Initialization | PASS, explicit local backend, readonly provider lock |
| Import existing unconditional member | PASS, one resource with one indexed instance |
| Saved real plan | **0 additions, 0 changes, 1 deletion**; detailed exit code 2 |
| Offline plan guard | PASS on JSON exported from that saved binary |
| Independent human-readable display | Exact target and deletion only |
| Project IAM before/after planning | Identical full policy, including etag |
| Guard tests rerun | 29 passed |
| Apply / IAM mutation / deployment / publication | Not executed |

The only deletion is `google_project_iam_member.legacy_default_worker[0]`:

- Project: `tripse-ai`.
- Role: `roles/cloudbuild.builds.builder`.
- Member: `serviceAccount:690165197462@cloudbuild.gserviceaccount.com`.
- Condition: none.

This removes one role membership, not the service account. It does not manage
the dedicated builder, Compute default account, Cloud Build service agent,
DEV/PROD identities, WIF, buckets, registry or Cloud Run services. The guard
accepted exactly one delete, with no other resource/output changes or drift.

## Execution isolation and evidence

Private evidence root, ignored by Git:
`local-data/phase-b-gate-c2/operator-state/`.

The execution copy contains byte-identical approved `main.tf` and lockfile plus
`local-backend.tf`, fixing the absolute local state path to
`D:\Projects\tripse-ai-ci-integration\local-data\phase-b-gate-c2\operator-state\legacy-default-builder.tfstate`.
`TF_DATA_DIR` was confined to `operator-state/terraform-data`; its backend
metadata was checked for local type and that exact path. No production state
was copied, migrated or locked. The new state has serial 1 and contains only
the imported member. Its private backup is `imported-state.private-backup.json`.

Commands executed in the isolated execution directory were `init`, `import`
with retain=true, `plan` with retain=false and a saved binary, and `show`
in JSON/text formats. No retain=true plan or apply was run.
Provider authentication used a short-lived token from the existing authorized
account `kontakt@protolume.pl`, only in the Terraform child environment.
Inherited credential/impersonation, CLI argument and Terraform log overrides
were excluded. Account/ADC configuration was not changed. The exact token was
absent from captured command output, state and all decompressed saved-plan
members. No credentials were printed or persisted.

| Artifact under evidence root | SHA-256 |
|---|---|
| `legacy-default-builder-removal.tfplan` | `34e4ac7ef58fd181fa173a93e7d8625fe5f8864a1a6752b973987680b965c494` |
| `legacy-default-builder-removal.plan.json` | `885d5b5000d4107204e0e41a90e9ee13b34360570cc087820b140bbac854fb82` |
| `legacy-default-builder-removal.plan.txt` | `db451321e51708978631ada3f5d2dff01977b1ddc87cd7896bdaa9cdd7f87b7e` |
| `legacy-default-builder.tfstate` | `75217071392afebdf0abd3c61ccf9a35675b1a220ce6e739ee9d8e5e3b527434` |
| `execution/main.tf` | `9e2c2c3919472d4b6d39daf5527ce55fe2a2cffbc25c04d1fd4cc1eadd280ffc` |
| `execution/.terraform.lock.hcl` | `0fc7578308f51b19c38039ab1e8d01bc462e28f914e41307035019b4f5a8a691` |
| `execution/local-backend.tf` | `348325e24bffcd0956ef425490e09a34cdc2f9e99543c54beb81d7094d3ef67d` |

`execution-context.json`, `plan-review-summary.json`, `guard-review.json`, command
logs and `iam-before.json` / `iam-after-plan.json` retain the private audit trail.
The binary and exports were produced together in this execution; the offline
guard alone does not establish that correspondence or authorize application.

## Preservation, limits and next checkpoint

The six approved C.2 package files and all six pre-existing modified/untracked
C.1/Gate C files retain their recorded hashes. The C.1 remediation patch remains
unchanged. Existing worktrees were not modified. This follow-up changes only
this new report and ignored operational evidence. No commit or push occurred.
The prior 1086-pass full suite and 330-pass focused suite remain historical
C.2 evidence; only the 29 plan-guard tests were rerun for this execution.

The real plan proves the proposed action shape, not absence of every dependency.
Before apply the owner must confirm no competing state/automation owns the
binding and no unaudited consumer needs the legacy grant. The earlier limits
remain: other regions/external consumers, deny/PAB/group effects and denied
access to the service agent's own IAM policy were not resolved by import.
No additional access was granted to fill those gaps. CI probe execution and a
real restore remain unverified; no cloud release acceptance is claimed.

**STOP at Phase 2:** separate explicit operator approval is required for IAM
removal using the exact saved binary and hash above. Before executing an
approved apply, verify the artifact/module/backend/state hashes, fresh IAM and
dependency ownership; stop for review if evidence changed. Do not silently
regenerate or auto-approve a replacement plan. Post-apply IAM verification and
the separately authorized recovery procedure remain mandatory. Approval of
this IAM plan does not approve a build, deployment, probe or Gate D experiment.
