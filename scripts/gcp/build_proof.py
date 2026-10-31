"""Verify reused tags against actual Cloud Build source, not tag spelling.

DEV branches can submit builds, so an immutable SHA tag alone must not authorize
production. A trusted master acceptance verifies the builder command and exact
generation-pinned source bytes before issuing its release evidence.
"""
import io
import hashlib
import json
import re
import tarfile
from dataclasses import dataclass
from types import MappingProxyType
from scripts.gcp import deployment as d

BUILD_ID = re.compile(r"[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}")


@dataclass(frozen=True)
class HistoricalContext:
    version: str
    image: str
    build_id: str
    digest: str
    extra_files: tuple[str, ...]
    manifest_sha256: str


# Code-reviewed trust anchor, NOT a policy version supplied by an artifact/build.
# Gate C.1 independently verified this commit, accepted master PROD evidence,
# build recipe and generation-pinned source. No range/ancestry/prefix fallback.
HISTORICAL_CONTEXTS = MappingProxyType({
    "497ea150b158bd10ec347e8bdc2b6b44dc94d2a4": HistoricalContext(
        "legacy-fixtures-497ea150-v1",
        "europe-central2-docker.pkg.dev/tripse-ai/tripse-ai/tripse-ai",
        "23f06da9-270d-4250-bdc8-670c37bd3267",
        "sha256:4bf16a5a8fc9aafa11576e8e91444e6ca4c8ac773c64e7c8df342e409771b2e6",
        ("demo-fixtures/campaigns/demo-northern-journeys.json",
         "demo-fixtures/document-presets/iceland.json",
         "demo-fixtures/trips/demo-canada.json",
         "demo-fixtures/trips/demo-iceland.json",
         "demo-fixtures/trips/demo-norway.json"),
        "59284ce900e3e41c080117c485a4469810ef4e24bc629fbef1d7aec2a3228cd7",
    ),
})


def context_manifest(files):
    entries = [[name, hashlib.sha256(content).hexdigest()] for name, content in sorted(files.items())]
    return hashlib.sha256(json.dumps(entries, separators=(",", ":")).encode()).hexdigest()


def expected_source(sha):
    d.image_tag(sha)
    # source_files applies the versioned Docker frontend input contract. The
    # existing exact manifest/archive comparison now covers Node pin, lockfile,
    # configs and source bytes too; pre-integration releases retain their context.
    files = dict(d.source_files(sha))
    policy = HISTORICAL_CONTEXTS.get(sha)
    if policy is not None:
        for name in policy.extra_files:
            # Paths are fixed in reviewed code; bytes come from the exact commit.
            content = d.run(["git", "show", sha + ":" + name], binary=True)
            d.validate_source_file(name, content)
            if name in files:
                raise ProvenanceError("conflicting_historical_source_policy")
            files[name] = content
        if context_manifest(files) != policy.manifest_sha256:
            raise ProvenanceError("historical_source_manifest_mismatch")
    return files | {"app/_build_version.txt": sha.encode()}


class ProvenanceError(ValueError):
    """Fixed operator-facing categories, never raw API/command response bodies."""
    def __init__(self, category):
        self.category = category
        super().__init__("Cloud Build provenance rejected: " + category)

def validate_recipe(build, config, sha, digest):
    tag = f"{config.image}:{sha}"
    if (build.get("status") != "SUCCESS" or build.get("images") != [tag]
        or build.get("serviceAccount") != f'projects/{config["GCP_PROJECT_ID"]}/serviceAccounts/{config.build_account}'
        or not any(i.get("name") == tag and i.get("digest") == digest for i in build.get("results", {}).get("images", []))):
        raise ValueError("Build identity, image output or status does not match the release")
    steps = build.get("steps", [])
    if len(steps) != 1:
        raise ValueError("Only the reviewed single Docker build recipe is accepted")
    step = steps[0]
    args = ["build", "--network", "cloudbuild", "--no-cache", "-t", tag, "."]
    recipes = {"gcr.io/cloud-builders/gcb-internal": ["docker", *args], "gcr.io/cloud-builders/docker": args}
    if step.get("name") not in recipes or step.get("args") != recipes[step["name"]]:
        raise ValueError("Unrecognized image build command; recipe review required")
    if (any(step.get(k) for k in ("entrypoint", "script", "env", "secretEnv", "volumes"))
        or step.get("dir", ".") not in {"", "."} or build.get("secrets") or build.get("availableSecrets")
        or build.get("substitutions")
        or any(build.get("options", {}).get(k) for k in ("env", "secretEnv", "volumes", "pool", "dynamicSubstitutions", "automapSubstitutions"))):
        raise ValueError("Unreviewed build execution overrides are forbidden")
    source = build.get("sourceProvenance", {}).get("resolvedStorageSource", {})
    if (source.get("bucket") != config["GCP_PROJECT_ID"] + "_europe-central2_cloudbuild"
        or not re.fullmatch(r"source/[a-zA-Z0-9._-]+\.tgz", source.get("object", ""))
        or not re.fullmatch(r"[1-9][0-9]*", str(source.get("generation", "")))):
        raise ValueError("Missing immutable source archive provenance")
    return source


