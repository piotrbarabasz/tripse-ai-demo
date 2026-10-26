"""Operator-invoked READ-ONLY GitHub/GCP checks and local nonsecret config preparation.

Never creates environments, writes GitHub variables, applies Terraform or deploys.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch

from scripts.gcp.ci_config import ENVIRONMENTS, REQUIRED, identities, validate

REPO = "piotrbarabasz/tripse-ai-demo"


def command(args):
    try:
        result = subprocess.run(args, capture_output=True, check=False)
    except OSError:
        raise ValueError("Required operator CLI unavailable; install gh/gcloud as appropriate.") from None
    if result.returncode:
        if args[0] == "gh":
            raise ValueError("GitHub configuration unavailable: verify gh authentication and repository Environment/variable read visibility; no settings changed. See docs/CICD_BOOTSTRAP.md.")
        raise ValueError("GCP bootstrap MISSING/INACCESSIBLE: verify operator authentication and metadata IAM; review infra/gcp/github-actions and private app resources via docs/CICD_BOOTSTRAP.md. No settings changed.")
    try:
        return json.loads(result.stdout)
    except ValueError:
        raise ValueError("Operator API returned invalid metadata; no settings were changed.") from None


def full_validate(environment, settings):
    validate(environment, settings)
    from scripts.gcp.ci import config_from_environment
    with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, settings):
        return config_from_environment(environment, Path(directory))


def prepare(environment, source, output, mode):
    # All inputs are nonsecret deployment contract values, never key material.
    try:
        data = json.loads(source.read_text(encoding="utf-8-sig"))
    except (ValueError, OSError):
        raise ValueError("Input config is unavailable or is not valid JSON.") from None
    settings = identities(environment) | {"DEPLOY_CONFIG_JSON": json.dumps(data, separators=(",", ":")),
                                         "EXPECTED_CLOUD_FEATURE_MODE": mode}
    full_validate(environment, settings)
    # Exclusive creation: never silently overwrite previously reviewed config.
    with output.open("x", encoding="utf-8") as stream:
        json.dump(settings, stream, indent=2)
    print(f"READY: validated nonsecret bundle for {ENVIRONMENTS[environment]}; local file created. No GitHub/GCP settings written.")


def check(environment, *, gcp=False):
    name = ENVIRONMENTS[environment]
    base = f"repos/{REPO}"
    environments = command(["gh", "api", "--paginate", "--slurp", base + "/environments?per_page=100"])
    if name not in {e["name"] for page in environments for e in page.get("environments", [])}:
        print(f"MISSING: GitHub Environment {name}. Create Settings -> Environments -> {name}.")
        return False
    pages = command(["gh", "api", "--paginate", "--slurp", base + f"/environments/{name}/variables?per_page=100"])
    settings = {v["name"]: v["value"] for page in pages for v in page.get("variables", []) if v.get("name") in REQUIRED}
    missing = [k for k in REQUIRED if not settings.get(k, "").strip()]
    if missing:
        for key in missing:
            print(f"MISSING: {key} ({name}). Settings -> Environments -> {name} -> Environment variables.")
        return False
    try:
        full_validate(environment, settings)
    except ValueError as exc:
        print("INVALID: " + str(exc))
        return False
    print(f"READY: {name} variable names, values, runtime schema and expected identity names validated (values hidden).")
    if not gcp:
        print("MISSING VERIFICATION: GCP bootstrap not inspected. Use --gcp for read-only provider/account checks; app resources/IAP and real runner acceptance remain separate gates.")
        return True
    provider = command(["gcloud", "iam", "workload-identity-pools", "providers", "describe", f"github-{environment}",
                        "--workload-identity-pool=tripse-github", "--location=global", "--project=tripse-ai", "--format=json"])
    if provider.get("name") != identities(environment)["WIF_PROVIDER"] or provider.get("state") != "ACTIVE" or provider.get("disabled"):
        print(f"INVALID: {name} WIF provider name/state. Review infra/gcp/github-actions plan; do not create keys.")
        return False
    # Presence alone is not proof that the actual trust/IAM policy is correct.
    for account in (settings["DEPLOY_SERVICE_ACCOUNT"], settings["CI_PROBE_ACCOUNT"],
                    f"tripse-ai-{environment}@tripse-ai.iam.gserviceaccount.com"):
        result = command(["gcloud", "iam", "service-accounts", "describe", account, "--project=tripse-ai", "--format=json"])
        if result.get("email") != account or result.get("disabled"):
            print(f"INVALID: {name} required service account name/state.")
            return False
    print(f"READY: {name} GCP provider and deploy/probe/runtime accounts exist and are enabled.")
    print("MISSING VERIFICATION: review Terraform trust/IAM drift and bootstrap private GCS, Firestore, Tasks, direct IAP/OAuth and app/probe permissions via docs/DEPLOY_GCP.md. CI performs read-only prerequisite checks before build/deploy; live WIF/IAP acceptance still required.")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    inspect = sub.add_parser("check")
    inspect.add_argument("--gcp", action="store_true")
    generate = sub.add_parser("prepare")
    generate.add_argument("--input", type=Path, required=True)
    generate.add_argument("--output", type=Path, required=True)
    generate.add_argument("--mode", choices=["cloud_demo", "readonly_demo"], required=True)
    for p in (inspect, generate):
        p.add_argument("--environment", choices=list(ENVIRONMENTS.values()), required=True)
    args = parser.parse_args()
    environment = {v: k for k, v in ENVIRONMENTS.items()}[args.environment]
    try:
        if args.action == "prepare":
            prepare(environment, args.input, args.output, args.mode)
        elif not check(environment, gcp=args.gcp):
            raise SystemExit(1)
    except (ValueError, OSError) as exc:
        # Never print CLI stderr or config contents, including JSON parse snippets.
        message = str(exc) if isinstance(exc, ValueError) else "Local output unavailable/already exists; choose a new file."
        print("INVALID/MISSING: " + message)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
