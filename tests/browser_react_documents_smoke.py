"""Read-only React catalog/library against temporary JSON and offline cloud actors."""
from hashlib import sha256
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit

import httpx
import pytest
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.document_studio.repository import JsonRepository
from tests.react_document_fixtures import seed_documents
from scripts.dev import stop

ARTIFACTS = ROOT / "local-data/react-documents-qa"


def fingerprint(root):
    return {str(path.relative_to(root)): sha256(path.read_bytes()).hexdigest() for path in root.rglob("*.json")}


def exercise(context, base, *, can_edit, label, pagination):
    external, errors, mutations = [], [], []
    def seen(request):
        if not request.url.startswith(base + "/"): external.append(request.url)
        if "/api/document-studio/" in request.url and request.method != "GET": mutations.append(request.method)
    context.on("request", seen)
    page = context.new_page()
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.add_init_script("window.__cspViolations=[];document.addEventListener('securitypolicyviolation',e=>window.__cspViolations.push(e.violatedDirective));")
    page.goto(base + "/app/documents")
    expect(page.get_by_role("heading", name="Document Studio", exact=True)).to_be_visible()
    expect(page.locator(".document-card")).to_have_count(8)
    assert page.get_by_role("region", name="Oferty", exact=True).locator("article").count() == 4
    assert page.get_by_role("region", name="Materiały pilota", exact=True).locator("article").count() == 3
    assert page.get_by_role("region", name="Marketing", exact=True).locator("article").count() == 1
    assert page.get_by_role("link", name=re.compile("Tworzenie w dotychczasowym Studio")).count() == (8 if can_edit else 0)
    page.screenshot(path=str(ARTIFACTS / f"{label}-catalog.png"), full_page=True)
    for width in (320, 390, 768, 1024):
        page.set_viewport_size({"width": width, "height": 900})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(ARTIFACTS / f"{label}-catalog-mobile.png"), full_page=True)
    page.get_by_role("navigation", name="Widoki Document Studio").get_by_role("link", name="Biblioteka dokumentów").focus()
    page.keyboard.press("Enter")
    expect(page.locator(".document-card").first).to_be_visible()
    page.get_by_label("Sortuj według").select_option("title")
    page.get_by_label("Kierunek").select_option("asc")
    expect(page.get_by_role("heading", name="Dokument QA 00 po zapisie", exact=True)).to_be_visible()
    if pagination:
        expect(page.locator(".document-card")).to_have_count(25)
        page.get_by_role("button", name="Następna strona").click()
        expect(page.locator(".document-card")).to_have_count(2)
        expect(page.get_by_text("26–27 z 27", exact=True)).to_be_visible()
        page.get_by_role("button", name="Poprzednia strona").click()
        expect(page.locator(".document-card")).to_have_count(25)
    page.get_by_label("Archiwum").select_option("only")
    expect(page.locator(".document-card")).to_have_count(1)
    expect(page.get_by_text("W archiwum", exact=True)).to_be_visible()
    assert page.get_by_role("link", name=re.compile("Edytuj w dotychczasowym Studio")).count() == 0
    page.get_by_role("button", name="Wyczyść filtry").click()
    page.get_by_label("Rodzina").select_option("pilot")
    expect(page.locator(".document-card").first).to_be_visible()
    assert page.locator(".document-card").count() > 0
    page.get_by_role("button", name="Wyczyść filtry").click()
    page.get_by_label("Szukaj po tytule").fill("brak-takiego-qa")
    expect(page.get_by_text("Brak dokumentów pasujących do filtrów.", exact=True)).to_be_visible()
    page.get_by_label("Szukaj po tytule").fill("QA 00")
    expect(page.locator(".document-card")).to_have_count(1)
    page.screenshot(path=str(ARTIFACTS / f"{label}-library-mobile.png"), full_page=True)
    page.set_viewport_size({"width": 1440, "height": 1100})
    page.evaluate("window.scrollTo(0,0)")
    page.screenshot(path=str(ARTIFACTS / f"{label}-library.png"), full_page=True)
    page.get_by_role("link", name=re.compile("Szczegóły i historia")).click()
    expect(page.get_by_role("heading", name="Rewizja 2", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name="Rewizja 1", exact=True)).to_be_visible()
    page.reload()
    expect(page.get_by_role("heading", name="Rewizja 1", exact=True)).to_be_visible()
    assert page.url == base + "/app/documents/library/react-qa-00"
    assert page.title() == "Document Studio — TRIPSE"
    expect(page.locator('nav a[aria-current="page"]').filter(has_text="Document Studio")).to_have_count(1)
    assert page.locator("iframe").count() == 0
    assert page.evaluate("window.__cspViolations") == []
    editor = page.get_by_role("link", name=re.compile("Edytuj w dotychczasowym Studio"))
    assert editor.count() == (1 if can_edit else 0)
    editor_url = editor.get_attribute("href") if can_edit else None
    history_url = page.get_by_role("link", name=re.compile("Historia w dotychczasowym Studio")).get_attribute("href")
    page.screenshot(path=str(ARTIFACTS / f"{label}-history.png"), full_page=True)
    with context.expect_page() as opened:
        page.get_by_role("link", name="Podgląd rewizji 1 (nowa karta)", exact=True).click()
    preview = opened.value
    preview.wait_for_load_state()
    assert preview.url == base + "/api/document-studio/library/react-qa-00/revisions/1/preview"
    expect(preview.locator("body")).to_be_visible()
    assert not mutations, mutations
    preview.close()
    # Beyond this point the existing legacy application owns its own read/preview
    # projection calls. No save/create/archive/duplicate action is performed.
    page.goto(base + history_url)
    expect(page.get_by_role("heading", name="Historia dokumentu", exact=True)).to_be_visible()
    if editor_url:
        page.goto(base + editor_url)
        expect(page.locator("#d-save")).to_be_visible()
    assert not external and not errors, (external, errors)
    page.close()


