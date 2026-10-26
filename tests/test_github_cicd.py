import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from scripts.gcp import ci, deployment as d, smoke_auth
from scripts.gcp.deployment_contract import Config, ROOT
from scripts.gcp.ci_config import identities

SHA = "a" * 40
IMAGE_DIGEST = "sha256:" + "b" * 64
ORIGIN = "https://tripse-ai-dev-example.run.app"


@pytest.fixture(autouse=True)
def reviewed_ci_identity_settings(monkeypatch):
    for key, value in identities("dev").items():
        monkeypatch.setenv(key, value)


def values(environment="dev", mode="readonly_demo"):
    data = dict(GCP_PROJECT_ID="tripse-ai", GCP_REGION="europe-central2", GCP_ARTIFACT_REPO="tripse-ai",
        GCP_IMAGE_NAME="tripse-ai", GCP_SERVICE_NAME=f"tripse-ai-{environment}", GCP_PUBLIC_ACCESS="false",
        GCP_MIN_INSTANCES="0", GCP_MAX_INSTANCES="1", GCP_CPU="1", GCP_MEMORY="512Mi",
        APP_ENV=environment, PLANNING_MODE="mock", CLOUD_FEATURE_MODE=mode)
    if mode == "cloud_demo":
        data.update(GCP_PROJECT_NUMBER="690165197462", PUBLIC_BASE_URL=ORIGIN,
            IAP_OAUTH_CLIENT_ID="123-test.apps.googleusercontent.com", DEMO_EDITORS="operator@example.com|" +
                f"tripse-ai-{environment}-ci-probe@tripse-ai.iam.gserviceaccount.com", DEMO_READERS="",
            GCP_DOCUMENT_BUCKET=f"tripse-ai-tripse-ai-{environment}-documents",
            GCP_FIRESTORE_DATABASE=f"tripse-ai-{environment}",
            GCP_TASK_QUEUE=f"projects/tripse-ai/locations/europe-central2/queues/tripse-ai-{environment}",
            GCP_TASK_ACCOUNT=f"tripse-ai-{environment}-tasks@tripse-ai.iam.gserviceaccount.com")
    return data


def workflow(name):
    # BaseLoader preserves the YAML key 'on' instead of YAML-1.1 boolean coercion.
    return yaml.load((ROOT / ".github/workflows" / name).read_text(), Loader=yaml.BaseLoader)


def test_workflows_events_credentials_and_environment_boundaries():
    checks, delivery = workflow("ci.yml"), workflow("delivery.yml")
    assert checks["on"]["pull_request"]["branches"] == ["master"]
    assert "pull_request_target" not in checks["on"] | delivery["on"]
    assert checks["permissions"] == {"contents": "read"}
    assert not any("auth@" in step.get("uses", "") for step in checks["jobs"]["checks"]["steps"])
    assert delivery["on"]["push"]["branches"] == ["dev", "master"]
    assert delivery["jobs"]["dev"]["concurrency"] == {"group": "tripse-dev-global", "cancel-in-progress": "false"}
    assert delivery["jobs"]["prod"]["concurrency"]["group"] == "tripse-prod-global"
    prod = delivery["jobs"]["prod"]
    assert prod["environment"] == "production" and "refs/heads/master" in prod["if"]
    assert "needs.dev.result == 'success'" in prod["if"]
    assert delivery["jobs"]["dev"]["needs"] == "ci"
    for job in (delivery["jobs"]["dev"], prod):
        assert job["permissions"]["id-token"] == "write"
        assert any(s.get("uses", "").startswith("google-github-actions/auth@") and
                   "workload_identity_provider" in s["with"] and "credentials_json" not in s["with"] for s in job["steps"])
        assert not any("terraform apply" in s.get("run", "") for s in job["steps"])
    import re
    for wf in (checks, delivery):
        for job in wf["jobs"].values():
            for step in job.get("steps", []):
                if "uses" in step:
                    assert re.fullmatch(r"[\w/-]+@[a-f0-9]{40}", step["uses"])


