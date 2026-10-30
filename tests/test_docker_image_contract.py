"""CI-002 static gates; these do not claim to build or execute a Linux image."""
import json
from pathlib import Path
import re
import subprocess

import pytest
import yaml

from scripts.gcp.deployment import source_files

ROOT = Path(__file__).resolve().parents[1]


def instructions():
    return [line.strip() for line in (ROOT / "Dockerfile").read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


def test_pinned_official_python_single_stage_keeps_runtime_contract():
    lines = instructions()
    assert re.fullmatch(r"FROM python:3\.12-slim@sha256:[a-f0-9]{64}", lines[0])
    assert sum(line.startswith("FROM ") for line in lines) == 1
    assert "RUN pip install --no-cache-dir -r requirements.txt" in lines
    assert lines.index("COPY requirements.txt .") < lines.index("RUN pip install --no-cache-dir -r requirements.txt") < lines.index("COPY app ./app")
    cmd = json.loads(next(line[4:] for line in lines if line.startswith("CMD ")))
    assert cmd == ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--timeout-graceful-shutdown", "8"]
    assert not any(line.startswith(("ENTRYPOINT", "USER", "VOLUME", "ADD")) for line in lines)
    assert "DATABASE_PATH=/data/tripse.sqlite3" in (ROOT / "Dockerfile").read_text()


def test_only_required_runtime_inputs_are_copied_and_allowlisted():
    copies = [line for line in instructions() if line.startswith("COPY ")]
    assert copies == ["COPY requirements.txt .", "COPY app ./app", "COPY demo-fixtures/gt-v1 ./demo-fixtures/gt-v1"]
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    committed = dict(source_files(sha))
    # CI-002 doesn't require widening the source allowlist or injecting new files.
    assert "requirements.txt" in committed and "app/main.py" in committed
    assert "demo-fixtures/gt-v1/examples.json" in committed
    assert all((ROOT / name).is_file() for name in committed)
    assert not any(name.startswith(("tests/", "local-data/", "scripts/", "docs/")) for name in committed)


@pytest.mark.parametrize("filename", [".dockerignore", ".gcloudignore"])
def test_context_excludes_credentials_data_and_local_outputs(filename):
    patterns = set((ROOT / filename).read_text().splitlines())
    assert {".git", ".env", ".env.*", "**/.env", "**/.env.*", "**/*.pem", "**/*.key",
        "**/*.p12", "**/*.pfx", "**/*.pyc", "**/*.log", ".tmp", ".worktrees", "node_modules"} <= patterns
    assert {"local-data", "local-data/**"} & patterns
    assert {"data", "data/**"} & patterns
    assert {"tests", "tests/**"} & patterns
    assert not any("!" in line for line in patterns if not line.startswith("#"))


def test_api_worker_share_existing_storage_and_worker_command():
    compose = yaml.safe_load((ROOT / "compose.yaml").read_text())
    api, worker = (compose["services"][key] for key in ("api", "worker"))
    assert api["build"] == worker["build"] == "."
    assert worker["command"] == ["python", "-m", "app.worker"]
    assert api["environment"]["DATABASE_PATH"] == worker["environment"]["DATABASE_PATH"] == "/data/tripse.sqlite3"
    assert "tripse_data:/data" in api["volumes"] and "tripse_data:/data" in worker["volumes"]
    assert "./local-data/document-studio:/app/local-data/document-studio" in api["volumes"]
    assert api["environment"]["DOCUMENT_STUDIO_DATA_PATH"] == "/app/local-data/document-studio"
    assert not any("user" in service for service in (api, worker))
    assert not any("chmod" in line or "chown" in line for line in instructions())
