"""Offline subprocess/HTTP mocks: never submit builds, deploy or contact GCP."""
import io
import json
import sys
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest

from scripts.gcp import ci, deployment as d
from scripts.gcp.deployment_contract import Config
from tests.test_github_cicd import values

SECRET = "never-log-credential"
SHA = "a" * 40


@pytest.mark.parametrize("executable", ["gcloud", "/opt/google-cloud-sdk/bin/gcloud",
    r"C:\private-credential-files\google-cloud-sdk\bin\gcloud.CMD"])
@pytest.mark.parametrize("words,label", [
    (["artifacts", "docker", "images", "list"], "gcloud artifacts docker images list"),
    (["auth", "print-access-token"], "gcloud auth print-access-token"),
    (["builds", "submit"], "gcloud builds submit"),
    (["storage", "cat"], "gcloud storage cat"),
])
def test_subprocess_error_reports_only_static_operation_stage_and_native_exit(monkeypatch, executable, words, label, capsys):
    monkeypatch.setattr(d.subprocess, "run", lambda *a, **kw: SimpleNamespace(
        returncode=17, stdout=SECRET.encode(), stderr=(SECRET + " JWT header arguments").encode()))
    with pytest.raises(d.CommandError) as error:
        with d.command_stage("build.submit"):
            d.run([executable, *words, SECRET, "--credential-file=" + SECRET, "--authorization=Bearer " + SECRET])
    assert error.value.code == 17 and error.value.operation == label and error.value.stage == "build.submit"
    message = str(error.value)
    assert "exit 17" in message and "stage=build.submit" in message and label in message
    assert SECRET not in message and "private-credential-files" not in message and "--credential-file" not in message
    assert capsys.readouterr() == ("", "")


def test_unknown_operation_and_executable_never_echo_positional_values(monkeypatch):
    monkeypatch.setattr(d.subprocess, "run", lambda *a, **kw: SimpleNamespace(returncode=2))
    for args in (["gcloud", SECRET, SECRET], [r"C:\private\credentials.json", SECRET]):
        with pytest.raises(d.CommandError) as error:
            d.run(args)
        assert error.value.operation.endswith("unclassified")
        assert SECRET not in str(error.value) and "credentials.json" not in str(error.value)


def test_stage_is_restored_after_failure_and_unknown_labels_are_not_echoed():
    with pytest.raises(d.CommandError) as error:
        with d.command_stage("build"):
            with d.command_stage("build.act_as"):
                raise d.CommandError("gcloud", 1)
    assert error.value.stage == "build.act_as"
    assert d.CommandError("gcloud", 1).stage == "unspecified"
    with pytest.raises(ValueError) as invalid:
        with d.command_stage(SECRET):
            pytest.fail("Unknown stage accepted")
    assert SECRET not in str(invalid.value)


@pytest.mark.parametrize("failure,expected_stage,expected_operation", [
    ("repository", "build.repository", "gcloud artifacts repositories list"),
    ("images", "build.image_lookup", "gcloud artifacts docker images list"),
    ("act_as_token", "build.act_as", "gcloud auth print-access-token"),
    ("submit", "build.submit", "gcloud builds submit"),
    ("new_digest", "build.verify_digest", "gcloud artifacts docker images describe"),
    ("reuse_digest", "build.reuse_digest", "gcloud artifacts docker images describe"),
])
def test_build_failure_identifies_actual_suboperation_without_fallback(monkeypatch, failure, expected_stage, expected_operation):
    config = Config(values())
    monkeypatch.setattr(d.shutil, "which", lambda _: "/tool/gcloud")
    calls = []
    def subprocess(args, **kwargs):
        _, operation = d.safe_command_operation(args)
        calls.append(operation)
        failed = {"repository": "gcloud artifacts repositories list", "images": "gcloud artifacts docker images list",
                  "act_as_token": "gcloud auth print-access-token", "submit": "gcloud builds submit",
                  "new_digest": "gcloud artifacts docker images describe", "reuse_digest": "gcloud artifacts docker images describe"}[failure]
        if operation == failed:
            return SimpleNamespace(returncode=1, stdout=SECRET.encode(), stderr=SECRET.encode())
        if operation == "gcloud artifacts repositories list":
            data = [{"name": "tripse-ai", "labels": d.LABELS, "format": "DOCKER", "dockerConfig": {"immutableTags": True}}]
            output = json.dumps(data)
        elif operation == "gcloud artifacts docker images list":
            output = json.dumps([{"tags": [config.image + ":" + SHA]}] if failure == "reuse_digest" else [])
        elif operation == "gcloud auth print-access-token":
            output = SECRET
        elif operation == "gcloud version":
            output = json.dumps({"Google Cloud SDK": "590.0.1"})
        elif operation == "gcloud projects describe":
            output = json.dumps({"projectNumber": "690165197462"})
        elif operation == "gcloud storage buckets describe":
            output = json.dumps({"name": args[4].removeprefix("gs://"), "projectNumber": "690165197462", "location": "EUROPE-CENTRAL2"})
        elif operation == "gcloud builds submit":
            output = json.dumps({"id": "9c54ce2d-d425-44cd-9328-a765affb8bad"})
        elif operation == "gcloud builds describe":
            output = json.dumps({"status": "SUCCESS"})
        else:
            output = ""
        return SimpleNamespace(returncode=0, stdout=output.encode(), stderr=b"")
    monkeypatch.setattr(d.subprocess, "run", subprocess)
    monkeypatch.setattr(d, "urlopen", lambda *a, **kw: io.BytesIO(b'{"permissions":["iam.serviceAccounts.actAs"]}'))
    monkeypatch.setattr(d, "source_files", lambda _: iter([("Dockerfile", b"FROM scratch"), ("app/main.py", b"# synthetic source")]))
    with pytest.raises(d.CommandError) as error:
        d.build(d.Gcloud(config), SHA)
    assert error.value.stage == expected_stage and error.value.operation == expected_operation and error.value.code == 1
    assert SECRET not in str(error.value)
    if failure in {"repository", "images", "act_as_token", "reuse_digest"}:
        assert "gcloud builds submit" not in calls
    assert calls[-1] == expected_operation


