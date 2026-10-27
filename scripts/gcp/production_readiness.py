"""Read-only operator verification of production GitHub release protections."""
import argparse
import json
from pathlib import Path

from scripts.gcp.bootstrap import command, full_validate

BASE = "repos/piotrbarabasz/tripse-ai-demo"


def check():
    errors = []
    try:
        env = command(["gh", "api", BASE + "/environments/production"])
    except ValueError:
        return ["Production Environment missing or not readable; configure and review it first"]
    reviewers = [r for r in env.get("protection_rules", []) if r.get("type") == "required_reviewers"]
    if not any(not r.get("prevent_self_review", False) and
               any(v.get("type") == "User" and v.get("reviewer", {}).get("id") == 72949549
                   for v in r.get("reviewers", [])) for r in reviewers):
        errors.append("Require reviewer piotrbarabasz with self-review allowed, as explicitly selected")
    policy = env.get("deployment_branch_policy") or {}
    if policy.get("custom_branch_policies") is not True or policy.get("protected_branches") is not False:
        errors.append("Production must use custom deployment branch policies")
    try:
        branches = command(["gh", "api", BASE + "/environments/production/deployment-branch-policies?per_page=100"])
        if [(b.get("name"), b.get("type")) for b in branches.get("branch_policies", [])] != [("master", "branch")]:
            errors.append("Production deployment branch policy must be exactly branch master")
    except ValueError:
        errors.append("Production deployment branch policies missing or unreadable")
    try:
        branch = command(["gh", "api", BASE + "/branches/master/protection"])
        contexts = branch.get("required_status_checks") or {}
        names = set(contexts.get("contexts", [])) | {c.get("context") for c in contexts.get("checks", [])}
        if "Tests and offline contracts" not in names or contexts.get("strict") is not True:
            errors.append("Master must require strict PR CI check Tests and offline contracts")
        if not any(c.get("context") == "Tests and offline contracts" and c.get("app_id") == 15368 for c in contexts.get("checks", [])):
            errors.append("Required PR CI check must be pinned to the observed GitHub Actions App 15368")
        if branch.get("enforce_admins", {}).get("enabled") is not True:
            errors.append("Master protections must apply to administrators")
        if branch.get("required_pull_request_reviews") is None:
            errors.append("Master must require the PR path (single operator may use review count zero)")
        if branch.get("allow_force_pushes", {}).get("enabled") or branch.get("allow_deletions", {}).get("enabled"):
            errors.append("Master force-push/deletion must remain disabled")
    except ValueError:
        errors.append("Master branch protection missing or unreadable")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variables-file", type=Path)
    args = parser.parse_args()
    try:
        if args.variables_file:
            full_validate("prod", json.loads(args.variables_file.read_text(encoding="utf-8-sig")))
            print("Local production variables schema and identities PASS (values hidden)")
        errors = check()
    except (ValueError, OSError):
        raise SystemExit("Production check blocked: invalid/unavailable reviewed configuration; values suppressed") from None
    for error in errors:
        print("MISSING/INVALID: " + error)
    if errors:
        raise SystemExit(1)
    print("GitHub production API checks PASS. Manually verify admin-bypass is disabled in Settings -> Environments -> production; REST does not expose that setting here.")


if __name__ == "__main__":
    main()
