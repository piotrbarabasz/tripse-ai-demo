"""Manual gcloud orchestration. No credentials, global config changes or automatic triggers."""
import argparse
from contextlib import contextmanager
from contextvars import ContextVar
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
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen, HTTPRedirectHandler, build_opener

try:
    from .deployment_contract import ROOT, image_tag, load_pair
except ImportError:  # PowerShell invokes the file directly.
    from deployment_contract import ROOT, image_tag, load_pair

LABELS = {"app": "tripse-ai", "managed-by": "tripse-scripts"}
APIS = ("run.googleapis.com", "artifactregistry.googleapis.com", "cloudbuild.googleapis.com", "iam.googleapis.com", "logging.googleapis.com", "cloudresourcemanager.googleapis.com")

# Only fixed command words are eligible for logs. Never derive labels by joining
# argv: positional resource names, paths and flag values may contain credentials.
GCLOUD_OPERATIONS = tuple(tuple(value.split()) for value in (
    "version", "auth print-access-token", "auth print-identity-token", "projects describe",
    "projects get-iam-policy", "projects add-iam-policy-binding", "services list", "services enable",
    "run regions list", "run services list", "run services describe", "run revisions describe",
    "run services get-iam-policy", "run services remove-iam-policy-binding", "run services update",
    "run services update-traffic", "run deploy", "artifacts repositories list", "artifacts repositories create",
    "artifacts docker images list", "artifacts docker images describe", "builds submit", "builds list", "builds describe",
    "iam service-accounts describe", "iam service-accounts create", "iam service-accounts get-iam-policy",
    "storage buckets describe", "storage buckets get-iam-policy", "storage cat",
    "firestore databases describe", "tasks queues describe", "tasks queues get-iam-policy",
    "iap web get-iam-policy", "iap settings get",
))
COMMAND_STAGES = frozenset({"unspecified", "credentials", "preflight", "prerequisites",
    "build", "build.repository", "build.image_lookup", "build.reuse_digest", "build.act_as",
    "build.client", "build.source_bucket", "build.log_bucket", "build.source", "build.submit", "build.wait", "build.verify_digest", "release.digest", "release.source_proof",
    "release.snapshot", "release.deploy", "release.verify", "release.acceptance", "release.restore"})
_COMMAND_STAGE = ContextVar("gcp_command_stage", default="unspecified")


@contextmanager
def command_stage(name):
    if name not in COMMAND_STAGES:
        raise ValueError("Unknown internal command stage")
    token = _COMMAND_STAGE.set(name)
    try:
        yield
    finally:
        _COMMAND_STAGE.reset(token)


def safe_command_operation(args):
    executable = str(args[0]).replace("\\", "/").rsplit("/", 1)[-1].lower()
    if executable in {"gcloud", "gcloud.cmd", "gcloud.exe", "gcloud.bat"}:
        for prefix in GCLOUD_OPERATIONS:
            if tuple(args[1:1 + len(prefix)]) == prefix:
                return "gcloud", "gcloud " + " ".join(prefix)
        return "gcloud", "gcloud unclassified"
    if executable in {"git", "git.exe"}:
        # Fixed Git verbs only; commit IDs, refs and archive/file arguments omitted.
        verb = args[1] if len(args) > 1 and args[1] in {"archive", "status", "rev-parse", "merge-base", "ls-remote"} else "unclassified"
        return "git", "git " + verb
    return "external command", "unclassified"


class CommandError(RuntimeError):
    def __init__(self, name, code, detail=None, *, operation=None, stage=None, diagnostic=None):
        self.operation = operation or "unclassified"
        self.stage = stage or _COMMAND_STAGE.get()
        self.diagnostic = diagnostic or ""
        super().__init__(f"{name} failed (exit {code}); operation stopped"
                         f" [stage={self.stage}; operation={self.operation}]"
                         + (f" [{self.diagnostic}]" if self.diagnostic else "") + (f". {detail}" if detail else ""))
        self.code = code


