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


def test_pinned_builder_and_official_python_keep_runtime_contract():
    lines = instructions()
    from scripts.gcp.frontend_build import NODE_IMAGE, PYTHON_IMAGE
    assert [line for line in lines if line.startswith("FROM ")] == [f"FROM {NODE_IMAGE} AS frontend-build", f"FROM {PYTHON_IMAGE}"]
    assert "RUN npm run build" in lines
    assert 'RUN test "$(node --version)" = "v$(tr -d \'\\r\\n\' < .nvmrc)" && npm ci' in lines
    assert "RUN pip install --no-cache-dir -r requirements.txt" in lines
    assert lines.index("COPY requirements.txt .") < lines.index("RUN pip install --no-cache-dir -r requirements.txt") < lines.index("COPY app ./app")
    cmd = json.loads(next(line[4:] for line in lines if line.startswith("CMD ")))
    assert cmd == ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--timeout-graceful-shutdown", "8"]
    assert not any(line.startswith(("ENTRYPOINT", "USER", "VOLUME", "ADD")) for line in lines)
    assert "DATABASE_PATH=/data/tripse.sqlite3" in (ROOT / "Dockerfile").read_text()


def test_only_required_runtime_inputs_are_copied_and_allowlisted():
    copies = [line for line in instructions() if line.startswith("COPY ")]
    assert copies == ["COPY frontend/package.json frontend/package-lock.json frontend/.nvmrc ./",
        "COPY frontend/index.html frontend/tsconfig.json frontend/vite.config.ts ./", "COPY frontend/src ./src",
        "COPY requirements.txt .", "COPY app ./app", "COPY demo-fixtures/gt-v1 ./demo-fixtures/gt-v1",
        "COPY --from=frontend-build /build/frontend/dist ./app/spa_dist"]
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    committed = dict(source_files(sha))
    # FRONT-001B widens only commits declaring the versioned frontend recipe.
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
    assert {"frontend/*.tsbuildinfo"} <= patterns
    assert {"frontend/dist", "frontend/dist/**"} & patterns
    assert {"app/spa_dist", "app/spa_dist/**"} & patterns


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
