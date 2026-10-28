import os
import sqlite3
from contextlib import asynccontextmanager
from typing import Literal
from uuid import UUID

from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, StringConstraints
from typing_extensions import Annotated

from app.db import Database
from app.waha import WahaSettings, webhook_router
from app.viewer import STATIC_DIR, viewer_router


class TripRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)]


class TripAccepted(BaseModel):
    trip_id: UUID
    status: Literal["queued"] = "queued"


class TripStatus(BaseModel):
    trip_id: UUID
    request_text: str
    status: Literal["queued", "running", "completed", "failed"]
    result: dict | None
    error: str | None
    created_at: str
    updated_at: str


def create_app(database_path=None, *, waha_settings=None, document_data_path=None, document_fixtures_path=None,
               cloud_components=None):
    from app.cloud_preview import CloudSettings, create_preview_app
    cloud = CloudSettings.from_env()
    if cloud is not None and cloud.mode == "readonly_demo":
        return create_preview_app(cloud)
    from app.document_studio.api import document_router, local_only
    from app.document_studio.repository import JsonRepository
    access_policy, asset_store = local_only, None
    if cloud is not None:
        from app.cloud_runtime import DemoSettings, build_components
        from app.cloud_access import authenticated_demo
        settings = DemoSettings.from_env(cloud)
        components = cloud_components or build_components(settings)
        database, document_repository = components.jobs, components.repository
        access_policy, asset_store = authenticated_demo, components.assets
    else:
        database = Database(database_path or os.getenv("DATABASE_PATH", "data/tripse.sqlite3"))
        document_repository = JsonRepository(
            document_data_path or os.getenv("DOCUMENT_STUDIO_DATA_PATH"), document_fixtures_path,
        )

    @asynccontextmanager
    async def lifespan(app):
        database.initialize()
        document_repository.initialize()
        yield

    app = FastAPI(title="Tripse AI Trip Planner Demo v0.1", lifespan=lifespan,
                  **({"docs_url": None, "redoc_url": None, "openapi_url": None} if cloud else {}))
    if cloud:
        from fastapi.responses import JSONResponse
        from starlette.concurrency import run_in_threadpool
        from app.cloud_jobs import principal
        from app.document_studio.repository import StorageError
        from google.api_core.exceptions import GoogleAPIError

        @app.middleware("http")
        async def cloud_boundary(request, call_next):
            marker = None
            try:
                if request.url.path != "/health":
                    if request.headers.get("host") != settings.origin.removeprefix("https://"):
                        raise HTTPException(400, "Unexpected request host")
                    subject = await run_in_threadpool(components.access.authenticate, request)
                    marker = principal.set(subject)
                response = await call_next(request)
            except HTTPException as exc:
                response = JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
            except (StorageError, GoogleAPIError):
                response = JSONResponse({"detail": "Cloud storage or queue unavailable; retry safely"}, status_code=503)
            finally:
                if marker is not None:
                    principal.reset(marker)
            response.headers.update({"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
                                     "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY"})
            return response

        @app.post("/internal/jobs/{trip_id}", include_in_schema=False)
        def process_cloud_job(trip_id: UUID):
            database.process(str(trip_id))
            return {"status": "processed"}
    else:
        app.include_router(webhook_router(database, waha_settings or WahaSettings.from_env()))

    @app.get("/", include_in_schema=False)
    def home():
        return RedirectResponse("/hub", status_code=302, headers={"Cache-Control": "no-store"})

    app.include_router(viewer_router(database, cloud_mode=bool(cloud)))
    from app.demo import demo_router
    app.include_router(demo_router(database, cloud_mode=bool(cloud)))
    app.include_router(document_router(document_repository, access_policy=access_policy, asset_store=asset_store, cloud_mode=bool(cloud)))
    from app.hub import hub_router
    app.include_router(hub_router(access_policy=access_policy, cloud_mode=bool(cloud)))
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/health")
    def health():
        if cloud:
            return {"status": "ok", "environment": cloud.environment, "generation_mode": "mock",
                    "feature_mode": "cloud_demo", "image_version": cloud.version, "service": cloud.service,
                    "storage": "gcs_firestore"}
        try:
            database.check()
        except sqlite3.Error:
            raise HTTPException(status_code=503, detail="Database unavailable") from None
        return {"status": "ok", "generation_mode": os.getenv("PLANNING_MODE", "live")}

    @app.post("/api/trips", status_code=202, response_model=TripAccepted)
    def create_trip(request: TripRequest, response: Response, http_request: Request):
        key = http_request.headers.get("idempotency-key")
        if cloud:
            if key is not None:
                try:
                    key = str(UUID(key))
                except ValueError:
                    raise HTTPException(422, "Invalid Idempotency-Key") from None
            trip_id = database.create_trip(request.text, idempotency_key=key)
        else:
            trip_id = database.create_trip(request.text)
        response.headers["Location"] = f"/api/trips/{trip_id}"
        return {"trip_id": trip_id, "status": "queued"}

    @app.get("/api/trips/{trip_id}", response_model=TripStatus)
    def get_trip(trip_id: UUID):
        trip = database.get_trip(str(trip_id))
        if trip is None:
            raise HTTPException(status_code=404, detail="Trip not found")
        return trip

    return app


app = create_app()
