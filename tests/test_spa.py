"""Private compiled SPA routing/security; fixtures never substitute for browser QA."""
import re

import pytest
from fastapi.testclient import TestClient

from app import spa
from app.main import create_app
from test_cloud_demo import cloud_demo, ORIGIN  # fixture with offline verified-identity double

NAV = {"accept": "text/html", "sec-fetch-dest": "document"}


@pytest.fixture
def dist(tmp_path):
    root = tmp_path / "dist"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text('<!doctype html><meta name="tripse-style-nonce" content="__TRIPSE_STYLE_NONCE__"><div id="root"></div>', encoding="utf-8")
    (root / "assets/index-abcdefgh.js").write_text('export const compiled = true;', encoding="utf-8")
    (root / "assets/index-abcdefgh.css").write_text('body{color:navy}', encoding="utf-8")
    return root


@pytest.fixture
def local(dist, tmp_path, monkeypatch):
    monkeypatch.setenv("CLOUD_FEATURE_MODE", "local")
    monkeypatch.delenv("K_SERVICE", raising=False)
    monkeypatch.delenv("DOCUMENT_STUDIO_DOCKER_LOCAL", raising=False)
    return create_app(tmp_path / "db.sqlite3", document_data_path=tmp_path / "documents", frontend_dist=dist)


def client(app, **kwargs):
    return TestClient(app, base_url="http://localhost", client=("127.0.0.1", 12345), **kwargs)


@pytest.mark.parametrize("path", ["/app", "/app/", "/app/planner", "/app/documents", "/app/marketing", "/app/automations", "/app/assistant", "/app/unknown/deep-link"])
def test_entry_and_document_navigation_refresh(local, path):
    with client(local) as c:
        for _ in range(2):
            response = c.get(path, headers=NAV)
            assert response.status_code == 200 and 'id="root"' in response.text
            assert response.headers["content-type"].startswith("text/html")
            assert response.headers["cache-control"] == "private, no-store"


def test_nonce_is_unique_and_csp_is_narrow(local):
    with client(local) as c:
        first, second = c.get("/app"), c.get("/app")
        nonce = re.search(r'content="([\w-]+)"', first.text)[1]
        assert nonce not in second.text and spa.NONCE_MARKER not in first.text
        policy = first.headers["content-security-policy"]
        assert f"style-src 'self' 'nonce-{nonce}'" in policy
        assert "script-src 'self'" in policy and "connect-src 'self'" in policy
        assert "unsafe-inline" not in policy and "unsafe-eval" not in policy
        assert "frame-ancestors 'none'" in policy and "base-uri 'none'" in policy
        assert first.headers["x-content-type-options"] == "nosniff"
        assert first.headers["x-frame-options"] == "DENY"
        assert first.headers["referrer-policy"] == "no-referrer"
        assert c.head("/app").content == b""


@pytest.mark.parametrize("suffix,mime", [("js", "javascript"), ("css", "text/css")])
def test_assets_are_private_cacheable_and_have_correct_mime(local, suffix, mime):
    with client(local) as c:
        response = c.get(f"/app/assets/index-abcdefgh.{suffix}")
        assert response.status_code == 200 and mime in response.headers["content-type"]
        assert response.headers["cache-control"] == "private, max-age=31536000, immutable"
        assert "etag" in response.headers and "last-modified" in response.headers


@pytest.mark.parametrize("path", ["/app/assets/missing.js", "/app/assets/missing", "/app/assets", "/app/assets/", "/app/missing.css", "/app/favicon.ico", "/app/assets/%2e%2e/index.html", "/app/assets/%5csecret.js", "/app/assets/C:secret.js", "/app/.env"])
def test_missing_resources_never_receive_html(local, path):
    with client(local) as c:
        response = c.get(path, headers=NAV)
        assert response.status_code == 404
        assert "text/html" not in response.headers["content-type"]
        assert 'id="root"' not in response.text


def test_non_navigation_fetch_and_post_do_not_get_fallback(local):
    with client(local) as c:
        assert c.get("/app/planner").status_code == 404
        assert c.get("/app/planner", headers={**NAV, "sec-fetch-dest": "script"}).status_code == 404
        assert c.post("/app/planner").status_code == 405


