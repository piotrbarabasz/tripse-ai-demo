"""Manual gcloud orchestration. No credentials, global config changes or automatic triggers."""
import argparse
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from urllib.error import HTTPError
from urllib.request import Request, urlopen

try:
    from .deployment_contract import ROOT, image_tag, load_pair
except ImportError:  # PowerShell invokes the file directly.
    from deployment_contract import ROOT, image_tag, load_pair

LABELS = {"app": "tripse-ai", "managed-by": "tripse-scripts"}
APIS = ("run.googleapis.com", "artifactregistry.googleapis.com", "cloudbuild.googleapis.com", "iam.googleapis.com", "logging.googleapis.com", "cloudresourcemanager.googleapis.com")


class CommandError(RuntimeError):
    def __init__(self, name, code):
        super().__init__(f"{name} failed (exit {code}); operation stopped")
        self.code = code


def run(args, *, binary=False):
    # No secret values ever appear in commands or output. Tokens are captured, not printed.
    result = subprocess.run(args, cwd=ROOT, capture_output=True)
    if result.returncode:
        raise CommandError(Path(args[0]).stem, result.returncode)
    return result.stdout if binary else result.stdout.decode("utf-8").strip()


class Gcloud:
    def __init__(self, config):
        self.config = config
        self.executable = shutil.which("gcloud")
        if not self.executable:
            raise ValueError("gcloud CLI not found; install Google Cloud SDK and authenticate first")

    def __call__(self, *args, json_output=False):
        command = [self.executable, *args, f'--project={self.config["GCP_PROJECT_ID"]}', "--quiet"]
        if json_output:
            command.append("--format=json")
        value = run(command)
        return json.loads(value) if json_output else value


def assert_owned(labels, *, environment=None):
    expected = LABELS | ({"environment": environment} if environment else {})
    if any(labels.get(k) != v for k,v in expected.items()):
        raise ValueError("Existing resource has different/missing ownership labels; identify it manually before proceeding")


def find_named(items, name):
    return next((item for item in items if item.get("name", item.get("metadata", {}).get("name", "")).split("/")[-1] == name), None)


def check_permissions(g, permissions):
    # IAM testIamPermissions is non-mutating. Never log the access token or response body.
    token = g("auth", "print-access-token")
    project = g.config["GCP_PROJECT_ID"]
    request = Request(f"https://cloudresourcemanager.googleapis.com/v1/projects/{project}:testIamPermissions",
                      data=json.dumps({"permissions": permissions}).encode(),
                      headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=30) as response:
            granted = json.load(response).get("permissions", [])
    except (HTTPError, OSError):
        raise ValueError("Cannot verify project IAM permissions; no deployment attempted") from None
    missing = set(permissions)-set(granted)
    if missing:
        raise ValueError("Missing project permissions: " + ", ".join(sorted(missing)))


def online_preflight(g, action):
    if not g("auth", "list", "--filter=status:ACTIVE", "--format=value(account)"):
        raise ValueError("No active gcloud account")
    project = g("projects", "describe", g.config["GCP_PROJECT_ID"], json_output=True)
    if project.get("lifecycleState") != "ACTIVE":
        raise ValueError("Project must be ACTIVE with billing enabled by the operator")
    permissions = ["resourcemanager.projects.get"]
    if action == "setup":
        permissions += ["serviceusage.services.enable", "artifactregistry.repositories.create", "iam.serviceAccounts.create", "resourcemanager.projects.setIamPolicy"]
    else:
        permissions += ["run.services.get", "run.services.list", "artifactregistry.repositories.get"]
        check_region(g)
    if action == "build":
        permissions += ["cloudbuild.builds.create", "artifactregistry.repositories.downloadArtifacts"]
    elif action in {"deploy", "rollback", "preflight"}:
        permissions += ["run.services.create", "run.services.update", "run.services.setIamPolicy", "artifactregistry.repositories.downloadArtifacts"]
    check_permissions(g, permissions)


def check_region(g):
    regions = g("run", "regions", "list", "--format=value(locationId)")
    if g.config["GCP_REGION"] not in regions.split():
        raise ValueError("Configured region is not available for Cloud Run")


