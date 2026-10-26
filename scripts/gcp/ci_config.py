"""Dependency-free checks run before package installation or cloud authentication."""
import json
import os
from scripts.gcp.deployment_contract import FIELDS, DEMO_FIELDS, DEMO_OPTIONAL_FIELDS

ENVIRONMENTS = {"dev": "development", "prod": "production"}
REQUIRED = ("DEPLOY_CONFIG_JSON", "EXPECTED_CLOUD_FEATURE_MODE", "WIF_PROVIDER",
            "DEPLOY_SERVICE_ACCOUNT", "CI_PROBE_ACCOUNT")


def identities(environment):
    return {
        "WIF_PROVIDER": "projects/690165197462/locations/global/workloadIdentityPools/tripse-github/providers/github-" + environment,
        "DEPLOY_SERVICE_ACCOUNT": f"tripse-ai-{environment}-ci-deploy@tripse-ai.iam.gserviceaccount.com",
        "CI_PROBE_ACCOUNT": f"tripse-ai-{environment}-ci-probe@tripse-ai.iam.gserviceaccount.com",
    }


def validate(environment, settings=None):
    if environment not in ENVIRONMENTS:
        raise ValueError("Invalid CI target environment")
    settings = os.environ if settings is None else settings
    name = ENVIRONMENTS[environment]
    for key in REQUIRED:
        if not isinstance(settings.get(key), str) or not settings[key].strip():
            template = f"{name}.cloud_demo.json.example"
            raise ValueError(f"Missing GitHub Environment variable: {key} ({name}). "
                             f"Configure it under Settings -> Environments -> {name} -> Environment variables. "
                             f"Use the reviewed {template} template after replacing placeholders.")
    try:
        values = json.loads(settings["DEPLOY_CONFIG_JSON"])
    except (ValueError, RecursionError):
        raise ValueError("DEPLOY_CONFIG_JSON is not valid JSON.") from None
    if not isinstance(values, dict) or any(not isinstance(k, str) or not isinstance(v, str)
            or any(c in k + v for c in "\r\n") for k, v in values.items()):
        raise ValueError("Invalid runtime schema: DEPLOY_CONFIG_JSON must be an object of single-line strings.")
    mode = settings["EXPECTED_CLOUD_FEATURE_MODE"]
    if mode not in {"readonly_demo", "cloud_demo"}:
        raise ValueError("Invalid runtime schema: EXPECTED_CLOUD_FEATURE_MODE must be explicitly cloud_demo or readonly_demo.")
    required = FIELDS | DEMO_FIELDS if mode == "cloud_demo" else FIELDS
    allowed = required | (DEMO_OPTIONAL_FIELDS if mode == "cloud_demo" else set())
    if not required <= values.keys() or values.keys() - allowed:
        # Unknown keys are deliberately not echoed (they may contain pasted secrets).
        raise ValueError("Invalid runtime schema: missing required or unknown/mode-inappropriate deployment fields. Review the environment template.")
    for key, expected in {"GCP_PROJECT_ID": "tripse-ai", "GCP_REGION": "europe-central2",
                          "GCP_SERVICE_NAME": f"tripse-ai-{environment}", "APP_ENV": environment,
                          "CLOUD_FEATURE_MODE": mode, "PLANNING_MODE": "mock"}.items():
        if values.get(key) != expected:
            raise ValueError(f"Invalid runtime schema: {key} does not match the reviewed CI target/mode.")
    if mode == "cloud_demo" and values["GCP_PUBLIC_ACCESS"] != "false":
        raise ValueError("Invalid runtime schema: cloud_demo requires GCP_PUBLIC_ACCESS=false.")
    if any("REPLACE" in v.upper() for v in values.values()):
        raise ValueError("Invalid runtime schema: replace template placeholders before bootstrap.")
    for key, expected in identities(environment).items():
        if settings[key] != expected:
            raise ValueError(f"Invalid GitHub Environment variable: {key} ({name}); use the reviewed Terraform output for this environment.")
    return values


def failure_summary(message):
    path = os.getenv("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as stream:
            stream.write("## Configuration blocked before cloud authentication\n\n" + message + "\n\n"
                         "Run `python -m scripts.gcp.bootstrap check --environment development` "
                         "(or production). See docs/GITHUB_CICD.md. No deployment was attempted by this check.\n")