def validate_archive(raw, expected):
    if len(raw) > 32_000_000:
        raise ValueError("Oversized build source")
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        files = {}
        for member in archive.getmembers():
            if member.isdir():
                continue
            name = member.name.removeprefix("./")
            if not member.isfile() or name in files or name not in expected or member.size != len(expected[name]):
                raise ValueError("Build source entry differs from the committed release")
            files[name] = archive.extractfile(member).read()
        if files != expected:
            raise ValueError("Actual Cloud Build source does not equal the committed image context")


def verify(g, sha, digest, build_id=None):
    d.image_tag(sha)
    if not isinstance(digest, str) or not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
        raise ProvenanceError("invalid_image_digest")
    policy = HISTORICAL_CONTEXTS.get(sha)
    if policy is not None and (digest != policy.digest or g.config.image != policy.image
                              or (build_id is not None and build_id != policy.build_id)):
        raise ProvenanceError("historical_build_identity_mismatch")
    expected = expected_source(sha)
    if build_id is not None:
        if not isinstance(build_id, str) or not BUILD_ID.fullmatch(build_id):
            raise ProvenanceError("invalid_build_lookup_hint")
        # A hint from a fresh submission or accepted artifact is NOT proof.
        # Describe the exact regional ID; do not silently fall back on mismatch.
        build = g("builds", "describe", build_id, "--region=europe-central2", json_output=True)
        if not isinstance(build, dict) or build.get("id") != build_id:
            raise ProvenanceError("missing_or_conflicting_build_record")
        return verify_candidate(g, build, sha, digest, expected)
    # Compatibility only: an existing tag without accepted evidence has no ID.
    # Keep resource bounds and fail closed instead of scanning history forever.
    query = f'status="SUCCESS" AND results.images.name="{g.config.image}:{sha}" AND results.images.digest="{digest}"'
    builds = g("builds", "list", "--region=europe-central2", "--filter=" + query,
               "--page-size=100", "--limit=1000", json_output=True)
    if not isinstance(builds, list) or len(builds) > 1000 or any(not isinstance(b, dict) for b in builds):
        raise ProvenanceError("invalid_or_incomplete_discovery")
    try:
        candidates = [b for b in builds if any(i.get("digest") == digest and i.get("name") == f"{g.config.image}:{sha}"
                       for i in b.get("results", {}).get("images", []))]
    except (TypeError, AttributeError):
        raise ProvenanceError("invalid_or_incomplete_discovery") from None
    for build in candidates:
        try:
            return verify_candidate(g, build, sha, digest, expected)
        except ValueError:
            continue
    raise ProvenanceError("bounded_discovery_exhausted; exact_build_id_required_for_older_history")


def verify_candidate(g, build, sha, digest, expected):
    policy = HISTORICAL_CONTEXTS.get(sha)
    if policy is not None and (build.get("id") != policy.build_id or digest != policy.digest
                              or g.config.image != policy.image):
        raise ProvenanceError("historical_build_identity_mismatch")
    if not isinstance(build.get("id"), str) or not BUILD_ID.fullmatch(build["id"]):
        raise ProvenanceError("invalid_build_identity")
    if build.get("projectId", g.config["GCP_PROJECT_ID"]) != g.config["GCP_PROJECT_ID"]:
        raise ProvenanceError("conflicting_build_project")
    if "name" in build:
        projects = {g.config["GCP_PROJECT_ID"], g.config.values.get("GCP_PROJECT_NUMBER", "")}
        names = {f"projects/{project}/locations/europe-central2/builds/{build['id']}" for project in projects if project}
        if build["name"] not in names:
            raise ProvenanceError("conflicting_build_resource")
    try:
        source = validate_recipe(build, g.config, sha, digest)
    except (ValueError, TypeError, AttributeError, KeyError):
        raise ProvenanceError("invalid_build_recipe_or_identity") from None
    uri = f"gs://{source['bucket']}/{source['object']}#{source['generation']}"
    # CommandError retains the safe source-read operation/stage and exit code.
    raw = d.run([g.executable, "storage", "cat", uri, "--project=" + g.config["GCP_PROJECT_ID"], "--quiet"], binary=True)
    try:
        validate_archive(raw, expected)
    except (ValueError, TypeError, tarfile.TarError, OSError, EOFError):
        raise ProvenanceError("invalid_source_archive_bytes") from None
    return build["id"]
