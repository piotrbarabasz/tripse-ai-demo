"""Gate D.0: real probe/HTTP contracts with synthetic responses, no cloud access."""
import copy
import io
import json
import sys
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest

from scripts.gcp import ci, deployment as d, smoke_auth
from scripts.gcp.deployment_contract import Config
from scripts.gcp.parity_smoke import Acceptance, NoRedirect
from tests.test_github_cicd import values, receiving_revision, workflow, SHA, IMAGE_DIGEST, ORIGIN


@pytest.fixture
def serving_dev(monkeypatch):
    monkeypatch.setenv("DEPLOY_SERVICE_ACCOUNT", "tripse-ai-dev-ci-deploy@tripse-ai.iam.gserviceaccount.com")
    monkeypatch.setenv("GCP_SMOKE_ACCOUNT", "tripse-ai-dev-ci-probe@tripse-ai.iam.gserviceaccount.com")
    monkeypatch.setenv("GITHUB_RUN_NUMBER", "50")
    config = Config(values(mode="cloud_demo"))
    revision = receiving_revision(config, SHA, "cloud_demo", "tripse-ai-dev-00031-test")
    current = {"metadata": {"name": "tripse-ai-dev", "labels": d.LABELS | {"environment": "dev"},
                           "annotations": {"run.googleapis.com/iap-enabled": "true"}},
               "spec": {"template": {"spec": copy.deepcopy(revision["spec"])}},
               "status": {"url": ORIGIN, "traffic": [{"revisionName": "tripse-ai-dev-00031-test", "percent": 100}]}}
    policy = {"bindings": [{"role": "roles/run.invoker", "members": [
        "serviceAccount:tripse-ai-dev-ci-probe@tripse-ai.iam.gserviceaccount.com"]}]}
    health = dict(status="ok", environment="dev", feature_mode="cloud_demo", image_version=SHA,
                  service="tripse-ai-dev", generation_mode="mock", storage="gcs_firestore")
    calls, signed, requests = [], [], []

    def g(*args, **kwargs):
        calls.append(args)
        if args[:3] == ("run", "services", "list"):return [current]
        if args[:3] == ("run", "services", "get-iam-policy"):return policy
        if args[:3] == ("run", "revisions", "describe"):return revision
        if args[:4] == ("artifacts", "docker", "images", "describe"):return IMAGE_DIGEST
        if args == ("auth", "print-access-token"):return "SECRET_ACCESS_TOKEN"
        pytest.fail("Unexpected operation: " + repr(args))
    g.config = config

    class Response:
        status, headers = 200, {}
        def __init__(self, data):self.data = data
        def __enter__(self):return self
        def __exit__(self, *args):pass
        def read(self):return json.dumps(self.data).encode()

    def sign(request, **kwargs):
        signed.append(request)
        assert request.get_header("Authorization") == "Bearer SECRET_ACCESS_TOKEN"
        assert request.full_url.endswith("/tripse-ai-dev-ci-probe@tripse-ai.iam.gserviceaccount.com:signJwt")
        return Response({"signedJwt": "SECRET_PROBE_TOKEN"})

    def get(request, **kwargs):
        requests.append(request)
        assert request.get_method() == "GET" and request.data is None
        assert request.full_url == ORIGIN + "/health"
        assert request.get_header("Authorization") == "Bearer SECRET_PROBE_TOKEN"
        return Response(health)

    def opener(handler):
        assert isinstance(handler, NoRedirect)
        return SimpleNamespace(open=get)

    monkeypatch.setattr(smoke_auth, "urlopen", sign)
    monkeypatch.setattr("scripts.gcp.parity_smoke.build_opener", opener)
    return SimpleNamespace(g=g, current=current, revision=revision, policy=policy,
                           health=health, calls=calls, signed=signed, requests=requests)


def test_preflight_reads_serving_identity_and_uses_only_authenticated_health(serving_dev, monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_SHA", "c" * 40)
    monkeypatch.setenv("CI_RELEASE_SHA", "c" * 40)
    ci.dev_health(serving_dev.g)
    assert len(serving_dev.requests) == len(serving_dev.signed) == 1
    claims = json.loads(json.loads(serving_dev.signed[0].data)["payload"])
    assert claims["aud"] == ORIGIN + "/*" and claims["exp"] - claims["iat"] == 600
    assert claims["iss"] == claims["sub"] == "tripse-ai-dev-ci-probe@tripse-ai.iam.gserviceaccount.com"
    # The serving SHA is intentionally different from the new workflow SHA.
    assert serving_dev.health["image_version"] == SHA
    assert "SECRET" not in str(capsys.readouterr())


@pytest.mark.parametrize("field,value", [("status", "failed"), ("environment", "prod"),
    ("feature_mode", "readonly_demo"), ("image_version", "c" * 40),
    ("service", "tripse-ai-prod"), ("generation_mode", "live"), ("storage", "sqlite")])
def test_preflight_rejects_wrong_or_missing_health_fields(serving_dev, field, value):
    serving_dev.health[field] = value
    with pytest.raises(ValueError, match="authenticated health preflight failed"):
        ci.dev_health(serving_dev.g)
    assert len(serving_dev.requests) == 1
    serving_dev.health.pop(field)
    with pytest.raises(ValueError):ci.dev_health(serving_dev.g)


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308, 401, 403, 500, 503])
def test_preflight_rejects_redirects_and_http_failures_without_credential_output(serving_dev, monkeypatch, capsys, status):
    def fail(*args, **kwargs):
        raise HTTPError(ORIGIN + "/health", status, "SECRET_PROBE_TOKEN", {}, io.BytesIO(b"SECRET_ACCESS_TOKEN"))
    monkeypatch.setattr("scripts.gcp.parity_smoke.build_opener", lambda _: SimpleNamespace(open=fail))
    with pytest.raises(ValueError, match="authenticated health preflight failed") as error:
        ci.dev_health(serving_dev.g)
    assert "SECRET" not in str(error.value) + str(capsys.readouterr())


