"""Verify reused tags against actual Cloud Build source, not tag spelling.

DEV branches can submit builds, so an immutable SHA tag alone must not authorize
production. A trusted master acceptance verifies the builder command and exact
generation-pinned source bytes before issuing its release evidence.
"""
import io
import re
import tarfile

from scripts.gcp import deployment as d


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


def verify(g, sha, digest):
    builds = g("builds", "list", "--region=europe-central2", "--filter=status=SUCCESS",
               "--sort-by=~createTime", "--limit=1000", json_output=True)
    candidates = [b for b in builds if any(i.get("digest") == digest and i.get("name") == f"{g.config.image}:{sha}"
                   for i in b.get("results", {}).get("images", []))]
    expected = dict(d.source_files(sha)) | {"app/_build_version.txt": sha.encode()}
    for build in candidates:
        try:
            source = validate_recipe(build, g.config, sha, digest)
            uri = f"gs://{source['bucket']}/{source['object']}#{source['generation']}"
            raw = d.run([g.executable, "storage", "cat", uri, "--project=" + g.config["GCP_PROJECT_ID"], "--quiet"], binary=True)
            validate_archive(raw, expected)
            return build["id"]
        except ValueError:
            continue
    raise ValueError("No matching verified Cloud Build source/recipe for this digest; tag reuse is insufficient")
