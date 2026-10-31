"""Compiled FastAPI SPA browser QA: local server plus offline cloud/IAP doubles.

Run npm run build in frontend first, then python tests/browser_spa_smoke.py.
No deployed service, live providers or real IAP credentials are used.
"""
import os
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
ARTIFACTS = ROOT / "local-data/spa-qa"


def exercise(page, base):
    errors, external = [], []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("request", lambda request: external.append(request.url) if not request.url.startswith(base + "/") else None)
    page.add_init_script("window.__cspViolations=[];document.addEventListener('securitypolicyviolation',e=>window.__cspViolations.push(e.violatedDirective));")
    response = page.goto(base + "/app")
    assert response and response.status == 200, (response.status if response else None)
    try:
        page.get_by_role("heading", level=1).wait_for(timeout=5000)
    except Exception:
        page.screenshot(path=str(ARTIFACTS / "bootstrap-failure.png"), full_page=True)
        print("Bootstrap diagnostics:", errors, page.evaluate("window.__cspViolations"), page.locator("body").inner_text())
        raise
    expect(page.get_by_role("heading", level=1)).to_have_text("Dobry początek każdej podróży.")
    expect(page.get_by_text("Usługa odpowiada prawidłowo.")).to_be_visible()
    assert page.locator('a[href="/planner"]').count() == 1
    assert page.locator('a[href="/documents/demo"]').count() == 1
    assert page.locator('a[href="/hub"]').count() == 2
    page.screenshot(path=str(ARTIFACTS / ("cloud-desktop.png" if base.startswith("https") else "local-desktop.png")), full_page=True)
    for route, heading in (("planner", "Planer podróży"), ("documents", "Document Studio"), ("marketing", "Marketing"), ("automations", "Automatyzacje"), ("assistant", "Asystent AI")):
        page.goto(base + "/app/" + route)
        expect(page.get_by_role("heading", level=1)).to_have_text(heading)
        page.reload()
        expect(page.get_by_role("heading", level=1)).to_have_text(heading)
        expect(page.locator('nav a[aria-current="page"]')).to_have_text(heading)
        assert page.evaluate("window.__cspViolations") == []
    page.goto(base + "/app/not-a-module")
    expect(page.get_by_role("heading", level=1)).to_have_text("Nie znaleziono strony")
    page.get_by_role("link", name="Wróć do pulpitu").click()
    expect(page.get_by_role("heading", level=1)).to_be_focused()
    for width in (320, 390, 768, 1024):
        page.set_viewport_size({"width": width, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
    page.set_viewport_size({"width": 390, "height": 844})
    trigger = page.get_by_role("button", name="Otwórz nawigację")
    trigger.click()
    dialog = page.get_by_role("dialog", name="Nawigacja TRIPSE")
    expect(dialog).to_be_visible()
    assert page.evaluate("document.body.getAttribute('data-scroll-locked')")
    # Runtime Radix style tags must use the server-generated CSP style nonce.
    assert page.locator("style").count() > 0
    assert page.locator("style").evaluate_all("nodes=>nodes.every(n=>n.nonce && n.nonce===document.querySelector('meta[name=tripse-style-nonce]').content)")
    page.screenshot(path=str(ARTIFACTS / ("cloud-mobile-drawer.png" if base.startswith("https") else "local-mobile-drawer.png")), full_page=True)
    dialog.get_by_role("button", name="Zamknij nawigację").focus()
    page.keyboard.press("Tab")
    assert dialog.evaluate("node=>node.contains(document.activeElement)")
    page.keyboard.press("Escape")
    expect(dialog).not_to_be_visible()
    expect(trigger).to_be_focused()
    trigger.click()
    page.get_by_role("dialog").get_by_role("link", name="Marketing", exact=True).click()
    expect(page.get_by_role("dialog")).not_to_be_visible()
    expect(page.get_by_role("heading", level=1, name="Marketing")).to_be_focused()
    page.screenshot(path=str(ARTIFACTS / ("cloud-mobile.png" if base.startswith("https") else "local-mobile.png")), full_page=True)
    assert page.evaluate("window.__cspViolations") == []
    assert not errors, errors
    assert not external, external


def run():
    assert (ROOT / "frontend/dist/index.html").is_file(), "Build frontend first"
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0)); port = listener.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="tripse-spa-qa-") as temporary:
        env = dict(os.environ, CLOUD_FEATURE_MODE="local", PLANNING_MODE="mock",
                   DATABASE_PATH=str(Path(temporary)/"db.sqlite3"), DOCUMENT_STUDIO_DATA_PATH=str(Path(temporary)/"documents"))
        for key in ("K_SERVICE", "DOCUMENT_STUDIO_DOCKER_LOCAL", "OPENAI_API_KEY", "GOOGLE_MAPS_API_KEY", "GOOGLE_MAPS_BROWSER_KEY", "GOOGLE_PLACES_API_KEY", "GOOGLE_ROUTES_API_KEY"):
            env.pop(key, None)
        server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port), "--no-access-log"],
            cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        try:
            base = f"http://127.0.0.1:{port}"
            for _ in range(100):
                try:
                    if httpx.get(base+"/health", timeout=1).status_code == 200: break
                except httpx.TransportError: pass
                if server.poll() is not None: raise RuntimeError("QA API exited")
                time.sleep(.1)
            else: raise RuntimeError("QA API startup timeout")
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page(viewport={"width":1440, "height":1100})
                exercise(page, base)
                page.close()
                with pytest.MonkeyPatch.context() as patch:
                    for key in ("K_SERVICE", "OPENAI_API_KEY", "GOOGLE_MAPS_API_KEY", "GOOGLE_PLACES_API_KEY", "GOOGLE_ROUTES_API_KEY", "GOOGLE_MAPS_BROWSER_KEY", "WAHA_API_KEY", "WAHA_WEBHOOK_SECRET", "WAHA_WEBHOOK_HMAC_KEY"):
                        patch.delenv(key, raising=False)
                    patch.setenv("PLANNING_MODE", "mock")
                    from test_cloud_demo import cloud_demo, ORIGIN
                    demo = cloud_demo.__wrapped__(patch)
                    with demo.client("reader") as client:
                        context = browser.new_context(viewport={"width":1440, "height":1100})
                        def route_request(route):
                            request = route.request
                            if not request.url.startswith(ORIGIN+"/"):
                                route.abort(); raise AssertionError("Unexpected external request")
                            response = client.request(request.method, urlsplit(request.url).path,
                                headers=request.all_headers(), content=request.post_data_buffer, follow_redirects=False)
                            headers = {k:v for k,v in response.headers.items() if k.lower() not in {"content-length", "content-encoding"}}
                            route.fulfill(status=response.status_code, headers=headers, body=response.content)
                        context.route("**/*", route_request)
                        exercise(context.new_page(), ORIGIN)
                        context.close()
                browser.close()
        finally:
            server.terminate(); server.wait(timeout=15)
    print("SPA browser PASS: compiled local FastAPI and offline cloud reader; deep links/reloads; health; keyboard/mobile focus; strict CSP nonce drawer; no external requests. Hosted IAP not tested.")


if __name__ == "__main__": run()
