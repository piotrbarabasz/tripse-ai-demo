"""Gate C.1: exact historical trust anchor; synthetic bytes and no credentials/network."""
import copy
from dataclasses import replace
import io
import tarfile
from types import MappingProxyType

import pytest

from scripts.gcp import build_proof as b, ci, deployment as d
from scripts.gcp.deployment_contract import Config
from tests.test_github_cicd import values, proof, workflow
from tests.test_delivery_hardening import coordinator

LEGACY_SHA = "497ea150b158bd10ec347e8bdc2b6b44dc94d2a4"
OTHER_SHA = "b" * 40


def archive(files, attack=None):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w:gz") as stream:
        for name, data in files.items():
            item = tarfile.TarInfo(name)
            item.size = len(data)
            stream.addfile(item, io.BytesIO(data))
        if attack == "duplicate":
            item = tarfile.TarInfo("Dockerfile"); item.size = len(files["Dockerfile"])
            stream.addfile(item, io.BytesIO(files["Dockerfile"]))
        elif attack == "symlink":
            item = tarfile.TarInfo("legacy-link"); item.type = tarfile.SYMTYPE
            item.linkname = "Dockerfile"; stream.addfile(item)
    return raw.getvalue()


@pytest.fixture
def legacy(monkeypatch):
    policy = b.HISTORICAL_CONTEXTS[LEGACY_SHA]
    base = {"Dockerfile": b"FROM python:3.12-slim\n", "app/main.py": b"synthetic source\n"}
    extras = {name: b'{"synthetic":true}\n' for name in policy.extra_files}
    policy = replace(policy, manifest_sha256=b.context_manifest(base | extras))
    monkeypatch.setattr(b, "HISTORICAL_CONTEXTS", MappingProxyType({LEGACY_SHA: policy}))
    source = base | extras | {"app/_build_version.txt": LEGACY_SHA.encode()}
    config = Config(values())
    tag = config.image + ":" + LEGACY_SHA
    build = {"id": policy.build_id, "projectId": "tripse-ai", "status": "SUCCESS",
             "images": [tag], "serviceAccount": "projects/tripse-ai/serviceAccounts/" + config.build_account,
             "steps": [{"name": "gcr.io/cloud-builders/docker", "args": ["build", "--network", "cloudbuild", "--no-cache", "-t", tag, "."]}],
             "results": {"images": [{"name": tag, "digest": policy.digest}]},
             "sourceProvenance": {"resolvedStorageSource": {"bucket": "tripse-ai_europe-central2_cloudbuild", "object": "source/synthetic.tgz", "generation": "123"}}}
    calls = []; reads = []
    def cloud(*args, **kwargs):
        calls.append(args)
        assert args[:2] in {("builds", "describe"), ("builds", "list")}
        return [copy.deepcopy(build)] if args[1] == "list" else copy.deepcopy(build)
    cloud.config = config; cloud.executable = "gcloud"
    def read(args, **kwargs):
        reads.append(args)
        if args[:2] == ["git", "show"]:
            sha, name = args[2].split(":", 1)
            assert sha == LEGACY_SHA
            return extras[name]
        assert args[:3] == ["gcloud", "storage", "cat"]
        return archive(source)
    monkeypatch.setattr(d, "source_files", lambda sha: iter(base.items()))
    monkeypatch.setattr(d, "run", read)
    return cloud, policy, build, base, extras, source, calls, reads


@pytest.mark.parametrize("direct", [True, False])
def test_exact_reviewed_context_passes_direct_and_targeted_lookup(legacy, direct):
    g, policy, _, base, extras, _, calls, reads = legacy
    assert b.verify(g, LEGACY_SHA, policy.digest, policy.build_id if direct else None) == policy.build_id
    assert calls[0][:2] == ("builds", "describe" if direct else "list")
    assert any(args[3].endswith("#123") for args in reads if args[0] == "gcloud")
    assert dict(d.source_files(LEGACY_SHA)) == base  # New-build allowlist is unchanged.
    assert b.expected_source(LEGACY_SHA).keys() == (base | extras | {"app/_build_version.txt": b""}).keys()


