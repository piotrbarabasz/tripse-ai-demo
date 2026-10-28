"""Self-contained local browser + process-restart check; no external services.

Run: python tests/browser_document_studio_smoke.py
Screenshots: local-data/document-studio-qa/ (gitignored).
"""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

import httpx
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def run():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    artifacts = ROOT / "local-data" / "document-studio-qa"
    artifacts.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="tripse-document-studio-") as temporary:
        env = dict(os.environ, PLANNING_MODE="mock", DATABASE_PATH=str(Path(temporary) / "planner.sqlite3"),
                   DOCUMENT_STUDIO_DATA_PATH=str(Path(temporary) / "documents"))
        env.pop("DOCUMENT_STUDIO_DOCKER_LOCAL", None)
        process = None

        def start():
            server = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port), "--no-access-log"],
                cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            for _ in range(100):
                if server.poll() is not None:
                    raise RuntimeError("Local test server exited")
                try:
                    if httpx.get(base + "/health", timeout=1).status_code == 200:
                        return server
                except httpx.TransportError:
                    pass
                time.sleep(0.1)
            server.terminate()
            server.wait(timeout=10)
            raise RuntimeError("Local test server did not start")

        try:
            process = start()
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page(viewport={"width":1440,"height":1000})
                errors, requests = [], []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("request", lambda request: requests.append(request.url))
                page.on("dialog", lambda dialog: dialog.accept())
                page.goto(base + "/documents/demo#trips")
                expect(page.locator(".card")).to_have_count(3)
                page.screenshot(path=str(artifacts / "library-desktop.png"), full_page=True)
                page.locator('[data-go="trips/demo-canada"]').click()
                expect(page.locator(".day")).to_have_count(15)
                page.get_by_role("button", name="Dodaj dzień", exact=False).click()
                expect(page.locator(".day")).to_have_count(16)
                page.locator('[data-remove-day="15"]').click()
                expect(page.locator(".day")).to_have_count(15)
                page.locator('[data-nav="trips"]').click()
                page.get_by_role("button", name="Nowa wycieczka", exact=False).click()
                page.locator('[data-field="title"]').fill("Własna podróż — żółć, góry i Þingvellir")
                page.locator('[data-field="destinations"]').fill("Islandia, Kanada")
                page.locator('[data-field="start_date"]').fill("2027-06-01")
                page.locator('[data-add-stop="0"]').click()
                page.locator('[data-field="days.0.stops.0.name"]').fill("Przykładowa atrakcja")
                page.locator('[data-field="days.0.stops.0.description"]').fill('<script>window.injected = true</script> — fikcyjne dane')
                page.get_by_role("button", name="Dodaj dzień", exact=False).click()
                page.locator('[data-add-stop="1"]').click()
                page.locator('[data-remove-stop="1.0"]').click()
                page.locator("#save-trip").click()
                expect(page.locator("#message")).to_have_text("Wycieczka zapisana.")
                trip_hash = page.evaluate("location.hash")
                page.screenshot(path=str(artifacts / "editor-desktop.png"), full_page=True)
                page.locator("#editorial-notes").fill("Notatka do zachowania po restarcie")
                page.locator("#template").select_option("offer.private")
                page.locator("#create-draft").click()
                expect(page.locator(".snapshot-day")).to_have_count(2)
                expect(page.locator("main")).to_contain_text("Notatka do zachowania po restarcie")
                assert page.evaluate("window.injected") is None
                draft_hash = page.evaluate("location.hash")
                page.locator('[data-nav="campaigns"]').click()
                expect(page.locator(".card")).to_have_count(1)
                page.locator(".card .open").click()
                expect(page.locator('button[data-go^="trips/"]')).to_have_count(3)
                page.locator("#variant").select_option("theme_collection")
                page.locator("#create-draft").click()
                expect(page.locator(".snapshot-day")).to_have_count(30)
                page.set_viewport_size({"width":390,"height":844})
                page.goto(base + "/documents/demo" + trip_hash)
                expect(page.locator(".day")).to_have_count(2)
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                expect(page.locator("#message")).to_be_hidden(timeout=10000)
                page.screenshot(path=str(artifacts / "editor-mobile.png"), full_page=True)
                # Restart the actual server process, not just a repository object.
                process.terminate()
                process.wait(timeout=10)
                process = start()
                page.goto(base + "/documents/demo" + trip_hash)
                expect(page.locator('[data-field="title"]')).to_have_value("Własna podróż — żółć, góry i Þingvellir")
                expect(page.locator(".day")).to_have_count(2)
                page.goto(base + "/documents/demo" + draft_hash)
                expect(page.locator(".snapshot-day")).to_have_count(2)
                expect(page.locator("main")).to_contain_text("Notatka do zachowania po restarcie")
                assert not errors, errors
                assert all(url.startswith(base + "/") for url in requests), requests
                browser.close()
        finally:
            if process and process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
    print("Document Studio browser PASS: library, 15 days, add/remove days and stops, save, drafts, campaign, mobile, XSS escaping, actual process restart; no external requests.")


if __name__ == "__main__":
    run()
    from studio_catalog_qa import run_catalog
    run_catalog()
    from library_qa import run_library
    run_library()
    from reliability_qa import run as run_reliability
    run_reliability()
