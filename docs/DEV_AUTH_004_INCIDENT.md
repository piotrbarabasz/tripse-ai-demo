# TRIPSE-CICD-DEV-AUTH-004: DEV IAP 401 and deployment handoff

Date: 2026-10-27 (Europe/Warsaw). Scope: **DEV only**, project `tripse-ai`
(`690165197462`), region `europe-central2`, service `tripse-ai-dev`, origin
`https://tripse-ai-dev-64ctpggq3a-lm.a.run.app`. Target: private `cloud_demo`,
planning `mock`. No paid provider integration or PROD rollout is authorized here.

## Current outcome and evidence levels

**CONFIRMED — code defect:** IAP service-account JWT `aud` was the bare origin,
but Acceptance requests `/health`, `/hub`, document/API/assets paths. Google's
documented JWT URL scope requires an exact requested URL or `origin/*`. A bare
origin is not authority for every path. The fix signs `origin/*`, limited to this
one validated HTTPS Run origin; the non-IAP Google ID token still uses bare origin.

**HYPOTHESIS — incident attribution:** the incorrect URL scope causes IAP to reject
the authenticated health request. This matches the observed 401 and the official
contract, but a live old-vs-corrected-token comparison was **NOT TESTED**: the
local operator's signJwt request returned **403**. No extra IAM was granted to
make that comparison possible. The exact rejecting layer of the historical 401
cannot be proven from status alone. New failure metadata will help distinguish it.

**CONFIRMED — still blocked:** latest inspected DEV serves revision
`tripse-ai-dev-00005-hqb`, SHA `3729ee53292ea29f96284358b3d2d3473297c390`,
`readonly_demo/mock`, with 100% traffic. No successful cloud_demo image rollout or
API/UI acceptance exists in the examined runs. No PROD operation was performed
in this task; PROD jobs in both examined runs were skipped. PROD was not queried
or changed during this investigation; its current live state is not re-certified.

## Architecture and distinct authentication boundaries

1. GitHub job `development`, Delivery push dev/master (or explicit dispatch),
   requests a GitHub OIDC token. Google STS checks issuer/audience, immutable
   repo/owner IDs, immutable subject, environment/event/ref and workflow predicates.
2. WIF impersonates `tripse-ai-dev-ci-deploy@tripse-ai.iam.gserviceaccount.com`.
   It reads prerequisites and can mint credentials only for the dedicated probe.
3. IAM Credentials `signJwt` signs as
   `tripse-ai-dev-ci-probe@tripse-ai.iam.gserviceaccount.com`; no private key is
   exported. `iss=sub=probe email`, `iat=now`, `exp=now+600`, corrected
   `aud=<reviewed origin>/*`. `projects/-/serviceAccounts/...:signJwt` is used.
4. Acceptance sends the signed JWT in `Authorization: Bearer` and the reviewed
   `Origin`, with redirects disabled. This JWT is **not** the GitHub OIDC token,
   a Cloud Run Google-issued ID token, or an application IAP assertion.
5. Direct IAP checks the credential and probe IAP membership. Then Run IAM checks
   the IAP service agent's invoker authority. Do not supply a fabricated
   `X-Serverless-Authorization` header to skip this boundary.
6. cloud_demo verifies IAP's **separate ES256 assertion** and explicit app
   reader/editor permissions on private routes. `/health` is an app-level metadata
   exception, still protected by IAP. The old readonly app has no private Studio
   and also returns health metadata without an app-level identity check.
7. Preflight requires authenticated HTTP 200 on the receiving revision. Deployment
   then validates exact SHA/digest/traffic and cloud_demo mode, authenticated API/UI,
   synthetic mock operations and anonymous denial before issuing immutable proof.
   PROD cannot use offline-only results or an unaccepted/feature release artifact.

The corrected wildcard covers paths on one service, not hosts, projects or IAM
roles. Application reader/editor/task checks continue to restrict allowed routes.
OAuth client audience for Cloud Tasks and application signed-header audience are
different contracts; neither replaces the signed service-account JWT URL scope.

## Chronological operator history and verified outcomes