@pytest.mark.parametrize("change", [{"CLOUD_FEATURE_MODE": "readonly_demo"}, {"GCP_SERVICE_NAME": "tripse-ai-prod"},
    {"GCP_PROJECT_ID": "wrong-project"}, {"GCP_REGION": "europe-west1"}, {"APP_ENV": "prod"},
    {"GCP_PUBLIC_ACCESS": "true"}, {"OPENAI_API_KEY": "never-log-this-value"}])
def test_config_rejects_silent_fallback_wrong_target_and_secret(tmp_path, monkeypatch, change):
    monkeypatch.setenv("EXPECTED_CLOUD_FEATURE_MODE", "cloud_demo")
    monkeypatch.setenv("DEPLOY_CONFIG_JSON", json.dumps(values(mode="cloud_demo") | change))
    with pytest.raises(ValueError) as error:
        ci.config_from_environment("dev", tmp_path)
    assert "never-log-this-value" not in str(error.value)


def test_configs_are_outside_checkout_and_other_environment_is_only_stub(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPECTED_CLOUD_FEATURE_MODE", "cloud_demo")
    monkeypatch.setenv("GCP_SMOKE_ACCOUNT", "tripse-ai-dev-ci-probe@tripse-ai.iam.gserviceaccount.com")
    monkeypatch.setenv("DEPLOY_CONFIG_JSON", json.dumps(values(mode="cloud_demo")))
    c = ci.config_from_environment("dev", tmp_path)
    assert c["CLOUD_FEATURE_MODE"] == "cloud_demo"
    assert "CLOUD_FEATURE_MODE=readonly_demo" in (tmp_path / ".env.prod").read_text()
    assert "DEMO_EDITORS" not in (tmp_path / ".env.prod").read_text()
    monkeypatch.delenv("EXPECTED_CLOUD_FEATURE_MODE")
    with pytest.raises(ValueError):
        ci.config_from_environment("dev", tmp_path)


def proof():
    run = dict(id=123, repository={"full_name": ci.REPOSITORY}, path=ci.WORKFLOW, event="push",
               head_branch="master", head_sha=SHA, run_attempt=1)
    artifact = dict(workflow_run={"id": 123}, expired=False, name=f"dev-accepted-{SHA}-123-1")
    record = dict(repository=ci.REPOSITORY, run_id=123, policy_sha=SHA, environment="dev", image_sha=SHA,
                  feature_mode="cloud_demo", image_digest=IMAGE_DIGEST, accepted=True, source_ref="refs/heads/master",
                  run_attempt=1, acceptance="api_ui_mock")
    record.update(source_verified=True, source_build_id="9c54ce2d-d425-44cd-9328-a765affb8bad")
    jobs = [{"name": "DEV deployment", "conclusion": "success", "run_attempt": 1}]
    return record, run, artifact, jobs


@pytest.mark.parametrize("case", ["feature", "pr", "other_workflow", "other_repository", "digest", "sha", "mode",
    "expired", "other_run", "failed_job", "unaccepted", "offline_only", "attempt"])
def test_forged_or_unaccepted_release_proof_cannot_promote(case):
    record, run, artifact, jobs = proof()
    ci.validate_proof(record, run, artifact, jobs, "dev", SHA, "cloud_demo", production=True)
    if case == "feature":run["head_branch"] = "feature"; record["source_ref"] = "refs/heads/feature"
    elif case == "pr":run["event"] = "pull_request"
    elif case == "other_workflow":run["path"] = ".github/workflows/untrusted.yml"
    elif case == "other_repository":run["repository"]["full_name"] = "attacker/repo"
    elif case == "digest":record["image_digest"] = "latest"
    elif case == "sha":record["image_sha"] = "c" * 40
    elif case == "mode":record["feature_mode"] = "readonly_demo"
    elif case == "expired":artifact["expired"] = True
    elif case == "other_run":artifact["workflow_run"]["id"] = 999
    elif case == "failed_job":jobs[0]["conclusion"] = "failure"
    elif case == "unaccepted":record["accepted"] = False
    elif case == "offline_only":record["acceptance"] = "offline"
    elif case == "attempt":record["run_attempt"] = 2
    with pytest.raises(ValueError):
        ci.validate_proof(record, run, artifact, jobs, "dev", SHA, "cloud_demo", production=True)


def test_stale_runs_rejected_and_new_manual_run_can_select_old_sha():
    current = {"metadata": {"labels": {"github-workflow": "delivery-v1", "github-run-number": "20"}}}
    with pytest.raises(ValueError, match="Stale"):
        ci.fresh(current, 19)
    ci.fresh(current, 20)
    ci.fresh(current, 21)


@pytest.mark.parametrize("iap", [True, False])
def test_keyless_probe_signs_short_lived_jwt_or_generates_explicit_id_token(monkeypatch, capsys, iap):
    monkeypatch.setenv("GCP_SMOKE_ACCOUNT", "tripse-ai-dev-ci-probe@tripse-ai.iam.gserviceaccount.com")
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    requests = []
    class Response:
        def __enter__(self):return self
        def __exit__(self, *args):pass
        def read(self):return json.dumps({"signedJwt" if iap else "token": "sensitive-probe"}).encode()
    def open_(request, **kwargs):
        requests.append(request)
        assert request.get_header("Authorization") == "Bearer sensitive-access"
        return Response()
    monkeypatch.setattr(smoke_auth, "urlopen", open_)
    g = lambda *args: "sensitive-access"
    g.config = Config(values())
    assert smoke_auth.probe_token(g, ORIGIN, iap=iap) == "sensitive-probe"
    payload = json.loads(requests[0].data)
    if iap:
        claims = json.loads(payload["payload"])
        assert claims["aud"] == ORIGIN and claims["exp"] - claims["iat"] == 600
        assert claims["iss"] == claims["sub"] == "tripse-ai-dev-ci-probe@tripse-ai.iam.gserviceaccount.com"
        assert requests[0].full_url.endswith(":signJwt")
    else:
        assert payload == {"audience": ORIGIN, "includeEmail": True}
        assert requests[0].full_url.endswith(":generateIdToken")
    assert "sensitive" not in capsys.readouterr().out


@pytest.mark.parametrize("event,ref,environment,operation", [("pull_request", "refs/pull/1/merge", "dev", "dev"),
    ("pull_request_target", "refs/heads/master", "prod", "promote"),
    ("push", "refs/heads/feature", "prod", "promote"),
    ("push", "refs/heads/master", "dev", "rollback"),
    ("push", "refs/tags/release", "dev", "dev")])
def test_events_fail_before_cloud_access(monkeypatch, event, ref, environment, operation):
    for key, value in dict(GITHUB_REPOSITORY=ci.REPOSITORY, GITHUB_EVENT_NAME=event, GITHUB_REF=ref,
                           CI_TARGET_ENV=environment, CI_OPERATION=operation).items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(ci.d, "Gcloud", lambda *args: pytest.fail("Forbidden cloud access"))
    with pytest.raises(ValueError):ci.execute()


def test_traffic_digest_verification_uses_actual_receiving_revision():
    config = Config(values())
    value = {"metadata": {"labels": d.LABELS | {"environment": "dev"}},
        "spec": {"template": {"spec": {"containers": [{"image": f"{config.image}@{IMAGE_DIGEST}"}]}}},
        "status": {"url": ORIGIN, "conditions": [{"type": "Ready", "status": "True"}],
            "latestReadyRevisionName": "tripse-ai-dev-00003-test", "latestCreatedRevisionName": "tripse-ai-dev-00003-test",
            "traffic": [{"revisionName": "tripse-ai-dev-00003-test", "percent": 100}]}}
    actual_digest = IMAGE_DIGEST
    def g(*args, **kwargs):
        if args[:3] == ("run", "services", "describe"):return copy.deepcopy(value)
        if args[:3] == ("run", "revisions", "describe"):return {"status": {"imageDigest": config.image + "@" + actual_digest}}
        return IMAGE_DIGEST
    g.config = config
    assert d.deployed_state(g, SHA)["revision"] == "tripse-ai-dev-00003-test"
    value["status"]["traffic"][0]["revisionName"] = "tripse-ai-dev-00001-old"
    with pytest.raises(ValueError, match="traffic"):d.deployed_state(g, SHA)
    value["status"]["traffic"][0]["revisionName"] = "tripse-ai-dev-00003-test"
    actual_digest = "sha256:" + "f" * 64
    with pytest.raises(ValueError, match="digest"):d.deployed_state(g, SHA)


@pytest.mark.parametrize("mode", ["cloud_demo", "readonly_demo"])
def test_failed_release_restores_previous_traffic_but_keeps_access_private(monkeypatch, mode):
    calls = []
    old = {"sha": SHA, "mode": mode, "iap_enabled": True, "url": ORIGIN,
           "traffic": [{"revisionName": "tripse-ai-dev-00001-old", "percent": 100}]}
    def g(*args, **kwargs):
        calls.append(args)
        return {"status": {"traffic": old["traffic"]}}
    g.config = Config(values(mode="cloud_demo"))
    monkeypatch.setattr(smoke_auth, "probe_token", lambda *a, **k: "private-token")
    from scripts.gcp.parity_smoke import Acceptance
    monkeypatch.setattr(Acceptance, "call", lambda *a, **k: {"image_version": SHA, "feature_mode": mode})
    ci.restore(g, old)
    assert "--invoker-iam-check" in calls[0] and "--iap" in calls[0]
    assert "--to-revisions=tripse-ai-dev-00001-old=100" in calls[1]
    assert not any("--no-invoker-iam-check" in c or "builds" in c or "delete" in c for c in calls)


def test_missing_prerequisites_never_provision_or_deploy(monkeypatch):
    g = lambda *args, **kwargs: pytest.fail("No mutation or API bootstrap expected")
    g.config = Config(values(mode="cloud_demo"))
    monkeypatch.setattr(d, "service", lambda _: None)
    with pytest.raises(ValueError, match="Bootstrap"):ci.prerequisites(g)


@pytest.mark.parametrize("environment,operation,fail", [("dev", "dev", False), ("prod", "promote", False),
    ("prod", "rollback", False), ("prod", "promote", True)])
def test_coordinator_builds_only_dev_and_never_records_failed_acceptance(tmp_path, monkeypatch, environment, operation, fail):
    calls = []
    env = dict(GITHUB_REPOSITORY=ci.REPOSITORY, GITHUB_EVENT_NAME="push" if operation == "dev" else "workflow_dispatch",
        GITHUB_REF="refs/heads/master", GITHUB_SHA=SHA, GITHUB_RUN_ID="123", GITHUB_RUN_NUMBER="10",
        GITHUB_RUN_ATTEMPT="1", RUNNER_TEMP=str(tmp_path), GITHUB_OUTPUT=str(tmp_path / "output"),
        GITHUB_STEP_SUMMARY=str(tmp_path / "summary"), CI_OPERATION=operation, CI_TARGET_ENV=environment,
        CI_RELEASE_SHA=SHA, DEPLOY_SERVICE_ACCOUNT=f"tripse-ai-{environment}-ci-deploy@tripse-ai.iam.gserviceaccount.com",
        GCP_CI="1")
    for key, value in env.items():monkeypatch.setenv(key, value)
    config = Config(values(environment))
    monkeypatch.setattr(d, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(ci, "config_from_environment", lambda *args: config)
    monkeypatch.setattr(d, "run", lambda args: SHA + "\trefs/heads/master" if args[:2] == ["git", "ls-remote"] else "")
    monkeypatch.setattr(ci, "GitHub", lambda: SimpleNamespace(request=lambda _: {"object": {"sha": SHA}}))
    monkeypatch.setattr(d, "check_release_source", lambda _: {})
    class FakeG:
        def __call__(self, *args, **kwargs):
            return {"spec": {"containers": [{"env": [{"name": "EXPECTED_IMAGE_SHA", "value": "c" * 40},
                {"name": "CLOUD_FEATURE_MODE", "value": "readonly_demo"}, {"name": "APP_ENV", "value": environment}]}]}}
    g = FakeG()
    g.config = config
    monkeypatch.setattr(d, "Gcloud", lambda _: g)
    monkeypatch.setattr(d, "online_preflight", lambda *a: None)
    monkeypatch.setattr(ci, "prerequisites", lambda _: {"metadata": {},
        "spec": {"template": {"spec": {"containers": [{"env": [{"name": "EXPECTED_IMAGE_SHA", "value": "c" * 40},
            {"name": "CLOUD_FEATURE_MODE", "value": "readonly_demo"}]}]}}},
        "status": {"url": ORIGIN, "traffic": [{"revisionName": "tripse-ai-dev-00001-old", "percent": 100}]}})
    monkeypatch.setattr(ci, "release_proof", lambda *a, **k: {"image_digest": IMAGE_DIGEST, "source_build_id": "9c54ce2d-d425-44cd-9328-a765affb8bad"})
    from scripts.gcp import build_proof
    monkeypatch.setattr(build_proof, "verify", lambda *a: "9c54ce2d-d425-44cd-9328-a765affb8bad")
    monkeypatch.setattr(d, "build", lambda *a: calls.append("build"))
    monkeypatch.setattr(d, "digest", lambda *a: IMAGE_DIGEST)
    def deploy(*args):
        calls.append("deploy")
        if fail:raise ValueError("simulated smoke failure")
    monkeypatch.setattr(d, "deploy", deploy)
    monkeypatch.setattr(d, "deployed_state", lambda *a: {"image_digest": IMAGE_DIGEST, "url": ORIGIN,
        "image_sha": SHA, "revision": f"tripse-ai-{environment}-00002-new", "traffic": [{"percent": 100}]})
    monkeypatch.setattr(ci, "restore", lambda *a: calls.append("restore"))
    if fail:
        with pytest.raises(ValueError, match="smoke"):ci.execute()
        assert calls == ["deploy", "restore"]
        assert not (tmp_path / "tripse-deployment/release.json").exists()
        assert '"accepted": false' in (tmp_path / "summary").read_text()
    else:
        ci.execute()
        assert calls == (["build", "deploy"] if environment == "dev" else ["deploy"])
        record = json.loads((tmp_path / "tripse-deployment/release.json").read_text())
        assert record["accepted"] is True and record["image_digest"] == IMAGE_DIGEST
        assert record["previous_sha"] == "c" * 40


def test_wif_bootstrap_requires_exact_repo_environment_event_and_prod_ref():
    data = (ROOT / "infra/gcp/github-actions/main.tf").read_text()
    for condition in ("assertion.repository_id", "assertion.repository_owner_id", "assertion.event_name",
        "assertion.environment", "assertion.workflow_ref", "refs/heads/master", "assertion.sub"):
        assert condition in data
    assert 'repo_id        = "1430252241"' in data
    assert 'owner_id       = "72949549"' in data
    assert "google_service_account_key" not in data


@pytest.mark.parametrize("failure", [None, "public_bucket", "unbounded_retry", "missing_minter", "unscoped_database",
    "iap_disabled", "wrong_origin", "missing_probe", "missing_oauth", "probe_denied", "runtime_disabled", "probe_disabled"])
def test_concrete_cloud_prerequisites_are_read_only_and_fail_closed(monkeypatch, failure):
    config = Config(values(mode="cloud_demo"))
    settings = config.demo_settings()
    runtime = "serviceAccount:" + config.runtime_account
    role = lambda r, m: {"role": r, "members": [m]}
    graph = {
        "bucket": {"public_access_prevention": "enforced", "uniform_bucket_level_access": True, "versioning_enabled": True},
        "db": {"name": "projects/tripse-ai/databases/tripse-ai-dev", "locationId": "europe-central2", "type": "FIRESTORE_NATIVE",
               "pointInTimeRecoveryEnablement": "POINT_IN_TIME_RECOVERY_ENABLED", "deleteProtectionState": "DELETE_PROTECTION_ENABLED"},
        "queue": {"name": settings.queue, "state": "RUNNING", "rateLimits": {"maxConcurrentDispatches": 2, "maxDispatchesPerSecond": 1}, "retryConfig": {"maxAttempts": 12}},
        "account": {"email": settings.task_account},
        "bucket_iam": {"bindings": [role("roles/storage.objectUser", runtime)]},
        "queue_iam": {"bindings": [role("roles/cloudtasks.enqueuer", runtime)]},
        "caller_iam": {"bindings": [role("roles/iam.serviceAccountUser", runtime), role("roles/iam.serviceAccountTokenCreator", "serviceAccount:service-690165197462@gcp-sa-cloudtasks.iam.gserviceaccount.com")]},
        "project_iam": {"bindings": [role("roles/datastore.user", runtime) | {"condition": {"expression": "resource.name == 'projects/tripse-ai/databases/tripse-ai-dev'"}}]},
        "live": {"iapEnabled": True, "invokerIamDisabled": False, "uri": ORIGIN},
        "iap_iam": {"bindings": [{"role": "roles/iap.httpsResourceAccessor", "members": ["user:operator@example.com", "serviceAccount:tripse-ai-dev-ci-probe@tripse-ai.iam.gserviceaccount.com", "serviceAccount:" + settings.task_account]}]},
        "oauth": {"accessSettings": {"oauthSettings": {"programmaticClients": [settings.oauth_client]}}},
    }
    if failure == "public_bucket":graph["bucket"]["public_access_prevention"] = "inherited"
    elif failure == "unbounded_retry":graph["queue"]["retryConfig"]["maxAttempts"] = -1
    elif failure == "missing_minter":graph["caller_iam"]["bindings"].pop()
    elif failure == "unscoped_database":graph["project_iam"]["bindings"].append(role("roles/datastore.user", runtime))
    elif failure == "iap_disabled":graph["live"]["iapEnabled"] = False
    elif failure == "wrong_origin":graph["live"]["uri"] = "https://wrong.run.app"
    elif failure == "missing_probe":graph["iap_iam"]["bindings"][0]["members"].pop(1)
    elif failure == "missing_oauth":graph["oauth"] = {}
    calls = []
    def g(*args, **kwargs):
        calls.append(args)
        if args[:3] == ("iam", "service-accounts", "describe") and args[3] != settings.task_account:
            return {"email": args[3], "disabled":
                    (failure == "runtime_disabled" and args[3] == config.runtime_account) or
                    (failure == "probe_disabled" and "ci-probe@" in args[3])}
        key = {("storage", "buckets", "describe"): "bucket", ("storage", "buckets", "get-iam-policy"): "bucket_iam",
               ("firestore", "databases", "describe"): "db", ("tasks", "queues", "describe"): "queue",
               ("tasks", "queues", "get-iam-policy"): "queue_iam", ("iam", "service-accounts", "describe"): "account",
               ("iam", "service-accounts", "get-iam-policy"): "caller_iam", ("iap", "web", "get-iam-policy"): "iap_iam",
               ("iap", "settings", "get"): "oauth"}.get(args[:3])
        if args[:2] == ("projects", "get-iam-policy"):key = "project_iam"
        assert key, args
        return graph[key]
    g.config = config
    monkeypatch.setattr(d, "service", lambda _: {"metadata": {}})
    monkeypatch.setattr(d, "repository", lambda _: True)
    monkeypatch.setattr(ci, "google_json", lambda *args: graph["live"])
    def token(*args, **kwargs):
        if failure == "probe_denied":raise ValueError("Probe denied")
        return "private-token"
    monkeypatch.setattr(smoke_auth, "probe_token", token)
    from scripts.gcp.parity_smoke import Acceptance
    monkeypatch.setattr(Acceptance, "call", lambda *args, **kwargs: {"status": "ok"})
    if failure:
        with pytest.raises(ValueError):ci.prerequisites(g)
    else:
        assert ci.prerequisites(g) == {"metadata": {}}
    assert all(not any(word in call for word in ("deploy", "enable", "create", "set-iam-policy", "update")) for call in calls)


def test_previous_sha_comes_from_receiving_revision_and_split_traffic_blocks_release():
    current = {"status": {"url": ORIGIN, "traffic": [{"revisionName": "tripse-ai-dev-00001-old", "percent": 100}]},
        "spec": {"template": {"spec": {"containers": [{"env": [{"name": "EXPECTED_IMAGE_SHA", "value": "f" * 40}]}]}}}}
    def g(*args, **kwargs):
        assert args[3] == "tripse-ai-dev-00001-old"
        return {"spec": {"containers": [{"env": [{"name": "EXPECTED_IMAGE_SHA", "value": SHA},
            {"name": "APP_ENV", "value": "dev"}, {"name": "CLOUD_FEATURE_MODE", "value": "readonly_demo"}]}]}}
    g.config = Config(values())
    assert ci.snapshot(current, g)["sha"] == SHA
    current["status"]["traffic"][0]["percent"] = 50
    with pytest.raises(ValueError, match="split"):ci.snapshot(current, g)


@pytest.mark.parametrize("attack", [None, "extra_step", "other_builder", "command", "env", "entrypoint", "source_generation", "other_account", "other_digest", "source_bytes", "extra_file"])
def test_reused_sha_tag_requires_exact_cloud_build_recipe_and_source(monkeypatch, attack):
    import io
    import tarfile
    from scripts.gcp import build_proof
    config = Config(values())
    tag = config.image + ":" + SHA
    build = {"id": "9c54ce2d-d425-44cd-9328-a765affb8bad", "status": "SUCCESS", "images": [tag],
        "serviceAccount": f"projects/tripse-ai/serviceAccounts/{config.build_account}",
        "results": {"images": [{"name": tag, "digest": IMAGE_DIGEST}]},
        "steps": [{"name": "gcr.io/cloud-builders/gcb-internal", "args": ["docker", "build", "--network", "cloudbuild", "--no-cache", "-t", tag, "."]}],
        "sourceProvenance": {"resolvedStorageSource": {"bucket": "tripse-ai_europe-central2_cloudbuild", "object": "source/build.tgz", "generation": "123"}}}
    expected = {"Dockerfile": b"FROM python:3.12-slim", "app/main.py": b"trusted source"}
    actual = expected | {"app/_build_version.txt": SHA.encode()}
    if attack == "extra_step":build["steps"].append({"name": "malicious"})
    elif attack == "other_builder":build["steps"][0]["name"] = "attacker/image"
    elif attack == "command":build["steps"][0]["args"] = ["docker", "pull", "attacker/image"]
    elif attack == "env":build["options"] = {"env": ["DOCKER_HOST=attacker"]}
    elif attack == "entrypoint":build["steps"][0]["entrypoint"] = "sh"
    elif attack == "source_generation":build["sourceProvenance"]["resolvedStorageSource"].pop("generation")
    elif attack == "other_account":build["serviceAccount"] = "projects/tripse-ai/serviceAccounts/other"
    elif attack == "other_digest":build["results"]["images"][0]["digest"] = "sha256:" + "f" * 64
    elif attack == "source_bytes":actual["app/main.py"] = b"different code"
    elif attack == "extra_file":actual["credential.json"] = b"not in reviewed source"
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w:gz") as tar:
        for name, data in actual.items():
            info = tarfile.TarInfo(name);info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    def g(*args, **kwargs):return [build]
    g.config, g.executable = config, "gcloud"
    monkeypatch.setattr(d, "source_files", lambda _: expected.items())
    monkeypatch.setattr(d, "run", lambda *a, **k: raw.getvalue())
    if attack:
        with pytest.raises(ValueError):build_proof.verify(g, SHA, IMAGE_DIGEST)
    else:
        assert build_proof.verify(g, SHA, IMAGE_DIGEST) == build["id"]


def test_source_verified_boolean_is_required_in_production_proof():
    record, run, artifact, jobs = proof()
    for flag in (False, "true", None):
        record["source_verified"] = flag
        with pytest.raises(ValueError):
            ci.validate_proof(record, run, artifact, jobs, "dev", SHA, "cloud_demo", production=True)
