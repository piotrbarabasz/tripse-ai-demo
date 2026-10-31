"""Revision-safe React editor against real temporary JSON and offline cloud stores."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

import httpx
import pytest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.document_studio.repository import JsonRepository
from tests.browser_react_document_creation_smoke import seed_creation_sources
from tests.react_editor_flow import exercise
from scripts.dev import stop

ARTIFACTS = ROOT / "local-data/react-document-editor-qa"


def run():
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    assert (ROOT / "frontend/dist/index.html").is_file(), "Build frontend first"
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0)); port = listener.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory(prefix="tripse-react-editor-") as temporary:
        root = Path(temporary) / "documents"
        repository = JsonRepository(root, Path(temporary) / "empty-fixtures")
        seed_creation_sources(repository)
        env = dict(os.environ, CLOUD_FEATURE_MODE="local", PLANNING_MODE="mock", DATABASE_PATH=str(Path(temporary) / "jobs.sqlite3"), DOCUMENT_STUDIO_DATA_PATH=str(root))
        for key in ("K_SERVICE", "EXPECTED_IMAGE_SHA", "DOCUMENT_STUDIO_DOCKER_LOCAL", "OPENAI_API_KEY", "GOOGLE_MAPS_API_KEY", "GOOGLE_MAPS_BROWSER_KEY", "GOOGLE_PLACES_API_KEY", "GOOGLE_ROUTES_API_KEY", "WAHA_API_KEY", "WAHA_WEBHOOK_HMAC_KEY"):
            env.pop(key, None)
        server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port), "--no-access-log"], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        try:
            for _ in range(100):
                try:
                    if httpx.get(base + "/health", timeout=1).status_code == 200: break
                except httpx.TransportError: pass
                if server.poll() is not None: raise RuntimeError("Mock API exited")
                time.sleep(.1)
            else: raise RuntimeError("Mock API startup timeout")
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                context = browser.new_context(viewport={"width": 1440, "height": 1100})
                context.route("**/*", lambda route: route.continue_() if route.request.url.startswith(base + "/") else route.abort())
                # Commit a Pilot document, then replace the POST response with a
                # 503. The wizard must recover by GET without a second POST.
                def lose_response(route):
                    if route.request.post_data_json["template_id"] == "pilot.advanced":
                        response = route.fetch()
                        assert response.status == 201
                        route.fulfill(status=503, content_type="application/json", body='{"detail":"Unavailable"}')
                    else: route.continue_()
                context.route("**/api/document-studio/drafts", lose_response)
                def lose_saved_response(route):
                    if route.request.method == "PUT" and route.request.post_data_json["title"] == "Zmieniony pilot.advanced":
                        response = route.fetch(); assert response.status == 200
                        route.fulfill(status=503, content_type="application/json", body='{"detail":"Unavailable"}')
                    else: route.continue_()
                context.route("**/api/document-studio/drafts/*", lose_saved_response)
                exercise(context, base, repository, label="local", can_edit=True, api=lambda method, path, **kwargs: httpx.request(method, base + path, **kwargs))
                context.close()
                with pytest.MonkeyPatch.context() as patch:
                    patch.setenv("CLOUD_FEATURE_MODE", "local"); patch.setenv("PLANNING_MODE", "mock")
                    for key in ("K_SERVICE", "OPENAI_API_KEY", "GOOGLE_MAPS_API_KEY", "GOOGLE_PLACES_API_KEY", "GOOGLE_ROUTES_API_KEY", "GOOGLE_MAPS_BROWSER_KEY", "WAHA_API_KEY", "WAHA_WEBHOOK_SECRET", "WAHA_WEBHOOK_HMAC_KEY"):
                        patch.delenv(key, raising=False)
                    from test_cloud_demo import cloud_demo, ORIGIN
                    demo = cloud_demo.__wrapped__(patch)
                    repository = demo.components().repository
                    seed_creation_sources(repository)
                    for identity in ("editor", "reader"):
                        context = browser.new_context(viewport={"width": 1440, "height": 1100})
                        with demo.client(identity) as client:
                            def route_request(route):
                                request = route.request
                                if not request.url.startswith(ORIGIN + "/"):
                                    route.abort(); return
                                response = client.request(request.method, request.url, headers=request.all_headers(), content=request.post_data_buffer, follow_redirects=False)
                                headers = {key: value for key, value in response.headers.items() if key.lower() not in {"content-length", "content-encoding"}}
                                route.fulfill(status=response.status_code, headers=headers, body=response.content)
                            context.route("**/*", route_request)
                            exercise(context, ORIGIN, repository, label="cloud-" + identity, can_edit=identity == "editor", api=lambda method, path, **kwargs: client.request(method, path, **kwargs))
                            head = repository.list("drafts")[0]
                            unchanged = head.model_dump(mode="json")
                            update_path = "/api/document-studio/drafts/" + head.document_id
                            update = {"revision": head.revision, "title": "Denied QA change"}
                            payload = {"document_id": "forbidden-origin-test", "source_revision": 1, "template_id": "offer.private", "source_type": "trip", "source_id": "react-qa-source"}
                            # This identity double supplies an Origin by default;
                            # remove it explicitly to exercise the missing header.
                            origin = client.headers.pop("origin")
                            try:
                                assert client.post("/api/document-studio/drafts", json=payload).status_code == 403
                                assert client.put(update_path, json=update).status_code == 403
                            finally:
                                client.headers["Origin"] = origin
                            assert client.post("/api/document-studio/drafts", json=payload, headers={"Origin": "https://evil.example"}).status_code == 403
                            assert client.put(update_path, json=update, headers={"Origin": "https://evil.example"}).status_code == 403
                            if identity == "reader":
                                assert client.post("/api/document-studio/drafts", json=payload, headers={"Origin": ORIGIN}).status_code == 403
                                assert client.put(update_path, json=update, headers={"Origin": ORIGIN}).status_code == 403
                            assert repository.get("drafts", head.document_id).model_dump(mode="json") == unchanged
                        context.close()
                browser.close()
        finally:
            stop(server); server.wait(timeout=15)
    print("React editor PASS: B creation to React editing; Offer/Pilot logistics/knowledge/Marketing; JSON + fake-GCS editor/reader; revision-safe PUT and GET verification; preserved sources/business objects/gallery/history; conflict review/discard; lost-save503 recovery; mobile/keyboard/CSP; legacy editor and real preview. Evidence: local-data/react-document-editor-qa")


if __name__ == "__main__":
    run()
