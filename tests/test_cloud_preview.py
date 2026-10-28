from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import cloud_preview
from app.main import create_app


@pytest.fixture
def cloud(monkeypatch, tmp_path):
    monkeypatch.setenv("CLOUD_FEATURE_MODE", "readonly_demo")
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.delenv("K_SERVICE", raising=False)
    monkeypatch.setattr(cloud_preview, "VERSION_FILE", tmp_path / "absent")
    return create_app


def test_no_storage_or_provider_construction(cloud, monkeypatch, tmp_path):
    from app.db import Database
    from app.document_studio.repository import JsonRepository
    from app import planning_providers
    def forbidden(*args, **kwargs):
        pytest.fail("Cloud preview constructed a persistent repository/provider")
    monkeypatch.setattr(Database, "__init__", forbidden)
    monkeypatch.setattr(JsonRepository, "__init__", forbidden)
    monkeypatch.setattr(planning_providers.OpenAIPlanner, "__init__", forbidden)
    for _ in range(2):
        with TestClient(cloud(tmp_path / "private.sqlite3", document_data_path=tmp_path / "private")) as client:
            assert client.get("/health").json()["storage"] == "fixtures_readonly"
            for path in ("/hub", "/preview/planner", "/preview/planner?scenario=coast", "/preview/documents", "/preview/documents/collection?variant=new_trips", "/preview/documents/collection?variant=theme_collection"):
                assert client.get(path).status_code == 200
    assert not list(tmp_path.iterdir())


def test_readonly_homepage_has_single_temporary_redirect(cloud):
    with TestClient(cloud()) as client:
        root = client.get("/", follow_redirects=False)
        assert root.status_code == 302 and root.headers["location"] == "/hub"
        assert root.headers["cache-control"] == "no-store"
        assert client.get("/hub", follow_redirects=False).status_code == 200
        response = client.get("/")
        assert response.url.path == "/hub" and len(response.history) == 1
        for path in ("/preview/planner", "/preview/documents"):
            assert client.get(path, follow_redirects=False).status_code == 200


@pytest.mark.parametrize("path", ["/api/trips", "/api/demo/messages", "/api/document-studio/trips", "/api/document-studio/drafts", "/api/document-studio/assets", "/webhooks/waha", "/hub"])
@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_write_blocked(cloud, path, method):
    with TestClient(cloud()) as client:
        assert client.request(method, path, content=b"invalid untrusted payload").status_code == 403


@pytest.mark.parametrize("path", ["/planner", "/documents/demo", "/demo/chat", "/api/document-studio/trips", "/api/document-studio/drafts", "/api/document-studio/assets/private/content", "/preview/documents/pilot.basic", "/static/create.html", "/static/demo.html", "/docs", "/openapi.json", "/documents/assets/studio.js", "/documents/assets/../models.py"])
def test_private_routes_absent(cloud, path):
    with TestClient(cloud()) as client:
        assert client.get(path).status_code == 404


def test_whitelisted_content_and_invalid_input(cloud):
    with TestClient(cloud()) as client:
        for name in cloud_preview.DOCUMENT_ASSETS:
            assert client.get("/documents/assets/"+name).status_code == 200
        assert client.get("/preview/planner?scenario=../../private").status_code == 422
        assert client.get("/preview/documents/collection?variant=pilot.basic").status_code == 422
        response = client.get("/preview/documents/collection")
        assert "source-blocks" in response.text
        for forbidden in ("internal_notes", "reservation", "pilot_data", "/api/document-studio/assets/"):
            assert forbidden not in response.text
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


@pytest.mark.parametrize("values", [
    {"K_SERVICE": "tripse-ai-dev", "CLOUD_FEATURE_MODE": "local"},
    {"PLANNING_MODE": "live"}, {"APP_ENV": "production"},
    {"K_SERVICE": "tripse-ai-prod"}, {"GOOGLE_ROUTES_API_KEY": "not-a-real-key"},
    {"K_SERVICE": "tripse-ai-dev", "EXPECTED_IMAGE_SHA": "b"*40},
])
def test_fail_closed(cloud, monkeypatch, values):
    for key,value in values.items():
        monkeypatch.setenv(key,value)
    with pytest.raises(ValueError):
        cloud()


def test_baked_version_and_service_identity(cloud, monkeypatch, tmp_path):
    version = tmp_path / "version"
    version.write_text("a"*40)
    monkeypatch.setattr(cloud_preview, "VERSION_FILE", version)
    monkeypatch.setenv("K_SERVICE", "tripse-ai-dev")
    monkeypatch.setenv("EXPECTED_IMAGE_SHA", "a"*40)
    with TestClient(cloud()) as client:
        assert client.get("/health").json()["image_version"] == "a"*40


def test_worker_refuses_cloud_before_database(cloud, monkeypatch):
    from app.worker import main
    with pytest.raises(ValueError, match="disabled"):
        main()
