import ipaddress
import os
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import Field

from app.document_studio.models import Campaign, DocumentDraft, Identifier, Model, Title, Trip, Text, OfferData, PilotData, DayOverride
from app.document_studio.repository import ConflictError, JsonRepository, StorageError
from app.document_studio.service import DocumentService
from app.document_studio.templates import TEMPLATES
from app.document_studio.assets import AssetStore, MAX_UPLOAD_BYTES
from app.document_studio.marketing import build_marketing
from app.document_studio.rendering import render_marketing
from app.document_studio.rendering.trip_documents import render_trip_document
from app.document_studio.trip_documents import trip_document_issues, SUPPORTED_TRIP_TEMPLATES

WEB = Path(__file__).parent / "frontend"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def local_only(request: Request):
    """Do not trust proxy headers. Docker access requires explicit opt-in and localhost Host."""
    try:
        peer = ipaddress.ip_address(request.client.host if request.client else "")
        local_peer = peer.is_loopback or (os.getenv("DOCUMENT_STUDIO_DOCKER_LOCAL") == "1" and peer.is_private)
        origin = request.headers.get("origin")
        origin_ok = not origin or (origin == f"{request.url.scheme}://{request.headers.get('host')}")
        allowed = (
            local_peer and request.url.hostname in LOCAL_HOSTS and origin_ok
            and not any(h in request.headers for h in ("forwarded", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"))
            and request.headers.get("sec-fetch-site") != "cross-site"
        )
    except ValueError:
        allowed = False
    if not allowed:
        raise HTTPException(403, "Document Studio jest dostępne wyłącznie lokalnie.")


class DraftRequest(Model):
    template_id: str
    source_type: Literal["trip", "campaign"]
    source_id: Identifier
    layout_variant: str = "standard"
    title: Title | None = None
    editorial_notes: str = Field(default="", max_length=20000)
    demo_example: bool = False


class DraftUpdate(Model):
    revision: int = Field(ge=1)
    title: Title
    date_label: str = Field(default="", max_length=200)
    editorial_notes: Text = ""
    day_overrides: list[DayOverride] = Field(default_factory=list)
    offer_data: OfferData | None = None
    pilot_data: PilotData | None = None


class TripPreviewRequest(Model):
    draft: DocumentDraft


class MarketingPreviewRequest(Model):
    campaign: Campaign
    output_format: Literal["a4", "social"] = "a4"


def document_router(repository: JsonRepository):
    router = APIRouter(dependencies=[Depends(local_only)])
    service = DocumentService(repository)
    assets = AssetStore(repository)

    def marketing_data(campaign, trips=None, label="Podgląd roboczy"):
        trips = trips if trips is not None else [repository.get("trips", i.trip_id) for i in campaign.items]
        return build_marketing(campaign, trips, assets, label)

    def html(document, output_format):
        return HTMLResponse(render_marketing(document, output_format), headers={
            "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "same-origin",
        })

    def run(operation):
        try:
            return operation()
        except KeyError:
            raise HTTPException(404, "Nie znaleziono danych źródłowych.") from None
        except ConflictError as exc:
            raise HTTPException(409, str(exc)) from None
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
        except StorageError:
            raise HTTPException(503, "Błąd lokalnego magazynu JSON. Sprawdź pliki i uprawnienia.") from None

    @router.get("/documents/demo", include_in_schema=False)
    def panel():
        return FileResponse(WEB / "index.html", headers={"Cache-Control": "no-store"})

    @router.get("/documents/assets/{filename}", include_in_schema=False)
    def asset(filename: str):
        if filename not in {"studio.js", "studio.css", "marketing-editor.js", "marketing-editor.css", "brand-tokens.css", "marketing.css", "print-export.js", "trip-documents.css", "trip-editor.js", "trip-editor.css"}:
            raise HTTPException(404)
        return FileResponse(WEB / filename)

    @router.get("/api/document-studio/templates")
    def templates():
        return list(TEMPLATES.values())

    @router.get("/api/document-studio/trips", response_model=list[Trip])
    def trips():
        return run(lambda: repository.list("trips"))

    @router.get("/api/document-studio/trips/{identifier}", response_model=Trip)
    def trip(identifier: Identifier):
        return run(lambda: repository.get("trips", identifier))

    @router.post("/api/document-studio/trips", status_code=201, response_model=Trip)
    def create_trip(value: Trip):
        return run(lambda: repository.save("trips", value, create=True))

    @router.put("/api/document-studio/trips/{identifier}", response_model=Trip)
    def update_trip(identifier: Identifier, value: Trip):
        if identifier != value.trip_id:
            raise HTTPException(422, "ID ścieżki i danych muszą być zgodne")
        def update():
            repository.get("trips", identifier)
            return repository.save("trips", value)
        return run(update)

    @router.get("/api/document-studio/campaigns", response_model=list[Campaign])
    def campaigns():
        return run(lambda: repository.list("campaigns"))

    @router.get("/api/document-studio/campaigns/{identifier}", response_model=Campaign)
    def campaign(identifier: Identifier):
        return run(lambda: repository.get("campaigns", identifier))

    @router.post("/api/document-studio/campaigns", status_code=201, response_model=Campaign)
    def create_campaign(value: Campaign):
        return run(lambda: service.save_campaign(value, create=True))

    @router.put("/api/document-studio/campaigns/{identifier}", response_model=Campaign)
    def update_campaign(identifier: Identifier, value: Campaign):
        if identifier != value.campaign_id:
            raise HTTPException(422, "ID ścieżki i danych muszą być zgodne")
        def update():
            repository.get("campaigns", identifier)
            return service.save_campaign(value)
        return run(update)

    @router.get("/api/document-studio/drafts", response_model=list[DocumentDraft])
    def drafts():
        return run(lambda: repository.list("drafts"))

    @router.get("/api/document-studio/drafts/{identifier}", response_model=DocumentDraft)
    def draft(identifier: Identifier):
        return run(lambda: repository.get("drafts", identifier))

    @router.post("/api/document-studio/drafts", status_code=201, response_model=DocumentDraft)
    def create_draft(value: DraftRequest):
        return run(lambda: service.create_draft(value))

    @router.put("/api/document-studio/drafts/{identifier}", response_model=DocumentDraft)
    def update_draft(identifier: Identifier, value: DraftUpdate):
        return run(lambda: service.update_draft(identifier, value))

    @router.post("/api/document-studio/trip-documents/validate")
    def validate_trip_document(value: TripPreviewRequest):
        return run(lambda: trip_document_issues(value.draft, assets))

    @router.post("/api/document-studio/trip-documents/preview")
    def preview_trip_document(value: TripPreviewRequest):
        return run(lambda: HTMLResponse(render_trip_document(value.draft, assets), headers={"Cache-Control":"no-store"}))

    @router.get("/api/document-studio/assets")
    def asset_list():
        return run(lambda: repository.list("assets"))

    @router.post("/api/document-studio/assets", status_code=201)
    async def upload_asset(request: Request, filename: str = Query(min_length=1, max_length=200), rights_confirmed: bool = False):
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > MAX_UPLOAD_BYTES:
                raise HTTPException(413, "Zdjęcie przekracza limit 8 MB.")
        return run(lambda: assets.upload(bytes(data), request.headers.get("content-type", "").split(";")[0].lower(), filename, rights_confirmed))

    @router.get("/api/document-studio/assets/{identifier}/content")
    def asset_content(identifier: Identifier):
        def content():
            asset, path = assets.get(identifier)
            return FileResponse(path, media_type=asset.media_type, headers={"X-Content-Type-Options":"nosniff", "Cache-Control":"private, no-store"})
        return run(content)

    @router.post("/api/document-studio/marketing/validate")
    def validate_marketing(value: MarketingPreviewRequest):
        return run(lambda: marketing_data(value.campaign).issues)

    @router.post("/api/document-studio/marketing/preview")
    def preview_marketing(value: MarketingPreviewRequest):
        return run(lambda: html(marketing_data(value.campaign), value.output_format))

    @router.get("/api/document-studio/campaigns/{identifier}/preview")
    def preview_campaign(identifier: Identifier, output_format: Literal["a4", "social"] = "a4"):
        return run(lambda: html(marketing_data(repository.get("campaigns", identifier)), output_format))

    @router.get("/api/document-studio/drafts/{identifier}/preview")
    def preview_draft(identifier: Identifier, output_format: Literal["a4", "social"] = "a4"):
        def preview():
            draft = repository.get("drafts", identifier)
            if draft.template_id in SUPPORTED_TRIP_TEMPLATES:
                if output_format != "a4":
                    raise ValueError("Oferta i rozpiska pilota obsługują format A4")
                return HTMLResponse(render_trip_document(draft, assets), headers={"Cache-Control":"no-store", "X-Content-Type-Options":"nosniff"})
            if draft.template_id != "marketing.collection" or not draft.campaign_snapshot:
                raise ValueError("Podgląd graficzny jest dostępny dla marketing.collection.")
            campaign = draft.campaign_snapshot.model_copy(deep=True)
            campaign.layout_variant = draft.layout_variant
            campaign.title = draft.title
            return html(marketing_data(campaign, draft.campaign_trip_snapshots,
                        f"Dokument {draft.document_id[:8]} · rewizja {draft.revision} · szablon {draft.template_version}"), output_format)
        return run(preview)

    return router
