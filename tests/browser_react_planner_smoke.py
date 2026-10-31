"""Compiled React Planner -> real mock API/worker -> existing viewer, plus offline IAP doubles."""
import os
import re
from pathlib import Path
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
from scripts.dev import stop
ARTIFACTS = ROOT / "local-data/react-planner-qa"


def instrument(page, base):
    external, errors, posts, reads = [], [], [], []
    page.add_init_script("window.__cspViolations=[];document.addEventListener('securitypolicyviolation',e=>window.__cspViolations.push(e.violatedDirective));")
    page.on("pageerror", lambda error: errors.append(str(error)))
    def request_seen(request):
        if not request.url.startswith(base + "/"):
            external.append(request.url)
        if request.method == "POST" and request.url == base + "/api/trips":
            posts.append(request)
        if request.method == "GET" and urlsplit(request.url).path.startswith("/api/trips/"):
            reads.append(request.url)
    page.on("request", request_seen)
    return external, errors, posts, reads


def fill_and_submit(page):
    expect(page.get_by_role("heading", name="Planer podróży", exact=True)).to_be_visible()
    example = page.get_by_role("button", name="Ojców · 1 dzień")
    expect(example).to_be_enabled()
    example.focus()
    page.keyboard.press("Enter")
    expect(page.get_by_label("Opisz wycieczkę")).to_be_focused()
    expect(page.get_by_label("Opisz wycieczkę")).to_have_value(re.compile("Kraków"))
    page.get_by_role("button", name="Przygotuj plan", exact=True).click()
    expect(page.get_by_text("W kolejce", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="Przygotuj plan", exact=True)).to_be_disabled()


