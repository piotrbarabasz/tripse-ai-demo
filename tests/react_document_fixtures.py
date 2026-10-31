"""Synthetic document data for isolated React QA; never invoked by application startup."""
from datetime import datetime, timezone
from app.document_studio.api import DraftRequest, DraftUpdate
from app.document_studio.models import Campaign, CampaignItem, Trip, TripDay
from app.document_studio.service import DocumentService
from app.document_studio.templates import TEMPLATES


def seed_documents(repository, count=28):
    repository.initialize()
    trip = repository.save("trips", Trip(trip_id="react-qa-source", title="Syntetyczny program QA",
        duration_days=1, days=[TripDay(day_number=1, title="Dzień testowy")], data_origin="synthetic_test"), create=True)
    repository.save("campaigns", Campaign(campaign_id="react-qa-campaign", title="Syntetyczna kampania QA",
        items=[CampaignItem(trip_id=trip.trip_id)], data_origin="synthetic_test"), create=True)
    service = DocumentService(repository)
    templates = list(TEMPLATES.values())
    for index in range(count):
        template = templates[index % len(templates)]
        draft = service.create_draft(DraftRequest(document_id=f"react-qa-{index:02}", title=f"Dokument QA {index:02}",
            template_id=template.template_id, source_type=template.source_type,
            source_id=trip.trip_id if template.source_type == "trip" else "react-qa-campaign",
            layout_variant=template.layout_variants[0]))
        if index == 0:
            service.update_draft(draft.document_id, DraftUpdate(revision=1, title="Dokument QA 00 po zapisie"))
        elif index == count - 1:
            draft.document_status, draft.archived_at = "archived", datetime.now(timezone.utc)
            repository.save("drafts", draft)
        elif index % 3:
            draft.document_status = "in_review" if index % 3 == 1 else "ready"
            repository.save("drafts", draft)
