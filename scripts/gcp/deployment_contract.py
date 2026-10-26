"""Strict non-secret deployment contract. No shell evaluation of dotenv files."""
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIELDS = {
    "GCP_PROJECT_ID", "GCP_REGION", "GCP_ARTIFACT_REPO", "GCP_IMAGE_NAME", "GCP_SERVICE_NAME",
    "APP_ENV", "PLANNING_MODE", "CLOUD_FEATURE_MODE", "GCP_PUBLIC_ACCESS", "GCP_MIN_INSTANCES",
    "GCP_MAX_INSTANCES", "GCP_CPU", "GCP_MEMORY",
}
DEMO_FIELDS = {
    "GCP_PROJECT_NUMBER", "PUBLIC_BASE_URL", "IAP_OAUTH_CLIENT_ID", "DEMO_EDITORS", "DEMO_READERS",
    "GCP_DOCUMENT_BUCKET", "GCP_FIRESTORE_DATABASE", "GCP_TASK_QUEUE", "GCP_TASK_ACCOUNT",
}
DEMO_OPTIONAL_FIELDS = {"GCP_BROWSER_MAPS_SECRET", "GOOGLE_MAPS_MAP_ID"}


def image_tag(value):
    if not re.fullmatch(r"[0-9a-f]{40}", value or ""):
        raise ValueError("ImageTag must be a full, lowercase 40-character commit SHA; latest is forbidden")
    return value


@dataclass(frozen=True)
class Config:
    values: dict

    def __getitem__(self, key):
        return self.values[key]

    @property
    def image(self):
        return f'{self["GCP_REGION"]}-docker.pkg.dev/{self["GCP_PROJECT_ID"]}/{self["GCP_ARTIFACT_REPO"]}/{self["GCP_IMAGE_NAME"]}'

    @property
    def runtime_account(self):
        return f'tripse-ai-{self["APP_ENV"]}@{self["GCP_PROJECT_ID"]}.iam.gserviceaccount.com'

    @property
    def build_account(self):
        return f'tripse-ai-build@{self["GCP_PROJECT_ID"]}.iam.gserviceaccount.com'

    def runtime(self, sha):
        values = {key: self[key] for key in ("APP_ENV", "PLANNING_MODE", "CLOUD_FEATURE_MODE")} | {"EXPECTED_IMAGE_SHA": image_tag(sha)}
        if self["CLOUD_FEATURE_MODE"] == "cloud_demo":
            values.update({key: self[key] for key in DEMO_FIELDS | {"GCP_PROJECT_ID"}})
            if "GOOGLE_MAPS_MAP_ID" in self.values:
                values["GOOGLE_MAPS_MAP_ID"] = self["GOOGLE_MAPS_MAP_ID"]
        return values

    def demo_settings(self):
        """Validate the runtime contract in isolation without mutating process env."""
        from app.cloud_preview import CloudSettings
        from app.cloud_runtime import DemoSettings
        return DemoSettings.from_env(CloudSettings(self["APP_ENV"], "a" * 40, self["GCP_SERVICE_NAME"], "cloud_demo"), self.runtime("a" * 40))


def load_config(path: Path, environment: str):
    values = {}
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        key, value = key.strip(), value.strip()
        # Error messages deliberately never include values or raw lines.
        if not sep or key not in FIELDS | DEMO_FIELDS | DEMO_OPTIONAL_FIELDS or key in values:
            raise ValueError(f"Invalid, unknown or duplicate field at line {number} in {path.name}")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if (not value and key != "DEMO_READERS") or any(c in value for c in "$`<>\\\r\n"):
            raise ValueError(f"Missing value or forbidden interpolation in {key}")
        values[key] = value
    required = FIELDS | DEMO_FIELDS if values.get("CLOUD_FEATURE_MODE") == "cloud_demo" else FIELDS
    allowed = required | (DEMO_OPTIONAL_FIELDS if values.get("CLOUD_FEATURE_MODE") == "cloud_demo" else set())
    if not required <= values.keys() or values.keys() - allowed:
        raise ValueError("Missing or mode-inappropriate deployment fields: " + ", ".join(sorted(required ^ values.keys())))
    checks = {
        "GCP_PROJECT_ID": r"[a-z][a-z0-9-]{4,28}[a-z0-9]",
        "GCP_REGION": r"[a-z]+-[a-z]+[0-9]",
        "GCP_ARTIFACT_REPO": r"[a-z][a-z0-9-]{0,62}",
        "GCP_IMAGE_NAME": r"[a-z][a-z0-9-]{0,62}",
    }
    for key, pattern in checks.items():
        if not re.fullmatch(pattern, values[key]):
            raise ValueError(f"Invalid {key}")
    for key, expected in {
        "APP_ENV": environment, "GCP_SERVICE_NAME": f"tripse-ai-{environment}",
        "PLANNING_MODE": "mock",
        "GCP_MIN_INSTANCES": "0", "GCP_CPU": "1",
    }.items():
        if values[key] != expected:
            raise ValueError(f"Invalid {key} for {environment}")
    if values["GCP_PUBLIC_ACCESS"] not in {"true", "false"}:
        raise ValueError("GCP_PUBLIC_ACCESS must be true or false")
    if values["GCP_MAX_INSTANCES"] not in {"1", "2", "3"} or values["GCP_MEMORY"] not in {"512Mi", "1Gi"}:
        raise ValueError("Preview supports max 1..3 instances and 512Mi or 1Gi memory")
    config = Config(values)
    if values["CLOUD_FEATURE_MODE"] not in {"readonly_demo", "cloud_demo"}:
        raise ValueError("Invalid CLOUD_FEATURE_MODE")
    if values["CLOUD_FEATURE_MODE"] == "cloud_demo":
        if values["GCP_PUBLIC_ACCESS"] != "false" or values["GCP_REGION"] != "europe-central2":
            raise ValueError("cloud_demo requires private access in europe-central2")
        config.demo_settings()
        if "GCP_BROWSER_MAPS_SECRET" in values and not re.fullmatch(
            rf'projects/{values["GCP_PROJECT_ID"]}/secrets/tripse-ai-{environment}-maps-browser/versions/[1-9][0-9]*',
            values["GCP_BROWSER_MAPS_SECRET"],
        ):
            raise ValueError("Browser key must reference a pinned environment-specific Secret Manager version")
        if "GOOGLE_MAPS_MAP_ID" in values and not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", values["GOOGLE_MAPS_MAP_ID"]):
            raise ValueError("Invalid GOOGLE_MAPS_MAP_ID")
    return config


def load_pair(environment, config_dir=ROOT):
    configs = {name: load_config(config_dir / f".env.{name}", name) for name in ("dev", "prod")}
    for field in ("GCP_PROJECT_ID", "GCP_REGION", "GCP_ARTIFACT_REPO", "GCP_IMAGE_NAME"):
        if configs["dev"][field] != configs["prod"][field]:
            raise ValueError(f"DEV and PROD must share {field}; services and runtime configuration remain separate")
    if all(configs[name]["CLOUD_FEATURE_MODE"] == "cloud_demo" for name in configs):
        for field in ("GCP_DOCUMENT_BUCKET", "GCP_FIRESTORE_DATABASE", "GCP_TASK_QUEUE", "GCP_TASK_ACCOUNT", "PUBLIC_BASE_URL"):
            if configs["dev"][field] == configs["prod"][field]:
                raise ValueError(f"DEV and PROD must not share {field}")
    return configs[environment]
