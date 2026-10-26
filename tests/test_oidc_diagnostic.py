"""Synthetic tokens only; no runner, GitHub OIDC, STS or GCP calls."""
import base64
import io
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from scripts.gcp import oidc_diagnostic as diagnostic
from scripts.gcp.ci_config import identities
from tests.test_github_cicd import workflow

POLICY = json.loads(diagnostic.POLICY.read_text(encoding="utf-8"))


def test_shared_contract_pins_reviewed_immutable_identity_and_existing_branch_policy():
    assert POLICY == {
        "repository": "piotrbarabasz/tripse-ai-demo", "repository_id": "1430252241",
        "repository_owner_id": "72949549", "environment": "development",
        "sub": "repo:piotrbarabasz@72949549/tripse-ai-demo@1430252241:environment:development",
        "events": ["push", "workflow_dispatch"], "push_refs": ["refs/heads/dev", "refs/heads/master"],
        "dispatch_ref_prefix": "refs/heads/",
        "workflow_ref_prefix": "piotrbarabasz/tripse-ai-demo/.github/workflows/delivery.yml@"}


def claims(event="push", ref="refs/heads/dev"):
    return {k: POLICY[k] for k in ("repository", "repository_id", "repository_owner_id", "environment", "sub")} | {
        "event_name": event, "ref": ref, "workflow_ref": POLICY["workflow_ref_prefix"] + ref}


@pytest.mark.parametrize("event,ref", [("push", "refs/heads/dev"), ("push", "refs/heads/master"),
    ("workflow_dispatch", "refs/heads/dev"), ("workflow_dispatch", "refs/heads/reviewed-manual")])
def test_exact_dev_claim_contract_accepts_approved_events_and_refs(event, ref):
    assert all(diagnostic.checks(claims(event, ref), POLICY).values())


@pytest.mark.parametrize("key,value", [("repository", "attacker/tripse-ai-demo"),
    ("repository_id", "1430252242"), ("repository_owner_id", "72949550"),
    ("environment", "production"), ("environment", None), ("sub", diagnostic.LEGACY_SUB),
    ("sub", POLICY["sub"].replace("1430252241", "1430252242")),
    ("sub", POLICY["sub"].replace("development", "production")),
    ("event_name", "pull_request"), ("event_name", "pull_request_target"), ("event_name", "dynamic"),
    ("ref", "refs/heads/feature"), ("ref", "refs/tags/v1"), ("ref", "refs/pull/1/merge"),
    ("workflow_ref", "piotrbarabasz/tripse-ai-demo/.github/workflows/ci.yml@refs/heads/dev"),
    ("workflow_ref", POLICY["workflow_ref_prefix"] + "refs/heads/master")])
def test_condition_rejects_each_incorrect_claim(key, value):
    result = diagnostic.checks(claims() | {key: value}, POLICY)
    assert result[key] is False
    assert not all(result.values())


def test_legacy_subject_is_specific_failed_condition_not_missing_environment(capsys):
    data = claims()
    assert all(diagnostic.checks(data, POLICY).values())
    assert data["sub"] != diagnostic.LEGACY_SUB
    assert diagnostic.report(data, POLICY)
    output = capsys.readouterr().out
    assert 'sub="' + POLICY["sub"] + '" source Terraform check=PASS' in output
    assert "Audited pre-fix provider legacy sub comparison=FAIL" in output
    assert POLICY["workflow_ref_prefix"] + "refs/heads/dev" in output


def synthetic_token(data):
    encoded = base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")
    return "synthetic-header." + encoded + ".synthetic-signature"


