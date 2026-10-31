"""Offline generation, wire snapshots and source inclusion regression gates."""
import json
import os
import subprocess
import sys

from scripts.export_openapi import OUTPUT, ROOT, schema_text
from scripts.export_api_fixtures import OUTPUT as FIXTURES, fixture_text


def test_schema_is_deterministic_and_committed(monkeypatch):
    from app.db import Database
    from app.document_studio.repository import JsonRepository
    import socket

    def forbidden(*args, **kwargs):
        raise AssertionError("Schema export must not initialize storage or connect")

    monkeypatch.setattr(Database, "initialize", forbidden)
    monkeypatch.setattr(JsonRepository, "initialize", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    assert schema_text() == schema_text() == OUTPUT.read_text(encoding="utf-8")
    schema = json.loads(schema_text())
    assert "/internal/jobs/{trip_id}" not in schema["paths"]
    assert "/app/{path}" not in schema["paths"]
    assert schema["paths"]["/api/trips"]["post"]["responses"]["202"]["content"]["application/json"]["schema"]["$ref"].endswith("/TripAccepted")
    assert schema["paths"]["/api/document-studio/access"]["get"]["responses"]["200"]["content"]["application/json"]["schema"] == {}


def test_export_is_safe_on_fresh_import_with_hostile_environment(tmp_path):
    # A subprocess proves isolation BEFORE main's module-level composition.
    env = dict(os.environ, CLOUD_FEATURE_MODE="cloud_demo", K_SERVICE="wrong-service", PLANNING_MODE="live",
               APP_ENV="prod", DATABASE_PATH=str(tmp_path / "real.sqlite"),
               DOCUMENT_STUDIO_DATA_PATH=str(tmp_path / "real-documents"), OPENAI_API_KEY="synthetic-forbidden")
    code = """
import socket
from app.db import Database
from app.document_studio.repository import JsonRepository
def forbidden(*a, **kw):
    raise AssertionError('storage or network touched')
socket.socket.connect = forbidden
Database.initialize = forbidden
JsonRepository.initialize = forbidden
from scripts.export_openapi import schema_text
assert '/api/trips' in schema_text()
"""
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, check=True, capture_output=True)
    assert not (tmp_path / "real.sqlite").exists()
    assert not (tmp_path / "real-documents").exists()


def test_schema_check_fails_on_drift_without_overwriting(tmp_path):
    target = tmp_path / "schema.json"
    target.write_text("{}\n", encoding="utf-8")
    result = subprocess.run([sys.executable, "-m", "scripts.export_openapi", "--check", "--output", str(target)], cwd=ROOT, capture_output=True)
    assert result.returncode == 1 and b"OpenAPI drift" in result.stderr
    assert target.read_text() == "{}\n"


def test_synthetic_wire_fixture_matches_real_fastapi():
    assert fixture_text() == FIXTURES.read_text(encoding="utf-8")


def test_local_planner_does_not_promise_cloud_create_idempotency():
    from fastapi.testclient import TestClient
    from scripts.export_openapi import isolated_app

    with isolated_app() as app, TestClient(app) as client:
        headers = {"Idempotency-Key": "00000000-0000-4000-8000-000000000001"}
        first = client.post("/api/trips", json={"text": "Synthetic request"}, headers=headers)
        second = client.post("/api/trips", json={"text": "Synthetic request"}, headers=headers)
        assert first.status_code == second.status_code == 202
        assert first.json()["trip_id"] != second.json()["trip_id"]


def test_ci_checks_both_schema_and_types():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()
    assert "python -m scripts.export_openapi --check" in workflow
    assert "npm --prefix frontend run api:check" in workflow
