"""Real-editor assertions shared by local JSON and offline cloud browser compositions."""
import io
from pathlib import Path
import re
from PIL import Image
from playwright.sync_api import expect
from app.document_studio.models import DocumentSection
from app.document_studio.templates import TEMPLATES

ARTIFACTS = Path(__file__).resolve().parents[1] / "local-data/react-document-editor-qa"
CASES = (("offer.private", "standard"), ("pilot.advanced", "standard"), ("pilot.knowledge", "standard"), ("marketing.collection", "theme_collection"))


def sources(repository):
    return {kind: [item.model_dump(mode="json") for item in repository.list(kind)] for kind in ("trips", "campaigns")}


def enrich(api, identifier):
    response = api("GET", "/api/document-studio/drafts/" + identifier)
    assert response.status_code == 200
    draft = response.json()
    image = io.BytesIO(); Image.new("RGB", (3, 3), "white").save(image, format="PNG")
    response = api("POST", "/api/document-studio/assets?filename=qa.png&rights_confirmed=true", content=image.getvalue(), headers={"content-type": "image/png"})
    assert response.status_code == 201
    asset = response.json()
    gallery = DocumentSection(kind="gallery", title="Załącznik QA", order=len(draft["sections"]), images=[{"asset_id": asset["asset_id"], "caption": "Podpis istniejącego zdjęcia", "position": {"x": 12, "y": 34, "zoom": 1.4}}]).model_dump(mode="json")
    payload = {"revision": draft["revision"], "title": draft["title"], "sections": [*draft["sections"], gallery]}
    if draft["offer_data"]:
        payload["offer_data"] = {**draft["offer_data"], "summary": "Syntetyczna oferta QA", "photo_asset_ids": [asset["asset_id"]], "price": {"amount": "123.45", "currency": "PLN", "unit": "person", "status": "confirmed", "source": "Syntetyczna wycena QA"}}
    if draft["pilot_data"]:
        payload["pilot_data"] = {**draft["pilot_data"], "leader": "Pilot QA", "contacts": [{"label": "Syntetyczny kontakt", "value": "QA-PRIVATE-CONTACT"}], "accommodations": [{"entry_id": "qa-stay", "day_id": draft["trip_snapshot"]["days"][0]["day_id"], "title": "Nocleg QA", "booking_reference": "QA-BOOKING", "time_zone": "Europe/Warsaw"}]}
    if draft["campaign_snapshot"]:
        payload["campaign_snapshot"] = {**draft["campaign_snapshot"], "description": "Syntetyczna treść kampanii QA"}
    response = api("PUT", "/api/document-studio/drafts/" + identifier, json=payload)
    assert response.status_code == 200
    return response.json()


