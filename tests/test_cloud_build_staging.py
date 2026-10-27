"""No cloud calls. Models the audited SDK default-vs-explicit staging contract."""
from types import SimpleNamespace

import pytest

from scripts.gcp import deployment as d
from scripts.gcp.deployment_contract import Config
from tests.test_github_cicd import values

SHA = "a" * 40
BUCKET = "tripse-ai_europe-central2_cloudbuild"
METADATA = {"name": BUCKET, "projectNumber": "690165197462", "location": "EUROPE-CENTRAL2"}


@pytest.mark.parametrize("change", [{"projectNumber": "111111111111"}, {"projectNumber": ""},
    {"name": "other-bucket"}, {"location": "US"}, {"projectNumber": None}])
def test_explicit_staging_cannot_skip_owner_name_or_region_validation(change):
    calls = []
    def g(*args, **kwargs):
        calls.append(args)
        if args[:2] == ("projects", "describe"):
            return {"projectNumber": "690165197462"}
        assert args[:3] == ("storage", "buckets", "describe") and "--raw" in args
        return METADATA | change
    g.config = Config(values())
    with pytest.raises(ValueError, match="no source uploaded"):
        d.build_source_staging(g)
    assert all("submit" not in call and "create" not in call and "list" not in call for call in calls)


def test_missing_bucket_is_not_created_or_ignored():
    def g(*args, **kwargs):
        if args[0] == "projects":
            return {"projectNumber": "690165197462"}
        raise d.CommandError("gcloud", 1, operation="gcloud storage buckets describe")
    g.config = Config(values())
    with pytest.raises(d.CommandError):
        d.build_source_staging(g)


def test_build_uses_explicit_verified_bucket_without_project_bucket_listing(monkeypatch, capsys):
    calls = []
    config = Config(values())
    def g(*args, **kwargs):
        calls.append(args)
        if args == ("version",): return {"Google Cloud SDK": "590.0.1"}
        if args[:2] == ("projects", "describe"): return {"projectNumber": "690165197462"}
        if args[:3] == ("storage", "buckets", "describe"):
            return METADATA if args[3] == "gs://" + BUCKET else METADATA | {"name": "690165197462-europe-central2-cloudbuild-logs"}
        if args[:4] == ("artifacts", "docker", "images", "list"): return []
        if args[:2] == ("builds", "submit"):
            # In the audited SDK, omission selects default_gcs_source=True,
            # which calls buckets.List(project,prefix) before upload/CreateBuild.
            # Our restricted CI principal has bucket get/object access, not list.
            if "--gcs-source-staging-dir=gs://" + BUCKET + "/source" not in args:
                raise d.CommandError("gcloud", 1, operation="gcloud builds submit",
                                     diagnostic=d.safe_build_error(b"PERMISSION_DENIED storage.buckets.list"))
            assert "--default-buckets-behavior=regional-user-owned-bucket" in args
            assert "--service-account=projects/tripse-ai/serviceAccounts/tripse-ai-build@tripse-ai.iam.gserviceaccount.com" in args
            assert "--timeout=600" in args and "--suppress-logs" in args
            assert "--gcs-log-dir=gs://690165197462-europe-central2-cloudbuild-logs" in args
            assert "--async" in args and kwargs["json_output"] is True
            assert "--tag=" + config.image + ":" + SHA in args
            return {"id": "9c54ce2d-d425-44cd-9328-a765affb8bad"}
        if args[:2] == ("builds", "describe"):
            return {"status": "SUCCESS"}
        pytest.fail("Unexpected command in restricted CI simulation")
    g.config = config
    monkeypatch.setattr(d, "repository", lambda *_: True)
    monkeypatch.setattr(d, "check_act_as", lambda *_: None)
    monkeypatch.setattr(d, "source_files", lambda *_: iter([("Dockerfile", b"FROM scratch"), ("app/main.py", b"# synthetic source")]))
    monkeypatch.setattr(d, "digest", lambda *_: "sha256:" + "b" * 64)
    d.build(g, SHA)
    submit_index = next(i for i,c in enumerate(calls) if c[:2] == ("builds", "submit"))
    assert any(c[:3] == ("storage", "buckets", "describe") for c in calls[:submit_index])
    assert not any(c[:3] in {("storage", "buckets", "list"), ("storage", "buckets", "create")} for c in calls)
    assert "Cloud Build client SDK version: 590.0.1" in capsys.readouterr().out


