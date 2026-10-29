"""Offline review guard for the one-member legacy worker cleanup plan. Never applies."""
import argparse
import json
from pathlib import Path

ADDRESS = "google_project_iam_member.legacy_default_worker[0]"
MEMBER = "serviceAccount:690165197462@cloudbuild.gserviceaccount.com"
ROLE = "roles/cloudbuild.builds.builder"


def validate_plan(plan):
    """A safety check, not proof of current IAM or authorization to execute a plan."""
    if (not isinstance(plan, dict) or plan.get("format_version") != "1.2"
        or ("errored" in plan and type(plan["errored"]) is not bool)
        or ("complete" in plan and type(plan["complete"]) is not bool)
        or ("applyable" in plan and plan["applyable"] is not True)
        or plan.get("errored") is True or plan.get("complete") is False
        or plan.get("resource_drift") or plan.get("deferred_changes")):
        raise ValueError("Unsupported, incomplete or drifted cleanup plan")
    changes = plan.get("resource_changes")
    if not isinstance(changes, list) or len(changes) != 1:
        raise ValueError("Cleanup must contain exactly one resource change")
    resource = changes[0]
    if (not isinstance(resource, dict) or resource.get("address") != ADDRESS
        or resource.get("mode") != "managed" or resource.get("type") != "google_project_iam_member"
        or resource.get("provider_name") != "registry.terraform.io/hashicorp/google"):
        raise ValueError("Unexpected cleanup resource identity")
    change = resource.get("change")
    if (not isinstance(change, dict) or change.get("actions") != ["delete"]
        or "after" not in change or change.get("after") is not None or change.get("after_unknown")
        or change.get("importing") or resource.get("previous_address")):
        raise ValueError("Only removal of the existing imported member is allowed")
    before = change.get("before")
    if (not isinstance(before, dict) or before.get("project") != "tripse-ai"
        or before.get("role") != ROLE or before.get("member") != MEMBER
        or before.get("condition") not in (None, [])):
        raise ValueError("Cleanup target differs from the unconditional reviewed grant")
    if plan.get("output_changes"):
        raise ValueError("Unexpected output changes in isolated cleanup plan")
    return {"review": "expected_single_member_removal", "address": ADDRESS,
            "project": "tripse-ai", "member": MEMBER, "role": ROLE,
            "operator_approval_required": True, "applied": False}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate cleanup plan field")
        result[key] = value
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-json", type=Path, required=True)
    args = parser.parse_args()
    try:
        plan = json.loads(args.plan_json.read_text(encoding="utf-8-sig"), object_pairs_hook=unique_object)
        result = validate_plan(plan)
    except (ValueError, OSError, TypeError):
        parser.exit(2, "Cleanup plan rejected; inspect the reviewed plan locally. No action executed.\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
