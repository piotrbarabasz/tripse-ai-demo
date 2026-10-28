"""Structured marketing data and validation, independent of HTML and export."""
from typing import Literal

from pydantic import Field

from app.document_studio.models import Campaign, ImagePosition, Model, DataOrigin


class Issue(Model):
    severity: Literal["error", "warning"]
    field_path: str
    message: str


class MarketingCard(Model):
    title: str
    destination: str
    date_label: str
    description: str
    highlights: list[str]
    badge: str
    image_asset_id: str | None
    image_position: ImagePosition
    leader: str = ""


class MarketingDocument(Model):
    title: str
    season: str
    theme: str
    description: str
    cta: str
    variant: Literal["new_trips", "theme_collection"]
    hero_asset_id: str | None
    hero_position: ImagePosition
    cards: list[MarketingCard]
    issues: list[Issue] = Field(default_factory=list)
    revision_label: str = "Podgląd roboczy"
    leader: str = ""
    data_origin: DataOrigin = "unknown"


def build_marketing(campaign: Campaign, trips, assets, revision_label="Podgląd roboczy"):
    """Explicit whitelist: no trip days, internal notes or operations reach HTML."""
    lookup = {trip.trip_id: trip for trip in trips}
    issues = []

    def issue(field, message, severity="warning"):
        issues.append(Issue(field_path=field, message=message, severity=severity))

    def check_image(identifier, field):
        if not identifier:
            issue(field, "Brak zdjęcia: użyto neutralnego placeholdera, oznaczonego w dokumencie.")
        else:
            try:
                assets.get(identifier)
            except KeyError:
                issue(field, "Wybrane zdjęcie nie istnieje. Wybierz inne zdjęcie.", "error")

    if not campaign.cta.strip():
        issue("cta", "Uzupełnij CTA / kontakt przed eksportem PDF.", "error")
    if not campaign.season.strip():
        issue("season", "Nie podano sezonu kampanii.")
    if campaign.layout_variant == "theme_collection":
        if not campaign.theme.strip():
            issue("theme", "Uzupełnij temat przewodni kolekcji.", "error")
        check_image(campaign.hero_asset_id, "hero_asset_id")
    cards = []
    for index, item in enumerate(campaign.items):
        trip = lookup.get(item.trip_id)
        if trip is None:
            raise KeyError(item.trip_id)
        prefix = f"items.{index}"
        check_image(item.image_asset_id, prefix + ".image_asset_id")
        if "ustalenia" in item.date_range_or_label.lower() or "przygotowaniu" in item.date_range_or_label.lower():
            issue(prefix + ".date_range_or_label", "Termin do ustalenia — nie jest potwierdzoną datą wyjazdu.")
        if not item.short_hook.strip():
            issue(prefix + ".short_hook", "Brak krótkiego opisu kierunku.")
        cards.append(MarketingCard(
            title=item.display_title.strip() or trip.title, destination=" · ".join(trip.destinations),
            date_label=item.date_range_or_label, description=item.short_hook,
            highlights=item.highlights, badge={"concept":"Propozycja", "new":"Nowość", "pilot":"Pilotaż"}[item.badge],
            image_asset_id=item.image_asset_id, image_position=item.image_position,
            leader=item.leader or "",
        ))
    return MarketingDocument(
        title=campaign.title, season=campaign.season, theme=campaign.theme,
        description=campaign.description, cta=campaign.cta, variant=campaign.layout_variant,
        hero_asset_id=campaign.hero_asset_id, hero_position=campaign.hero_position,
        cards=cards, issues=issues, revision_label=revision_label,
        leader=campaign.leader or "",
        data_origin=campaign.data_origin,
    )
