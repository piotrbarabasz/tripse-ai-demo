"""GitHub release coordination around the existing deployment implementation.

No provisioning. Runtime config, proof verification and prerequisites fail closed.
The executable path is only used by explicit CI jobs / the gcp-ci Make target.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, build_opener, HTTPRedirectHandler, urlopen
from urllib.parse import quote
import zipfile

from scripts.gcp import deployment as d
from scripts.gcp.deployment_contract import FIELDS, ROOT, image_tag, load_pair
from scripts.gcp.ci_config import validate as validate_environment, failure_summary

REPOSITORY = "piotrbarabasz/tripse-ai-demo"
WORKFLOW = ".github/workflows/delivery.yml"
JOBS = {"dev": "DEV deployment", "prod": "PROD deployment"}
DIGEST = re.compile(r"sha256:[a-f0-9]{64}")


def config_from_environment(environment, directory):
    values = validate_environment(environment)
    expected = os.environ["EXPECTED_CLOUD_FEATURE_MODE"]
    os.environ["GCP_SMOKE_ACCOUNT"] = os.environ["CI_PROBE_ACCOUNT"]
    for key, value in {"GCP_PROJECT_ID": "tripse-ai", "GCP_REGION": "europe-central2",
                       "GCP_SERVICE_NAME": f"tripse-ai-{environment}", "APP_ENV": environment,
                       "CLOUD_FEATURE_MODE": expected, "PLANNING_MODE": "mock"}.items():
        if values.get(key) != value:
            raise ValueError("Configuration does not match the reviewed CI target/mode")
    if any(not isinstance(k, str) or not isinstance(v, str) or any(c in k + v for c in "\r\n") for k, v in values.items()):
        raise ValueError("Deployment configuration must contain single-line string values")
    directory.mkdir(parents=True, exist_ok=True)
    # load_pair needs both files. The counterpart is a validation-only private
    # readonly stub; no production variables/secrets are exposed to a DEV job.
    other = "prod" if environment == "dev" else "dev"
    sibling = {k: values[k] for k in FIELDS if k in values}
    sibling.update(APP_ENV=other, GCP_SERVICE_NAME=f"tripse-ai-{other}",
                   CLOUD_FEATURE_MODE="readonly_demo", GCP_PUBLIC_ACCESS="false")
    for name, data in ((environment, values), (other, sibling)):
        (directory / f".env.{name}").write_text("".join(f"{k}={v}\n" for k, v in sorted(data.items())), encoding="utf-8")
    try:
        config = load_pair(environment, directory)
    except ValueError:
        raise ValueError("Invalid runtime schema: deployment contract rejected configuration. Review the environment template and docs/GITHUB_CICD.md.") from None
    if expected == "cloud_demo":
        settings = config.demo_settings()
        probe = os.environ.get("GCP_SMOKE_ACCOUNT", "")
        allowed = settings.editors if environment == "dev" else settings.readers | settings.editors
        if probe not in allowed:
            raise ValueError("Approved CI probe is missing from the application's access lists")
    return config


def google_json(g, url):
    token = g("auth", "print-access-token")
    try:
        with urlopen(Request(url, headers={"Authorization": "Bearer " + token}), timeout=30) as response:
            return json.load(response)
    except (OSError, ValueError):
        raise ValueError("Cannot read required Google resource configuration") from None


def includes(policy, role, member):
    return any(b.get("role") == role and member in b.get("members", []) and not b.get("condition")
               for b in policy.get("bindings", []))


def prerequisites(g):
    """Only reads; never enables an API or creates missing resources."""
    c = g.config
    current = d.service(g)
    if not current:
        raise ValueError("Bootstrap the existing target service before enabling CI")
    if not d.repository(g):
        raise ValueError("Missing immutable Artifact Registry repository")
    if c["CLOUD_FEATURE_MODE"] == "readonly_demo":
        return current
    settings = c.demo_settings()
    for identity in (c.runtime_account, f"tripse-ai-{c['APP_ENV']}-ci-probe@tripse-ai.iam.gserviceaccount.com"):
        account = g("iam", "service-accounts", "describe", identity, json_output=True)
        if account.get("email") != identity or account.get("disabled", False):
            raise ValueError("Dedicated runtime or CI probe account unavailable")
    bucket = g("storage", "buckets", "describe", "gs://" + settings.bucket, json_output=True)
    iam = bucket.get("iamConfiguration", {})
    pap = bucket.get("public_access_prevention", iam.get("publicAccessPrevention"))
    uniform = bucket.get("uniform_bucket_level_access", iam.get("uniformBucketLevelAccess", {}).get("enabled"))
    versioned = bucket.get("versioning_enabled", bucket.get("versioning", {}).get("enabled"))
    if pap != "enforced" or uniform is not True or versioned is not True:
        raise ValueError("Document bucket must be private, uniform and versioned")
    database = g("firestore", "databases", "describe", f"--database={settings.database}", json_output=True)
    if (database.get("name") != f"projects/{settings.project}/databases/{settings.database}"
        or database.get("locationId") != "europe-central2" or database.get("type") != "FIRESTORE_NATIVE"
        or database.get("pointInTimeRecoveryEnablement") != "POINT_IN_TIME_RECOVERY_ENABLED"
        or database.get("deleteProtectionState") != "DELETE_PROTECTION_ENABLED"):
        raise ValueError("Firestore environment or backup protection is incorrect")
    queue = g("tasks", "queues", "describe", settings.queue, json_output=True)
    limits, retry = queue.get("rateLimits", {}), queue.get("retryConfig", {})
    if (queue.get("name") != settings.queue or queue.get("state") != "RUNNING"
        or not 0 < limits.get("maxConcurrentDispatches", 0) <= 2
        or not 0 < limits.get("maxDispatchesPerSecond", 0) <= 1
        or not 0 < retry.get("maxAttempts", 0) <= 12):
        raise ValueError("Task queue identity, limits or bounded retries are incorrect")
    account = g("iam", "service-accounts", "describe", settings.task_account, json_output=True)
    if account.get("email") != settings.task_account or account.get("disabled", False):
        raise ValueError("Dedicated task account unavailable")
    runtime = "serviceAccount:" + c.runtime_account
    bucket_policy = g("storage", "buckets", "get-iam-policy", "gs://" + settings.bucket, json_output=True)
    if not includes(bucket_policy, "roles/storage.objectUser", runtime):
        raise ValueError("Missing environment bucket runtime IAM")
    queue_policy = g("tasks", "queues", "get-iam-policy", settings.queue, json_output=True)
    if not includes(queue_policy, "roles/cloudtasks.enqueuer", runtime):
        raise ValueError("Missing environment queue runtime IAM")
    caller_policy = g("iam", "service-accounts", "get-iam-policy", settings.task_account, json_output=True)
    if not includes(caller_policy, "roles/iam.serviceAccountUser", runtime):
        raise ValueError("Missing task account actAs grant")
    task_agent = "serviceAccount:service-" + c["GCP_PROJECT_NUMBER"] + "@gcp-sa-cloudtasks.iam.gserviceaccount.com"
    if not includes(caller_policy, "roles/iam.serviceAccountTokenCreator", task_agent):
        raise ValueError("Missing dedicated Tasks token-minting grant")
    project_policy = g("projects", "get-iam-policy", settings.project, json_output=True)
    expression = f"resource.name=='projects/{settings.project}/databases/{settings.database}'"
    grants = [b for b in project_policy.get("bindings", []) if runtime in b.get("members", [])]
    if not any(b.get("role") == "roles/datastore.user" and
               b.get("condition", {}).get("expression", "").replace('"', "'").replace(" ", "") == expression for b in grants):
        raise ValueError("Missing database-scoped runtime IAM")
    if any(b.get("role") in {"roles/owner", "roles/editor", "roles/datastore.owner", "roles/datastore.user"}
           and not b.get("condition") for b in grants):
        raise ValueError("Unscoped runtime data IAM is forbidden")
    live = google_json(g, f"https://run.googleapis.com/v2/projects/{settings.project}/locations/europe-central2/services/{c['GCP_SERVICE_NAME']}")
    if live.get("iapEnabled") is not True or live.get("invokerIamDisabled", False) or live.get("uri") != settings.origin:
        raise ValueError("Bootstrap direct IAP and the reviewed private origin before CI deployment")
    policy = g("iap", "web", "get-iam-policy", "--resource-type=cloud-run", "--region=europe-central2",
               f"--service={c['GCP_SERVICE_NAME']}", json_output=True)
    for email in settings.readers | settings.editors | {settings.task_account}:
        kind = "serviceAccount:" if email.endswith(".gserviceaccount.com") else "user:"
        if not includes(policy, "roles/iap.httpsResourceAccessor", kind + email):
            raise ValueError("IAP membership does not match approved application/task identities")
    oauth = g("iap", "settings", "get", "--resource-type=cloud-run", "--region=europe-central2",
              f"--service={c['GCP_SERVICE_NAME']}", json_output=True)
    access = oauth.get("accessSettings", oauth.get("access_settings", {}))
    clients = access.get("oauthSettings", access.get("oauth_settings", {}))
    if settings.oauth_client not in clients.get("programmaticClients", clients.get("programmatic_clients", [])):
        raise ValueError("Tasks OAuth audience is not enabled for IAP programmatic access")
    # Fail before a build/deploy if signJwt, probe IAM, or existing IAP auth fails.
    from scripts.gcp.smoke_auth import probe_token
    from scripts.gcp.parity_smoke import Acceptance
    token = probe_token(g, settings.origin, iap=True)
    # The receiving revision may still be readonly_demo on the first rollout.
    # Require real authenticated HTTP 200 here; validate cloud_demo only after
    # deployment, never by accepting an authentication failure during bootstrap.
    Acceptance(settings.origin, token).call("/health")
    return current


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


class GitHub:
    def __init__(self):
        self.token = os.environ["GH_TOKEN"]
        self.opener = build_opener(NoRedirect())

    def request(self, path, *, archive=False):
        if not path.startswith(("/actions/", "/git/ref/heads/")):
            raise ValueError("Unexpected GitHub API path")
        request = Request(f"https://api.github.com/repos/{REPOSITORY}" + path,
            headers={"Authorization": "Bearer " + self.token, "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28"})
        try:
            with self.opener.open(request, timeout=30) as response:
                return json.load(response)
        except HTTPError as error:
            if not archive or error.code != 302:
                raise ValueError("GitHub release evidence cannot be read") from None
            location = error.headers.get("Location", "")
            if not location.startswith("https://"):
                raise ValueError("Unsafe artifact redirect")
            # Never forward the GitHub bearer token to artifact storage.
            with urlopen(Request(location), timeout=30) as response:
                data = response.read(2_000_001)
            if len(data) > 2_000_000:
                raise ValueError("Oversized evidence archive")
            return data

    def pages(self, path, field):
        values = []
        for page in range(1, 101):
            data = self.request(path + ("&" if "?" in path else "?") + f"per_page=100&page={page}")[field]
            values.extend(data)
            if len(data) < 100:
                return values
        raise ValueError("Evidence listing exceeded pagination limit")


def validate_proof(record, run, artifact, jobs, environment, sha, mode, *, production):
    if (run.get("repository", {}).get("full_name") != REPOSITORY or run.get("path") != WORKFLOW
        or run.get("event") not in {"push", "workflow_dispatch"} or artifact.get("expired")
        or artifact.get("workflow_run", {}).get("id") != run.get("id")
        or record.get("repository") != REPOSITORY or record.get("run_id") != run.get("id")
        or record.get("policy_sha") != run.get("head_sha") or record.get("environment") != environment
        or record.get("image_sha") != sha or record.get("feature_mode") != mode
        or not DIGEST.fullmatch(record.get("image_digest", ""))
        or record.get("accepted") is not True or record.get("source_verified") is not True
        or not re.fullmatch(r"[a-f0-9-]{36}", record.get("source_build_id", ""))
        or record.get("source_ref") != "refs/heads/" + run.get("head_branch", "")
        or record.get("run_attempt") != run.get("run_attempt")
        or artifact.get("name") != f"{environment}-accepted-{sha}-{run.get('id')}-{run.get('run_attempt')}"):
        raise ValueError("Release artifact provenance or runtime contract mismatch")
    if production and run.get("head_branch") != "master":
        raise ValueError("A feature branch cannot supply a production release")
    if not any(j.get("name") == JOBS[environment] and j.get("conclusion") == "success" and
               j.get("run_attempt") == record["run_attempt"] for j in jobs):
        raise ValueError("Evidence job did not finish successfully")
    acceptance = "api_ui_mock" if mode == "cloud_demo" and environment == "dev" else "smoke"
    if record.get("acceptance") != acceptance:
        raise ValueError("Required deployed acceptance did not pass")


def release_proof(environment, sha, mode, *, production):
    run_id, artifact_id = os.getenv("CI_EVIDENCE_RUN_ID", ""), os.getenv("CI_EVIDENCE_ARTIFACT_ID", "")
    if not run_id.isdigit() or not artifact_id.isdigit():
        raise ValueError("Promotion/rollback requires an accepted run ID and immutable artifact ID")
    gh = GitHub()
    run = gh.request(f"/actions/runs/{run_id}")
    artifact = gh.request(f"/actions/artifacts/{artifact_id}")
    raw = gh.request(f"/actions/artifacts/{artifact_id}/zip", archive=True)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if archive.namelist() != ["release.json"] or archive.getinfo("release.json").file_size > 64_000:
            raise ValueError("Invalid release evidence archive")
        record = json.loads(archive.read("release.json"))
    jobs = gh.pages(f"/actions/runs/{run_id}/attempts/{run['run_attempt']}/jobs", "jobs")
    validate_proof(record, run, artifact, jobs, environment, sha, mode, production=production)
    return record


def fresh(current, sequence):
    labels = current.get("metadata", {}).get("labels", {})
    if labels.get("github-workflow") == "delivery-v1" and int(labels.get("github-run-number", "0")) > sequence:
        raise ValueError("Stale workflow cannot overwrite a newer deployment; start a new manual run instead")


def snapshot(current, g):
    traffic = [t for t in current.get("status", {}).get("traffic", []) if t.get("percent", 0)]
    if len(traffic) != 1 or traffic[0].get("percent") != 100 or not traffic[0].get("revisionName"):
        raise ValueError("Resolve split/unknown traffic before a CI release")
    revision = g("run", "revisions", "describe", traffic[0]["revisionName"], "--region=europe-central2", json_output=True)
    env = {e["name"]: e.get("value") for c in revision.get("spec", {}).get("containers", []) for e in c.get("env", [])}
    image_tag(env.get("EXPECTED_IMAGE_SHA"))
    if env.get("APP_ENV") != g.config["APP_ENV"] or env.get("CLOUD_FEATURE_MODE") not in {"readonly_demo", "cloud_demo"}:
        raise ValueError("Previous receiving revision has no recognized runtime contract")
    return {"sha": env.get("EXPECTED_IMAGE_SHA"), "mode": env.get("CLOUD_FEATURE_MODE"),
            "traffic": traffic,
            "iap_enabled": current.get("metadata", {}).get("annotations", {}).get("run.googleapis.com/iap-enabled") == "true",
            "url": current.get("status", {}).get("url")}


def restore(g, previous):
    """Restore recorded traffic, retain private access, and verify old health.

    Public preview access is intentionally not automatically reopened on failure.
    Storage and schemas are never restored/deleted by a code rollback.
    """
    c = g.config
    sha = image_tag(previous.get("sha"))
    traffic = previous["traffic"]
    if not traffic or sum(t.get("percent", 0) for t in traffic) != 100:
        raise ValueError("No verified previous traffic allocation to restore")
    for t in traffic:
        if not re.fullmatch(r"tripse-ai-(?:dev|prod)-[a-z0-9-]+", t.get("revisionName", "")):
            raise ValueError("Invalid previous revision")
    base = ("run", "services", "update", c["GCP_SERVICE_NAME"], "--region=europe-central2")
    iap = previous["mode"] == "cloud_demo" or previous.get("iap_enabled", False)
    g(*base, "--invoker-iam-check", "--iap" if iap else "--no-iap")
    allocation = ",".join(f"{t['revisionName']}={t['percent']}" for t in traffic)
    g("run", "services", "update-traffic", c["GCP_SERVICE_NAME"], "--region=europe-central2", "--to-revisions=" + allocation)
    from scripts.gcp.parity_smoke import Acceptance
    from scripts.gcp.smoke_auth import probe_token
    token = probe_token(g, d.validate_url(previous["url"]), iap=iap)
    health = Acceptance(previous["url"], token).call("/health")
    if health.get("image_version") != sha or health.get("feature_mode") != previous["mode"]:
        raise ValueError("Previous runtime restoration was not verified")
    actual = g("run", "services", "describe", c["GCP_SERVICE_NAME"], "--region=europe-central2", json_output=True)
    if sorted((t.get("revisionName"), t.get("percent")) for t in actual.get("status", {}).get("traffic", []) if t.get("percent", 0)) != sorted((t["revisionName"], t["percent"]) for t in traffic):
        raise ValueError("Previous traffic restoration was not verified")


def browser_acceptance(origin, token, trip_id):
    from playwright.sync_api import sync_playwright, expect
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(extra_http_headers={"Authorization": "Bearer " + token})
        # No paid Maps/AI/third-party requests during acceptance. Tokens must
        # never be sent to Google Maps or another external page.
        context.route("**/*", lambda route: route.continue_() if route.request.url.startswith(origin + "/") else route.abort())
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(type(error).__name__))
        page.goto(origin + "/hub")
        expect(page.locator("#documents-link")).to_have_attribute("href", "/documents/demo")
        page.goto(origin + "/documents/demo#trips/" + trip_id)
        expect(page.locator(".day")).to_have_count(15)
        page.goto(origin + "/demo/chat")
        expect(page.locator("#chat-text")).not_to_be_empty()
        if errors:
            raise ValueError("Authenticated browser acceptance reported a script error")
        browser.close()


def summary(record):
    path = os.getenv("GITHUB_STEP_SUMMARY")
    if path:
        safe = json.dumps(record, indent=2, ensure_ascii=True).replace("`", "\\u0060")
        with open(path, "a", encoding="utf-8") as stream:
            stream.write("\nTRIPSE deployment result\n\n```json\n" + safe + "\n```\n")


def execute():
    operation = os.getenv("CI_OPERATION", "dev")
    environment = os.getenv("CI_TARGET_ENV", "dev")
    event, ref = os.getenv("GITHUB_EVENT_NAME"), os.getenv("GITHUB_REF", "")
    if (os.getenv("GITHUB_REPOSITORY") != REPOSITORY or event not in {"push", "workflow_dispatch"}
        or not ref.startswith("refs/heads/") or environment not in {"dev", "prod"}
        or operation not in {"dev", "promote", "rollback"}
        or (environment == "prod" and (ref != "refs/heads/master" or operation == "dev"))
        or (environment == "dev" and operation == "promote")):
        raise ValueError("Event, ref or deployment target is not permitted")
    if event == "push" and (ref not in {"refs/heads/dev", "refs/heads/master"}
                            or os.getenv("CI_RELEASE_SHA") not in {None, "", os.getenv("GITHUB_SHA")}):
        raise ValueError("Automatic deployment requires dev/master and the exact pushed commit SHA")
    if operation != "dev" and event != "workflow_dispatch" and not (operation == "promote" and ref == "refs/heads/master"):
        raise ValueError("Rollback is manual; promotion requires a master release")
    directory = Path(os.environ["RUNNER_TEMP"]) / "tripse-deployment"
    config = config_from_environment(environment, directory / "config")
    os.environ["GCP_CI"] = "1"
    expected_identity = f"tripse-ai-{environment}-ci-deploy@tripse-ai.iam.gserviceaccount.com"
    if os.getenv("DEPLOY_SERVICE_ACCOUNT") != expected_identity:
        raise ValueError("Wrong deployment service account")
    sha = image_tag(os.getenv("CI_RELEASE_SHA") or os.environ["GITHUB_SHA"])
    if environment == "prod":
        d.run(["git", "merge-base", "--is-ancestor", sha, "origin/master"])
    if d.run(["git", "status", "--porcelain"]):
        raise ValueError("CI build/deployment requires a clean checkout")
    d.CONFIG_DIR = directory / "config"
    d.check_release_source(sha)
    g = d.Gcloud(config)
    proof = release_proof(environment if operation == "rollback" else "dev", sha,
                          config["CLOUD_FEATURE_MODE"], production=environment == "prod") if operation != "dev" else None
    try:
        if not g("auth", "print-access-token"):
            raise ValueError("No usable runner credential")
    except (ValueError, d.CommandError):
        raise ValueError("IAM/WIF authentication error: runner cannot obtain a short-lived access token. Review environment trust and impersonation bindings; no deployment attempted.") from None
    try:
        d.online_preflight(g, "build" if operation == "dev" else "deploy")
    except (ValueError, d.CommandError):
        raise ValueError("GCP preflight blocked: check WIF authentication/IAM, enabled APIs and reviewed GCP bootstrap. See docs/GITHUB_CICD.md; no application deployment attempted.") from None
    try:
        current = prerequisites(g)
    except d.CommandError:
        raise ValueError("GCP bootstrap check failed: resource missing or metadata IAM denied. Review private resources and probe access in docs/GITHUB_CICD.md; no application deployment attempted.") from None
    except ValueError as exc:
        raise ValueError("GCP bootstrap blocked: " + str(exc) + ". See docs/GITHUB_CICD.md; no application deployment attempted.") from None
    fresh(current, int(os.environ["GITHUB_RUN_NUMBER"]))
    # A delayed push from an obsolete branch head must not deploy after a newer
    # push; a manual dispatch is the explicit way to select an older SHA.
    if event == "push":
        remote = GitHub().request("/git/ref/" + quote(ref.removeprefix("refs/"), safe="/"))
        if remote.get("object", {}).get("sha") != os.environ["GITHUB_SHA"]:
            raise ValueError("Push was superseded by a newer branch head")
    if operation == "dev":
        d.build(g, sha)
    selected_digest = d.digest(g, sha)
    if proof and selected_digest != proof["image_digest"]:
        raise ValueError("Registry digest differs from the accepted immutable evidence")
    if environment == "dev":
        from scripts.gcp.build_proof import verify
        source_build_id = verify(g, sha, selected_digest)
    else:
        source_build_id = proof["source_build_id"]
    previous = snapshot(current, g)
    record = {"repository": REPOSITORY, "run_id": int(os.environ["GITHUB_RUN_ID"]),
        "run_attempt": int(os.environ["GITHUB_RUN_ATTEMPT"]), "policy_sha": os.environ["GITHUB_SHA"],
        "source_ref": ref, "image_sha": sha, "image_digest": selected_digest,
        "feature_mode": config["CLOUD_FEATURE_MODE"], "environment": environment,
        "source_verified": True, "source_build_id": source_build_id,
        "previous_sha": previous["sha"], "accepted": False,
        "rollback": f"Manual rollback: select {environment}, SHA {previous['sha']} and its last successful acceptance artifact"}
    try:
        d.deploy(g, sha)
        state = d.deployed_state(g, sha)
        if state["image_digest"] != selected_digest:
            raise ValueError("Deployed digest changed during release")
        record.update(state)
        if environment == "dev" and config["CLOUD_FEATURE_MODE"] == "cloud_demo":
            from scripts.gcp.smoke_auth import probe_token
            from scripts.gcp.parity_smoke import Acceptance
            token = probe_token(g, state["url"], iap=True)
            acceptance = Acceptance(state["url"], token)
            acceptance.read_only("dev")
            fixtures = acceptance.writes()
            browser_acceptance(state["url"], token, fixtures["trip_id"])
            record["acceptance"] = "api_ui_mock"
        else:
            record["acceptance"] = "smoke"
        # Recheck after acceptance while the cross-branch DEV lock is still held.
        record.update(d.deployed_state(g, sha))
        record.update(accepted=True, accepted_at=int(time.time()))
        record["config_hash"] = hashlib.sha256(json.dumps(config.values, sort_keys=True).encode()).hexdigest()
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "release.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
            stream.write(f"sha={sha}\ndigest={selected_digest}\n")
    except Exception:
        record["failure_stage"] = "Application deployment or deployed acceptance failed; release not accepted"
        try:
            restore(g, previous)
            record["recovery"] = "Previous traffic and health verified; access retained private. Deployment FAILED."
        except Exception:
            record["recovery"] = "Restoration NOT verified. Deployment FAILED; operator recovery required."
        raise
    finally:
        summary(record)


def offline():
    sha = image_tag(os.environ.get("GITHUB_SHA") or d.run(["git", "rev-parse", "HEAD"]))
    files = d.check_release_source(sha)
    required = {"Dockerfile", "requirements.txt", "app/cloud_preview.py", "app/cloud_runtime.py", "app/cloud_access.py",
                "app/cloud_jobs.py", "app/document_studio/cloud_storage.py"}
    if not required <= files.keys():
        raise ValueError("Image source is missing required cloud modules")
    directory = Path(os.environ.get("RUNNER_TEMP", "local-data/ci-offline")) / "tripse-offline-config"
    directory.mkdir(parents=True, exist_ok=True)
    for env in ("dev", "prod"):
        data = (ROOT / f"infra/gcp/.env.{env}.example").read_text(encoding="utf-8")
        data = data.replace("GCP_PROJECT_ID=", "GCP_PROJECT_ID=tripse-ai", 1)
        (directory / f".env.{env}").write_text(data, encoding="utf-8")
    for env in ("dev", "prod"):
        d.offline_runtime(load_pair(env, directory))
    print("Offline source and preview contracts PASS; no cloud credential or deployment used")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["offline", "configure", "execute"])
    parser.add_argument("--basic", action="store_true", help="Dependency-free configuration check only")
    args = parser.parse_args()
    try:
        if args.action == "offline":
            offline()
        elif args.action == "configure":
            if args.basic:
                validate_environment(os.environ["CI_TARGET_ENV"])
            else:
                config_from_environment(os.environ["CI_TARGET_ENV"], Path(os.environ["RUNNER_TEMP"]) / "tripse-deployment/config")
            print("Explicit target and runtime configuration validated; no cloud credentials requested")
        else:
            execute()
    except Exception as exc:
        # Do not dump HTTP Request objects, external-account credentials or raw
        # cloud response bodies. Known validation messages contain no values.
        message = str(exc) if isinstance(exc, (ValueError, d.CommandError)) else type(exc).__name__
        if args.action == "configure":
            failure_summary(message)
        print("CI blocked: " + message, file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
