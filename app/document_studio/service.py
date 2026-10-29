from app.document_studio.models import DocumentDraft, OfferData, PilotData, OfferDetails
from app.document_studio.sections import default_sections, section_issues
from app.document_studio.repository import Repository
from app.document_studio.templates import TEMPLATES
from app.document_studio.trip_documents import offer_trip_snapshot


class DocumentService:
    def __init__(self, repository: Repository, assets=None):
        self.repository = repository
        from app.document_studio.assets import AssetStore
        self.assets = assets or AssetStore(repository)

    def save_campaign(self, campaign, *, create=False):
        for item in campaign.items:
            self.repository.get("trips", item.trip_id)
            if item.image_asset_id:
                self.repository.get("assets", item.image_asset_id)
        if campaign.hero_asset_id:
            self.repository.get("assets", campaign.hero_asset_id)
        return self.repository.save("campaigns", campaign, create=create)

    def create_draft(self, request, actor=None, *, persist=True):
        from app.document_studio.repository import ConflictError
        identifier = getattr(request, "document_id", None)
        source_revision = getattr(request, "source_revision", None)
        def existing_creation():
            existing = self.repository.get("drafts", identifier)
            source = existing.trip_snapshot or existing.campaign_snapshot
            source_id = source.trip_id if existing.trip_snapshot else source.campaign_id
            if (existing.template_id != request.template_id or existing.layout_variant != request.layout_variant
                or ("trip" if existing.trip_snapshot else "campaign") != request.source_type
                or source_id != request.source_id or source_revision is not None and source.revision != source_revision
                or existing.editorial_notes != request.editorial_notes or existing.demo_example != getattr(request, "demo_example", False)
                or request.title is not None and existing.title != request.title):
                raise ConflictError("Ten zapis dotyczy innego dokumentu. Sprawdź bibliotekę przed ponowną próbą.")
            return existing
        if identifier:
            try:
                return existing_creation()
            except KeyError:
                pass
        template = TEMPLATES.get(request.template_id)
        if template is None:
            raise ValueError("Nieznany typ dokumentu")
        if request.source_type != template.source_type or request.layout_variant not in template.layout_variants:
            raise ValueError("Typ źródła lub wariant nie pasuje do szablonu")
        source = self.repository.get("campaigns" if template.source_type == "campaign" else "trips", request.source_id)
        if source_revision is not None and source.revision != source_revision:
            raise ConflictError("Program zmienił się. Otwórz aktualne źródło i sprawdź je przed utworzeniem dokumentu.")

        def snapshot(trip):
            if template.confidentiality in ("public", "client"):
                return offer_trip_snapshot(trip)
            return trip.model_copy(deep=True)

        draft = DocumentDraft(
            **({"document_id": identifier} if identifier else {}),
            title=request.title or source.title, template_id=template.template_id,
            data_origin=source.data_origin,
            template_version=template.template_version, layout_variant=request.layout_variant,
            confidentiality=template.confidentiality,
            created_by=actor, updated_by=actor,
            trip_snapshot=snapshot(source) if template.source_type == "trip" else None,
            campaign_snapshot=source.model_copy(deep=True, update={"layout_variant": request.layout_variant}) if template.source_type == "campaign" else None,
            campaign_trip_snapshots=[snapshot(self.repository.get("trips", item.trip_id)) for item in source.items] if template.source_type == "campaign" else [],
            editorial_notes=request.editorial_notes,
            offer_data=OfferData(summary=source.description) if template.family == "offer" else None,
            offer_details=OfferDetails() if template.family == "offer" else None,
            pilot_data=PilotData() if template.template_id in {"pilot.basic", "pilot.advanced"} else None,
        )
        if getattr(request, "demo_example", False):
            raise ValueError("Wybierz przykład w katalogu Przykładowe dokumenty DEMO i utwórz kopię do edycji.")
        draft.sections = default_sections(draft)
        if not persist:
            return draft
        try:
            return self.repository.save("drafts", draft, create=True)
        except ConflictError:
            if identifier:
                return existing_creation()
            raise

    def update_draft(self, identifier, value, actor=None):
        from app.document_studio.examples import protect_canonical
        protect_canonical(identifier)
        draft = self.repository.get("drafts", identifier)
        if draft.document_status == "archived":
            from app.document_studio.repository import ConflictError
            raise ConflictError("Dokument jest w archiwum. Przywróć go przed edycją.")
        data = draft.model_dump(mode="json")
        data.update(value.model_dump(mode="json", exclude_unset=True))
        if draft.sections is not None and data.get("sections") is None:
            raise ValueError("Nie można usunąć mechanizmu sekcji z istniejącego dokumentu")
        if draft.sections is None and data.get("sections") is not None:
            data["template_version"] = TEMPLATES[draft.template_id].template_version
        if draft.template_id != "marketing.collection" and data.get("campaign_snapshot"):
            raise ValueError("Kampania należy do dokumentu marketingowego")
        if draft.campaign_snapshot:
            campaign = data["campaign_snapshot"]
            if not campaign or campaign["campaign_id"] != draft.campaign_snapshot.campaign_id:
                raise ValueError("Nie można zmienić tożsamości kampanii snapshotu")
            data["layout_variant"] = campaign["layout_variant"]
            old = {t.trip_id: t for t in draft.campaign_trip_snapshots}
            data["campaign_trip_snapshots"] = [offer_trip_snapshot(old.get(item["trip_id"]) or self.repository.get("trips", item["trip_id"])).model_dump(mode="json") for item in campaign["items"]]
        result = DocumentDraft.model_validate(data)
        result.updated_by = actor
        result.last_library_operation = None
        if result.template_id.startswith("offer."):
            result.trip_snapshot = offer_trip_snapshot(result.trip_snapshot)
            if result.offer_data:
                for identifier in [result.offer_data.cover_asset_id, *result.offer_data.photo_asset_ids]:
                    if identifier:
                        self.repository.get("assets", identifier)
            if result.offer_details:
                for identifier in result.offer_details.hotel.photo_asset_ids:
                    self.repository.get("assets", identifier)
        section_issues(result, self.assets)
        if result.campaign_snapshot:
            for identifier in [result.campaign_snapshot.hero_asset_id, *(i.image_asset_id for i in result.campaign_snapshot.items)]:
                if identifier:
                    self.repository.get("assets", identifier)
        return self.repository.save("drafts", result)
