"""Offline destructive-plan review boundaries; all policies/plans are synthetic."""
import copy
import json
from pathlib import Path

import pytest

from scripts.gcp import legacy_builder_plan as review

ROOT = Path(__file__).resolve().parents[1]


def removal_plan():
    return {"format_version": "1.2", "errored": False, "complete": True,
            "resource_changes": [{"address": review.ADDRESS, "mode": "managed",
                                  "type": "google_project_iam_member",
                                  "provider_name": "registry.terraform.io/hashicorp/google",
                                  "change": {"actions": ["delete"], "after": None,
                                             "before": {"project": "tripse-ai", "role": review.ROLE,
                                                        "member": review.MEMBER, "condition": []}}}]}


def test_expected_plan_is_reviewable_but_never_authorizes_apply():
    result = review.validate_plan(removal_plan())
    assert result["member"] == review.MEMBER
    assert result["operator_approval_required"] is True and result["applied"] is False


@pytest.mark.parametrize("attack", ["empty", "additional_grant", "dedicated_builder", "compute_default", "service_agent", "wrong_project", "wrong_role", "conditional", "authoritative_binding", "wrong_provider", "create", "update", "replace", "import", "move", "unknown", "drift", "deferred", "incomplete", "errored", "outputs", "unsupported_version", "malformed_boolean", "missing_after", "malformed_condition", "not_applyable"])
def test_missing_excessive_or_wrong_iam_changes_fail_closed(attack):
    plan = removal_plan(); resource = plan["resource_changes"][0]; change = resource["change"]
    if attack == "empty": plan["resource_changes"] = []
    if attack == "additional_grant": plan["resource_changes"].append(copy.deepcopy(resource))
    if attack == "dedicated_builder": change["before"]["member"] = "serviceAccount:tripse-ai-build@tripse-ai.iam.gserviceaccount.com"
    if attack == "compute_default": change["before"]["member"] = "serviceAccount:690165197462-compute@developer.gserviceaccount.com"
    if attack == "service_agent": change["before"]["member"] = "serviceAccount:service-690165197462@gcp-sa-cloudbuild.iam.gserviceaccount.com"
    if attack == "wrong_project": change["before"]["project"] = "other-project"
    if attack == "wrong_role": change["before"]["role"] = "roles/cloudbuild.serviceAgent"
    if attack == "conditional": change["before"]["condition"] = [{"expression": "true"}]
    if attack == "authoritative_binding": resource["type"] = "google_project_iam_binding"
    if attack == "wrong_provider": resource["provider_name"] = "untrusted/provider"
    if attack in {"create", "update"}: change["actions"] = [attack]
    if attack == "replace": change["actions"] = ["delete", "create"]
    if attack == "import": change["importing"] = {"id": "synthetic"}
    if attack == "move": resource["previous_address"] = "other.address"
    if attack == "unknown": change["after_unknown"] = {"member": True}
    if attack == "drift": plan["resource_drift"] = [resource]
    if attack == "deferred": plan["deferred_changes"] = [resource]
    if attack == "incomplete": plan["complete"] = False
    if attack == "errored": plan["errored"] = True
    if attack == "outputs": plan["output_changes"] = {"unexpected": {"actions": ["create"]}}
    if attack == "unsupported_version": plan["format_version"] = "99.0"
    if attack == "malformed_boolean": plan["errored"] = "false"
    if attack == "missing_after": change.pop("after")
    if attack == "malformed_condition": change["before"]["condition"] = {}
    if attack == "not_applyable": plan["applyable"] = False
    with pytest.raises(ValueError): review.validate_plan(plan)


def test_duplicate_json_fields_cannot_hide_a_grant():
    with pytest.raises(ValueError, match="Duplicate"):
        json.loads('{"resource_changes":[],"resource_changes":[]}', object_pairs_hook=review.unique_object)


def test_cleanup_module_is_isolated_and_only_targets_numeric_legacy_member():
    source = (ROOT / "infra/gcp/legacy-default-builder-cleanup/main.tf").read_text()
    assert source.count('resource "') == 1
    assert 'resource "google_project_iam_member" "legacy_default_worker"' in source
    assert 'default     = false' in source
    assert 'var.retain_legacy_default_worker_grant ? 1 : 0' in source
    assert 'member  = "' + review.MEMBER + '"' in source
    assert 'role    = "' + review.ROLE + '"' in source
    assert 'backend "' not in source
    assert 'google_project_iam_policy' not in source and 'google_project_iam_binding' not in source
