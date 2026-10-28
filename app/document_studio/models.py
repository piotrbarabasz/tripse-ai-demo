from datetime import date as Date, datetime, timedelta, timezone
from typing import Annotated, Literal
from uuid import uuid4
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Identifier = Annotated[str, StringConstraints(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}$")]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Text = Annotated[str, StringConstraints(max_length=20000)]
Verification = Literal["unverified", "proposed", "verified", "rejected"]
Confidentiality = Literal["public", "client", "internal", "internal_restricted"]


def new_id():
    return uuid4().hex


def now():
    return datetime.now(timezone.utc)


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")


class Stop(Model):
    stop_id: Identifier = Field(default_factory=new_id)
    name: Title
    place_id: str | None = None
    location: str = ""
    description: Text = ""
    verification_status: Verification = "unverified"
    source: str | None = None
    estimated_visit_duration_min: int | None = Field(default=None, ge=1)


class TripDay(Model):
    day_id: Identifier = Field(default_factory=new_id)
    day_number: int = Field(ge=1)
    date: Date | None = None
    title: Title
    stops: list[Stop] = Field(default_factory=list)
    public_description: Text = ""
    internal_notes: Text = ""
    time_zone: str | None = None


class Trip(Model):
    trip_id: Identifier = Field(default_factory=new_id)
    schema_version: Literal[1] = 1
    revision: int = Field(default=1, ge=1)
    title: Title
    destinations: list[Title] = Field(default_factory=list)
    description: Text = ""
    start_date: Date | None = None
    end_date: Date | None = None
    duration_days: int = Field(default=0, ge=0)
    status: Literal["idea", "draft", "planned", "confirmed", "completed", "cancelled"] = "draft"
    days: list[TripDay] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=now)

    @model_validator(mode="after")
    def consistent_days(self):
        if self.duration_days != len(self.days):
            raise ValueError("duration_days must equal the number of days")
        if [d.day_number for d in self.days] != list(range(1, len(self.days) + 1)):
            raise ValueError("Days must be consecutively numbered from 1")
        ids = [d.day_id for d in self.days]
        stop_ids = [s.stop_id for d in self.days for s in d.stops]
        if len(ids) != len(set(ids)) or len(stop_ids) != len(set(stop_ids)):
            raise ValueError("Day and stop IDs must be unique within a trip")
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValueError("End date precedes start date")
            if self.days and (self.end_date - self.start_date).days + 1 != len(self.days):
                raise ValueError("Date range must match duration_days")
        dates = [d.date for d in self.days if d.date]
        if dates != sorted(set(dates)):
            raise ValueError("Day dates must be unique and increasing")
        for day in self.days:
            if day.date and self.start_date and day.date != self.start_date + timedelta(days=day.day_number - 1):
                raise ValueError("Day date does not match start date and day number")
            if day.date and self.end_date and day.date > self.end_date:
                raise ValueError("Day date exceeds end date")
        return self


class ImagePosition(Model):
    x: float = Field(default=50, ge=0, le=100, allow_inf_nan=False)
    y: float = Field(default=50, ge=0, le=100, allow_inf_nan=False)
    zoom: float = Field(default=1, ge=1, le=3, allow_inf_nan=False)


class ImageAsset(Model):
    asset_id: Identifier = Field(default_factory=new_id)
    schema_version: Literal[1] = 1
    revision: int = Field(default=1, ge=1)
    original_name: Annotated[str, StringConstraints(max_length=200)]
    media_type: Literal["image/jpeg", "image/png", "image/webp"]
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    rights_confirmed: Literal[True]
    created_at: datetime = Field(default_factory=now)


class CampaignItem(Model):
    trip_id: Identifier
    display_title: Annotated[str, StringConstraints(max_length=200)] = ""
    short_hook: Annotated[str, StringConstraints(max_length=500)] = ""
    date_range_or_label: Title = "Termin do ustalenia"
    highlights: list[Title] = Field(default_factory=list)
    image_asset_id: Identifier | None = None
    image_position: ImagePosition = Field(default_factory=ImagePosition)
    badge: Literal["concept", "new", "pilot"] = "concept"
    publication_status: Literal["draft", "approved"] = "draft"
    leader: Title | None = None


class Campaign(Model):
    campaign_id: Identifier = Field(default_factory=new_id)
    schema_version: Literal[1] = 1
    revision: int = Field(default=1, ge=1)
    title: Title
    season: str = ""
    layout_variant: Literal["new_trips", "theme_collection"] = "new_trips"
    theme: str = ""
    cta: str = ""
    description: Annotated[str, StringConstraints(max_length=1000)] = ""
    hero_asset_id: Identifier | None = None
    hero_position: ImagePosition = Field(default_factory=ImagePosition)
    items: list[CampaignItem] = Field(min_length=1)
    updated_at: datetime = Field(default_factory=now)
    leader: Title | None = None

    @model_validator(mode="after")
    def unique_trips(self):
        if len({i.trip_id for i in self.items}) != len(self.items):
            raise ValueError("Campaign trips must be unique")
        return self