def exercise(context, base, repository, *, label, can_edit, api):
    errors, external, writes, creates = [], [], [], []
    context.on("request", lambda request: external.append(request.url) if not request.url.startswith(base + "/") else None)
    def seen(request):
        if "/api/document-studio/drafts" in request.url:
            if request.method == "PUT": writes.append(request.post_data_json)
            if request.method == "POST": creates.append(request.post_data_json)
    context.on("request", seen)
    page = context.new_page()
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.add_init_script("window.__cspViolations=[];document.addEventListener('securitypolicyviolation',e=>window.__cspViolations.push(e.violatedDirective));")
    before = sources(repository)
    if not can_edit:
        identifier = repository.list("drafts")[0].document_id
        page.goto(base + f"/app/documents/{identifier}/edit")
        expect(page.get_by_role("alert")).to_have_text("Brak uprawnień do edycji dokumentu.")
        assert page.get_by_label("Tytuł dokumentu").count() == 0 and not writes and not creates
    else:
        for template_id, variant in CASES:
            template = TEMPLATES[template_id]
            page.goto(base + "/app/documents/new?template=" + template_id)
            page.get_by_label("Wariant układu").select_option(variant)
            page.get_by_role("button", name="Dalej: źródło").click()
            source_id = "react-qa-source" if template.source_type == "trip" else "react-qa-campaign"
            page.locator(f'input[name="source"][value="{source_id}"]').check()
            page.get_by_role("button", name="Dalej: potwierdzenie").click()
            page.get_by_label("Tytuł dokumentu").fill(f"QA {label} {template_id}")
            page.get_by_role("button", name="Utwórz i zapisz dokument").click()
            expect(page.get_by_role("heading", name="Dokument został zapisany", exact=True)).to_be_visible()
            identifier = creates[-1]["document_id"]
            original = enrich(api, identifier)
            page.get_by_role("link", name="Edytuj w React", exact=True).click()
            expect(page.get_by_role("heading", name="Edytuj dokument", exact=True)).to_be_visible()
            expect(page.get_by_label("Tytuł dokumentu")).to_have_value(original["title"])
            page.get_by_label("Tytuł dokumentu").fill("Zmieniony " + template_id)
            page.get_by_label("Dodatkowe uwagi sekcji źródłowej").fill("Uwagi sekcji źródłowej QA")
            page.get_by_role("button", name="Dodaj sekcję", exact=True).click()
            page.get_by_label("Tytuł sekcji", exact=True).fill("Własna treść QA")
            page.get_by_label("Treść sekcji", exact=True).fill("Zachowany tekst testowy — żółć.")
            page.get_by_role("button", name="Przesuń sekcję w górę").click()
            if template_id == "pilot.advanced":
                page.get_by_role("navigation", name="Sekcje dokumentu").get_by_role("button", name=re.compile("· Logistyka ·")).first.click()
                page.get_by_label("Dystans jazdy (km)", exact=True).fill("12.5")
                page.get_by_label("Strefa IANA", exact=True).fill("Europe/Warsaw")
                page.get_by_label("Notatki organizacyjne", exact=True).fill("Syntetyczna logistyka QA")
                page.get_by_label("Plan B", exact=True).fill("Wariant QA")
                page.get_by_label("Nocleg ze wspólnej logistyki").select_option("qa-stay")
                page.get_by_label("Status weryfikacji").select_option("verified")
                expect(page.get_by_role("button", name="Zapisz zmiany", exact=True)).to_be_disabled()
                page.get_by_label("Źródło pomiaru", exact=True).fill("Syntetyczny pomiar QA")
            if template_id == "pilot.knowledge":
                page.get_by_role("navigation", name="Sekcje dokumentu").get_by_role("button", name=re.compile("· Wiedza ·")).first.click()
                page.get_by_label("Fakty i opisy atrakcji").fill("Syntetyczna treść QA")
                page.get_by_label("Status weryfikacji").select_option("verified")
                expect(page.get_by_role("button", name="Zapisz zmiany", exact=True)).to_be_disabled()
                page.get_by_role("button", name="Dodaj źródło", exact=True).click()
                page.get_by_label("Dokładne odniesienie 1").fill("Syntetyczne opracowanie QA")
                page.get_by_label("Data sprawdzenia 1").fill("2026-10-31")
            for width in (320, 390, 768, 1024):
                page.set_viewport_size({"width": width, "height": 900})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (label, template_id, width)
            page.set_viewport_size({"width": 390, "height": 844})
            page.screenshot(path=str(ARTIFACTS / f"{label}-{template_id}-dirty-mobile.png"), full_page=True)
            page.get_by_role("link", name="Wróć do biblioteki", exact=True).click()
            expect(page.get_by_role("alertdialog")).to_be_visible()
            page.get_by_role("button", name="Zostań w formularzu", exact=True).click()
            count = len(writes)
            page.get_by_role("button", name="Zapisz zmiany", exact=True).focus(); page.keyboard.press("Enter")
            if template_id == "pilot.advanced" and label == "local":
                expect(page.get_by_text("Niepewny wynik zapisu.", exact=False)).to_be_visible()
                assert len(writes) == count + 1
                page.get_by_role("button", name="Sprawdź wersję serwera", exact=True).click()
            expect(page.get_by_text(f"Zapisano rewizję {original['revision'] + 1}.", exact=True)).to_be_visible()
            assert len(writes) == count + 1
            payload = writes[-1]
            assert set(payload) == {"revision", "title", "sections"} and payload["revision"] == original["revision"]
            saved = repository.get("drafts", identifier).model_dump(mode="json")
            for key in ("trip_snapshot", "campaign_snapshot", "campaign_trip_snapshots", "offer_data", "offer_details", "pilot_data", "confidentiality", "template_id", "layout_variant", "data_origin", "created_at", "created_by", "document_status", "day_overrides"):
                assert saved[key] == original[key], (template_id, key)
            assert saved["revision"] == original["revision"] + 1
            assert saved["sections"][0]["body"] == "Uwagi sekcji źródłowej QA"
            assert saved["sections"][-2]["title"] == "Własna treść QA" and saved["sections"][-2]["body"] == "Zachowany tekst testowy — żółć."
            assert {k: v for k, v in saved["sections"][-1].items() if k != "order"} == {k: v for k, v in original["sections"][-1].items() if k != "order"}, "Unedited gallery asset/crop/caption was lost"
            assert [s["order"] for s in saved["sections"]] == list(range(len(saved["sections"])))
            assert {s["section_id"] for s in original["sections"]} < {s["section_id"] for s in saved["sections"]}
            assert repository.get_revision(identifier, original["revision"]).model_dump(mode="json") == original
            page.reload(); expect(page.get_by_label("Tytuł dokumentu")).to_have_value(saved["title"])
            expect(page.get_by_role("button", name="Zapisz zmiany", exact=True)).to_be_disabled()
            page.set_viewport_size({"width": 1440, "height": 1100})
            page.screenshot(path=str(ARTIFACTS / f"{label}-{template_id}-saved.png"), full_page=True)
            with context.expect_page() as opened:
                page.get_by_role("link", name="Podgląd ostatniego zapisu (nowa karta)", exact=True).click()
            preview = opened.value; preview.wait_for_load_state(); expect(preview.locator("body")).to_contain_text("Zachowany tekst testowy")
            preview.close()
            page.get_by_role("link", name="Szczegóły i historia", exact=True).click()
            expect(page.get_by_role("heading", name=f"Rewizja {saved['revision']}", exact=True)).to_be_visible()
            expect(page.get_by_role("heading", name=f"Rewizja {original['revision']}", exact=True)).to_be_visible()
            page.get_by_role("link", name=re.compile("Edytuj w React")).click()
            expect(page.get_by_label("Tytuł dokumentu")).to_have_value(saved["title"])
            if template_id == "offer.private":
                concurrent = api("PUT", "/api/document-studio/drafts/" + identifier, json={"revision": saved["revision"], "title": "Inny redaktor QA"})
                assert concurrent.status_code == 200
                page.get_by_label("Tytuł dokumentu").fill("Lokalna zmiana po konflikcie")
                page.get_by_role("button", name="Zapisz zmiany", exact=True).click()
                expect(page.get_by_text("Konflikt —", exact=False)).to_be_visible()
                expect(page.get_by_label("Tytuł dokumentu")).to_have_value("Lokalna zmiana po konflikcie")
                page.get_by_role("button", name="Sprawdź wersję serwera", exact=True).click()
                expect(page.get_by_role("heading", name=f"Wersja serwera: rewizja {saved['revision'] + 1}")).to_be_visible()
                page.get_by_role("button", name="Wczytaj wersję serwera i odrzuć moje zmiany").click()
                page.get_by_role("button", name="Potwierdź odrzucenie", exact=True).click()
                expect(page.get_by_label("Tytuł dokumentu")).to_have_value("Inny redaktor QA")
            page.get_by_role("link", name="Edytuj w dotychczasowym Studio", exact=True).click()
            expect(page.locator("#m-save" if template.source_type == "campaign" else "#d-save")).to_be_visible()
    assert sources(repository) == before
    assert not errors and not external, (errors, external)
    assert page.evaluate("window.__cspViolations") == []
    page.close()
