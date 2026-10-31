"""React writes through real FastAPI/DocumentService, temporary JSON and fake GCS."""
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time

import httpx
import pytest
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.document_studio.repository import JsonRepository
from app.document_studio.templates import TEMPLATES
from tests.react_document_fixtures import seed_documents
from scripts.dev import stop

ARTIFACTS = ROOT / "local-data/react-document-creation-qa"
CASES = (("offer.private", "standard"), ("pilot.advanced", "standard"), ("marketing.collection", "theme_collection"))
PRIVATE_NOTE = "Synthetic restricted logistics QA"


def seed_creation_sources(repository):
    seed_documents(repository, count=0)
    trip = repository.get("trips", "react-qa-source")
    trip.days[0].internal_notes = PRIVATE_NOTE
    repository.save("trips", trip)


def sources(repository):
    return {kind: [item.model_dump(mode="json") for item in repository.list(kind)] for kind in ("trips", "campaigns")}


def exercise(context, base, repository, *, label, can_edit, replay):
    errors, external, posts, reads = [], [], [], []
    context.on("request", lambda request: external.append(request.url) if not request.url.startswith(base + "/") else None)
    def seen(request):
        if request.url.endswith("/api/document-studio/drafts") and request.method == "POST": posts.append(request.post_data_json)
        if "/api/document-studio/drafts/" in request.url and request.method == "GET": reads.append(request.url)
    context.on("request", seen)
    page = context.new_page()
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.add_init_script("window.__cspViolations=[];document.addEventListener('securitypolicyviolation',e=>window.__cspViolations.push(e.violatedDirective));")
    before = sources(repository)
    count = len(repository.list("drafts"))
    if not can_edit:
        page.goto(base + "/app/documents/new?template=offer.private")
        expect(page.get_by_role("alert")).to_have_text("Brak uprawnień do tworzenia dokumentów.")
        assert page.get_by_role("radio").count() == 0
        assert page.get_by_role("button", name="Utwórz i zapisz dokument").count() == 0
        assert not posts
    else:
        for index, (template_id, variant) in enumerate(CASES):
            template = TEMPLATES[template_id]
            page.goto(base + "/app/documents")
            page.get_by_role("article").filter(has=page.get_by_role("heading", name=template.name, exact=True)).get_by_role("link", name=re.compile(r"^Utwórz dokument")).click()
            expect(page.get_by_role("radio")).to_have_count(8)
            expect(page.locator(f'input[value="{template_id}"]')).to_be_checked()
            page.reload()
            expect(page.locator(f'input[value="{template_id}"]')).to_be_checked()
            page.get_by_label("Wariant układu").select_option(variant)
            # Real keyboard activation, then mobile sources/confirmation.
            page.get_by_role("button", name="Dalej: źródło").focus()
            page.keyboard.press("Enter")
            source_id = "react-qa-source" if template.source_type == "trip" else "react-qa-campaign"
            source = repository.get("trips" if template.source_type == "trip" else "campaigns", source_id)
            page.get_by_label("Szukaj źródła").fill(source.title)
            page.get_by_role("radio", name=re.compile(re.escape(source.title))).check()
            for width in (320, 390, 768, 1024):
                page.set_viewport_size({"width": width, "height": 900})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (label, width)
            page.set_viewport_size({"width": 390, "height": 844})
            page.screenshot(path=str(ARTIFACTS / f"{label}-{index}-sources-mobile.png"), full_page=True)
            page.get_by_role("button", name="Dalej: potwierdzenie").click()
            title = f"React {label} QA {template_id}"
            page.get_by_label("Tytuł dokumentu").fill(title)
            assert len(posts) == index, "Navigation must not create drafts"
            assert PRIVATE_NOTE not in page.locator("body").inner_text(), "Selector/review exposed restricted fields"
            # Browser Back is a real router-blocked POP, not just a mocked link.
            if index == 0:
                page.go_back(wait_until="commit")
                expect(page.get_by_role("alertdialog")).to_be_visible()
                page.get_by_role("button", name="Zostań w formularzu").click()
                expect(page.get_by_label("Tytuł dokumentu")).to_have_value(title)
            page.screenshot(path=str(ARTIFACTS / f"{label}-{index}-review-mobile.png"), full_page=True)
            page.get_by_role("button", name="Utwórz i zapisz dokument").click()
            expect(page.get_by_role("heading", name="Dokument został zapisany", exact=True)).to_be_visible()
            assert len(posts) == index + 1
            payload = posts[-1]
            assert payload["source_revision"] == source.revision and payload["source_type"] == template.source_type
            identifier = payload["document_id"]
            assert any(url.endswith("/drafts/" + identifier) for url in reads), "Persisted GET verification missing"
            draft = repository.get("drafts", identifier)
            assert draft.title == title and draft.template_id == template_id and draft.layout_variant == variant
            assert draft.revision == 1 and draft.confidentiality == template.confidentiality
            assert draft.sections and all(section.section_id for section in draft.sections)
            if template.source_type == "trip":
                assert draft.trip_snapshot.trip_id == source_id and draft.trip_snapshot.revision == source.revision
                assert draft.campaign_snapshot is None
                assert draft.trip_snapshot.title == source.title
                assert draft.trip_snapshot.days[0].internal_notes == (PRIVATE_NOTE if template.family == "pilot" else "")
                assert draft.pilot_data is not None if template.family == "pilot" else draft.offer_data is not None
            else:
                assert draft.campaign_snapshot.campaign_id == source_id and draft.campaign_snapshot.revision == source.revision
                assert draft.campaign_snapshot.layout_variant == variant and draft.trip_snapshot is None
                assert [trip.trip_id for trip in draft.campaign_trip_snapshots] == [item.trip_id for item in source.items]
                assert all(trip.days[0].internal_notes == "" for trip in draft.campaign_trip_snapshots)
            # Exact frozen-ID retry uses the existing server semantics, no new
            # document/revision. The real browser itself has sent only one POST.
            response = replay(payload)
            assert response.status_code == 201 and response.json()["document_id"] == identifier
            assert repository.get("drafts", identifier).revision == 1
            page.set_viewport_size({"width": 1440, "height": 1100})
            page.screenshot(path=str(ARTIFACTS / f"{label}-{index}-saved.png"), full_page=True)
            editor = page.get_by_role("link", name="Otwórz dokument w edytorze", exact=True)
            expect(editor).to_have_attribute("href", "/documents/demo#edit-draft/" + identifier)
            editor.click()
            expect(page.locator("#m-save" if template.source_type == "campaign" else "#d-save")).to_be_visible()
            assert page.url.endswith("#edit-draft/" + identifier)
        assert len(repository.list("drafts")) == count + len(CASES)
    assert sources(repository) == before, "Creation changed an original source"
    assert not errors and not external, (errors, external)
    assert page.evaluate("window.__cspViolations") == []
    page.close()