@pytest.mark.parametrize("attack", ["digest", "hint", "image", "discovered_id"])
def test_historical_exception_is_bound_to_image_digest_and_exact_build(legacy, attack):
    g, policy, build, *_ = legacy
    digest, hint = policy.digest, policy.build_id
    if attack == "digest": digest = "sha256:" + "f" * 64
    if attack == "hint": hint = "11111111-1111-1111-1111-111111111111"
    if attack == "image": g.config = Config(values() | {"GCP_PROJECT_ID": "foreign"})
    if attack == "discovered_id":
        build["id"] = "11111111-1111-1111-1111-111111111111"; hint = None
    with pytest.raises(b.ProvenanceError): b.verify(g, LEGACY_SHA, digest, hint)


@pytest.mark.parametrize("attack", ["builder", "recipe", "generation", "project", "status", "sha"])
def test_historical_policy_never_bypasses_build_checks(legacy, attack):
    g, policy, build, *_ = legacy
    if attack == "builder": build["serviceAccount"] = "untrusted"
    if attack == "recipe": build["steps"][0]["args"].remove("--no-cache")
    if attack == "generation": build["sourceProvenance"]["resolvedStorageSource"].pop("generation")
    if attack == "project": build["projectId"] = "foreign"
    if attack == "status": build["status"] = "FAILURE"
    if attack == "sha": build["images"] = [g.config.image + ":" + OTHER_SHA]
    with pytest.raises(b.ProvenanceError): b.verify(g, LEGACY_SHA, policy.digest, policy.build_id)


@pytest.mark.parametrize("attack", ["extra", "missing", "changed", "baked_sha", "duplicate", "symlink"])
def test_historical_archive_still_requires_exact_names_types_and_bytes(legacy, monkeypatch, attack):
    g, policy, _, _, _, source, *_ = legacy
    if attack == "extra": source["demo-fixtures/trips/unreviewed.json"] = b"extra"
    if attack == "missing": source.pop(policy.extra_files[0])
    if attack == "changed": source[policy.extra_files[0]] = b"changed"
    if attack == "baked_sha": source["app/_build_version.txt"] = OTHER_SHA.encode()
    original = d.run
    def read(args, **kwargs):
        return archive(source, attack) if args[0] == "gcloud" else original(args, **kwargs)
    monkeypatch.setattr(d, "run", read)
    with pytest.raises(b.ProvenanceError, match="archive"): b.verify(g, LEGACY_SHA, policy.digest, policy.build_id)


def test_no_artifact_declared_policy_can_select_legacy_context_for_another_commit(legacy):
    g, policy, build, _, _, source, *_ = legacy
    # Untrusted release/build extensions have no authority over the policy selector.
    build["source_policy"] = policy.version
    build["images"] = [g.config.image + ":" + OTHER_SHA]
    build["results"]["images"][0]["name"] = build["images"][0]
    build["steps"][0]["args"][-2] = build["images"][0]
    source["app/_build_version.txt"] = OTHER_SHA.encode()
    with pytest.raises(b.ProvenanceError, match="archive"): b.verify(g, OTHER_SHA, policy.digest, policy.build_id)


@pytest.mark.parametrize("which", ["base", "extra"])
def test_committed_manifest_drift_is_rejected_before_cloud_lookup(legacy, which):
    g, policy, _, base, extras, _, calls, _ = legacy
    (base if which == "base" else extras)["app/main.py" if which == "base" else policy.extra_files[0]] = b"other committed bytes"
    with pytest.raises(b.ProvenanceError, match="manifest"): b.verify(g, LEGACY_SHA, policy.digest, policy.build_id)
    assert not calls


@pytest.mark.parametrize("secret", [b"-----BEGIN PRIVATE KEY-----", b'{"private_key":"synthetic"}', b"AIza" + b"x" * 35, b"sk-proj-" + b"x" * 20])
def test_legacy_additions_use_the_unchanged_secret_detector(legacy, monkeypatch, secret):
    g, policy, _, base, extras, _, calls, _ = legacy
    extras[policy.extra_files[0]] = secret
    # Even a reviewed manifest could never opt out of secret detection.
    policy = replace(policy, manifest_sha256=b.context_manifest(base | extras))
    monkeypatch.setattr(b, "HISTORICAL_CONTEXTS", {LEGACY_SHA: policy})
    with pytest.raises(ValueError, match="credential") as error: b.verify(g, LEGACY_SHA, policy.digest, policy.build_id)
    assert secret.decode() not in str(error.value) and not calls


@pytest.mark.parametrize("name", ["../private.txt", "/private.txt", "C:/private.txt", "app/..\\private.txt", "demo-fixtures/.env", "demo-fixtures/trips/client.key"])
def test_shared_source_guard_rejects_forbidden_paths(name):
    with pytest.raises(ValueError): d.validate_source_file(name, b"synthetic")


