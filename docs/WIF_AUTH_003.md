# TRIPSE-WIF-AUTH-003: DEV STS rejection

Current state - 2026-10-28: private DEV and PROD `cloud_demo` delivery is
accepted in [master run 40614584902](RELEASE_2026_10_28.md). That evidence record
includes artifact IDs, isolated infrastructure, operator-verified IAM/Organization
Policy and state adoption, and remaining acceptance limits. Earlier dated findings
below are historical snapshots, superseded for rollout status. Do not replay
completed bootstrap/import/cutover steps or use old saved plans. Human login,
restore/isolation drills and real customer-data readiness remain unverified.

2026-10-27 follow-up: operator applied the reviewed DEV correction and WIF auth
now succeeds in examined runs. The next blocker at that date was authenticated IAP health 401;
see [AUTH-004 incident and handoff](DEV_AUTH_004_INCIDENT.md). Original findings
and NOT TESTED statements below are retained as the 26 October historical record.

## Verified audit and diagnosis

Started on clean `dev` at `9883955dc21c92153609647171cef21fd7fefac5`.
Read-only GitHub API inspection confirms run `40341543860` (attempt 2), push/dev,
workflow `.github/workflows/delivery.yml`; job `121638710377` passed configuration
and failed authentication before build/deploy. No token was obtained by Codex.

Read-only `gcloud ... providers describe github-dev` found ACTIVE state and the
same condition/mapping as the original Terraform. The failing equality requires:

```text
repo:piotrbarabasz/tripse-ai-demo:environment:development
```

However `GET /repos/piotrbarabasz/tripse-ai-demo/actions/oidc/customization/sub`
returned `use_default=true`, `use_immutable_subject=true`, and
`sub_claim_prefix=repo:piotrbarabasz@72949549/tripse-ai-demo@1430252241`.
GitHub's documented immutable format plus the development job context requires:

```text
repo:piotrbarabasz@72949549/tripse-ai-demo@1430252241:environment:development
```

That value cannot equal the provider's legacy subject. This is a specific
configuration mismatch, not missing id-token permission, inactive identity,
Cloud Build or application failure. The historical signed token cannot be
retrieved; runner diagnostics will confirm its current actual selected claims.
Do not switch the repository back to legacy subjects or remove subject checks.

The issuer advertises every required claim: repository, repository_id,
repository_owner_id, event_name, environment, sub, ref, workflow_ref. Environment
is supplied by the environment-bound job; workflow_ref is the calling Delivery
file/ref, not CI's reusable workflow (`job_workflow_ref` is a different claim).

## Declarative fix and preserved trust

`dev-oidc-policy.json` is the shared nonsecret contract for DEV Terraform CEL and
runner diagnostics. Only DEV uses the exact immutable subject. Every previous
restriction remains: repository name, immutable owner/repo IDs, development,
push on dev/master or explicit branch dispatch, and exact Delivery workflow/ref.
PR, pull_request_target, Dependabot dynamic events, tags and mismatched workflows
remain rejected. Separate deploy/probe identities and environment IAM stay intact.

DEV mapping additionally includes repository, event_name, ref and workflow_ref;
existing google.subject, ID and environment mappings are retained. This aligns
all condition fields with Google's mapping guidance. There is no change to the
environment-based principalSet binding or any service-account role.
**PROD condition, mappings, workflow and identities remain unchanged.** The same
repository-wide immutable format may require separate PROD review later; this
task neither fixes nor provisions production and never claims it is ready.

## Temporary safe runner diagnostic

The DEV step immediately before auth uses GitHub's injected OIDC request URL and
request bearer internally, with the same audience as the pinned auth v3 source:
`https://iam.googleapis.com/` plus the exact DEV provider resource name.
It refuses redirects and non-GitHub HTTPS endpoints. It decodes only in runner
memory and returns/logs only the eight selected nonsecret fields. It never prints
or writes the JWT, request bearer, headers, complete response or credentials;
HTTP/decode errors are sanitized. Extra claims are discarded, strings escaped
and token-shaped values suppressed. No shell tracing or token CLI arguments.

Each field reports PASS/FAIL against the exact shared source condition; a mismatch
fails before auth. The audited pre-fix legacy-sub equality is separately labelled,
so its expected FAIL must not be mistaken for current source-policy failure.
Payload decoding does not verify the signature and never replaces Google STS
issuer/audience/signature verification or GitHub production approval.

## Operator runbook: reviewed DEV provider update

These commands are **instructions only**; no plan/apply, push/rerun/deploy or IAM
mutation was executed by Codex. A successful rerun continues the normal DEV
build/deployment and may incur costs; run it only when ready for that release.

1. Review/commit the changes on dev. Keep the existing CI-bootstrap Terraform
   state/backend and existing `bootstrap.auto.tfvars`. Do not create another state,
   replay old `dev-bootstrap.tfplan`, add prod or remove existing environments.