def run():
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    assert (ROOT / "frontend/dist/index.html").is_file(), "Build frontend first"
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0)); port = listener.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory(prefix="tripse-react-create-") as temporary:
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
                exercise(context, base, repository, label="local", can_edit=True, replay=lambda payload: httpx.post(base + "/api/document-studio/drafts", json=payload))
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
                            exercise(context, ORIGIN, repository, label="cloud-" + identity, can_edit=identity == "editor", replay=lambda payload: client.post("/api/document-studio/drafts", json=payload, headers={"Origin": ORIGIN}))
                            payload = {"document_id": "forbidden-origin-test", "source_revision": 1, "template_id": "offer.private", "source_type": "trip", "source_id": "react-qa-source"}
                            # This identity double supplies an Origin by default;
                            # remove it explicitly to exercise the missing header.
                            origin = client.headers.pop("origin")
                            try:
                                assert client.post("/api/document-studio/drafts", json=payload).status_code == 403
                            finally:
                                client.headers["Origin"] = origin
                            assert client.post("/api/document-studio/drafts", json=payload, headers={"Origin": "https://evil.example"}).status_code == 403
                            if identity == "reader":
                                assert client.post("/api/document-studio/drafts", json=payload, headers={"Origin": ORIGIN}).status_code == 403
                        context.close()
                browser.close()
        finally:
            stop(server); server.wait(timeout=15)
    print("React creation PASS: Offer/Pilot/Marketing, JSON + fake-GCS editor/reader, persisted GET/snapshots/default sections, stable-ID replay, lost POST-response recovery, source immutability, Origin denial, keyboard/back/mobile/CSP, legacy editor. Evidence: local-data/react-document-creation-qa")


if __name__ == "__main__":
    run()