class SectionSpec(Model):
    role: Identifier
    title: Title
    binding: str = "text"
    required: bool = True


class DocumentTemplate(Model):
    template_id: str
    name: Title
    template_version: str = "0.1.0"
    family: Literal["offer", "marketing", "pilot"]
    audience: str
    confidentiality: Confidentiality
    source_type: Literal["trip", "campaign"]
    layout_variants: list[str] = Field(default_factory=lambda: ["standard"])
    description: str
    default_sections: list[SectionSpec] = Field(default_factory=list)


class DayOverride(Model):
    day_id: Identifier
    title: Annotated[str, StringConstraints(max_length=200)] = ""
    description: Text = ""


class OfferPrice(Model):
    amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    currency: Literal["PLN", "EUR", "USD"] = "PLN"
    unit: Literal["person", "group"] = "person"
    participant_count: int | None = Field(default=None, ge=1)
    status: Literal["unknown", "example", "confirmed"] = "unknown"
    assumptions: Text = ""
    source: Annotated[str, StringConstraints(max_length=1000)] = ""

    @model_validator(mode="after")
    def confirmed_price(self):
        if self.status == "confirmed" and (self.amount is None or not self.source.strip()):
            raise ValueError("Potwierdzona cena wymaga kwoty i źródła organizatora")
        return self


class OfferData(Model):
    summary: Text = ""
    highlights: list[Title] = Field(default_factory=list)
    accommodation: Text = ""
    transport: Text = ""
    included: list[Title] = Field(default_factory=list)
    excluded: list[Title] = Field(default_factory=list)
    price: OfferPrice = Field(default_factory=OfferPrice)
    concept_only: bool = False
    cta: Text = ""
    cover_asset_id: Identifier | None = None
    cover_position: ImagePosition = Field(default_factory=ImagePosition)
    photo_asset_ids: list[Identifier] = Field(default_factory=list, max_length=10)


class OperationalEntry(Model):
    entry_id: Identifier = Field(default_factory=new_id)
    day_id: Identifier | None = None
    title: Title
    start_local: datetime | None = None
    end_local: datetime | None = None
    time_zone: Annotated[str, StringConstraints(max_length=100)] = ""
    end_time_zone: Annotated[str, StringConstraints(max_length=100)] = ""
    status: Literal["unknown", "planned", "confirmed"] = "unknown"
    details: Text = ""
    booking_reference: Annotated[str, StringConstraints(max_length=200)] = ""
    source: Annotated[str, StringConstraints(max_length=1000)] = ""

    @model_validator(mode="after")
    def local_times(self):
        for zone in (self.time_zone, self.end_time_zone):
            if zone:
                try:
                    ZoneInfo(zone)
                except ZoneInfoNotFoundError:
                    raise ValueError("Nieznana strefa czasu IANA") from None
        for value in (self.start_local, self.end_local):
            if value and value.tzinfo is not None:
                raise ValueError("Podaj lokalny czas bez offsetu i osobną strefę IANA")
        if (self.start_local or self.end_local) and not self.time_zone:
            raise ValueError("Lokalna godzina wymaga strefy IANA, np. Atlantic/Reykjavik")
        if self.start_local and self.end_local:
            start = self.start_local.replace(tzinfo=ZoneInfo(self.time_zone))
            end = self.end_local.replace(tzinfo=ZoneInfo(self.end_time_zone or self.time_zone))
            if end.astimezone(timezone.utc) < start.astimezone(timezone.utc):
                raise ValueError("Koniec zdarzenia poprzedza początek")
        if self.status == "confirmed" and not self.source.strip():
            raise ValueError("Potwierdzenie wymaga źródła")
        return self


class OrganizationContact(Model):
    label: Title
    value: Annotated[str, StringConstraints(max_length=1000)]


class PilotData(Model):
    leader: Annotated[str, StringConstraints(max_length=200)] = ""
    participant_count: int | None = Field(default=None, ge=1)
    meeting: Text = ""
    flights: list[OperationalEntry] = Field(default_factory=list)
    transfers: list[OperationalEntry] = Field(default_factory=list)
    accommodations: list[OperationalEntry] = Field(default_factory=list)
    activity_bookings: list[OperationalEntry] = Field(default_factory=list)
    schedule: list[OperationalEntry] = Field(default_factory=list)
    contacts: list[OrganizationContact] = Field(default_factory=list)
    open_items: list[OperationalEntry] = Field(default_factory=list)
    internal_notes: Text = ""


