"""Default section instances and completeness rules, independent of storage."""
from app.document_studio.models import DocumentSection, DayLogistics, KnowledgeContent
from app.document_studio.templates import TEMPLATES
from app.document_studio.marketing import Issue
from hashlib import sha256


def default_sections(draft):
    result = [DocumentSection(role=s.role, kind="source", title=s.title) for s in TEMPLATES[draft.template_id].default_sections]
    if draft.template_id == "pilot.advanced":
        for day in draft.trip_snapshot.days:
            result.append(DocumentSection(role="day-" + sha256(day.day_id.encode()).hexdigest()[:24], kind="logistics", day_id=day.day_id,
                title=f"Dzień {day.day_number} · {day.title}"[:200], logistics=DayLogistics(time_zone=day.time_zone or "")))
    if draft.template_id == "pilot.knowledge":
        for day in draft.trip_snapshot.days:
            for part, label in (("attractions", "Atrakcje"), ("context", "Kontekst"), ("narrative", "Narracja")):
                result.append(DocumentSection(role=part + "-" + sha256(day.day_id.encode()).hexdigest()[:24], kind="knowledge", day_id=day.day_id,
                    title=f"Dzień {day.day_number} · {label}",
                    knowledge=KnowledgeContent(part=part, stop_ids=[s.stop_id for s in day.stops])))
    for index, section in enumerate(result):
        section.order = index
    return result


def section_issues(draft, assets):
    if draft.sections is None:
        return []  # Read legacy snapshots without an implicit persistence migration.
    result = []
    defaults = default_sections(draft)
    required = {s.role for s in TEMPLATES[draft.template_id].default_sections if s.required}
    required |= {s.role for s in defaults if s.kind in {"logistics", "knowledge"}}
    actual = {s.role: s for s in draft.sections if s.role}
    for spec in defaults:
        found = actual.get(spec.role)
        if spec.role in required and (not found or not found.visible or found.kind != spec.kind or found.day_id != spec.day_id or spec.knowledge and (not found.knowledge or found.knowledge.part != spec.knowledge.part)):
            result.append(Issue(severity="error", field_path="sections", message=f"Wymagana sekcja: {spec.title} — przywróć ją i jej właściwy typ."))
    for section in draft.sections:
        if section.role and section.role not in {s.role for s in defaults}:
            raise ValueError("Nieznana rola sekcji dla tego szablonu")
        if section.kind == "source" and not section.role:
            raise ValueError("Sekcja źródłowa wymaga roli z definicji szablonu")
        if not section.visible:
            continue
        if section.kind in {"image", "gallery"} and not section.images:
            result.append(Issue(severity="warning", field_path="sections.images", message="Brak zdjęcia — używany placeholder."))
        if section.knowledge and section.knowledge.verification_status != "verified":
            result.append(Issue(severity="warning", field_path="sections", message=f"{section.title}: informacje NIEZWERYFIKOWANE — dodaj źródła i daty sprawdzenia."))
        if section.knowledge and not section.body.strip() and not any(getattr(section.knowledge, field).strip() for field in ("facts", "history", "geology_nature", "culture", "connection", "observations", "stories", "pilot_notes")):
            result.append(Issue(severity="warning", field_path="sections", message=f"{section.title}: uzupełnij wymaganą treść części merytorycznej."))
        if section.logistics and not section.body.strip() and not section.logistics.organizational_notes.strip():
            result.append(Issue(severity="warning", field_path="sections", message=f"{section.title}: uzupełnij program, harmonogram i logistykę dnia."))
        for image in section.images:
            if image.asset_id:
                try:
                    assets.get(image.asset_id)
                except KeyError:
                    result.append(Issue(severity="error", field_path="sections.images", message="Zdjęcie sekcji nie istnieje."))
            else:
                result.append(Issue(severity="warning", field_path="sections.images", message="Brak zdjęcia — używany placeholder."))
    return result
