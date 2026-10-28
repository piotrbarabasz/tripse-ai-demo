"""Trip document rules and safe projections. No storage or arbitrary HTML input."""
from app.document_studio.marketing import Issue
from app.document_studio.models import OfferData, PilotData, Trip

SUPPORTED_TRIP_TEMPLATES = {"offer.private", "offer.self_guide", "offer.school", "offer.incentive", "pilot.basic", "pilot.advanced", "pilot.knowledge"}
OFFER_TRIP_FIELDS = {
    "trip_id", "schema_version", "revision", "title", "destinations", "description",
    "start_date", "end_date", "duration_days", "status", "updated_at",
}
OFFER_DAY_FIELDS = {"day_id", "day_number", "date", "title", "public_description"}
OFFER_STOP_FIELDS = {"stop_id", "name", "location", "description", "verification_status", "estimated_visit_duration_min"}
OPERATION_GROUPS = ("flights", "transfers", "accommodations", "activity_bookings", "schedule", "open_items")


def offer_trip_snapshot(trip):
    data = trip.model_dump(include=OFFER_TRIP_FIELDS)
    data["days"] = []
    for day in trip.days:
        value = day.model_dump(include=OFFER_DAY_FIELDS)
        value["stops"] = [stop.model_dump(include=OFFER_STOP_FIELDS) for stop in day.stops]
        data["days"].append(value)
    return Trip.model_validate(data)


def trip_document_issues(draft, assets):
    if draft.template_id not in SUPPORTED_TRIP_TEMPLATES or not draft.trip_snapshot:
        raise ValueError("Wybierz offer.private lub pilot.basic z wycieczką źródłową")
    issues = []
    from app.document_studio.sections import section_issues
    issues.extend(section_issues(draft, assets))
    def issue(path, message, severity="warning"):
        issues.append(Issue(field_path=path, message=message, severity=severity))
    trip = draft.trip_snapshot
    if not trip.days:
        issue("trip.days", "Dodaj program wycieczki przed utworzeniem dokumentu.", "error")
    if not draft.date_label.strip() and not (trip.start_date and trip.end_date):
        issue("date_label", "Termin do ustalenia — uzupełnij daty lub jawny opis terminu.")
    if draft.demo_example:
        issue("demo_example", "FIKCYJNY PRZYKŁAD DEMO. Terminy, usługi, ceny i statusy nie są rzeczywistą ofertą ani rezerwacją.")
    if draft.template_id.startswith("offer."):
        offer = draft.offer_data or OfferData()
        for field, label in (("summary","podsumowanie"),("accommodation","zakwaterowanie"),("transport","transport"), ("included","świadczenia w cenie"),("excluded","świadczenia poza ceną"),("highlights","główne zalety")):
            if not getattr(offer, field):
                issue("offer_data."+field, f"Do uzupełnienia: {label}.")
        if not offer.cta.strip():
            issue("offer_data.cta", "Uzupełnij kontakt / CTA dla klienta.", "error")
        if offer.concept_only:
            issue("offer_data.price", "WERSJA KONCEPCYJNA BEZ WYCENY — kwota nie zostanie pokazana.")
        elif offer.price.amount is None or offer.price.status == "unknown":
            issue("offer_data.price", "Brak potwierdzonej ceny. Uzupełnij wycenę albo wybierz wersję koncepcyjną bez ceny.", "error")
        else:
            if not offer.price.assumptions.strip():
                issue("offer_data.price.assumptions", "Podaj założenia ceny i zakres kalkulacji.", "error")
            if offer.price.unit == "person" and offer.price.participant_count is None:
                issue("offer_data.price.participant_count", "Cena za osobę wymaga założonej liczby uczestników.", "error")
            if offer.price.status == "example":
                issue("offer_data.price", "Kwota jest FIKCYJNYM PRZYKŁADEM DEMO, nie ceną oferty.")
        if not offer.cover_asset_id:
            issue("offer_data.cover_asset_id", "Brak zdjęcia okładki — neutralny placeholder.")
        for identifier in [offer.cover_asset_id, *offer.photo_asset_ids]:
            if identifier:
                try:
                    assets.get(identifier)
                except KeyError:
                    issue("offer_data.cover_asset_id", "Wybrane zdjęcie nie istnieje.", "error")
    elif draft.template_id != "pilot.knowledge":
        pilot = draft.pilot_data or PilotData()
        for field, label in (("leader","pilot"),("meeting","zbiórka"),("contacts","kontakty organizacyjne")):
            if not getattr(pilot, field):
                issue("pilot_data."+field, f"Do ustalenia: {label}.")
        for day in trip.days[:-1]:
            if not any(entry.day_id == day.day_id for entry in pilot.accommodations):
                issue("pilot_data.accommodations", f"KRYTYCZNE: dzień {day.day_number} — brak noclegu, do potwierdzenia.")
        for group in OPERATION_GROUPS:
            for entry in getattr(pilot, group):
                if entry.status != "confirmed":
                    issue("pilot_data."+group, f"{entry.title}: {'planowane' if entry.status == 'planned' else 'do ustalenia'}.")
                if group not in {"open_items", "accommodations"} and not entry.start_local:
                    issue("pilot_data."+group, f"{entry.title}: godzina lokalna do ustalenia.")
    return issues


def date_label(draft):
    trip = draft.trip_snapshot
    if draft.date_label.strip():
        return draft.date_label
    if trip.start_date and trip.end_date:
        return f"{trip.start_date:%d.%m.%Y} – {trip.end_date:%d.%m.%Y}"
    return "Termin do ustalenia"