def test_prod_rollback_still_requires_accepted_proof_and_never_reads_cloud_build(tmp_path, monkeypatch):
    calls, _ = coordinator(tmp_path, monkeypatch, environment="prod", operation="rollback")
    monkeypatch.setattr(ci, "release_proof", lambda *a, **k: (_ for _ in ()).throw(ValueError("missing accepted proof")))
    with pytest.raises(ValueError, match="accepted proof"): ci.execute()
    assert not calls


def test_prod_coordinator_delegates_proof_without_new_build_or_source_permissions(tmp_path, monkeypatch):
    calls, _ = coordinator(tmp_path, monkeypatch, environment="prod", operation="rollback")
    monkeypatch.setattr(b, "verify", lambda *a: pytest.fail("PROD must not gain source-read permissions"))
    ci.execute()
    assert "deploy" in calls and "build" not in calls


@pytest.mark.parametrize("attack", [None, "expired", "unaccepted", "wrong_run", "attempt", "repository", "workflow", "feature", "sha", "digest", "environment", "acceptance", "failed_job"])
def test_historical_source_exception_does_not_authorize_untrusted_prod_evidence(attack):
    policy = b.HISTORICAL_CONTEXTS[LEGACY_SHA]
    record, run, artifact, jobs = proof()
    record.update(environment="prod", service="tripse-ai-prod", image_sha=LEGACY_SHA,
                  policy_sha=LEGACY_SHA, image_digest=policy.digest, source_build_id=policy.build_id,
                  revision="tripse-ai-prod-00006-test", traffic=[{"revisionName": "tripse-ai-prod-00006-test", "percent": 100}],
                  acceptance="smoke")
    run["head_sha"] = LEGACY_SHA
    artifact["name"] = f"prod-accepted-{LEGACY_SHA}-123-1"
    jobs[0]["name"] = "PROD deployment"
    if attack == "expired": artifact["expired"] = True
    if attack == "unaccepted": record["accepted"] = False
    if attack == "wrong_run": artifact["workflow_run"]["id"] = 999
    if attack == "attempt": record["run_attempt"] = 2
    if attack == "repository": run["repository"]["full_name"] = "foreign/repo"
    if attack == "workflow": run["path"] = ".github/workflows/untrusted.yml"
    if attack == "feature": run["head_branch"] = "feature"; record["source_ref"] = "refs/heads/feature"
    if attack == "sha": record["image_sha"] = OTHER_SHA
    if attack == "digest": record["image_digest"] = "unverified-tag"
    if attack == "environment": record["environment"] = "dev"
    if attack == "acceptance": record["acceptance"] = "offline"
    if attack == "failed_job": jobs[0]["conclusion"] = "failure"
    if attack:
        with pytest.raises(ValueError): ci.validate_proof(record, run, artifact, jobs, "prod", LEGACY_SHA, "cloud_demo", production=True)
    else:
        ci.validate_proof(record, run, artifact, jobs, "prod", LEGACY_SHA, "cloud_demo", production=True)


def test_manual_feature_dev_path_is_permitted_by_coordinator(tmp_path, monkeypatch):
    calls, _ = coordinator(tmp_path, monkeypatch, environment="dev", operation="dev")
    monkeypatch.setenv("GITHUB_REF", "refs/heads/ci/ci-006-integration-acceptance")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    ci.execute()
    assert "build" in calls and "deploy" in calls


@pytest.mark.parametrize("operation", ["dev", "promote", "rollback"])
def test_feature_ref_cannot_execute_any_prod_operation(tmp_path, monkeypatch, operation):
    calls, _ = coordinator(tmp_path, monkeypatch, environment="prod", operation=operation)
    monkeypatch.setenv("GITHUB_REF", "refs/heads/ci/ci-006-integration-acceptance")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    with pytest.raises(ValueError, match="not permitted"): ci.execute()
    assert not calls


def test_workflow_prod_ref_guard_is_a_mandatory_top_level_conjunction():
    expression = " ".join(workflow("delivery.yml")["jobs"]["prod"]["if"].split())
    assert expression.startswith("always() && needs.ci.result == 'success' && github.ref == 'refs/heads/master' &&")
    # The feature ref fails this required conjunct independently of all job results.
    assert "refs/heads/ci/ci-006-integration-acceptance" != "refs/heads/master"
