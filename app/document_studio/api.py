import ipaddress
import os
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Path as ApiPath
from fastapi.responses import FileResponse, HTMLResponse, Response
from pydantic import Field

from app.document_studio.models import Campaign, DocumentDraft, Identifier, Model, Title, Trip, Text, OfferData, PilotData, DayOverride, OfferDetails, DocumentSection
from app.document_studio.repository import ConflictError, JsonRepository, StorageError
from app.document_studio.service import DocumentService
from app.document_studio.templates import TEMPLATES
from app.document_studio.assets import AssetStore, MAX_UPLOAD_BYTES
from app.document_studio.marketing import build_marketing
from app.document_studio.rendering import render_marketing
from app.document_studio.library import DocumentLibrary, LibraryMutation, StatusMutation, LibraryPage, DocumentSummary

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
    offer_details: OfferDetails | None = None
    sections: list[DocumentSection] | None = None
    campaign_snapshot: Campaign | None = None
    document_status: Literal["draft", "in_review", "ready"] = "draft"


class TripPreviewRequest(Model):
    draft: DocumentDraft
    output_format: Literal["a4", "social"] = "a4"


class MarketingPreviewRequest(Model):
    campaign: Campaign
    output_format: Literal["a4", "social"] = "a4"


def document_router(repository, *, access_policy=local_only, asset_store=None, cloud_mode=False):
    router = APIRouter(dependencies=[Depends(access_policy)])
    assets = asset_store or AssetStore(repository)
    service = DocumentService(repository, assets)
    library = DocumentLibrary(repository)

    def actor(request):
        return getattr(request.state, "principal", None) if cloud_mode else None

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
            raise HTTPException(503, "Magazyn dokumentów jest niedostępny. Spróbuj ponownie.") from None

    @router.get("/documents/demo", include_in_schema=False)
    def panel():
        if cloud_mode:
            return HTMLResponse((WEB / "index.html").read_text(encoding="utf-8").replace("Lokalne demo", "Demo w chmurze"), headers={"Cache-Control": "no-store"})
        return FileResponse(WEB / "index.html", headers={"Cache-Control": "no-store"})

    @router.get("/documents/assets/{filename}", include_in_schema=False)
    def asset(filename: str):
        if filename not in {"studio.js", "studio.css", "marketing-editor.js", "marketing-editor.css", "brand-tokens.css", "marketing.css", "print-export.js", "trip-documents.css", "trip-editor.js", "trip-editor.css", "section-editor.js", "library.js"}:
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
    def create_draft(value: DraftRequest, request: Request):
        return run(lambda: service.create_draft(value, actor(request)))

    @router.put("/api/document-studio/drafts/{identifier}", response_model=DocumentDraft)
    def update_draft(identifier: Identifier, value: DraftUpdate, request: Request):
        return run(lambda: service.update_draft(identifier, value, actor(request)))

    @router.get("/api/document-studio/library", response_model=LibraryPage)
    def list_library(response: Response, search: str = Query(default="", max_length=200), family: Literal["offer", "pilot", "marketing"] | None = None,
                     template_id: str | None = None, document_status: Literal["draft", "in_review", "ready", "archived"] | None = None,
                     archived: Literal["exclude", "include", "only"] = "exclude",
                     sort: Literal["title", "created_at", "updated_at"] = "updated_at", direction: Literal["asc", "desc"] = "desc",
                     offset: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=100)):
        response.headers["Cache-Control"] = "private, no-store"
        return run(lambda: library.list(search=search.strip(), family=family, template_id=template_id,
            document_status=document_status, archived=archived, sort=sort, direction=direction, offset=offset, limit=limit))

    @router.post("/api/document-studio/library/{identifier}/duplicate", status_code=201)
    def duplicate_document(identifier: Identifier, value: LibraryMutation, request: Request):
        return run(lambda: library.duplicate(identifier, value, actor(request)))

    @router.post("/api/document-studio/library/{identifier}/archive")
    def archive_document(identifier: Identifier, value: LibraryMutation, request: Request):
        return run(lambda: library.transition(identifier, value, "archive", actor(request)))

    @router.post("/api/document-studio/library/{identifier}/restore")
    def restore_document(identifier: Identifier, value: LibraryMutation, request: Request):
        return run(lambda: library.transition(identifier, value, "restore", actor(request)))

    @router.post("/api/document-studio/library/{identifier}/status")
    def document_status(identifier: Identifier, value: StatusMutation, request: Request):
        return run(lambda: library.transition(identifier, value, "status", actor(request)))

    @router.get("/api/document-studio/library/{identifier}/revisions", response_model=list[DocumentSummary])
    def document_revisions(identifier: Identifier, response: Response):
        response.headers["Cache-Control"] = "private, no-store"
        return run(lambda: repository.list_revisions(identifier))

    @router.get("/api/document-studio/library/{identifier}/revisions/{revision}")
    def document_revision(identifier: Identifier, response: Response, revision: int = ApiPath(ge=1)):
        response.headers["Cache-Control"] = "private, no-store"
        return run(lambda: repository.get_revision(identifier, revision))

    @router.get("/api/document-studio/library/{identifier}/revisions/{revision}/preview")
    def revision_preview(identifier: Identifier, revision: int = ApiPath(ge=1), output_format: Literal["a4", "social"] = "a4"):
        from app.document_studio.rendering.sections import render_document
        return run(lambda: HTMLResponse(render_document(repository.get_revision(identifier, revision), assets, output_format),
            headers={"Cache-Control":"no-store", "X-Content-Type-Options":"nosniff"}))

    @router.post("/api/document-studio/trip-documents/validate")
    def validate_trip_document(value: TripPreviewRequest):
        from app.document_studio.rendering.sections import document_issues
        return run(lambda: document_issues(value.draft, assets))

    @router.post("/api/document-studio/trip-documents/initialize")
    def initialize_sections(value: TripPreviewRequest):
        from app.document_studio.sections import default_sections
        def initialize():
            draft = value.draft
            if draft.sections is None:
                draft.sections = default_sections(draft)
            if draft.template_id.startswith("offer.") and draft.offer_details is None:
                draft.offer_details = OfferDetails()
            return draft
        return run(initialize)

    @router.post("/api/document-studio/trip-documents/preview")
    def preview_trip_document(value: TripPreviewRequest):
        from app.document_studio.rendering.sections import render_document
        return run(lambda: HTMLResponse(render_document(value.draft, assets, value.output_format), headers={"Cache-Control":"no-store"}))

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
            if isinstance(path, bytes):
                return Response(path, media_type=asset.media_type, headers={"X-Content-Type-Options":"nosniff", "Cache-Control":"private, no-store"})
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
            from app.document_studio.rendering.sections import render_document
            return HTMLResponse(render_document(draft, assets, output_format), headers={"Cache-Control":"no-store", "X-Content-Type-Options":"nosniff"})
        return run(preview)

    return router