`CONFIRMED (operator history)` means explicitly supplied by the operator, not an
apply executed by this session. Commands below describe the operation family;
exact original command text/timestamps were not supplied unless noted.

| Date / evidence | Action / command family | Outcome |
|---|---|---|
| 26 Oct, operator history | GitHub development variables; CI identity Terraform bootstrap | 20 added, 0 changed, 0 destroyed; deploy/probe accounts and provider ACTIVE |
| 26 Oct, WIF_AUTH_003 and commit `b59a2b99d5ad3bba6e0180a53d25d28c2783b66b` (15:53:45 +01:00) | Reviewed CI-state Terraform plan/apply for immutable subject and mappings | WIF auth now succeeds; predicates retained |
| 26–27 Oct, operator history | Separate `infra/gcp/cloud-demo` state reviewed apply | 22 added, 0 changed, 0 destroyed; private GCS, named Firestore, bounded Tasks and scoped IAM |
| 26–27 Oct, operator history; current readback | Enable direct IAP, configure programmatic client, enforce Run invoker, verify origin | IAP true, invokerIamDisabled false, URI matches configured origin |
| Run `40343957774`, latest inspected attempt 5, dev SHA `b59a2b99d5ad3bba6e0180a53d25d28c2783b66b` | CI job `122065422581` PASS; DEV job `122065423406` | WIF succeeds; preflight health 401 at `2026-10-27T07:28:37Z`; PROD skipped |
| 27 Oct, commit `78b317d44c5ae594169d1b85d03d9b9c098af991` (10:44:17 +01:00) | Add `iap.webServices.getSettings` to custom inspect role; operator reviewed apply | 0 added, 1 changed, 0 destroyed (operator history); Git diff independently confirms only main.tf changed vs b59a2b9 |
| Run `40483100238`, attempt 1, SHA `78b317d44c5ae594169d1b85d03d9b9c098af991` | CI job `122118064118` PASS; DEV job `122119114600` | Prerequisites reach authenticated health; 401 at `2026-10-27T09:58:34Z`; no application deployment; PROD skipped |
| 27 Oct, this session | Clean starting dev HEAD `78b317d44c5ae594169d1b85d03d9b9c098af991`; inspect docs/scripts, API metadata and official docs | Specific JWT audience defect found; minimal code/tests/docs prepared; no commit/push/rerun |

## Diagnostic ledger: every cloud/HTTP attempt in this session

All gcloud stdout/stderr and credential HTTP responses were captured internally;
only whitelisted metadata/status classifications were emitted. No raw JWT,
authorization header, credential file, response body or full environment was logged.