def check_act_as(g, account):
    token = g("auth", "print-access-token")
    request = Request(f"https://iam.googleapis.com/v1/projects/-/serviceAccounts/{account}:testIamPermissions",
                      data=json.dumps({"permissions": ["iam.serviceAccounts.actAs"]}).encode(),
                      headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=30) as response:
            granted = json.load(response).get("permissions", [])
    except (HTTPError, OSError):
        raise ValueError("Cannot verify service-account actAs permission") from None
    if "iam.serviceAccounts.actAs" not in granted:
        raise ValueError("Operator needs iam.serviceAccounts.actAs on " + account)


def repository(g):
    c = g.config
    repos = g("artifacts", "repositories", "list", f'--location={c["GCP_REGION"]}', json_output=True)
    value = find_named(repos, c["GCP_ARTIFACT_REPO"])
    if value:
        assert_owned(value.get("labels", {}))
        if value.get("format") != "DOCKER" or not value.get("dockerConfig", {}).get("immutableTags"):
            raise ValueError("Existing Artifact Registry must use DOCKER and immutable tags; no automatic modification")
    return value


def service(g):
    c = g.config
    items = g("run", "services", "list", f'--region={c["GCP_REGION"]}', json_output=True)
    value = find_named(items, c["GCP_SERVICE_NAME"])
    if value:
        assert_owned(value.get("metadata", {}).get("labels", {}), environment=c["APP_ENV"])
        # Refuse sidecars, volumes or secret-bearing prior configurations.
        spec = value.get("spec", {}).get("template", {}).get("spec", {})
        containers = spec.get("containers", [])
        if len(containers) != 1 or spec.get("volumes") or any(e.get("valueFrom") for e in containers[0].get("env", [])):
            raise ValueError("Existing service has unexpected containers, volumes or secret references; inspect manually")
    return value


def setup(g):
    c = g.config
    # Project identity/IAM was checked first. API enablement is the only bootstrap
    # change before resource discovery; disabled APIs cannot list existing resources.
    enabled = g("services", "list", "--enabled", "--format=value(config.name)").split()
    missing = [api for api in APIS if api not in enabled]
    if missing:
        g("services", "enable", *missing)
    check_region(g)
    # All lists/describes must succeed. Permission errors are never interpreted as absence.
    existing_repo = repository(g)
    accounts = g("iam", "service-accounts", "list", json_output=True)
    expected_accounts = [("tripse-ai-build", "TRIPSE managed build"), ("tripse-ai-dev", "TRIPSE managed dev"), ("tripse-ai-prod", "TRIPSE managed prod")]
    for name, display in expected_accounts:
        found = next((a for a in accounts if a.get("email") == f'{name}@{c["GCP_PROJECT_ID"]}.iam.gserviceaccount.com'), None)
        if found and found.get("displayName") != display:
            raise ValueError("Existing service account is not identified as TRIPSE managed; inspect manually")
    # Identify both environment services before changing any resources.
    service(g)
    other = load_pair("prod" if c["APP_ENV"] == "dev" else "dev", CONFIG_DIR)
    service(Gcloud(other))
    if not existing_repo:
        g("artifacts", "repositories", "create", c["GCP_ARTIFACT_REPO"], f'--location={c["GCP_REGION"]}', "--repository-format=docker", "--immutable-tags", "--labels=app=tripse-ai,managed-by=tripse-scripts")
    for name, display in expected_accounts:
        if not any(a.get("email") == f'{name}@{c["GCP_PROJECT_ID"]}.iam.gserviceaccount.com' for a in accounts):
            g("iam", "service-accounts", "create", name, f"--display-name={display}")
    # One builder identity, separate zero-project-role runtime identities. Operator needs actAs.
    policy = g("projects", "get-iam-policy", c["GCP_PROJECT_ID"], json_output=True)
    member = f"serviceAccount:{c.build_account}"
    role = "roles/cloudbuild.builds.builder"
    if not any(b["role"] == role and member in b.get("members", []) and not b.get("condition") for b in policy.get("bindings", [])):
        g("projects", "add-iam-policy-binding", c["GCP_PROJECT_ID"], f"--member={member}", f"--role={role}", "--condition=None")