@pytest.mark.parametrize("path", ["/app", "/app/planner", "/app/assets/index-abcdefgh.js"])
@pytest.mark.parametrize("headers", [{"host": "evil.example"}, {"origin": "https://evil.example"}, {"forwarded": "for=127.0.0.1"}, {"x-forwarded-for": "127.0.0.1"}, {"x-forwarded-host": "localhost"}, {"x-forwarded-proto": "http"}, {"sec-fetch-site": "cross-site"}])
def test_local_policy_applies_to_html_navigation_and_assets(local, path, headers):
    with client(local) as c:
        response = c.get(path, headers={**NAV, **headers})
        assert response.status_code == 403 and 'id="root"' not in response.text
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["x-content-type-options"] == "nosniff"


def test_remote_peer_is_not_authorized_by_loopback_host(local):
    with TestClient(local, base_url="http://localhost", client=("203.0.113.5", 12345)) as c:
        assert c.get("/app", headers=NAV).status_code == 403


def test_absent_or_incompatible_build_keeps_legacy_available(local, dist):
    with client(local) as c:
        (dist / "index.html").unlink()
        response = c.get("/app")
        assert response.status_code == 503 and str(dist) not in response.text
        assert c.get("/hub").status_code == 200
        (dist / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
        assert c.get("/app").status_code == 503


def test_legacy_api_and_static_behavior_remains(local):
    with client(local) as c:
        assert c.get("/", follow_redirects=False).headers["location"] == "/hub"
        for path in ("/hub", "/planner", "/documents/demo", "/demo/chat", "/health"):
            assert c.get(path).status_code == 200
        for path in ("/api/not-a-route", "/internal/not-a-route", "/static/not-a-file.js", "/not-an-app-route"):
            assert c.get(path, headers=NAV).status_code == 404
        assert c.get("/trip/invalid").status_code == 404


@pytest.mark.parametrize("path", ["/app", "/app/planner", "/app/assets/index-abcdefgh.js"])
def test_cloud_global_iap_covers_shell_and_assets(cloud_demo, dist, monkeypatch, path):
    monkeypatch.setattr(spa, "PACKAGED_DIST", dist)
    for identity, status in [(None, 401), ("stranger", 403), ("task", 403), ("reader", 200), ("editor", 200)]:
        with cloud_demo.client(identity) as c:
            response = c.get(path, headers=NAV)
            assert response.status_code == status
            assert response.headers["cache-control"] == "private, no-store"
            assert "unsafe-inline" not in response.headers["content-security-policy"]
    with cloud_demo.client(None) as c:
        assert c.get(path, headers={**NAV, "x-goog-authenticated-user-email": "accounts.google.com:editor@example.com"}).status_code == 401
        assert c.get(path, headers={**NAV, "x-goog-iap-jwt-assertion": "forged"}).status_code == 401
        # Health keeps its pre-existing middleware exception; not a session check.
        assert c.get("/health", headers={"host": "wrong.invalid"}).status_code == 200
    with cloud_demo.client() as c:
        assert c.get(path, headers={**NAV, "host": "wrong.invalid"}).status_code == 400
        assert c.get(path, headers={**NAV, "sec-fetch-site": "same-site"}).status_code == 403
        assert c.post(path, headers={"origin": "https://evil.example"}).status_code == 403
    with cloud_demo.client("reader") as c:
        assert c.post(path).status_code == 403


def test_readonly_has_no_spa_routes_even_with_build(monkeypatch, dist):
    monkeypatch.setenv("CLOUD_FEATURE_MODE", "readonly_demo")
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.delenv("K_SERVICE", raising=False)
    app = create_app(frontend_dist=dist)
    assert not any(getattr(route, "path", "").startswith("/app") for route in app.routes)
    with TestClient(app) as c:
        for path in ("/app", "/app/", "/app/planner", "/app/assets/index-abcdefgh.js"):
            assert c.get(path, headers=NAV).status_code == 404