| Diagnostic | Result / interpretation |
|---|---|
| `gh run view <run> --log-failed`, filter only `CI blocked:`; `gh api .../actions/runs/<run>` and `/jobs` | Both runs fail at authenticated GET /health after WIF/config; run IDs/attempts/SHAs above. Initial broad log filter was narrowed to avoid irrelevant dependency output. No credential values emitted. |
| `git log`, `git show`, `git diff b59a2b9 78b317d` | Starting branch clean; commit times and one-file permission correction confirmed. |
| `gcloud run services describe tripse-ai-dev --region=europe-central2 --project=tripse-ai --format=json` (internally filtered) | Revision/SHA/mode/100% traffic above; dedicated DEV runtime account. |
| Run v2 GET `.../projects/tripse-ai/locations/europe-central2/services/tripse-ai-dev` | iapEnabled true, invokerIamDisabled false, exact reviewed URI. Access token captured in memory only. |
| `gcloud run services get-iam-policy tripse-ai-dev ...` | Probe and `service-690165197462@gcp-sa-iap.iam.gserviceaccount.com` have roles/run.invoker; no allUsers run.invoker binding. Grant presence is evidence, not a successful authenticated request. |
| `gcloud iap web get-iam-policy --resource-type=cloud-run --region=europe-central2 --service=tripse-ai-dev --project=tripse-ai` | Exact probe has roles/iap.httpsResourceAccessor. |
| `gcloud iam service-accounts get-iam-policy tripse-ai-dev-ci-probe@tripse-ai.iam.gserviceaccount.com --project=tripse-ai` | DEV CI deployer has unconditional roles/iam.serviceAccountTokenCreator on this probe. |
| `gcloud iap settings get --resource-type=cloud-run --region=europe-central2 --service=tripse-ai-dev --project=tripse-ai` | Expected OAuth programmatic client present; no secret read/printed. |
| Anonymous GET /health with redirects disabled | HTTP 302, Location present (not printed), IAP-generated-response flag true, no selected WWW-Authenticate scheme; body classified internally as IAP invalid-credential hint. Confirms edge interception, not the rejecting layer of the authenticated 401. |
| Logging read: exact DEV health URL after `2026-10-27T07:20:00Z`, limit 12 | Query permitted; zero entries. |
| Logging read: DEV cloud_run_revision or iap_web after same timestamp, limit 20 | Query permitted; zero entries. Not proof that requests never occurred; edge logging/resource selection/exclusions/retention remain possible. No private log payload was emitted. |
| In-memory signJwt comparison planned for bare origin, exact /health, origin/* | First signJwt call returned 403 for local operator; stopped. No signed probe JWT obtained, no authenticated GETs performed, latter variants NOT TESTED. No IAM grant/impersonation workaround attempted. |
| Official Google IAP JWT and direct-Run-IAP requirements compared with source | iss/sub, 600-second expiry, keyless signer and Bearer header align. Bare-origin aud violates documented exact/path-wildcard scope. No documented email payload requirement for this JWT flow; OAuth client is not its audience. |

## Additional operator finding and follow-up (27 October)

**CONFIRMED (operator report):** local gcloud reauthentication succeeded; a
`cloud_run_revision`, service `tripse-ai-dev`, HTTP 401 query for the last 24 hours
returned zero records. This is distinct from this session's earlier timestamped
queries. It suggests prioritizing IAP/edge checks but does not locate the rejecting
layer: logging selection, exclusions or upstream rejection can all yield no rows.

**CONFIRMED (follow-up attempt):** after receiving this update, the investigator
again captured an operator access token in memory and attempted signJwt for the
bare-origin comparison. Signing still returned **403**. No JWT was obtained and
no authenticated GET was sent; exact-health and wildcard variants were not minted.
Successful gcloud login does not establish permission to sign as the dedicated
probe. No IAM changes, delegation workaround, rerun or deployment was attempted.

The uncommitted patch already uses origin + `/*`. Added regressions run the actual
probe-token request and Acceptance path construction against a **test-only model**
of Google's documented URL matching: bare-origin fails all tested paths, exact
`/health` scopes only health, and the minted wildcard covers `/health`, `/hub`,
`/api/document-studio/trips`, `/documents/assets/studio.js`, `/api/demo/scenarios`.
Different hosts, scheme and origin spellings are excluded by this strict model.
These tests neither implement production authorization nor emulate Google's
cryptographic/IAM verification. The audience defect is confirmed against the
documented contract; attribution of the live 401 remains a hypothesis pending
an authorized corrected-token request or reviewed new CI run.

Follow-up validation: **85 focused tests passed**, including nine new URL-scope
cases; whitespace checks passed. Production code required no additional change
beyond the existing uncommitted audience correction. The previously recorded
530-test full suite predates these nine additional tests; it was not rerun for
this test/document-only follow-up.

## Gates and bounded hypotheses

| Gate | State |
|---|---|
| GitHub config, WIF identity exchange | CONFIRMED by examined successful auth stages |
| App resource bootstrap / metadata prerequisites before HTTP probe | CONFIRMED operator history and CI progression; not a complete negative-IAM/restore drill |
| Exact probe IAP role; IAP agent Run invoker; CI signer role | CONFIRMED readback |
| Existing protected readonly health | Anonymous denial CONFIRMED; authenticated reachability NOT TESTED locally |
| JWT audience correction | CONFIRMED source defect and offline tests; live effect NOT TESTED |
| Initial-bootstrap deadlock | No mode deadlock in code: preflight does not demand cloud_demo on old revision, only HTTP 200; it must not skip the 401. Tests preserve both bootstrap allowance and strict post-deploy cloud_demo checks. |
| IAP rejects old audience | HYPOTHESIS consistent with defect; requires corrected CI request and safe response metadata |
| Run IAM rejects IAP service agent | Less supported: expected invoker grant present and IAP precedes Run IAM; not excluded by historical status alone |
| Application rejects /health | Less supported: both app compositions exempt health identity check; current receiving app is readonly. End-to-end arrival not established by available logs |
| CI WIF signing permission failure | Current reported failure is HTTP GET, after token returned; signer grant exists. Local operator signJwt 403 is a separate identity failure |
| Cloud Build, cloud_demo rollout, API/UI/jobs, durable restart/restore acceptance | NOT TESTED in these failed runs; remain OPEN |
| Production | Both jobs skipped; no PROD operation or live re-certification in this task |

## Minimal implementation and ADR decision

- `smoke_auth.probe_token`: signed IAP JWT aud becomes origin + `/*`; private
  non-IAP ID-token aud remains bare origin, with issuer/sub/expiry unchanged.
- `Acceptance.call`: failed HTTP requests report only static IAP-generated,
  selected WWW-Authenticate scheme/error classification and redirect-present
  indicators. No challenge text, error_description, Location, cookies or bodies.
  These indicators help investigate; no single header proves every network layer.
- Preflight remains fail-closed. No catch-and-continue, public access, mode
  downgrade, signer-role change, token persistence or evidence bypass is added.
- Narrow tests cover URL scope, rejected origin inputs, credential/header/body
  suppression, denied redirects and strict post-deploy mode. Existing prerequisite
  tests explicitly allow authenticated health on the old readonly revision.

**No ADR-0013:** this corrects the already-chosen keyless IAP/fail-closed contract
in ADR-0012; it introduces no new architecture/security boundary. Update that ADR's
verified evidence and index, retain proposed status and leave ADR-0013 available.
Chronology belongs here rather than in a redundant decision record.

## Safe reproduction and next operator actions

1. Read this ledger and inspect current `git status`/HEAD before resuming. Review
   the minimal diff and run local tests. Do not rerun an old commit expecting it
   to contain this fix. Do not reapply infrastructure already created merely to
   diagnose an HTTP error. No Terraform change is required by this patch.
2. Metadata-only commands (safe to repeat with the approved operator identity):

```powershell
gh run view 40483100238 --log-failed | Select-String -SimpleMatch 'CI blocked:'
gcloud run services describe tripse-ai-dev --region=europe-central2 --project=tripse-ai --format="value(status.latestReadyRevisionName,status.url)"
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="tripse-ai-dev" AND httpRequest.status=401' --project=tripse-ai --limit=10 --format="table(timestamp,httpRequest.status,resource.labels.revision_name)"
.venv/Scripts/python.exe -m pytest tests/test_iap_probe.py tests/test_github_cicd.py -q
```

3. Optional authenticated **read-only** reproduction, using existing operator
   signing authority only; do not grant roles just to run it. The local identity
   lacked signJwt during this session, so 403 is expected unless preexisting
   authorized credentials are used. All credentials remain in process memory:

```powershell
@'
import os
from scripts.gcp.deployment_contract import load_pair
from scripts.gcp.deployment import Gcloud
from scripts.gcp.smoke_auth import probe_token
from scripts.gcp.parity_smoke import Acceptance
c = load_pair("dev")
assert c["GCP_PROJECT_ID"] == "tripse-ai" and c["GCP_SERVICE_NAME"] == "tripse-ai-dev"
assert c["CLOUD_FEATURE_MODE"] == "cloud_demo" and c["GCP_PUBLIC_ACCESS"] == "false"
os.environ["GCP_SMOKE_ACCOUNT"] = "tripse-ai-dev-ci-probe@tripse-ai.iam.gserviceaccount.com"
try:
    token = probe_token(Gcloud(c), c["PUBLIC_BASE_URL"], iap=True)
except Exception:
    raise SystemExit("Signing unavailable for this operator; no token logged. Do not change IAM for diagnosis.")
try:
    result = Acceptance(c["PUBLIC_BASE_URL"], token).call("/health")
    print({k: result.get(k) for k in ("environment", "feature_mode", "generation_mode", "image_version")})
except ValueError as error:
    raise SystemExit(str(error))
'@ | .venv/Scripts/python.exe -
```

4. After reviewing/committing the fix on dev, the operator may explicitly push
   it when ready for the normal billable DEV build/deployment. This session does
   **not** commit, push, dispatch or rerun any workflow:

```powershell
git branch --show-current
git status --short
# Stop unless the reviewed fix, including new tests/docs, is committed on dev.
git push origin dev
gh run list --workflow delivery.yml --branch dev --limit 5
gh run watch <NEW_RUN_ID> --exit-status
```

Replace `<NEW_RUN_ID>` with the numeric run ID. A new push builds/tests its exact
SHA; immutable existing tags are not force-overwritten. If HTTP 401 persists,
record its selected metadata and correlate logs/time; do not disable IAP/Run IAM
or replace the probe with a human token. Verify target configuration and selected
IAM principals, issuer/sub, URL audience and time, then investigate remaining
edge policies with authorized read-only tooling.
5. Success requires real CI DEV deployment **and** cloud_demo API/UI/mock
acceptance, exact SHA/digest/revision/100% traffic, private anonymous denial and
accepted release artifact. Passing /health alone is insufficient. Keep previous
revision/artifact for documented private rollback; never delete/restore user data
as part of this auth fix. No PROD promotion until separately reviewed.
6. WIF is confirmed working: if the temporary OIDC diagnostics are still enabled,
   the operator may now set development variable `WIF_DIAGNOSTICS=false` following
   [WIF_AUTH_003](WIF_AUTH_003.md). This task did not change remote GitHub variables.

## Resume from here

Start from clean baseline `78b317d...` plus this task's uncommitted reviewed diff
unless an operator has since committed it. Read this document, ADR-0012 and Git
status before editing. Keep credentials out of notes/attachments. Determine whether
the corrected code has been pushed and inspect its new run; the two historical
runs contain the old audience and cannot validate the patch. Preserve the ledger's
NOT TESTED gates until new evidence exists. If corrected auth succeeds, proceed
with the pipeline's normal fail-closed build/acceptance and investigate the next
actual blocker; do not broaden this incident into an infrastructure rewrite.

## Local validation and mutation record

2026-10-27: `make test` **530 passed**, one existing Starlette/AnyIO deprecation
warning. Focused auth/bootstrap tests: **76 passed**. Actionlint 1.7.7 passed;
Terraform 1.13.5 fmt/validate passed for both existing CI identity and cloud-demo
modules with Google 8.8.1; Git whitespace checks passed. Browser/Docker QA was not
repeated for this credential-scope/diagnostic-only change; no application runtime
behavior was edited. No successful authenticated live probe or pipeline acceptance
is claimed by these local results.

GCP persistent mutations: **none**. No IAM/resource changes, Terraform plan/apply,
deployments, workflow dispatch/reruns, GitHub-variable changes, commits or pushes.
Read-only metadata/log/anonymous-health checks and one denied short-lived signJwt
attempt are recorded above. The two Terraform states and existing resources remain
untouched by this task.

## Primary references

- [IAP service-account JWT URL audience, issuer/sub and lifetime](https://docs.cloud.google.com/iap/docs/authentication-howto#authenticate_with_a_service_account_jwt)
- [Direct Cloud Run IAP order and invoker boundary](https://docs.cloud.google.com/run/docs/securing/identity-aware-proxy-cloud-run)
- [Cloud Run Google-issued ID-token audience (different flow)](https://docs.cloud.google.com/run/docs/authenticating/service-to-service)
- [ADR-0012](adr/0012-github-actions-delivery.md), [ADR-0011](adr/0011-authenticated-cloud-demo.md), [bootstrap](CICD_BOOTSTRAP.md), [release/rollback](GITHUB_CICD.md).
