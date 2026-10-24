import secrets
import time

import pytest
from fastapi.testclient import TestClient

from app.db import Database
from app.generator import generate_mock_trip
from app.main import create_app
from app.viewer import browser_config


@pytest.fixture
def saved_plan(tmp_path):
    path = tmp_path / "viewer.sqlite3"
    with TestClient(create_app(path)) as client:
        database = Database(path)
        trip_id = database.create_trip("private original request Wrocław")
        database.claim_next()
        token = secrets.token_urlsafe(32)
        result = generate_mock_trip(trip_id, "private original request Wrocław")
        result["viewer_url"] = "http://localhost:8000/trip/" + token
        database.finish(trip_id, result=result, viewer_token=token,
                        viewer_expires_at=time.time() + 600)
        yield client, database, token


def test_html_and_private_data(saved_plan, monkeypatch):
    client, _, token = saved_plan
    monkeypatch.setenv("GOOGLE_MAPS_BROWSER_KEY", "public-browser-key")
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "server-secret-do-not-expose")
    monkeypatch.setenv("OPENAI_API_KEY", "another-server-secret")
    page = client.get("/trip/" + token)
    assert page.status_code == 200
    assert 'id="day-cards"' in page.text
    assert 'id="map"' in page.text
    assert 'name="viewport"' in page.text
    assert "private original request Wrocław" not in page.text
    assert page.headers["Cache-Control"] == "no-store"
    assert page.headers["Referrer-Policy"] == "strict-origin"
    assert "frame-ancestors 'none'" in page.headers["Content-Security-Policy"]
    data = client.get("/api/viewer/" + token)
    assert data.json()["maps"]["browser_key"] == "public-browser-key"
    assert "private original request Wrocław" not in data.text
    assert "viewer_url" not in data.json()["plan"]
    for response in (page, data):
        assert "server-secret" not in response.text
        assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert client.get("/static/viewer.js").status_code == 200
    assert client.get("/static/viewer.css").status_code == 200


@pytest.mark.parametrize("path", ["/trip/", "/api/viewer/"])
def test_expired_and_unknown_rejected(saved_plan, path):
    client, database, token = saved_plan
    assert client.get(path + secrets.token_urlsafe(32)).status_code == 404
    assert client.get(path + "short").status_code == 404
    assert client.get(path + "!" * 43).status_code == 404
    with database.connect() as connection:
        connection.execute("UPDATE trip_viewers SET expires_at = 0")
    expired = client.get(path + token)
    assert expired.status_code == 404
    assert expired.headers["Cache-Control"] == "no-store"
    assert "private original request Wrocław" not in expired.text


def test_browser_never_falls_back_to_server_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_BROWSER_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "secret")
    assert browser_config()["browser_key"] == ""
    monkeypatch.setenv("GOOGLE_MAPS_BROWSER_KEY", "secret")
    assert browser_config()["browser_key"] == ""


def test_viewer_remains_read_only(saved_plan):
    client, _, token = saved_plan
    for method in ("post", "put", "delete", "patch"):
        assert getattr(client, method)("/trip/" + token).status_code == 405
        assert getattr(client, method)("/api/viewer/" + token).status_code == 405
