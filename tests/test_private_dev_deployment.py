"""Existing private DEV must retain security without SDK IAM reconciliation flags."""
import copy

import pytest

from scripts.gcp import deployment as d
from scripts.gcp.deployment_contract import Config
from tests.test_github_cicd import values, SHA, IMAGE_DIGEST, ORIGIN


@pytest.fixture
def private_dev(monkeypatch, tmp_path):
    config = Config(values(mode="cloud_demo"))
    existing = {"metadata": {"name": "tripse-ai-dev", "labels": d.LABELS | {"environment": "dev"},
                            "annotations": {"run.googleapis.com/iap-enabled": "true"}},
                "spec": {"template": {"spec": {"containers": [{"image": config.image + "@" + IMAGE_DIGEST}]}}}}
    agent = "serviceAccount:service-690165197462@gcp-sa-iap.iam.gserviceaccount.com"
    policy = {"etag": "unchanged", "version": 1, "bindings": [
        {"role": "roles/run.invoker", "members": [agent, "serviceAccount:tripse-ai-dev-ci-probe@tripse-ai.iam.gserviceaccount.com"]},
        {"role": "roles/run.admin", "members": ["serviceAccount:tripse-ai-dev-ci-deploy@tripse-ai.iam.gserviceaccount.com"]}]}
    calls = []

    def g(*args, **kwargs):
        calls.append(args)
        if args[:3] == ("run", "services", "list"):return [existing] if existing else []
        if args[:3] == ("run", "services", "get-iam-policy"):return copy.deepcopy(policy)
        if args[:2] == ("run", "deploy") or args[:3] == ("run", "services", "update-traffic"):return None
        pytest.fail("Unexpected operation, including IAM mutation: " + repr(args))
    g.config = config
    monkeypatch.setenv("GCP_SMOKE_ACCOUNT", "tripse-ai-dev-ci-probe@tripse-ai.iam.gserviceaccount.com")
    monkeypatch.setattr(d, "check_release_source", lambda _: {name: b"" for name in (
        "app/cloud_runtime.py", "app/cloud_access.py", "app/cloud_jobs.py", "app/document_studio/cloud_storage.py")})
    monkeypatch.setattr(d, "repository", lambda _: True)
    monkeypatch.setattr(d, "check_act_as", lambda *a: None)
    monkeypatch.setattr(d, "digest", lambda *a: IMAGE_DIGEST)
    monkeypatch.setattr(d, "deployed_state", lambda *a: {"url": ORIGIN})
    monkeypatch.setattr(d, "smoke", lambda *a, **kw: calls.append(("smoke", kw.get("private"))))
    monkeypatch.setattr(d, "publish", lambda *a: pytest.fail("Private DEV published"))
    monkeypatch.setattr(d, "ROOT", tmp_path)
    return g, existing, policy, calls


@pytest.mark.parametrize("explicit_invoker_check", [False, True])
def test_existing_private_dev_does_not_request_iam_policy_reconciliation(private_dev, explicit_invoker_check):
    g, existing, policy, calls = private_dev
    if explicit_invoker_check:
        existing["metadata"]["annotations"]["run.googleapis.com/invoker-iam-disabled"] = "false"
    original = copy.deepcopy((existing, policy))
    d.deploy(g, SHA)
    deploy = next(c for c in calls if c[:2] == ("run", "deploy"))
    # SDK 591.0.0's separate allow-unauthenticated and IAP policy handlers are
    # activated by these flags, not by --invoker-iam-check itself.
    assert not {"--iap", "--no-iap", "--allow-unauthenticated", "--no-allow-unauthenticated", "--public"} & set(deploy)
    assert "--invoker-iam-check" in deploy and "--no-invoker-iam-check" not in deploy
    assert "--image=" + g.config.image + "@" + IMAGE_DIGEST in deploy
    assert "--service-account=tripse-ai-dev@tripse-ai.iam.gserviceaccount.com" in deploy
    assert g.config.build_account == "tripse-ai-build@tripse-ai.iam.gserviceaccount.com"
    assert calls.index(next(c for c in calls if c[:3] == ("run", "services", "get-iam-policy"))) < calls.index(deploy)
    assert (existing, policy) == original
    assert ("smoke", True) in calls
    assert all(c[:3] in {("run", "services", "list"), ("run", "services", "get-iam-policy"),
                        ("run", "services", "update-traffic")} or c[:2] == ("run", "deploy")
               or c == ("smoke", True) for c in calls)


@pytest.mark.parametrize("attack", ["missing_service", "iap_disabled", "iap_absent", "invoker_disabled",
    "invoker_unknown", "missing_agent", "wrong_agent", "wrong_role", "conditional_agent", "allUsers",
    "allAuthenticatedUsers", "conditional_public", "public_config"])
def test_private_dev_fails_before_any_mutation_instead_of_repairing_security(private_dev, attack):
    g, existing, policy, calls = private_dev
    annotations = existing["metadata"]["annotations"]
    if attack == "missing_service":existing.clear()
    if attack == "iap_disabled":annotations["run.googleapis.com/iap-enabled"] = "false"
    if attack == "iap_absent":annotations.pop("run.googleapis.com/iap-enabled")
    if attack == "invoker_disabled":annotations["run.googleapis.com/invoker-iam-disabled"] = "true"
    if attack == "invoker_unknown":annotations["run.googleapis.com/invoker-iam-disabled"] = "unknown"
    if attack == "missing_agent":policy["bindings"].pop(0)
    if attack == "wrong_agent":policy["bindings"][0]["members"][0] = "serviceAccount:service-123456789@gcp-sa-iap.iam.gserviceaccount.com"
    if attack == "wrong_role":policy["bindings"][0]["role"] = "roles/run.viewer"
    if attack == "conditional_agent":policy["bindings"][0]["condition"] = {"expression": "true", "title": "conditional"}
    if attack in {"allUsers", "allAuthenticatedUsers", "conditional_public"}:
        binding = {"role": "roles/run.invoker", "members": ["allAuthenticatedUsers" if attack == "allAuthenticatedUsers" else "allUsers"]}
        if attack == "conditional_public":binding["condition"] = {"expression": "true", "title": "conditional"}
        policy["bindings"].append(binding)
    if attack == "public_config":g.config.values["GCP_PUBLIC_ACCESS"] = "true"
    with pytest.raises(ValueError):d.deploy(g, SHA)
    assert all(c[:3] in {("run", "services", "list"), ("run", "services", "get-iam-policy")} for c in calls)


def test_private_dev_still_propagates_post_deployment_smoke_failure(private_dev, monkeypatch):
    g, _, _, calls = private_dev
    def fail(*a, **kw):raise ValueError("synthetic private smoke failure")
    monkeypatch.setattr(d, "smoke", fail)
    with pytest.raises(ValueError, match="private smoke failure"):d.deploy(g, SHA)
    assert any(c[:2] == ("run", "deploy") for c in calls)
    assert not any("--no-invoker-iam-check" in c or "--iap" in c for c in calls)