def source_files(sha):
    """Allowlisted committed files, never the working directory or developer data."""
    archive = run(["git", "archive", sha], binary=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for member in tar.getmembers():
            name = member.name
            allowed = name in {"Dockerfile", "requirements.txt", ".dockerignore", ".gcloudignore"} or name.startswith(("app/", "demo-fixtures/trips/", "demo-fixtures/campaigns/"))
            if not allowed or member.isdir():
                continue
            path = Path(name)
            if not member.isfile() or path.is_absolute() or ".." in path.parts:
                raise ValueError("Unsafe source archive entry")
            if any(p.startswith(".env") or p in {"local-data", "data", "__pycache__"} for p in path.parts) or re.search(r"\.(pem|key|db|sqlite3)(-|$|\.)|credentials|service.account", name, re.I):
                raise ValueError("Forbidden sensitive file in committed build context")
            content = tar.extractfile(member).read()
            if re.search(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\"private_key\"\s*:|AIza[0-9A-Za-z_-]{35}|sk-proj-[0-9A-Za-z_-]{20,}", content):
                raise ValueError("Possible credential detected in build context; file content suppressed")
            yield name, content


def clean_head():
    sha = image_tag(run(["git", "rev-parse", "HEAD"]))
    if run(["git", "status", "--porcelain"]):
        raise ValueError("Commit reviewed changes before building; image SHA must represent a clean HEAD")
    return sha


def digest(g, sha):
    value = g("artifacts", "docker", "images", "describe", f"{g.config.image}:{image_tag(sha)}", "--format=value(image_summary.digest)")
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", value):
        raise ValueError("Artifact Registry did not return a valid immutable image digest")
    return value


def check_release_source(sha):
    files = dict(source_files(sha))
    if "app/cloud_preview.py" not in files or b"CloudSettings.from_env()" not in files.get("app/main.py", b""):
        raise ValueError("Selected commit predates the readonly cloud runtime; refusing to expose the local application")


def build(g, sha):
    if not repository(g):
        raise ValueError("Run setup first")
    # List tags first to distinguish absence from an API/permission error.
    repo_uri = g.config.image.rsplit("/", 1)[0]
    images = g("artifacts", "docker", "images", "list", repo_uri, "--include-tags", json_output=True)
    if any(f"{g.config.image}:{sha}" in item.get("tags", []) or (item.get("package") == g.config.image and sha in item.get("tags", [])) for item in images):
        digest(g, sha)
        print("Existing immutable SHA tag reused; no rebuild")
        return
    check_act_as(g, g.config.build_account)
    with tempfile.TemporaryDirectory(prefix="tripse-build-") as directory:
        staging = Path(directory)
        for name, content in source_files(sha):
            target = staging / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        (staging / "app/_build_version.txt").write_text(sha, encoding="utf-8")
        g("builds", "submit", str(staging), f"--tag={g.config.image}:{sha}", f'--region={g.config["GCP_REGION"]}',
          f'--service-account=projects/{g.config["GCP_PROJECT_ID"]}/serviceAccounts/{g.config.build_account}',
          "--default-buckets-behavior=regional-user-owned-bucket", "--timeout=600", "--suppress-logs")
    digest(g, sha)


def validate_url(value):
    if not re.fullmatch(r"https://[a-z0-9-]+(?:\.[a-z0-9-]+)*\.run\.app", value or ""):
        raise ValueError("Unexpected Cloud Run URL")
    return value


def deployed_state(g, sha):
    c = g.config
    deployed = g("run", "services", "describe", c["GCP_SERVICE_NAME"], f'--region={c["GCP_REGION"]}', json_output=True)
    assert_owned(deployed["metadata"].get("labels", {}), environment=c["APP_ENV"])
    expected_digest = digest(g, sha)
    if deployed["spec"]["template"]["spec"]["containers"][0]["image"] != f"{c.image}@{expected_digest}":
        raise ValueError("Deployed service image does not match the requested digest")
    conditions = deployed.get("status", {}).get("conditions", [])
    if not any(x.get("type") == "Ready" and x.get("status") == "True" for x in conditions):
        raise ValueError("Cloud Run service is not Ready")
    return {"environment": c["APP_ENV"], "project": c["GCP_PROJECT_ID"], "region": c["GCP_REGION"],
            "service": c["GCP_SERVICE_NAME"], "url": validate_url(deployed["status"]["url"]),
            "image_sha": sha, "image_digest": expected_digest}


def deploy(g, sha):
    c = g.config
    check_release_source(sha)
    if not repository(g):
        raise ValueError("Run setup first")
    existing = service(g)
    check_act_as(g, c.runtime_account)
    pinned = f"{c.image}@{digest(g, sha)}"
    if existing:
        policy = g("run", "services", "get-iam-policy", c["GCP_SERVICE_NAME"], f'--region={c["GCP_REGION"]}', json_output=True)
        bindings = policy.get("bindings", [])
        for binding in bindings:
            if "allAuthenticatedUsers" in binding.get("members", []) or ("allUsers" in binding.get("members", []) and (binding["role"] != "roles/run.invoker" or binding.get("condition"))):
                raise ValueError("Unexpected public IAM binding; inspect it manually before deployment")
        if any("allUsers" in binding.get("members", []) for binding in bindings):
            g("run", "services", "remove-iam-policy-binding", c["GCP_SERVICE_NAME"], f'--region={c["GCP_REGION"]}',
              "--member=allUsers", "--role=roles/run.invoker", "--condition=None")
    with tempfile.TemporaryDirectory(prefix="tripse-runtime-") as directory:
        env_path = Path(directory) / "runtime.json"
        env_path.write_text(json.dumps(c.runtime(sha)), encoding="utf-8")
        g("run", "deploy", c["GCP_SERVICE_NAME"], f"--image={pinned}", f'--region={c["GCP_REGION"]}',
          "--port=8000", f"--service-account={c.runtime_account}", f"--env-vars-file={env_path}",
          f'--min-instances={c["GCP_MIN_INSTANCES"]}', f'--max-instances={c["GCP_MAX_INSTANCES"]}',
          "--min=0", f'--max={c["GCP_MAX_INSTANCES"]}', "--invoker-iam-check",
          f'--cpu={c["GCP_CPU"]}', f'--memory={c["GCP_MEMORY"]}', "--cpu-throttling", "--concurrency=16", "--timeout=60",
          "--ingress=all", "--clear-secrets", "--clear-volumes", "--clear-volume-mounts",
          "--command=", "--args=",
          "--labels=app=tripse-ai,managed-by=tripse-scripts,environment=" + c["APP_ENV"],
          "--startup-probe=httpGet.path=/health,httpGet.port=8000,initialDelaySeconds=0,timeoutSeconds=2,periodSeconds=5,failureThreshold=12",
          "--no-allow-unauthenticated")
    g("run", "services", "update-traffic", c["GCP_SERVICE_NAME"], f'--region={c["GCP_REGION"]}', "--to-latest")
    state = deployed_state(g, sha)
    # Record the actual URL even if smoke subsequently fails; failure is still propagated.
    state_dir = ROOT / ".gcp-state"
    state_dir.mkdir(exist_ok=True)
    path = state_dir / f'{c["APP_ENV"]}.json'
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2), encoding="utf-8")
    os.replace(temporary, path)
    # Verify the actual runtime before opening anonymous access. Failure leaves it private.
    smoke(g, state, private=True)
    if c["GCP_PUBLIC_ACCESS"] == "true":
        g("run", "services", "add-iam-policy-binding", c["GCP_SERVICE_NAME"], f'--region={c["GCP_REGION"]}',
          "--member=allUsers", "--role=roles/run.invoker", "--condition=None")
        smoke(g, state)
    print(f'{c["APP_ENV"]}: {state["url"]} ({sha})')


