"""Offline regression coverage; no cloud/gh processes are invoked by these tests."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.gcp import bootstrap, ci
from scripts.gcp.ci_config import REQUIRED, identities, validate
from tests.test_github_cicd import values, workflow


def settings(environment="dev", mode="cloud_demo"):
    return identities(environment) | {"DEPLOY_CONFIG_JSON": json.dumps(values(environment, mode)),
                                      "EXPECTED_CLOUD_FEATURE_MODE": mode}


@pytest.mark.parametrize("key", REQUIRED)
@pytest.mark.parametrize("value", [None, "", " \t\n"])
def test_missing_environment_settings_are_actionable_and_do_not_print_values(key, value):
    data = settings()
    if value is None:
        del data[key]
    else:
        data[key] = value
    with pytest.raises(ValueError) as error:
        validate("dev", data)
    assert f"Missing GitHub Environment variable: {key} (development)" in str(error.value)
    assert "Settings -> Environments -> development -> Environment variables" in str(error.value)
    assert data.get("DEPLOY_CONFIG_JSON", "not-a-config") not in str(error.value) or key == "DEPLOY_CONFIG_JSON"


@pytest.mark.parametrize("payload", ['{ secret-token:do-not-log', '"private-token"', '[]', 'null'])
def test_malformed_json_and_wrong_shapes_are_sanitized(payload):
    data = settings() | {"DEPLOY_CONFIG_JSON": payload}
    with pytest.raises(ValueError) as error:
        validate("dev", data)
    assert "private-token" not in str(error.value) and "do-not-log" not in str(error.value)
    assert str(error.value).startswith(("DEPLOY_CONFIG_JSON is not valid JSON.", "Invalid runtime schema:"))


@pytest.mark.parametrize("key", list(identities("dev")))
def test_identity_names_cannot_cross_environment(key):
    with pytest.raises(ValueError, match=key):
        validate("dev", settings() | {key: identities("prod")[key]})


@pytest.mark.parametrize("key,value", [("GCP_REGION", "europe-west1"), ("GCP_PROJECT_ID", "other-project"),
    ("GCP_SERVICE_NAME", "tripse-ai-prod"), ("CLOUD_FEATURE_MODE", "readonly_demo"), ("GCP_PUBLIC_ACCESS", "true")])
def test_no_target_or_cloud_mode_fallback(key, value):
    data = settings() | {"DEPLOY_CONFIG_JSON": json.dumps(values(mode="cloud_demo") | {key: value})}
    with pytest.raises(ValueError, match="Invalid runtime schema"):
        validate("dev", data)


def test_configuration_failure_has_safe_actions_summary(tmp_path, monkeypatch, capsys):
    for key, value in settings().items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("DEPLOY_CONFIG_JSON", "bad-private-value")
    monkeypatch.setenv("CI_TARGET_ENV", "dev")
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setattr(sys, "argv", ["ci", "configure", "--basic"])
    with pytest.raises(SystemExit) as error:
        ci.main()
    assert error.value.code == 1
    assert "not valid JSON" in summary.read_text()
    assert "bad-private-value" not in summary.read_text() + capsys.readouterr().err


def test_basic_check_requires_no_site_packages(tmp_path):
    env = dict(os.environ, **settings(), CI_TARGET_ENV="dev")
    env.pop("GITHUB_STEP_SUMMARY", None)
    result = subprocess.run([sys.executable, "-S", "-m", "scripts.gcp.ci", "configure", "--basic"],
                            env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("environment", ["dev", "prod"])
def test_prepare_validated_local_bundle_never_overwrites_or_calls_cloud(tmp_path, monkeypatch, environment):
    source, output = tmp_path / "source.json", tmp_path / "bundle.json"
    source.write_text(json.dumps(values(environment, "cloud_demo")))
    monkeypatch.setattr(bootstrap, "command", lambda *_: pytest.fail("unexpected API call"))
    bootstrap.prepare(environment, source, output, "cloud_demo")
    data = json.loads(output.read_text())
    assert set(data) == set(REQUIRED)
    assert bootstrap.full_validate(environment, data)["APP_ENV"] == environment
    with pytest.raises(FileExistsError):
        bootstrap.prepare(environment, source, output, "cloud_demo")


@pytest.mark.parametrize("case", ["ready", "missing_environment", "missing_variables", "invalid_config", "gcp"])
def test_readonly_operator_check_with_mock_github_metadata(monkeypatch, capsys, case):
    data = settings()
    if case == "missing_variables":
        del data["WIF_PROVIDER"]
        del data["CI_PROBE_ACCOUNT"]
    if case == "invalid_config":
        data["DEPLOY_CONFIG_JSON"] = "dont-log-this"
    calls = []
    def command(args):
        calls.append(args)
        if args[0] == "gh":
            assert args[:4] == ["gh", "api", "--paginate", "--slurp"]
            if args[-1].endswith("/environments?per_page=100"):
                return [{"environments": [] if case == "missing_environment" else [{"name": "development"}]}]
            return [{"variables": [{"name": k, "value": v} for k,v in data.items()]}]
        assert "describe" in args and "--format=json" in args
        if "providers" in args:
            return {"name": identities("dev")["WIF_PROVIDER"], "state": "ACTIVE"}
        return {"email": args[4]}
    monkeypatch.setattr(bootstrap, "command", command)
    assert bootstrap.check("dev", gcp=case == "gcp") == (case in {"ready", "gcp"})
    output = capsys.readouterr().out
    assert "dont-log-this" not in output and data["DEPLOY_CONFIG_JSON"] not in output
    if case == "missing_variables":
        assert "WIF_PROVIDER" in output and "CI_PROBE_ACCOUNT" in output
    if case == "ready":
        assert "MISSING VERIFICATION" in output


def test_workflow_early_check_is_before_dependency_browser_and_authentication():
    for job in (workflow("delivery.yml")["jobs"][name] for name in ("dev", "prod")):
        steps = job["steps"]
        basic = next(i for i,s in enumerate(steps) if "configure --basic" in s.get("run", ""))
        install = next(i for i,s in enumerate(steps) if s.get("run") == "make install-dev")
        full = next(i for i,s in enumerate(steps) if s.get("run", "").endswith("ci configure"))
        auth = next(i for i,s in enumerate(steps) if "google-github-actions/auth@" in s.get("uses", ""))
        assert basic < install < full < auth
        assert job["env"]["CI_PROBE_ACCOUNT"] == "${{ vars.CI_PROBE_ACCOUNT }}"
        assert job["env"]["WIF_PROVIDER"] == "${{ vars.WIF_PROVIDER }}"


@pytest.mark.parametrize("ref,sha", [("refs/heads/feature-x", "a" * 40), ("refs/heads/master", "b" * 40)])
def test_push_guard_rejects_feature_or_substituted_master_sha_before_cloud(monkeypatch, ref, sha):
    for key,value in dict(GITHUB_REPOSITORY=ci.REPOSITORY, GITHUB_EVENT_NAME="push", GITHUB_REF=ref,
                          GITHUB_SHA="a" * 40, CI_RELEASE_SHA=sha, CI_TARGET_ENV="dev", CI_OPERATION="dev").items():
        monkeypatch.setenv(key,value)
    monkeypatch.setattr(ci, "config_from_environment", lambda *_: pytest.fail("must fail before config/cloud"))
    with pytest.raises(ValueError, match="exact pushed commit SHA"):
        ci.execute()


def test_push_policy_and_wif_defense_agree():
    delivery = workflow("delivery.yml")
    assert delivery["on"]["push"]["branches"] == ["dev", "master"]
    assert "refs/heads/dev" in delivery["jobs"]["dev"]["if"]
    prod = delivery["jobs"]["prod"]
    assert "needs.ci.result == 'success'" in prod["if"]
    assert "needs.dev.result == 'success'" in prod["if"] and "refs/heads/master" in prod["if"]
    assert prod["env"]["CI_RELEASE_SHA"] == "${{ needs.dev.outputs.sha || inputs.release_sha }}"
    assert "pull_request" not in delivery["on"]
    tf = Path("infra/gcp/github-actions/main.tf").read_text()
    assert "assertion.ref in ['refs/heads/dev', 'refs/heads/master']" in tf
