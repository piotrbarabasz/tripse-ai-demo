"""Minimal trusted workspace hint; existing routing/auth remains authoritative."""
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from test_cloud_demo import cloud_demo, ORIGIN

PATH = "/api/workspace/capabilities"


@pytest.mark.parametrize("mode", ["mock", "live"])
def test_local_capabilities_and_minimal_wire(tmp_path, monkeypatch, mode):
    monkeypatch.setenv("CLOUD_FEATURE_MODE", "local")
    monkeypatch.setenv("PLANNING_MODE", mode)
    monkeypatch.delenv("K_SERVICE", raising=False)
    app = create_app(tmp_path / "db", document_data_path=tmp_path / "docs")
    with TestClient(app, base_url="http://localhost", client=("127.0.0.1", 50000)) as client:
        response = client.get(PATH)
        assert response.status_code == 200
        assert response.json() == {"runtime_mode": "local", "can_create_trip": True, "planning_mode": mode}
        assert response.headers["cache-control"] == "private, no-store"
        assert client.post(PATH).status_code == 405
        monkeypatch.setenv("PLANNING_MODE", "invalid")
        assert client.get(PATH).status_code == 503


@pytest.mark.parametrize("options,headers", [
    ({"client": ("203.0.113.2", 1)}, {}),
    ({"base_url": "http://evil.example"}, {}),
    ({}, {"Origin": "http://evil.example"}),
    ({}, {"Sec-Fetch-Site": "cross-site"}),
    ({}, {"X-Forwarded-For": "127.0.0.1"}),
])
def test_local_guard_is_not_bypassed(tmp_path, monkeypatch, options, headers):
    monkeypatch.setenv("CLOUD_FEATURE_MODE", "local")
    monkeypatch.delenv("K_SERVICE", raising=False)
    app = create_app(tmp_path / "db", document_data_path=tmp_path / "docs")
    with TestClient(app, **({"base_url": "http://localhost", "client": ("127.0.0.1", 1)} | options)) as client:
        assert client.get(PATH, headers=headers).status_code == 403


@pytest.mark.parametrize("identity,can_create", [("editor", True), ("reader", False)])
def test_cloud_capability_uses_verified_server_permissions(cloud_demo, identity, can_create):
    with cloud_demo.client(identity) as client:
        response = client.get(PATH, headers={"x-role": "editor", "x-can-edit": "true"})
        assert response.status_code == 200
        assert response.json() == {"runtime_mode": "cloud_demo", "planning_mode": "mock", "can_create_trip": can_create}
        assert response.headers["cache-control"] == "private, no-store"
        for path in ("/openapi.json", "/docs", "/redoc"):
            assert client.get(path).status_code == 404
        for origin in (None, "null", "https://evil.example"):
            client.headers.pop("origin", None)
            headers = {"origin": origin} if origin else {}
            assert client.post("/api/trips", json={"text": "Synthetic"}, headers=headers).status_code == 403
        if not can_create:
            assert client.post("/api/trips", json={"text": "Synthetic"}, headers={"origin": ORIGIN}).status_code == 403


@pytest.mark.parametrize("identity,expected", [(None, 401), ("stranger", 403), ("task", 403)])
def test_cloud_anonymous_membership_and_task_denials(cloud_demo, identity, expected):
    with cloud_demo.client(identity) as client:
        assert client.get(PATH).status_code == expected


def test_cloud_host_and_cross_origin_denials(cloud_demo):
    with cloud_demo.client() as client:
        assert client.get(PATH, headers={"host": "evil.example"}).status_code == 400
        assert client.get(PATH, headers={"sec-fetch-site": "cross-site"}).status_code == 403


def test_readonly_has_no_workspace_or_job_creation(monkeypatch):
    monkeypatch.setenv("CLOUD_FEATURE_MODE", "readonly_demo")
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.delenv("K_SERVICE", raising=False)
    with TestClient(create_app()) as client:
        assert client.get(PATH).status_code == 404
        assert client.post("/api/trips", json={"text": "Synthetic"}).status_code == 403