def smoke(g, state, *, private=False):
    c = g.config
    headers = {}
    if private or c["GCP_PUBLIC_ACCESS"] == "false":
        headers["Authorization"] = "Bearer " + g("auth", "print-identity-token")
    def get(path, expected, method="GET", authenticated=True):
        request = Request(state["url"]+path, headers=headers if authenticated else {}, method=method)
        try:
            with urlopen(request, timeout=90) as response:
                status, body = response.status, response.read()
        except HTTPError as error:
            status, body = error.code, b""
        if status not in expected:
            raise ValueError(f"Smoke failed: {method} {path} returned {status}")
        return body
    if not headers:
        get("/hub", {200})
    else:
        get("/hub", {403}, authenticated=False)
    health = json.loads(get("/health", {200}))
    expected = {"status": "ok", "environment": c["APP_ENV"], "image_version": state["image_sha"],
                "feature_mode": "readonly_demo", "generation_mode": "mock", "service": c["GCP_SERVICE_NAME"], "storage": "fixtures_readonly"}
    if any(health.get(k) != v for k,v in expected.items()):
        raise ValueError("Smoke failed: runtime environment, version or feature isolation mismatch")
    for path, marker in (("/hub", b"TRIPSE"), ("/preview/planner", b"<svg"), ("/preview/documents", b"kolekc"),
                         ("/preview/documents/collection", b"source-blocks"), ("/static/cloud-preview.css", b".cards"),
                         ("/documents/assets/brand-tokens.css", b":root"), ("/documents/assets/print-export.js", b"print")):
        if marker not in get(path, {200}):
            raise ValueError(f"Smoke failed: unexpected content at {path}")
    for path in ("/api/trips", "/api/demo/messages", "/api/document-studio/trips", "/api/document-studio/assets", "/webhooks/waha", "/hub"):
        get(path, {403,404}, method="POST")
    for path in ("/documents/demo", "/demo/chat", "/api/trips", "/api/document-studio/drafts", "/api/document-studio/assets/x/content", "/preview/documents/pilot.basic", "/static/create.html", "/openapi.json"):
        get(path, {403,404})
    print("Smoke PASS: readonly routes, assets, environment and baked image SHA")