2. From the repository root in PowerShell, using installed Terraform and the
   approved operator ADC identity, generate a **new** plan:

```powershell
terraform -chdir=infra/gcp/github-actions init -lockfile=readonly
if ($LASTEXITCODE -ne 0) { throw 'Terraform init failed' }
terraform -chdir=infra/gcp/github-actions fmt -check
if ($LASTEXITCODE -ne 0) { throw 'Terraform format check failed' }
terraform -chdir=infra/gcp/github-actions validate
if ($LASTEXITCODE -ne 0) { throw 'Terraform validation failed' }
terraform -chdir=infra/gcp/github-actions plan -out=wif-auth-003.tfplan
if ($LASTEXITCODE -ne 0) { throw 'Review operator authentication/state/bootstrap' }
terraform -chdir=infra/gcp/github-actions show wif-auth-003.tfplan
```

3. Review the exact saved plan. Expected: **one in-place update** to
   `google_iam_workload_identity_pool_provider.github["dev"]`: exact immutable
   subject and four additional DEV mappings; other predicates are semantically
   unchanged (list quote formatting can differ). No creates, deletes, replaces,
   IAM binding changes, service-account changes or PROD differences. Stop and
   reconcile state/drift if the plan differs; never use `-target` to conceal it.
   Keep the ignored plan/state private. After operator review, explicitly apply:

```powershell
terraform -chdir=infra/gcp/github-actions apply wif-auth-003.tfplan
if ($LASTEXITCODE -ne 0) { throw 'Apply failed; do not rerun delivery yet' }
gcloud iam workload-identity-pools providers describe github-dev --workload-identity-pool=tripse-github --location=global --project=tripse-ai --format="json(state,attributeCondition,attributeMapping)"
```

4. Wait for propagation. Leave development variable `WIF_DIAGNOSTICS` absent or
   set to `true` for the diagnostic run. Publishing reviewed changes to dev
   triggers its normal pipeline. A rerun uses the **original commit's** workflow,
   so rerunning the historical run will not load the new diagnostic step:

```powershell
# Historical run: validates corrected STS trust but has no new diagnostics.
gh run rerun 40341543860 --failed
gh run watch 40341543860 --exit-status
```

Use a new run containing this fix to see the selected claims; identify it with
`gh run list --workflow delivery.yml --branch dev --limit 5`, then
`gh run watch <NEW_RUN_ID> --exit-status` (replace the placeholder with its numeric
ID). Do not launch old/new pipelines together. Freshness guards may reject the
old run if a newer deployment already reached DEV; use a new reviewed run rather
than altering labels, evidence or relaxing branch checks.

5. Verification criteria: selected source checks PASS, immutable subject matches,
   old legacy comparison FAIL, auth step succeeds. If source checks pass but STS
   still rejects, compare the actual provider condition/mappings with the shared
   contract and account for propagation; do not broaden trust. Later IAM/probe/app
   failures are separate stages. Never upload an OIDC token for debugging.
6. **After successful WIF verification**, disable the temporary step in development:

```powershell
gh variable set WIF_DIAGNOSTICS --repo piotrbarabasz/tripse-ai-demo --env development --body false
gh api repos/piotrbarabasz/tripse-ai-demo/environments/development/variables/WIF_DIAGNOSTICS --jq .value
```

Expected value: `false`. This explicit operator setting disables claim inspection
while keeping auth and every provider check enabled. Confirm the diagnostic step
is skipped in the next new run. Remove it/helper in a later reviewed cleanup once
the incident is closed; do not remove the shared JSON used by Terraform. No remote
disable was performed during implementation because successful WIF is unverified.

## Sources and validation limits

- [GitHub OIDC claims, immutable subjects and runner token mechanism](https://docs.github.com/en/actions/reference/security/oidc)
- [GitHub issuer's supported claims](https://token.actions.githubusercontent.com/.well-known/openid-configuration)
- [Pinned auth Action audience implementation](https://github.com/google-github-actions/auth/blob/7c6bc770dae815cd3e89ee6cdf493a5fab2cc093/src/main.ts)
- [Google deployment-pipeline mappings and conditions](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines)

Local synthetic tests, workflow lint and Terraform schema validation do not prove
actual runner issuance/STS acceptance. Real token diagnostics, operator-reviewed
apply, successful WIF exchange and later DEV acceptance remain operator gates.

Validation on 2026-10-26: full offline suite **517 passed** (one existing
Starlette/AnyIO warning); after adding a final contract-pinning test, the diagnostic
suite **36 passed**. Actionlint 1.7.7, Terraform 1.13.5 fmt/validate with Google
8.8.1 and Git whitespace checks passed. PROD workflow was compared with starting
HEAD and is identical; workflow permissions unchanged. No browser/Docker tests
were repeated for this OIDC/Terraform-only change. No real OIDC request, STS
exchange, Terraform plan/apply, resource/IAM mutation or deployment was performed
by Codex; only public documentation and read-only GitHub/provider metadata were read.
