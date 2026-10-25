import os
import sqlite3
from contextlib import asynccontextmanager
from typing import Literal
from uuid import UUID

from fastapi import FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles
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


def create_app(database_path=None, *, waha_settings=None, document_data_path=None, document_fixtures_path=None):
    database = Database(database_path or os.getenv("DATABASE_PATH", "data/tripse.sqlite3"))
    from app.document_studio.api import document_router
    from app.document_studio.repository import JsonRepository
    document_repository = JsonRepository(
        document_data_path or os.getenv("DOCUMENT_STUDIO_DATA_PATH"), document_fixtures_path,
    )

    @asynccontextmanager
    async def lifespan(app):
        database.initialize()
        document_repository.initialize()
        yield

    app = FastAPI(title="Tripse AI Trip Planner Demo v0.1", lifespan=lifespan)
    app.include_router(webhook_router(database, waha_settings or WahaSettings.from_env()))
    app.include_router(viewer_router(database))
    from app.demo import demo_router
    app.include_router(demo_router(database))
    app.include_router(document_router(document_repository))
    from app.hub import hub_router
    app.include_router(hub_router())
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/health")
    def health():
        try:
            database.check()
        except sqlite3.Error:
            raise HTTPException(status_code=503, detail="Database unavailable") from None
        return {"status": "ok", "generation_mode": os.getenv("PLANNING_MODE", "live")}

    @app.post("/api/trips", status_code=202, response_model=TripAccepted)
    def create_trip(request: TripRequest, response: Response):
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