def offline_runtime(config):
    # Run in a child process with a minimal environment: no inherited credentials/config.
    env = {k:v for k,v in os.environ.items() if k.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "HOME", "USERPROFILE"}}
    env.update({key:config[key] for key in ("APP_ENV", "CLOUD_FEATURE_MODE", "PLANNING_MODE")})
    result = subprocess.run([sys.executable, "-m", "scripts.gcp.runtime_check"], cwd=ROOT, env=env, capture_output=True)
    if result.returncode:
        raise CommandError("Offline cloud startup/security check", result.returncode)


CONFIG_DIR = ROOT


def main(argv=None):
    global CONFIG_DIR
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["setup", "build", "deploy", "smoke", "rollback", "preflight"])
    parser.add_argument("--environment", choices=["dev", "prod"], required=True)
    parser.add_argument("--image-tag")
    parser.add_argument("--config-dir", type=Path, default=ROOT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    CONFIG_DIR = args.config_dir.resolve()
    c = load_pair(args.environment, CONFIG_DIR)
    sha = args.image_tag
    if (args.environment == "prod" and args.action in {"deploy", "smoke"}) or args.action == "rollback":
        if not sha:
            raise ValueError("An explicit -ImageTag SHA is required for PROD deployment/smoke and every rollback")
    if args.action == "build" and args.environment != "dev":
        raise ValueError("Build once in DEV; PROD promotes the existing image")
    sha = image_tag(sha or run(["git", "rev-parse", "HEAD"]))
    if args.action in {"build", "preflight"}:
        files = list(source_files(sha))
        if not files:
            raise ValueError("Empty build context")
    if args.action in {"build", "deploy", "rollback"} and not args.dry_run:
        check_release_source(sha)
    offline_runtime(c)
    if args.dry_run or args.offline:
        if args.offline and args.action != "preflight":
            raise ValueError("-Offline is only supported for preflight")
        print(f'OFFLINE {args.action}: {args.environment}, {c["GCP_PROJECT_ID"]}, {c["GCP_REGION"]}, {c["GCP_SERVICE_NAME"]}, {c.image}:{sha}')
        print("Config isolation and local cloud runtime PASS. No GCP calls/mutations. IAM, API availability and deployed image NOT verified.")
        return
    g = Gcloud(c)
    online_preflight(g, args.action)
    if args.action == "setup":
        setup(g)
    elif args.action == "build":
        if clean_head() != sha:
            raise ValueError("Build ImageTag must equal clean HEAD")
        build(g, sha)
    elif args.action in {"deploy", "rollback"}:
        deploy(g, sha)
    elif args.action == "smoke":
        service(g)
        smoke(g, deployed_state(g, sha))
    else:
        if not repository(g):
            raise ValueError("Artifact Registry missing; run setup first")
        service(g)
        check_act_as(g, c.runtime_account)
        check_act_as(g, c.build_account)
        if args.image_tag:
            check_release_source(sha)
            digest(g, sha)
        print("Online preflight PASS; final permission checks also occur in each gcloud operation")


if __name__ == "__main__":
    try:
        main()
    except CommandError as error:
        print(str(error), file=sys.stderr)
        sys.exit(error.code)
    except (ValueError, OSError, KeyError) as error:
        # Avoid dumping response bodies, token-bearing Request objects or subprocess args.
        print(f"Preflight/deployment stopped: {error}", file=sys.stderr)
        sys.exit(1)