@pytest.mark.parametrize("attack", ["iap_off", "invoker_disabled", "public", "public_authenticated",
    "split", "sha", "digest", "not_ready", "mode", "origin", "wrong_probe", "signing", "network", "non_json"])
def test_preflight_fails_closed_on_metadata_and_auth_errors(serving_dev, monkeypatch, attack):
    s = serving_dev
    if attack == "iap_off":s.current["metadata"]["annotations"]["run.googleapis.com/iap-enabled"] = "false"
    if attack == "invoker_disabled":s.current["metadata"]["annotations"]["run.googleapis.com/invoker-iam-disabled"] = "true"
    if attack in {"public", "public_authenticated"}:
        s.policy["bindings"][0]["members"].append("allUsers" if attack == "public" else "allAuthenticatedUsers")
    if attack == "split":s.current["status"]["traffic"][0]["percent"] = 99
    if attack == "sha":s.revision["spec"]["containers"][0]["env"][0]["value"] = "invalid"
    if attack == "digest":s.revision["status"]["imageDigest"] = "sha256:" + "c" * 64
    if attack == "not_ready":s.revision["status"]["conditions"] = []
    if attack == "mode":s.revision["spec"]["containers"][0]["env"][2]["value"] = "readonly_demo"
    if attack == "origin":s.current["status"]["url"] = "https://other.run.app"
    if attack == "wrong_probe":monkeypatch.setenv("GCP_SMOKE_ACCOUNT", "tripse-ai-prod-ci-probe@tripse-ai.iam.gserviceaccount.com")
    if attack in {"signing", "network"}:
        def fail(*args, **kwargs):raise OSError("SECRET_ACCESS_TOKEN")
        monkeypatch.setattr(smoke_auth if attack == "signing" else Acceptance,
                            "urlopen" if attack == "signing" else "call", fail)
    if attack == "non_json":monkeypatch.setattr(Acceptance, "call", lambda *a, **k: b"SECRET_PROBE_TOKEN")
    with pytest.raises(ValueError, match="authenticated health preflight failed") as error:
        ci.dev_health(s.g)
    assert "SECRET" not in str(error.value)


def test_preflight_cli_rejects_prod_before_any_configuration_or_cloud_call(monkeypatch, capsys):
    monkeypatch.setenv("CI_TARGET_ENV", "prod")
    monkeypatch.setattr(sys, "argv", ["ci", "dev-health"])
    monkeypatch.setattr(ci, "config_from_environment", lambda *a: pytest.fail("Configured PROD"))
    with pytest.raises(SystemExit) as error:ci.main()
    assert error.value.code == 1 and "another environment" in capsys.readouterr().err


@pytest.mark.parametrize("target", ["prod", "other_project", "other_service", "readonly", "other_deployer"])
def test_preflight_rejects_unreviewed_target_before_cloud_reads(serving_dev, monkeypatch, target):
    config = values(mode="cloud_demo")
    if target == "prod":config["APP_ENV"] = "prod"
    if target == "other_project":config["GCP_PROJECT_ID"] = "other-project"
    if target == "other_service":config["GCP_SERVICE_NAME"] = "tripse-ai-prod"
    if target == "readonly":config["CLOUD_FEATURE_MODE"] = "readonly_demo"
    if target == "other_deployer":monkeypatch.setenv("DEPLOY_SERVICE_ACCOUNT", "other@tripse-ai.iam.gserviceaccount.com")
    serving_dev.g.config = Config(config)
    with pytest.raises(ValueError, match="reviewed DEV cloud_demo target"):
        ci.dev_health(serving_dev.g)
    assert serving_dev.calls == []


def test_dev_health_cli_never_enters_release_coordinator(serving_dev, monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("CI_TARGET_ENV", "dev")
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    monkeypatch.setattr(sys, "argv", ["ci", "dev-health"])
    monkeypatch.setattr(ci, "config_from_environment", lambda env, path: serving_dev.g.config)
    monkeypatch.setattr(d, "Gcloud", lambda _: serving_dev.g)
    monkeypatch.setattr(ci, "execute", lambda: pytest.fail("Release coordinator entered"))
    ci.main()
    assert len(serving_dev.requests) == 1 and "SECRET" not in str(capsys.readouterr())
    assert list(tmp_path.iterdir()) == []


def test_preflight_workflow_is_mandatory_dev_only_after_wif_before_mutations():
    wf = workflow("delivery.yml")
    dev, prod = wf["jobs"]["dev"], wf["jobs"]["prod"]
    steps = dev["steps"]
    index = next(i for i, step in enumerate(steps) if step.get("run", "").endswith("scripts.gcp.ci dev-health"))
    assert not ({"if", "continue-on-error"} & steps[index].keys())
    assert next(i for i, step in enumerate(steps) if step.get("id") == "auth") < index
    assert next(i for i, step in enumerate(steps) if "setup-gcloud@" in step.get("uses", "")) < index
    assert index < next(i for i, step in enumerate(steps) if "make gcp-ci" in step.get("run", ""))
    assert not any("dev-health" in step.get("run", "") for step in prod["steps"])
    assert "refs/heads/master" in prod["if"] and "inputs.operation == 'promote'" in prod["if"]
    assert dev["concurrency"]["group"] == "tripse-dev-global"
