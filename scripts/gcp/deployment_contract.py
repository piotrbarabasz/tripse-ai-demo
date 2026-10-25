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
        return {key: self[key] for key in ("APP_ENV", "PLANNING_MODE", "CLOUD_FEATURE_MODE")} | {"EXPECTED_IMAGE_SHA": image_tag(sha)}


def load_config(path: Path, environment: str):
    values = {}
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        key, value = key.strip(), value.strip()
        # Error messages deliberately never include values or raw lines.
        if not sep or key not in FIELDS or key in values:
            raise ValueError(f"Invalid, unknown or duplicate field at line {number} in {path.name}")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if not value or any(c in value for c in "$`<>\\\r\n"):
            raise ValueError(f"Missing value or forbidden interpolation in {key}")
        values[key] = value
    if values.keys() != FIELDS:
        raise ValueError("Missing deployment fields: " + ", ".join(sorted(FIELDS-values.keys())))
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
        "PLANNING_MODE": "mock", "CLOUD_FEATURE_MODE": "readonly_demo",
        "GCP_MIN_INSTANCES": "0", "GCP_CPU": "1",
    }.items():
        if values[key] != expected:
            raise ValueError(f"Invalid {key} for {environment}")
    if values["GCP_PUBLIC_ACCESS"] not in {"true", "false"}:
        raise ValueError("GCP_PUBLIC_ACCESS must be true or false")
    if values["GCP_MAX_INSTANCES"] not in {"1", "2", "3"} or values["GCP_MEMORY"] not in {"512Mi", "1Gi"}:
        raise ValueError("Preview supports max 1..3 instances and 512Mi or 1Gi memory")
    return Config(values)


def load_pair(environment, config_dir=ROOT):
    configs = {name: load_config(config_dir / f".env.{name}", name) for name in ("dev", "prod")}
    for field in ("GCP_PROJECT_ID", "GCP_REGION", "GCP_ARTIFACT_REPO", "GCP_IMAGE_NAME"):
        if configs["dev"][field] != configs["prod"][field]:
            raise ValueError(f"DEV and PROD must share {field}; services and runtime configuration remain separate")
    return configs[environment]
