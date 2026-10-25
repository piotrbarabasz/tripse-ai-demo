import json
from datetime import datetime, timedelta
from pathlib import Path

from app.document_studio.models import DocumentDraft, OfferData, PilotData
from app.document_studio.repository import Repository
from app.document_studio.templates import TEMPLATES
from app.document_studio.trip_documents import offer_trip_snapshot, SUPPORTED_TRIP_TEMPLATES


class DocumentService:
    def __init__(self, repository: Repository):
        self.repository = repository

    def save_campaign(self, campaign, *, create=False):
        for item in campaign.items:
            self.repository.get("trips", item.trip_id)
            if item.image_asset_id:
                self.repository.get("assets", item.image_asset_id)
        if campaign.hero_asset_id:
            self.repository.get("assets", campaign.hero_asset_id)
        return self.repository.save("campaigns", campaign, create=create)

    def create_draft(self, request):
        template = TEMPLATES.get(request.template_id)
        if template is None:
            raise ValueError("Nieznany typ dokumentu")
        if request.source_type != template.source_type or request.layout_variant not in template.layout_variants:
            raise ValueError("Typ źródła lub wariant nie pasuje do szablonu")
        source = self.repository.get("campaigns" if template.source_type == "campaign" else "trips", request.source_id)

        def snapshot(trip):
            if template.template_id == "offer.private":
                return offer_trip_snapshot(trip)
            copy = trip.model_copy(deep=True)
            if template.confidentiality in ("public", "client"):
                for day in copy.days:
                    day.internal_notes = ""
            return copy

        draft = DocumentDraft(
            title=request.title or source.title, template_id=template.template_id,
            template_version=template.template_version, layout_variant=request.layout_variant,
            confidentiality=template.confidentiality,
            trip_snapshot=snapshot(source) if template.source_type == "trip" else None,
            campaign_snapshot=source if template.source_type == "campaign" else None,
            campaign_trip_snapshots=[snapshot(self.repository.get("trips", item.trip_id)) for item in source.items] if template.source_type == "campaign" else [],
            editorial_notes=request.editorial_notes,
            offer_data=OfferData() if template.template_id == "offer.private" else None,
            pilot_data=PilotData() if template.template_id == "pilot.basic" else None,
        )
        if getattr(request, "demo_example", False):
            if template.template_id not in SUPPORTED_TRIP_TEMPLATES or source.trip_id != "demo-iceland":
                raise ValueError("Fikcyjny przykład dostępny dla wycieczki demo-iceland i dwóch nowych szablonów")
            data = json.loads((Path(__file__).resolve().parents[2] / "demo-fixtures/document-presets/iceland.json").read_text(encoding="utf-8"))
            draft.demo_example = True
            draft.date_label = data["date_label"]
            if len(source.days) != 10:
                end = datetime(2027,6,1) + timedelta(days=max(0,len(source.days)-1))
                draft.date_label = f"01.06.2027 – {end:%d.%m.%Y} — FIKCYJNY TERMIN DEMO"
            if template.template_id == "offer.private":
                draft.offer_data = OfferData.model_validate(data["offer_data"])
            else:
                pilot = data["pilot_data"]
                pilot["accommodations"] = [{"day_id":day.day_id,"title":f"Pensjonat demonstracyjny {day.day_number} — DEMO", "status":"confirmed" if day.day_number == 1 else "planned", "source":"Fikcyjne potwierdzenie DEMO — brak rzeczywistej rezerwacji" if day.day_number == 1 else "", "details":"Fikcyjny obiekt demonstracyjny, pokój dwuosobowy. Nie jest rzeczywistym noclegiem."} for day in source.days[:-1]]
                pilot["schedule"] = [{"day_id":day.day_id,"title":day.title + " — program DEMO", "start_local":(datetime(2027,6,1,9)+timedelta(days=index)).isoformat(),"time_zone":"Atlantic/Reykjavik", "status":"planned", "details":"Fikcyjny harmonogram. Godziny i dostępność atrakcji do potwierdzenia."} for index,day in enumerate(source.days)]
                if source.days:
                    pilot["activity_bookings"] = [{"day_id":source.days[0].day_id,"title":"Wejście demonstracyjne — DEMO", "status":"unknown", "details":"Brak rezerwacji, godzina do ustalenia."}]
                draft.pilot_data = PilotData.model_validate(pilot)
        return self.repository.save("drafts", draft, create=True)

    def update_draft(self, identifier, value):
        draft = self.repository.get("drafts", identifier)
        if draft.template_id not in SUPPORTED_TRIP_TEMPLATES:
            raise ValueError("Edytor draftu obsługuje offer.private i pilot.basic")
        data = draft.model_dump(mode="json")
        data.update(value.model_dump(mode="json"))
        result = DocumentDraft.model_validate(data)
        if result.template_id == "offer.private":
            result.trip_snapshot = offer_trip_snapshot(result.trip_snapshot)
            if result.offer_data:
                for identifier in [result.offer_data.cover_asset_id, *result.offer_data.photo_asset_ids]:
                    if identifier:
                        self.repository.get("assets", identifier)
        return self.repository.save("drafts", result)