def runner_environment(monkeypatch):
    monkeypatch.setenv("WIF_PROVIDER", identities("dev")["WIF_PROVIDER"])
    monkeypatch.setenv("CI_TARGET_ENV", "dev")
    monkeypatch.setenv("ACTIONS_ID_TOKEN_REQUEST_URL", "https://run.actions.githubusercontent.com/oidc?api-version=2&audience=old")
    monkeypatch.setenv("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "private-request-token")


def test_oidc_request_uses_runner_mechanism_and_pinned_auth_audience_without_logging(monkeypatch, capsys):
    runner_environment(monkeypatch)
    data = claims() | {"private_extra": "never-print-this"}
    token = synthetic_token(data)
    requests = []
    class Opener:
        def open(self, request, **kwargs):
            requests.append(request)
            assert kwargs == {"timeout": 30}
            return io.BytesIO(json.dumps({"value": token}).encode())
    def opener(handler):
        assert handler.redirect_request(None) is None
        return Opener()
    monkeypatch.setattr(diagnostic, "build_opener", opener)
    decoded = diagnostic.request_claims()
    assert set(decoded) == set(diagnostic.CLAIMS)
    assert parse_qs(urlsplit(requests[0].full_url).query)["audience"] == [
        "https://iam.googleapis.com/" + identities("dev")["WIF_PROVIDER"]]
    assert requests[0].get_header("Authorization") == "Bearer private-request-token"
    diagnostic.report(decoded, POLICY)
    output = capsys.readouterr().out
    assert token not in output and "private-request-token" not in output and "never-print-this" not in output


@pytest.mark.parametrize("response", [b'{"value":"invalid-secret-token"}', b'private-response',
    b'{"value":"a.b.c"}', b'x' * 65537], ids=["bad-envelope", "bad-json", "bad-payload", "oversize"])
def test_request_decode_errors_never_expose_response_or_credentials(monkeypatch, response, capsys):
    runner_environment(monkeypatch)
    class Opener:
        def open(self, *args, **kwargs):
            return io.BytesIO(response)
    monkeypatch.setattr(diagnostic, "build_opener", lambda *_: Opener())
    with pytest.raises(ValueError, match="no credential details logged") as error:
        diagnostic.request_claims()
    assert "secret-token" not in str(error.value) and "private-response" not in str(error.value)
    assert capsys.readouterr().out == ""


def test_request_http_error_is_sanitized_at_cli_boundary(monkeypatch, capsys):
    runner_environment(monkeypatch)
    class Opener:
        def open(self, *args, **kwargs):
            raise OSError("private auth header and response")
    monkeypatch.setattr(diagnostic, "build_opener", lambda *_: Opener())
    with pytest.raises(SystemExit) as error:
        diagnostic.main()
    assert error.value.code == 1
    output = capsys.readouterr()
    assert "private auth" not in output.err and "Traceback" not in output.err
    assert output.out == ""


def test_report_prints_only_selected_safe_fields(monkeypatch, capsys):
    token = synthetic_token(claims())
    data = claims() | {"sub": token, "secret": "never-print", "ref": "bad\n::warning::oops"}
    assert not diagnostic.report(data, POLICY)
    output = capsys.readouterr().out
    assert token not in output and "never-print" not in output
    assert "\n::warning::" not in output


@pytest.mark.parametrize("setting,value", [("WIF_PROVIDER", "wrong-provider"), ("CI_TARGET_ENV", "prod"),
    ("ACTIONS_ID_TOKEN_REQUEST_TOKEN", ""), ("ACTIONS_ID_TOKEN_REQUEST_URL", "https://evil.example/token"),
    ("ACTIONS_ID_TOKEN_REQUEST_URL", "http://run.actions.githubusercontent.com/token")])
def test_request_guard_fails_before_request_for_wrong_provider_target_or_endpoint(monkeypatch, setting, value):
    runner_environment(monkeypatch)
    monkeypatch.setenv(setting, value)
    monkeypatch.setattr(diagnostic, "build_opener", lambda *_: pytest.fail("must not request token"))
    with pytest.raises(ValueError):
        diagnostic.request_claims()


def test_temporary_step_is_dev_only_immediately_before_auth_and_can_be_disabled():
    wf = workflow("delivery.yml")
    steps = wf["jobs"]["dev"]["steps"]
    index = next(i for i,s in enumerate(steps) if s.get("id") == "auth")
    assert steps[index-1]["run"] == ".venv/bin/python -m scripts.gcp.oidc_diagnostic"
    assert steps[index-1]["if"] == "vars.WIF_DIAGNOSTICS != 'false'"
    for job in (wf["jobs"]["prod"], workflow("ci.yml")["jobs"]["checks"]):
        assert not any("oidc_diagnostic" in s.get("run", "") for s in job["steps"])


def test_terraform_dev_contract_uses_all_same_fields_and_keeps_mapping_and_prod_branch():
    text = Path("infra/gcp/github-actions/main.tf").read_text(encoding="utf-8")
    dev = text.split('attribute_condition = each.key == "dev" ? join',1)[1].split(']) : join',1)[0]
    assert 'jsondecode(file("${path.module}/dev-oidc-policy.json"))' in text
    for key in POLICY:
        assert "local.dev_oidc." + key in dev
    for name in ("sub", "environment", "repository_id", "repository_owner_id"):
        assert '"assertion.' + name + '"' in text  # Unchanged raw-claim mappings.
    for name in ("repository", "event_name", "ref", "workflow_ref"):
        assert '"attribute.' + name + '"' in text and '"assertion.' + name + '"' in text
    assert '"assertion.sub == \'repo:${local.repository}:environment:${local.gh_env[each.key]}\'"' in text