class HotelData(Model):
    name_or_standard: Text = ""
    location: Text = ""
    room_types: Text = ""
    amenities: list[Title] = Field(default_factory=list)
    common_spaces: Text = ""
    conference_rooms: Text = ""
    photo_asset_ids: list[Identifier] = Field(default_factory=list, max_length=10)
    status: Literal["unknown", "proposed", "confirmed"] = "unknown"
    source: Text = ""

    @model_validator(mode="after")
    def confirmation_source(self):
        if self.status == "confirmed" and not self.source.strip():
            raise ValueError("Potwierdzony hotel wymaga źródła")
        return self


class EducationalGoal(Model):
    pillar: Literal["education", "nature", "integration"]
    description: Text = ""
    day_id: Identifier | None = None
    stop_id: Identifier | None = None


class OfferDetails(Model):
    organization_scope: Text = ""
    self_arrangements: Text = ""
    materials: Text = ""
    support: Text = ""
    online_briefing: Text = "Do uzgodnienia — briefing online nie jest gwarantowaną usługą."
    age_group: Text = ""
    group_size: int | None = Field(default=None, ge=1)
    goals: list[EducationalGoal] = Field(default_factory=list)
    supervision: Text = ""
    hotel: HotelData = Field(default_factory=HotelData)
    team_building: Text = ""
    workshops: Text = ""
    meals_events: Text = ""
    variants: Text = ""


class DayLogistics(Model):
    date: Date | None = None
    route_start: Text = ""
    route_end: Text = ""
    drive_km: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    walk_km: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    elevation_gain_m: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    drive_minutes: int | None = Field(default=None, ge=0)
    activity_minutes: int | None = Field(default=None, ge=0)
    time_zone: str = ""
    accommodation_entry_id: Identifier | None = None
    organizational_notes: Text = ""
    plan_b: Text = ""

    @model_validator(mode="after")
    def valid_zone(self):
        if self.time_zone:
            try:
                ZoneInfo(self.time_zone)
            except ZoneInfoNotFoundError:
                raise ValueError("Nieznana strefa czasu IANA") from None
        return self


class KnowledgeSource(Model):
    reference: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
    checked_on: Date | None = None


class KnowledgeContent(Model):
    part: Literal["attractions", "context", "narrative"] = "attractions"
    stop_ids: list[Identifier] = Field(default_factory=list)
    facts: Text = ""
    history: Text = ""
    geology_nature: Text = ""
    culture: Text = ""
    connection: Text = ""
    observations: Text = ""
    stories: Text = ""
    pilot_notes: Text = ""
    verification_status: Verification = "unverified"
    sources: list[KnowledgeSource] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def verified_sources(self):
        if self.verification_status == "verified" and (not self.sources or any(not s.checked_on for s in self.sources)):
            raise ValueError("Zweryfikowane informacje wymagają dokładnych źródeł i dat sprawdzenia")
        return self


class SectionImage(Model):
    asset_id: Identifier | None = None
    caption: Text = ""
    position: ImagePosition = Field(default_factory=ImagePosition)


class DocumentSection(Model):
    section_id: Identifier = Field(default_factory=new_id)
    role: Identifier | None = None
    kind: Literal["text", "list", "image", "gallery", "table", "callout", "day", "logistics", "knowledge", "source"] = "text"
    title: Title
    body: Text = ""
    order: int = Field(default=0, ge=0)
    visible: bool = True
    day_id: Identifier | None = None
    items: list[Text] = Field(default_factory=list, max_length=200)
    images: list[SectionImage] = Field(default_factory=list, max_length=20)
    columns: list[Title] = Field(default_factory=list, max_length=8)
    rows: list[list[Text]] = Field(default_factory=list, max_length=200)
    logistics: DayLogistics | None = None
    knowledge: KnowledgeContent | None = None

    @model_validator(mode="after")
    def structured_content(self):
        if self.kind == "table" and (not self.columns or any(len(row) != len(self.columns) for row in self.rows)):
            raise ValueError("Tabela wymaga kolumn i zgodnej liczby komórek")
        if self.kind == "image" and len(self.images) > 1:
            raise ValueError("Sekcja zdjęcia zawiera najwyżej jedno zdjęcie")
        if (self.kind == "logistics") != (self.logistics is not None):
            raise ValueError("Dane logistyczne wymagają sekcji logistics")
        if (self.kind == "knowledge") != (self.knowledge is not None):
            raise ValueError("Dane merytoryczne wymagają sekcji knowledge")
        return self


BusinessStatus = Literal["draft", "in_review", "ready", "archived"]


class LibraryOperation(Model):
    operation_id: str
    kind: Literal["archive", "restore", "status"]
    base_revision: int = Field(ge=1)