def safe_build_error(stderr, *, source_metadata=False):
    """Classify known Google/CLI errors; no substring of raw stderr is returned."""
    if isinstance(stderr, bytes):
        stderr = stderr[:1_000_000].decode("utf-8", errors="replace")
    text = (stderr or "")[:1_000_000]
    phase = "source_bucket_metadata" if source_metadata else "submit_or_wait"
    if "forbidden from accessing the bucket" in text:
        phase = "source_bucket_validation"
    elif "Could not upload file" in text:
        phase = "source_upload"
    elif "unrecognized arguments:" in text:
        phase = "client_arguments"
    elif "already exists in another project" in text or "already exists and is owned by another project" in text:
        phase = "source_bucket_ownership"
    elif "build.service_account" in text and ("logs_bucket" in text or "default_logs_bucket_behavior" in text):
        phase = "build_log_configuration"
    categories = ("PERMISSION_DENIED", "UNAUTHENTICATED", "INVALID_ARGUMENT", "NOT_FOUND",
                  "RESOURCE_EXHAUSTED", "FAILED_PRECONDITION", "SERVICE_DISABLED", "QUOTA_EXCEEDED")
    category = next((code for code in categories if re.search(r"\b" + code + r"\b", text)), "UNCLASSIFIED")
    if category == "UNCLASSIFIED":
        category = next(("HTTP_" + code for code in ("400", "401", "403", "404", "409", "429", "500", "503")
                         if re.search(r"\bHTTP(?:Error| error)?[ :]+" + code + r"\b", text, re.IGNORECASE)), category)
    if phase == "client_arguments":
        category = "CLI_ARGUMENT_ERROR"
    elif phase == "source_bucket_validation":
        category = "SOURCE_BUCKET_ACCESS_DENIED"
    elif phase == "source_bucket_ownership":
        category = "BUCKET_PROJECT_MISMATCH"
    permissions = ("storage.buckets.get", "storage.buckets.list", "storage.buckets.create",
                   "storage.objects.create", "storage.objects.get", "storage.objects.list",
                   "cloudbuild.builds.create", "cloudbuild.builds.get", "iam.serviceAccounts.actAs", "serviceusage.services.use",
                   "artifactregistry.repositories.uploadArtifacts", "logging.logEntries.create")
    recognized = [permission for permission in permissions if re.search(r"(?<![\w.])" + re.escape(permission) + r"(?![\w.])", text)]
    return (f"google_category={category}; submit_phase={phase}; "
            "recognized_permissions=" + (",".join(recognized) or "none"))