def run():
    assert (ROOT / "frontend/dist/index.html").is_file(), "Build frontend first"
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0)); port = listener.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory(prefix="tripse-react-planner-") as temporary:
        env = dict(os.environ, CLOUD_FEATURE_MODE="local", PLANNING_MODE="mock", PUBLIC_BASE_URL=base,
                   DATABASE_PATH=str(Path(temporary) / "jobs.sqlite3"), DOCUMENT_STUDIO_DATA_PATH=str(Path(temporary) / "documents"),
                   WORKER_POLL_SECONDS="0.1")
        for key in ("K_SERVICE", "EXPECTED_IMAGE_SHA", "DOCUMENT_STUDIO_DOCKER_LOCAL", "OPENAI_API_KEY", "GOOGLE_MAPS_API_KEY", "GOOGLE_MAPS_BROWSER_KEY", "GOOGLE_PLACES_API_KEY", "GOOGLE_ROUTES_API_KEY", "WAHA_API_KEY", "WAHA_WEBHOOK_HMAC_KEY"):
            env.pop(key, None)
        processes = []
        def start(module, *args):
            process = subprocess.Popen([sys.executable, "-m", module, *args], cwd=ROOT, env=env,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            processes.append(process)
            return process
        try:
            api = start("uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port), "--no-access-log")
            for _ in range(100):
                try:
                    if httpx.get(base + "/health", timeout=1).status_code == 200: break
                except httpx.TransportError: pass
                if api.poll() is not None: raise RuntimeError("Mock API exited")
                time.sleep(.1)
            else: raise RuntimeError("Mock API startup timeout")
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page(viewport={"width": 1440, "height": 1100})
                external, errors, posts, reads = instrument(page, base)
                page.route("**/*", lambda route: route.continue_() if route.request.url.startswith(base + "/") else route.abort())
                page.goto(base + "/app")
                planner_link = page.get_by_role("link", name=re.compile("Zaplanuj podróż.*Planer podróży"))
                expect(planner_link).to_be_visible()
                page.screenshot(path=str(ARTIFACTS / "hub-desktop.png"), full_page=True)
                planner_link.click()
                expect(page.get_by_text("DEMO / MOCK", exact=True)).to_be_visible()
                for width in (320, 390, 768, 1024):
                    page.set_viewport_size({"width": width, "height": 900})
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
                page.screenshot(path=str(ARTIFACTS / "planner-tablet.png"), full_page=True)
                page.set_viewport_size({"width": 390, "height": 844})
                page.screenshot(path=str(ARTIFACTS / "planner-mobile.png"), full_page=True)
                fill_and_submit(page)
                assert len(posts) == 1 and "idempotency-key" not in posts[0].all_headers()
                page.screenshot(path=str(ARTIFACTS / "planner-queued.png"), full_page=True)
                worker = start("app.worker")
                link = page.get_by_role("link", name="Otwórz plan i mapę", exact=True)
                expect(link).to_be_visible(timeout=20000)
                expect(page.get_by_text("Plan gotowy", exact=True)).to_be_visible()
                assert page.evaluate("window.__cspViolations") == []
                count = len(reads)
                page.wait_for_timeout(1800)
                assert len(reads) == count, "Terminal job kept polling"
                page.screenshot(path=str(ARTIFACTS / "planner-completed-mobile.png"), full_page=True)
                page.set_viewport_size({"width": 1440, "height": 1100})
                page.evaluate("window.scrollTo(0,0)")
                page.screenshot(path=str(ARTIFACTS / "planner-completed-desktop.png"), full_page=True)
                link.click()
                expect(page.locator(".day-card")).to_have_count(1)
                expect(page.get_by_role("img", name=re.compile("Mapa demonstracyjna"))).to_be_visible()
                page.screenshot(path=str(ARTIFACTS / "existing-viewer.png"), full_page=True)
                stop(worker); worker.wait(timeout=10)
                page.goto(base + "/app/planner")
                fill_and_submit(page)
                page.get_by_role("link", name="Wróć do pulpitu", exact=True).click()
                expect(page.get_by_role("heading", name="Moduły TRIPSE")).to_be_visible()
                count = len(reads)
                page.wait_for_timeout(2000)
                assert len(reads) == count, "Unmounted Planner kept polling"
                assert len(posts) == 2 and not external and not errors, (external, errors)
                page.close()

                with pytest.MonkeyPatch.context() as patch:
                    for key in ("K_SERVICE", "OPENAI_API_KEY", "GOOGLE_MAPS_API_KEY", "GOOGLE_PLACES_API_KEY", "GOOGLE_ROUTES_API_KEY", "GOOGLE_MAPS_BROWSER_KEY", "WAHA_API_KEY", "WAHA_WEBHOOK_SECRET", "WAHA_WEBHOOK_HMAC_KEY"):
                        patch.delenv(key, raising=False)
                    patch.setenv("PLANNING_MODE", "mock")
                    from test_cloud_demo import cloud_demo, ORIGIN
                    demo = cloud_demo.__wrapped__(patch)
                    for identity in ("editor", "reader"):
                        context = browser.new_context(viewport={"width": 1440, "height": 1100})
                        cloud_page = context.new_page()
                        external, errors, posts, reads = instrument(cloud_page, ORIGIN)
                        with demo.client(identity) as client, demo.client("task") as tasks:
                            seen = {}
                            def route_request(route):
                                request = route.request
                                if not request.url.startswith(ORIGIN + "/"):
                                    route.abort(); return
                                path = urlsplit(request.url).path
                                if path.startswith("/api/trips/"):
                                    seen[path] = seen.get(path, 0) + 1
                                    if seen[path] == 2:
                                        assert tasks.post("/internal/jobs/" + path.rsplit("/", 1)[1]).status_code == 200
                                response = client.request(request.method, path, headers=request.all_headers(), content=request.post_data_buffer, follow_redirects=False)
                                headers = {key: value for key, value in response.headers.items() if key.lower() not in {"content-length", "content-encoding"}}
                                route.fulfill(status=response.status_code, headers=headers, body=response.content)
                            context.route("**/*", route_request)
                            cloud_page.goto(ORIGIN + "/app/planner")
                            if identity == "reader":
                                expect(cloud_page.get_by_text("Dostęp tylko do odczytu.", exact=False)).to_be_visible()
                                expect(cloud_page.get_by_role("button", name="Przygotuj plan", exact=True)).to_be_disabled()
                                cloud_page.get_by_label("Opisz wycieczkę").fill("Synthetic forbidden")
                                cloud_page.locator("form").evaluate("form=>form.requestSubmit()")
                                cloud_page.wait_for_timeout(200)
                                assert not posts
                            else:
                                fill_and_submit(cloud_page)
                                expect(cloud_page.get_by_role("link", name="Otwórz plan i mapę", exact=True)).to_be_visible(timeout=20000)
                                assert len(posts) == 1 and len(posts[0].all_headers()["idempotency-key"]) == 36
                                assert cloud_page.evaluate("window.__cspViolations") == []
                                cloud_page.get_by_role("link", name="Otwórz plan i mapę", exact=True).click()
                                expect(cloud_page.locator(".day-card")).to_have_count(1)
                            cloud_page.screenshot(path=str(ARTIFACTS / f"cloud-{identity}.png"), full_page=True)
                            assert not external and not errors, (external, errors)
                        context.close()
                browser.close()
        finally:
            for process in reversed(processes):
                if process.poll() is None:
                    stop(process); process.wait(timeout=15)
    print("React Planner PASS: real local mock API/worker/viewer; one POST per intent; terminal/unmount polling stops; keyboard/mobile; strict CSP; offline cloud editor/reader; no external requests. Screenshots: local-data/react-planner-qa")


if __name__ == "__main__":
    run()
