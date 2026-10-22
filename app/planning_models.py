"""LLM suggestions and map-provider facts have separate schemas."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True)


class Requirements(StrictModel):
    start: str | None
    end: str | None
    days: int | None = Field(ge=1, le=30)
    required_places: list[str] = Field(max_length=8)
    preferences: list[str] = Field(max_length=10)
    max_daily_drive_min: int | None = Field(ge=1, le=1440)


class Candidate(StrictModel):
    query: str = Field(min_length=1, max_length=300)
    day: int = Field(ge=1, le=2)


class TripDraft(StrictModel):
    requirements: Requirements
    candidates: list[Candidate] = Field(max_length=8)


class Place(StrictModel):
    query: str
    place_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    verification_status: Literal["verified"] = "verified"
    source: Literal["google_places"] = "google_places"


class UnresolvedPlace(StrictModel):
    query: str
    verification_status: Literal["unresolved"] = "unresolved"
    reason: str


class Route(StrictModel):
    distance_meters: int = Field(ge=0, strict=True)
    duration_seconds: float = Field(ge=0)
    encoded_polyline: str = Field(min_length=1)


class TripDay(StrictModel):
    number: int
    stops: list[Place]
    routing_status: Literal["verified", "unverified", "routing_failed"] = "unverified"
    distance_meters: int | None = None
    duration_seconds: float | None = None
    drive_minutes: float | None = None
    distance_km: float | None = None
    encoded_polyline: str | None = None
    google_maps_url: str | None = None
    warnings: list[str] = Field(default_factory=list)


class TripPlan(StrictModel):
    trip_id: str
    status: Literal["completed"] = "completed"
    title: str
    generation_mode: Literal["live"] = "live"
    is_mock: Literal[False] = False
    verification_status: Literal["verified", "partial", "unverified"]
    requirements: Requirements
    places: list[Place]
    unresolved_places: list[UnresolvedPlace]
    days: list[TripDay]
    warnings: list[str]
    viewer_url: str | None = None
    viewer_expires_at: float | None = None