def run(args, *, binary=False):
    # No secret values ever appear in commands or output. Tokens are captured, not printed.
    result = subprocess.run(args, cwd=ROOT, capture_output=True)
    if result.returncode:
        name, operation = safe_command_operation(args)
        diagnostic = safe_build_error(getattr(result, "stderr", b"")) if operation in {"gcloud builds submit", "gcloud builds describe"} else None
        if _COMMAND_STAGE.get() == "build.source_bucket" and operation in {"gcloud storage buckets describe", "gcloud projects describe"}:
            diagnostic = safe_build_error(getattr(result, "stderr", b""), source_metadata=True)
        raise CommandError(name, result.returncode, operation=operation, diagnostic=diagnostic)
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
    # WIF uses external-account credentials, not an interactive gcloud login.
    if not g("auth", "print-access-token"):
        raise ValueError("No usable gcloud credentials")
    project = g("projects", "describe", g.config["GCP_PROJECT_ID"], json_output=True)
    if project.get("lifecycleState") != "ACTIVE":
        raise ValueError("Project must be ACTIVE with billing enabled by the operator")
    if g.config["CLOUD_FEATURE_MODE"] == "cloud_demo" and str(project.get("projectNumber")) != g.config["GCP_PROJECT_NUMBER"]:
        raise ValueError("IAP project number does not match the selected GCP project")
    permissions = ["resourcemanager.projects.get"]
    if os.getenv("GCP_CI") == "1":
        permissions += ["run.services.list", "artifactregistry.repositories.list"]
        if action == "build":
            permissions += ["cloudbuild.builds.create"]
        check_region(g)
        check_permissions(g, permissions)
        return
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
    except HTTPError as error:
        raise ValueError(f"Service-account actAs check failed [stage={_COMMAND_STAGE.get()}; "
                         f"operation=iam.serviceAccounts.testIamPermissions; HTTP {error.code}]") from None
    except OSError:
        raise ValueError(f"Service-account actAs check unavailable [stage={_COMMAND_STAGE.get()}; "
                         "operation=iam.serviceAccounts.testIamPermissions; transport error]") from None
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
        # Only the known environment browser-key reference may be rotated or
        # cleared. Other secret-bearing prior configurations require inspection.
        template = value.get("spec", {}).get("template", {})
        spec = template.get("spec", {})
        containers = spec.get("containers", [])
        references = [e for e in containers[0].get("env", []) if e.get("valueFrom")] if containers else []
        safe_refs = []
        aliases = dict(entry.split(":", 1) for entry in template.get("metadata", {}).get("annotations", {}).get("run.googleapis.com/secrets", "").split(",") if ":" in entry)
        secret_name = f'tripse-ai-{c["APP_ENV"]}-maps-browser'
        allowed = {secret_name, f'projects/{c["GCP_PROJECT_ID"]}/secrets/{secret_name}'}
        for item in references:
            ref = item.get("valueFrom", {}).get("secretKeyRef", {})
            resolved = aliases.get(ref.get("name"), ref.get("name"))
            if item.get("name") != "GOOGLE_MAPS_BROWSER_KEY" or not re.fullmatch(r"[1-9][0-9]*", str(ref.get("key", ""))):
                continue
            if resolved not in allowed and re.fullmatch(rf"projects/[0-9]+/secrets/{secret_name}", resolved or ""):
                # Cross-project aliases are rejected, including when rolling
                # back to preview config without a project-number field.
                number = c.values.get("GCP_PROJECT_NUMBER") or g("projects", "describe", c["GCP_PROJECT_ID"], "--format=value(projectNumber)")
                allowed.add(f"projects/{number}/secrets/{secret_name}")
            if resolved in allowed:
                safe_refs.append(item)
        if len(containers) != 1 or spec.get("volumes") or len(references) != len(safe_refs):
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
    scoped = f'projects/{c["GCP_PROJECT_ID"]}/roles/tripseBuildMetadata'
    if not any(b["role"] in {role, scoped} and member in b.get("members", []) and not b.get("condition") for b in policy.get("bindings", [])):
        raise ValueError("Provision reviewed scoped builder IAM with infra/gcp/github-actions; setup never grants project-wide build/data access")