def run():
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    assert (ROOT / "frontend/dist/index.html").is_file(), "Build frontend first"
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0)); port = listener.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory(prefix="tripse-react-documents-") as temporary:
        root = Path(temporary) / "documents"
        seed_documents(JsonRepository(root, Path(temporary) / "empty-fixtures"))
        before = fingerprint(root)
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
                exercise(context, base, can_edit=True, label="local", pagination=True)
                context.close()
                assert fingerprint(root) == before, "Saved JSON data changed during read-only QA"
                with pytest.MonkeyPatch.context() as patch:
                    patch.setenv("CLOUD_FEATURE_MODE", "local"); patch.setenv("PLANNING_MODE", "mock")
                    for key in ("K_SERVICE", "OPENAI_API_KEY", "GOOGLE_MAPS_API_KEY", "GOOGLE_PLACES_API_KEY", "GOOGLE_ROUTES_API_KEY", "GOOGLE_MAPS_BROWSER_KEY", "WAHA_API_KEY", "WAHA_WEBHOOK_SECRET", "WAHA_WEBHOOK_HMAC_KEY"):
                        patch.delenv(key, raising=False)
                    from test_cloud_demo import cloud_demo, ORIGIN
                    demo = cloud_demo.__wrapped__(patch)
                    seed_documents(demo.components().repository, count=9)
                    before_cloud = dict(demo.bucket.objects)
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
                            exercise(context, ORIGIN, can_edit=identity == "editor", label="cloud-" + identity, pagination=False)
                        context.close()
                    assert demo.bucket.objects == before_cloud, "Saved cloud-double data changed"
                browser.close()
        finally:
            stop(server); server.wait(timeout=15)
    print("React Documents PASS: 8 templates; real server filters/paging/history; local JSON + cloud editor/reader; safe legacy/preview links; mobile/keyboard/CSP; zero React writes; saved data/revisions unchanged. Evidence: local-data/react-documents-qa")


if __name__ == "__main__":
    run()