def test_act_as_http_failure_is_distinct_from_gcloud_process_failure(monkeypatch):
    def denied(*args, **kwargs):
        raise HTTPError("https://iam.googleapis.com/" + SECRET, 403, SECRET, {}, io.BytesIO(SECRET.encode()))
    monkeypatch.setattr(d, "urlopen", denied)
    with pytest.raises(ValueError) as error:
        with d.command_stage("build.act_as"):
            d.check_act_as(lambda *a: SECRET, "private-account")
    message = str(error.value)
    assert "HTTP 403" in message and "stage=build.act_as" in message and "iam.serviceAccounts.testIamPermissions" in message
    assert SECRET not in message and "private-account" not in message


def test_ci_prints_and_summarizes_safe_command_failure_without_acceptance_artifact(tmp_path, monkeypatch, capsys):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setattr(sys, "argv", ["ci", "execute"])
    monkeypatch.setattr(d.subprocess, "run", lambda *a, **kw: SimpleNamespace(returncode=1, stdout=SECRET.encode(),
        stderr=("PERMISSION_DENIED storage.objects.create " + SECRET).encode()))
    def execute():
        with d.command_stage("build.submit"):
            d.run(["gcloud", "builds", "submit", SECRET])
    monkeypatch.setattr(ci, "execute", execute)
    with pytest.raises(SystemExit) as error:
        ci.main()
    assert error.value.code == 1
    stderr = capsys.readouterr().err
    content = summary.read_text()
    for output in (stderr, content):
        assert "build.submit" in output and "gcloud builds submit" in output and SECRET not in output
        assert "PERMISSION_DENIED" in output and "storage.objects.create" in output
    assert "exit code: `1`" in content and "Release not accepted" in content
    assert not (tmp_path / "release.json").exists()


@pytest.mark.parametrize("stage,operation", [("credentials", "gcloud auth print-access-token"),
    ("preflight", "gcloud projects describe"), ("prerequisites", "gcloud artifacts repositories list")])
def test_ci_wrappers_preserve_command_diagnostics(tmp_path, monkeypatch, stage, operation):
    config = Config(values())
    for key, value in {"GITHUB_REPOSITORY": ci.REPOSITORY, "GITHUB_EVENT_NAME": "push",
        "GITHUB_REF": "refs/heads/dev", "GITHUB_SHA": SHA, "CI_RELEASE_SHA": SHA,
        "CI_OPERATION": "dev", "CI_TARGET_ENV": "dev", "RUNNER_TEMP": str(tmp_path), "GCP_CI": "1",
        "DEPLOY_SERVICE_ACCOUNT": config.runtime_account.replace("dev@", "dev-ci-deploy@")}.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(ci, "config_from_environment", lambda *a: config)
    monkeypatch.setattr(d, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(d, "check_release_source", lambda *a: {})
    monkeypatch.setattr(d, "run", lambda *a, **kw: "")
    class G:
        def __call__(self, *args, **kwargs):
            if "gcloud " + " ".join(args) == operation:
                raise d.CommandError("gcloud", 23, operation=operation)
            return "synthetic-token"
    g = G()
    g.config = config
    monkeypatch.setattr(d, "Gcloud", lambda *a: g)
    monkeypatch.setattr(d, "online_preflight", lambda g, *_: g("projects", "describe"))
    monkeypatch.setattr(ci, "prerequisites", lambda g: g("artifacts", "repositories", "list"))
    with pytest.raises(d.CommandError) as error:
        ci.execute()
    assert error.value.stage == stage and error.value.operation == operation and error.value.code == 23