def source_files(sha):
    """Allowlisted committed files, never the working directory or developer data."""
    archive = run(["git", "archive", sha], binary=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for member in tar.getmembers():
            name = member.name
            allowed = name in {"Dockerfile", "requirements.txt", ".dockerignore", ".gcloudignore"} or name.startswith(("app/", "demo-fixtures/gt-v1/"))
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
    return files


def build_source_staging(g):
    """Validate an existing bucket's owner directly; never discover/create buckets.

    Implicit gcloud staging validates ownership via project-wide buckets.list.
    Explicit staging omits that SDK check, so we enforce owner/name/location here
    with buckets.get before any source upload. Missing metadata fails closed.
    """
    c = g.config
    bucket = f'{c["GCP_PROJECT_ID"]}_{c["GCP_REGION"]}_cloudbuild'
    project = g("projects", "describe", c["GCP_PROJECT_ID"], json_output=True)
    metadata = g("storage", "buckets", "describe", "gs://" + bucket, "--raw", json_output=True)
    number = str(project.get("projectNumber", ""))
    if (not re.fullmatch(r"[1-9][0-9]*", number) or metadata.get("name") != bucket
        or str(metadata.get("projectNumber", "")) != number
        or metadata.get("location", "").lower() != c["GCP_REGION"]):
        raise ValueError("Build source bucket missing or owner/name/region differs; operator bootstrap required; no source uploaded")
    return "gs://" + bucket + "/source"


def wait_for_build(g, build_id):
    """Poll metadata only. SDK --suppress-logs still reads the GCS log object."""
    if not isinstance(build_id, str) or not re.fullmatch(r"[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}", build_id):
        raise ValueError("Cloud Build did not return a valid build ID")
    print("Cloud Build accepted: " + build_id)
    deadline = time.monotonic() + 900
    while time.monotonic() < deadline:
        state = g("builds", "describe", build_id, f'--region={g.config["GCP_REGION"]}', json_output=True)
        status = state.get("status")
        if status == "SUCCESS":
            return
        if status in {"FAILURE", "INTERNAL_ERROR", "TIMEOUT", "CANCELLED", "EXPIRED"}:
            raise ValueError(f"Cloud Build {build_id} ended with status {status}; release not accepted")
        if status not in {"QUEUED", "PENDING", "WORKING"}:
            raise ValueError("Cloud Build returned an unrecognized status; release not accepted")
        time.sleep(3)
    # Never cancel a possibly running build or start another automatically.
    raise ValueError(f"Cloud Build {build_id} status wait expired; inspect existing build before any retry; release not accepted")


def build_log_destination(g):
    # Explicit pre-existing logs bucket avoids backend bucket-create authority
    # when the shared builder is hardened before PROD receives private data.
    project = g("projects", "describe", g.config["GCP_PROJECT_ID"], json_output=True)
    number = str(project.get("projectNumber", ""))
    if not re.fullmatch(r"[1-9][0-9]*", number):
        raise ValueError("Cannot validate build log bucket project")
    name = f'{number}-{g.config["GCP_REGION"]}-cloudbuild-logs'
    metadata = g("storage", "buckets", "describe", "gs://" + name, "--raw", json_output=True)
    if (metadata.get("name") != name or str(metadata.get("projectNumber", "")) != number
        or metadata.get("location", "").lower() != g.config["GCP_REGION"]):
        raise ValueError("Build log bucket owner/name/region differs; no build submitted")
    return "gs://" + name


def build(g, sha):
    with command_stage("build.repository"):
        if not repository(g):
            raise ValueError("Run setup first")
    # List tags first to distinguish absence from an API/permission error.
    repo_uri = g.config.image.rsplit("/", 1)[0]
    with command_stage("build.image_lookup"):
        images = g("artifacts", "docker", "images", "list", repo_uri, "--include-tags", json_output=True)
    if any(f"{g.config.image}:{sha}" in item.get("tags", []) or (item.get("package") == g.config.image and sha in item.get("tags", [])) for item in images):
        with command_stage("build.reuse_digest"):
            digest(g, sha)
        print("Existing immutable SHA tag reused; no rebuild")
        return
    with command_stage("build.act_as"):
        check_act_as(g, g.config.build_account)
    with command_stage("build.client"):
        version = g("version", json_output=True).get("Google Cloud SDK", "")
        if not isinstance(version, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
            raise ValueError("Cannot determine Cloud Build client version safely")
        print("Cloud Build client SDK version: " + version)
    with command_stage("build.source_bucket"):
        source_staging = build_source_staging(g)
    with command_stage("build.log_bucket"):
        log_destination = build_log_destination(g)
    with tempfile.TemporaryDirectory(prefix="tripse-build-") as directory:
        staging = Path(directory)
        with command_stage("build.source"):
            for name, content in source_files(sha):
                target = staging / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
        (staging / "app/_build_version.txt").write_text(sha, encoding="utf-8")
        with command_stage("build.submit"):
            submitted = g("builds", "submit", str(staging), f"--tag={g.config.image}:{sha}", f'--region={g.config["GCP_REGION"]}',
              f'--service-account=projects/{g.config["GCP_PROJECT_ID"]}/serviceAccounts/{g.config.build_account}',
              f"--gcs-source-staging-dir={source_staging}",
              f"--gcs-log-dir={log_destination}",
              "--default-buckets-behavior=regional-user-owned-bucket", "--timeout=600", "--suppress-logs", "--async", json_output=True)
        with command_stage("build.wait"):
            wait_for_build(g, submitted.get("id"))
    with command_stage("build.verify_digest"):
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
    status = deployed["status"]
    revision = status.get("latestReadyRevisionName")
    traffic = [t for t in status.get("traffic", []) if t.get("percent", 0)]
    if not revision or status.get("latestCreatedRevisionName") != revision or len(traffic) != 1 or traffic[0].get("revisionName") != revision or traffic[0].get("percent") != 100:
        raise ValueError("Requested READY revision is not receiving all traffic")
    actual = g("run", "revisions", "describe", revision, f'--region={c["GCP_REGION"]}', json_output=True)
    if actual.get("status", {}).get("imageDigest") != f"{c.image}@{expected_digest}":
        raise ValueError("Traffic revision digest differs from requested image")
    return {"environment": c["APP_ENV"], "project": c["GCP_PROJECT_ID"], "region": c["GCP_REGION"],
            "service": c["GCP_SERVICE_NAME"], "url": validate_url(deployed["status"]["url"]),
            "image_sha": sha, "image_digest": expected_digest, "revision": revision, "traffic": traffic,
            "feature_mode": c["CLOUD_FEATURE_MODE"]}


def deploy(g, sha):
    if g.config["CLOUD_FEATURE_MODE"] == "cloud_demo":
        # Require smoke credentials before the first mutation. OAuth/IAP setup
        # remains an explicit operator step; never silently publish this mode.
        if not (os.getenv("CLOUD_DEMO_SMOKE_TOKEN") or os.getenv("GCP_SMOKE_ACCOUNT")):
            raise ValueError("cloud_demo deployment requires CLOUD_DEMO_SMOKE_TOKEN from the approved IAP OAuth flow")
    c = g.config
    files = check_release_source(sha)
    if c["CLOUD_FEATURE_MODE"] == "cloud_demo" and not {"app/cloud_runtime.py", "app/cloud_access.py", "app/cloud_jobs.py", "app/document_studio/cloud_storage.py"} <= files.keys():
        raise ValueError("Selected immutable image source predates authenticated cloud_demo")
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
        secret_ref = c.values.get("GCP_BROWSER_MAPS_SECRET")
        secret_flags = ["--set-secrets=GOOGLE_MAPS_BROWSER_KEY=" + secret_ref.replace("/versions/", ":")] if secret_ref else ["--clear-secrets"]
        labels = "--labels=app=tripse-ai,managed-by=tripse-scripts,environment=" + c["APP_ENV"]
        if os.getenv("GCP_CI") == "1":
            sequence = os.getenv("GITHUB_RUN_NUMBER", "")
            if not re.fullmatch(r"[1-9][0-9]*", sequence):
                raise ValueError("CI deployment requires a workflow sequence")
            labels += ",github-workflow=delivery-v1,github-run-number=" + sequence
        g("run", "deploy", c["GCP_SERVICE_NAME"], f"--image={pinned}", f'--region={c["GCP_REGION"]}',
          "--port=8000", f"--service-account={c.runtime_account}", f"--env-vars-file={env_path}",
          f'--min-instances={c["GCP_MIN_INSTANCES"]}', f'--max-instances={c["GCP_MAX_INSTANCES"]}',
          "--min=0", f'--max={c["GCP_MAX_INSTANCES"]}', "--invoker-iam-check",
          f'--cpu={c["GCP_CPU"]}', f'--memory={c["GCP_MEMORY"]}', "--cpu-throttling", "--concurrency=16", "--timeout=60",
          "--ingress=all", *secret_flags, "--clear-volumes", "--clear-volume-mounts",
          "--command=", "--args=",
          labels,
          "--startup-probe=httpGet.path=/health,httpGet.port=8000,initialDelaySeconds=0,timeoutSeconds=2,periodSeconds=5,failureThreshold=12",
          "--no-allow-unauthenticated", *(["--iap"] if c["CLOUD_FEATURE_MODE"] == "cloud_demo" else ["--no-iap"]))
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
        publish(g, state)
    print(f'{c["APP_ENV"]}: {state["url"]} ({sha})')


def publish(g, state):
    """Publish only after private QA; close access again on any publication failure."""
    c = g.config
    if c["CLOUD_FEATURE_MODE"] != "readonly_demo":
        raise ValueError("Anonymous publication is restricted to readonly_demo")
    command = ("run", "services", "update", c["GCP_SERVICE_NAME"], f'--region={c["GCP_REGION"]}')
    try:
        g(*command, "--no-invoker-iam-check")
        smoke(g, state)
    except (CommandError, ValueError, OSError) as error:
        # A CLI/network failure need not mean that the server rejected the update.
        # Re-enable IAM explicitly and verify access instead of assuming it is private.
        try:
            g(*command, "--invoker-iam-check")
            smoke(g, state, private=True)
        except (CommandError, ValueError, OSError):
            detail = "Publication failed; could not confirm private access restoration. Operator must inspect service access immediately."
        else:
            detail = "Publication failed; IAM check restored and private smoke passed."
        detail += (" Check organization policy constraints/run.managed.requireInvokerIam"
                   " (and legacy constraints/run.requireInvokerIam), operator permissions and gcloud flag support."
                   " No allUsers fallback or organization policy changes were attempted.")
        if isinstance(error, CommandError):
            raise CommandError("Cloud Run publication", error.code, detail,
                               operation=error.operation, stage=error.stage, diagnostic=error.diagnostic) from None
        raise ValueError(detail) from None


def smoke(g, state, *, private=False):
    c = g.config
    if c["CLOUD_FEATURE_MODE"] == "cloud_demo":
        return cloud_demo_smoke(g, state)
    headers = {}
    if private or c["GCP_PUBLIC_ACCESS"] == "false":
        if os.getenv("GCP_SMOKE_ACCOUNT"):
            from scripts.gcp.smoke_auth import probe_token
            token = probe_token(g, state["url"], iap=False)
        else:
            token = g("auth", "print-identity-token")
        if not token:
            raise ValueError("Private smoke requires an identity token")
        headers["Authorization"] = "Bearer " + token
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


def cloud_demo_smoke(g, state):
    """Read-only authenticated acceptance; no fixture writes or paid operations."""
    if os.getenv("GCP_SMOKE_ACCOUNT"):
        from scripts.gcp.smoke_auth import probe_token
        token = probe_token(g, state["url"], iap=True)
    else:
        token = os.getenv("CLOUD_DEMO_SMOKE_TOKEN")
    if not token:
        raise ValueError("Set CLOUD_DEMO_SMOKE_TOKEN in the shell, never in deployment dotenv")
    origin = g.config["PUBLIC_BASE_URL"]
    if state["url"] != origin:
        raise ValueError("Deployed origin differs from reviewed PUBLIC_BASE_URL")

    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    opener = build_opener(NoRedirect())

    def get(path, authenticated=True):
        headers = {"Authorization": "Bearer " + token} if authenticated else {}
        try:
            with opener.open(Request(origin + path, headers=headers), timeout=30) as response:
                return response.status, response.read()
        except HTTPError as error:
            return error.code, b""
    status, body = get("/health")
    if status != 200:
        raise ValueError("Authenticated health failed")
    health = json.loads(body)
    expected = {"feature_mode": "cloud_demo", "generation_mode": "mock", "storage": "gcs_firestore",
                "environment": g.config["APP_ENV"], "image_version": state["image_sha"]}
    if any(health.get(key) != value for key, value in expected.items()):
        raise ValueError("cloud_demo runtime mismatch")
    for path in ("/hub", "/documents/demo", "/documents/assets/studio.js", "/api/document-studio/trips", "/api/demo/scenarios"):
        if get(path)[0] != 200:
            raise ValueError(f"cloud_demo authenticated read failed: {path}")
        if get(path, False)[0] not in {302, 303, 401, 403}:
            raise ValueError("Anonymous denial was not established")
    print("Smoke PASS: authenticated cloud_demo reads; writes/jobs/browser/restore require DEV acceptance")


def offline_runtime(config):
    if config["CLOUD_FEATURE_MODE"] == "cloud_demo":
        config.demo_settings()
        print("cloud_demo configuration validated offline; adapter/router parity is covered by tests/test_cloud_demo.py")
        return
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
        if os.getenv("GCP_CI") != "1" or c["APP_ENV"] == "dev":
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