class DocumentDraft(Model):
    document_id: Identifier = Field(default_factory=new_id)
    schema_version: Literal[1] = 1
    revision: int = Field(default=1, ge=1)
    title: Title
    template_id: str
    template_version: str
    layout_variant: str = "standard"
    language: Literal["pl"] = "pl"
    confidentiality: Confidentiality
    status: Literal["draft"] = "draft"
    document_status: BusinessStatus = "draft"
    archived_at: datetime | None = None
    created_by: str | None = None
    updated_by: str | None = None
    duplicated_from_document_id: Identifier | None = None
    last_library_operation: LibraryOperation | None = None
    trip_snapshot: Trip | None = None
    campaign_snapshot: Campaign | None = None
    campaign_trip_snapshots: list[Trip] = Field(default_factory=list)
    editorial_notes: Text = ""
    date_label: Annotated[str, StringConstraints(max_length=200)] = ""
    demo_example: bool = False
    day_overrides: list[DayOverride] = Field(default_factory=list)
    offer_data: OfferData | None = None
    pilot_data: PilotData | None = None
    offer_details: OfferDetails | None = None
    # None identifies a legacy draft; an explicit [] must not restore deleted requirements.
    sections: list[DocumentSection] | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)

    @model_validator(mode="after")
    def valid_source(self):
        if (self.document_status == "archived") != (self.archived_at is not None):
            raise ValueError("Archiwizacja wymaga zgodnego statusu i daty")
        if (self.trip_snapshot is None) == (self.campaign_snapshot is None):
            raise ValueError("Exactly one trip or campaign snapshot is required")
        from app.document_studio.templates import TEMPLATES
        template = TEMPLATES.get(self.template_id)
        if template and ((template.source_type == "trip") != (self.trip_snapshot is not None) or template.confidentiality != self.confidentiality or self.layout_variant not in template.layout_variants):
            raise ValueError("Źródło, wariant i poufność muszą odpowiadać szablonowi")
        expected = [i.trip_id for i in self.campaign_snapshot.items] if self.campaign_snapshot else []
        if [t.trip_id for t in self.campaign_trip_snapshots] != expected:
            raise ValueError("Campaign snapshots must match its trips in order")
        if (self.offer_data is not None or self.offer_details is not None) and not self.template_id.startswith("offer."):
            raise ValueError("Pola oferty należą wyłącznie do ofert")
        if self.pilot_data is not None and self.template_id not in {"pilot.basic", "pilot.advanced"}:
            raise ValueError("Pola operacyjne należą wyłącznie do rozpisek pilota")
        day_ids = {d.day_id for d in self.trip_snapshot.days} if self.trip_snapshot else set()
        override_ids = [d.day_id for d in self.day_overrides]
        if len(set(override_ids)) != len(override_ids) or not set(override_ids) <= day_ids:
            raise ValueError("Nadpisania muszą wskazywać unikalne dni snapshotu")
        if self.pilot_data:
            for group in ("flights", "transfers", "accommodations", "activity_bookings", "schedule", "open_items"):
                for event in getattr(self.pilot_data, group):
                    if event.day_id and event.day_id not in day_ids:
                        raise ValueError("Zdarzenie wskazuje dzień spoza snapshotu")
        stop_days = {s.stop_id: d.day_id for d in self.trip_snapshot.days for s in d.stops} if self.trip_snapshot else {}
        if self.offer_details:
            for goal in self.offer_details.goals:
                if goal.day_id and goal.day_id not in day_ids or goal.stop_id and stop_days.get(goal.stop_id) != goal.day_id:
                    raise ValueError("Cel musi wskazywać punkt programu snapshotu")
        sections = self.sections or []
        if len({s.section_id for s in sections}) != len(sections):
            raise ValueError("Identyfikatory sekcji muszą być unikalne")
        roles = [s.role for s in sections if s.role]
        if len(roles) != len(set(roles)):
            raise ValueError("Role sekcji domyślnych muszą być unikalne")
        for section in sections:
            if section.day_id and section.day_id not in day_ids:
                raise ValueError("Sekcja wskazuje dzień spoza snapshotu")
            if section.knowledge:
                if self.template_id != "pilot.knowledge" or not section.day_id:
                    raise ValueError("Wiedza jest wewnętrzna i wymaga dnia programu")
                if any(stop_days.get(s) != section.day_id for s in section.knowledge.stop_ids):
                    raise ValueError("Atrakcja merytoryczna nie należy do programu tego dnia")
            if section.logistics:
                if self.template_id != "pilot.advanced" or not section.day_id:
                    raise ValueError("Logistyka szczegółowa wymaga dnia rozpiski zaawansowanej")
                ref = section.logistics.accommodation_entry_id
                if ref and (not self.pilot_data or not any(e.entry_id == ref for e in self.pilot_data.accommodations)):
                    raise ValueError("Nocleg musi wskazywać istniejący wpis wspólnej logistyki")
        return self