@pytest.mark.parametrize("stderr,category,phase,permission", [
    (b"ERROR PERMISSION_DENIED private-token storage.buckets.list", "PERMISSION_DENIED", "submit_or_wait", "storage.buckets.list"),
    (b"The user is forbidden from accessing the bucket [private-bucket] private-token", "SOURCE_BUCKET_ACCESS_DENIED", "source_bucket_validation", "none"),
    (b"Could not upload file [private-path]: PERMISSION_DENIED storage.objects.create private-token", "PERMISSION_DENIED", "source_upload", "storage.objects.create"),
    (b"unrecognized arguments: --private-token=value", "CLI_ARGUMENT_ERROR", "client_arguments", "none"),
    (b"INVALID_ARGUMENT if build.service_account specified private-token", "INVALID_ARGUMENT", "submit_or_wait", "none"),
    (b"INVALID_ARGUMENT if build.service_account specified logs_bucket is required private-token", "INVALID_ARGUMENT", "build_log_configuration", "none"),
    (b"HTTPError 403: private-token", "HTTP_403", "submit_or_wait", "none"),
    (b"RESOURCE_EXHAUSTED private-token", "RESOURCE_EXHAUSTED", "submit_or_wait", "none"),
    (b"private-token entirely unknown error", "UNCLASSIFIED", "submit_or_wait", "none"),
])
def test_google_error_classifier_reports_only_fixed_categories(stderr, category, phase, permission):
    output = d.safe_build_error(stderr)
    assert "google_category=" + category in output and "submit_phase=" + phase in output
    assert "recognized_permissions=" + permission in output
    assert all(secret not in output for secret in ("private-token", "private-path", "private-bucket", "--private"))


def test_native_submit_error_exposes_safe_google_category_not_stderr(monkeypatch):
    monkeypatch.setattr(d.subprocess, "run", lambda *a, **kw: SimpleNamespace(returncode=1, stdout=b"private-stdout",
        stderr=b"ERROR: PERMISSION_DENIED Permission storage.objects.create denied private-token Authorization: secret"))
    with pytest.raises(d.CommandError) as error:
        with d.command_stage("build.submit"):
            d.run(["gcloud", "builds", "submit", "private-context"])
    message = str(error.value)
    assert error.value.code == 1 and "PERMISSION_DENIED" in message and "storage.objects.create" in message
    assert not any(x in message for x in ("private", "Authorization", "secret"))


@pytest.mark.parametrize("status", ["FAILURE", "INTERNAL_ERROR", "TIMEOUT", "CANCELLED", "EXPIRED", "private-unknown"])
def test_build_wait_fails_closed_for_failed_or_unknown_status(status):
    def g(*args, **kwargs):
        assert args[:2] == ("builds", "describe")  # No log-object reads or mutations.
        return {"status": status}
    g.config = Config(values())
    with pytest.raises(ValueError, match="release not accepted") as error:
        d.wait_for_build(g, "9c54ce2d-d425-44cd-9328-a765affb8bad")
    assert "private-unknown" not in str(error.value)


def test_build_wait_polls_existing_build_to_success_without_log_access(monkeypatch):
    statuses = iter(["QUEUED", "WORKING", "SUCCESS"])
    calls = []
    def g(*args, **kwargs):
        calls.append(args)
        assert args[:2] == ("builds", "describe")
        return {"status": next(statuses)}
    g.config = Config(values())
    monkeypatch.setattr(d.time, "sleep", lambda *_: None)
    d.wait_for_build(g, "9c54ce2d-d425-44cd-9328-a765affb8bad")
    assert len(calls) == 3


def test_build_wait_timeout_never_cancels_or_resubmits(monkeypatch):
    moments = iter([0, 901])
    monkeypatch.setattr(d.time, "monotonic", lambda: next(moments))
    def g(*args, **kwargs):
        pytest.fail("Expired wait must not submit/cancel/read logs")
    g.config = Config(values())
    with pytest.raises(ValueError, match="inspect existing build before any retry"):
        d.wait_for_build(g, "9c54ce2d-d425-44cd-9328-a765affb8bad")


def test_build_wait_rejects_invalid_id_before_request_or_output(capsys):
    def g(*args, **kwargs):
        pytest.fail("Invalid ID must not reach Google")
    g.config = Config(values())
    with pytest.raises(ValueError, match="valid build ID"):
        d.wait_for_build(g, "private-jwt.header.signature")
    assert "private" not in capsys.readouterr().out
