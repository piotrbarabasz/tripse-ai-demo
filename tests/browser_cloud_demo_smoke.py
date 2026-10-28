"""Offline authenticated cloud UI against real routers and injected cloud stores.

Every browser request is intercepted; external requests fail the run. This is
not evidence about deployed IAP, GCP SDK consistency or real Google Maps billing.
Run: python tests/browser_cloud_demo_smoke.py
"""
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pytest
from playwright.sync_api import expect, sync_playwright


def run():
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("CLOUD_FEATURE_MODE", "local")
        patch.setenv("PLANNING_MODE", "mock")
        for key in ("K_SERVICE", "OPENAI_API_KEY", "GOOGLE_MAPS_API_KEY", "GOOGLE_PLACES_API_KEY",
                    "GOOGLE_ROUTES_API_KEY", "GOOGLE_MAPS_BROWSER_KEY", "WAHA_API_KEY", "WAHA_WEBHOOK_HMAC_KEY"):
            patch.delenv(key, raising=False)
        from test_cloud_demo import cloud_demo, ORIGIN
        demo = cloud_demo.__wrapped__(patch)
        artifacts = ROOT / "local-data/cloud-demo-qa"
        artifacts.mkdir(parents=True, exist_ok=True)
        errors, external = [], []
        with demo.client() as client, demo.client("task") as task, sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("dialog", lambda dialog: dialog.accept())

            def route_request(route):
                request = route.request
                if request.url.startswith("https://maps.googleapis.com/maps/api/js?") and "key=fake-browser-key" in request.url:
                    from browser_smoke import MAPS_DOUBLE
                    script = MAPS_DOUBLE.replace("window.tripseMapsReady();", "window.google.maps.LatLng = class {constructor(lat,lng){this.a=lat;this.o=lng;}lat(){return this.a;}lng(){return this.o;}}; window.tripseMapsReady();")
                    route.fulfill(status=200, content_type="application/javascript", body=script)
                    return
                if not request.url.startswith(ORIGIN + "/"):
                    external.append(request.url)
                    route.abort()
                    return
                path = urlsplit(request.url).path
                response = client.request(request.method, request.url,
                    headers=request.all_headers(), content=request.post_data_buffer, follow_redirects=False)
                if response.status_code == 202 and path in {"/api/trips", "/api/demo/messages"}:
                    job_id = response.json()["trip_id"]
                    assert task.post(f"/internal/jobs/{job_id}").status_code == 200
                # TestClient transparently decodes transfer encodings; do not
                # forward a stale content-length into Playwright fulfillment.
                headers = {key: value for key, value in response.headers.items()
                           if key.lower() not in {"content-length", "content-encoding"}}
                route.fulfill(status=response.status_code, headers=headers, body=response.content)

            context.route("**/*", route_request)
            # Playwright routes only the first URL of a redirected request. Check
            # the redirect at the ASGI boundary, then load its destination offline.
            root = client.get("/", follow_redirects=False)
            assert root.status_code == 302 and root.headers["location"] == "/hub"
            page.goto(ORIGIN + root.headers["location"])
            assert page.url == ORIGIN + "/hub"
            assert page.locator("#planner-link").get_attribute("href") == "/planner"
            expect(page.locator(".environment")).to_contain_text("Demo w chmurze")
            page.goto(ORIGIN + "/documents/demo#trips/demo-canada")
            expect(page.locator(".day")).to_have_count(15)
            page.locator(".module-hub-link").click()
            page.locator("#documents-link").click()
            page.goto(ORIGIN + "/documents/demo#trips/demo-canada")
            expect(page.locator(".day")).to_have_count(15)
            page.locator('[data-field="title"]').fill("Cloud persisted 15 day trip")
            page.locator("#save-trip").click()
            expect(page.locator("#message")).to_have_text("Program wycieczki zapisany.")
            page.reload()
            expect(page.locator('[data-field="title"]')).to_have_value("Cloud persisted 15 day trip")
            for template in ("offer.private", "pilot.basic"):
                page.goto(ORIGIN + "/documents/demo#trips/demo-iceland")
                page.locator("#create-draft").click()
                page.locator('[data-create-template="'+template+'"]').click()
                page.locator('#source-demo-option details').evaluate('el=>el.open=true')
                page.locator('#flow-demo').check()
                page.locator("#source-create").click()
                expect(page.locator("#d-save")).to_be_visible()
                page.locator("#d-save").click()
                expect(page.locator("#d-revision")).to_have_text("2")
                frame = page.frame_locator("#d-preview")
                expect(frame.locator(".sheet").first).to_be_visible()
                page.locator("#document-review").click()
                with page.expect_popup() as popup:
                    page.locator("#review-export").click()
                preview = popup.value
                preview.wait_for_load_state()
                preview.pdf(path=str(artifacts / f"{template}.pdf"), prefer_css_page_size=True, print_background=True)
                preview.close()
                expect(page.frame_locator("#review-preview").locator(".sheet").first).to_be_visible()
                page.screenshot(path=str(artifacts / f"{template}.png"), full_page=True)
            page.goto(ORIGIN + "/planner")
            page.reload()
            expect(page.locator("#trip-form")).to_be_visible()
            expect(page.locator("#hub-return")).to_be_visible()
            page.locator("#hub-return").click()
            expect(page.locator("#planner-link")).to_be_visible()
            page.locator("#planner-link").click()
            assert page.url == ORIGIN + "/planner"
            page.locator("#examples button").first.click()
            page.locator("#submit-trip").click()
            expect(page.locator("#open-trip")).to_be_visible(timeout=15000)
            page.locator("#open-trip").click()
            expect(page.locator(".day-card")).to_have_count(2)
            page.screenshot(path=str(artifacts / "mock-viewer.png"), full_page=True)
            # Exercise the optional Google base-map path with an intercepted SDK
            # and a fake key. No real Maps request leaves this process.
            patch.setenv("GOOGLE_MAPS_BROWSER_KEY", "fake-browser-key")
            page.reload()
            expect(page.locator("#map")).to_contain_text("Google Maps test double")
            expect(page.locator("#map-caption")).to_contain_text("linie DEMO")
            assert page.evaluate("() => window.mapTest.markers.length === 5 && window.mapTest.lines.length === 2")
            patch.delenv("GOOGLE_MAPS_BROWSER_KEY")
            page.goto(ORIGIN + "/demo/chat")
            expect(page.locator("#hub-return")).to_be_visible()
            page.locator("#hub-return").click()
            page.locator("#assistant-link").click()
            assert page.url == ORIGIN + "/demo/chat"
            expect(page.locator("#chat-text")).not_to_be_empty()
            page.locator("#send").click()
            expect(page.locator(".bubble a")).to_be_visible(timeout=15000)
            page.locator("#replay").click()
            expect(page.locator("#messages")).to_contain_text("Duplikat zdarzenia")
            page.locator("#new-chat").click()
            expect(page.locator(".bubble")).to_have_count(0)
            page.screenshot(path=str(artifacts / "chat.png"), full_page=True)
            assert not errors, errors
            assert not external, external
            browser.close()
    print("Authenticated cloud UI PASS: shared Hub, 15 days/save/reload, offer/pilot editors and previews, mock planner/viewer, chat/dedup/new conversation; no external requests.")


if __name__ == "__main__":
    run()
