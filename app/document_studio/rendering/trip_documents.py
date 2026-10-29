"""Controlled trip layouts reuse the shared shell, photo and escaping components."""
from app.document_studio.models import ImagePosition, OfferData, PilotData
from app.document_studio.rendering import render_shell
from app.document_studio.rendering.components import photo, text
from app.document_studio.trip_documents import date_label, trip_document_issues

STATUS = {"confirmed":"Potwierdzone", "planned":"Planowane", "unknown":"Do ustalenia"}


def chunks(value, size=650):
    """Bounded text blocks, preserving every character, so long copy can paginate."""
    value = str(value or "")
    if not value:
        return [""]
    result = []
    while value:
        end = min(len(value), size)
        # Short lines can overflow a page well below the character limit.
        # Preserve their separators while bounding the height of each block.
        lines = [i for i, char in enumerate(value[:end]) if char == "\n"]
        if len(lines) >= 16:
            end = lines[15] + 1
        elif end < len(value):
            space = value.rfind(" ", size//2, end)
            end = space + 1 if space >= 0 else end
        result.append(value[:end])
        value = value[end:]
    return result


def section(title, body, css=""):
    return f'<section class="block document-section {css}"><h2>{text(title)}</h2><p>{text(body)}</p></section>'


def listing(title, values):
    if not values:
        return section(title, "Do uzupełnienia")
    return f'<section class="block document-section"><h2>{text(title)}</h2><ul>' + ''.join(f'<li>{text(item)}</li>' for item in values) + '</ul></section>'


def program(draft, operational=False):
    overrides = {override.day_id: override for override in draft.day_overrides}
    blocks = ""
    pilot = draft.pilot_data or PilotData()
    for day in draft.trip_snapshot.days:
        override = overrides.get(day.day_id)
        heading = f"Dzień {day.day_number} · {override.title if override and override.title else day.title}"
        description = override.description if override and override.description else day.public_description
        blocks += section(heading, description or "Program do opracowania", "day-section")
        for stop in day.stops:
            blocks += section(f"Dzień {day.day_number} · {stop.name}", stop.description or stop.location or "Atrakcja do weryfikacji", "stop-section")
        if operational:
            entries = [e for e in pilot.schedule if e.day_id == day.day_id]
            if entries:
                blocks += operational_entries("Harmonogram · " + heading, entries)
            hotels = [entry for entry in pilot.accommodations if entry.day_id == day.day_id]
            if not hotels and day.day_number < len(draft.trip_snapshot.days):
                blocks += section(f"Dzień {day.day_number} · Nocleg", "KRYTYCZNE: brak noclegu — DO POTWIERDZENIA", "missing-data")
            for hotel in hotels:
                blocks += section(f"Dzień {day.day_number} · Nocleg", hotel.title + "\nStatus: " + STATUS[hotel.status])
            if day.internal_notes:
                blocks += section(f"Dzień {day.day_number} · Notatka wewnętrzna", day.internal_notes)
    return blocks


def local(value, zone):
    return f"{value:%d.%m.%Y %H:%M} · {zone}" if value else "Godzina do ustalenia"


def operational_row(entry):
    body = entry.details
    for field, title in (("carrier", "Przewoźnik"), ("flight_number", "Numer lotu"), ("origin", "Z"), ("destination", "Do"), ("travel_group", "Grupa przylotowa / powrotna")):
        if getattr(entry, field):
            body += f"\n{title}: {getattr(entry, field)}"
    if entry.booking_reference:
        body += "\nNumer rezerwacji: " + entry.booking_reference
    if entry.source:
        body += "\nŹródło: " + entry.source
    time = local(entry.start_local, entry.time_zone)
    if entry.end_local:
        time += "\n→ " + local(entry.end_local, entry.end_time_zone or entry.time_zone)
    return f'<tr><td>{text(time)}</td><td><strong>{text(entry.title)}</strong><p>{text(body)}</p></td><td><span class="operation-status {entry.status}">{STATUS[entry.status]}</span></td></tr>'


def operational_entries(label, entries):
    return f'<section class="block operation-entry operational-table"><h2>{text(label)}</h2><table><thead><tr><th>Godzina lokalna</th><th>Zdarzenie / ustalenia</th><th>Status</th></tr></thead><tbody>' + ''.join(operational_row(e) for e in entries) + '</tbody></table></section>'


def operational_entry(label, entry):
    return operational_entries(label, [entry])


def render_trip_document(draft, assets):
    issues = trip_document_issues(draft, assets)
    trip = draft.trip_snapshot
    demo = '<section class="block demo-banner">FIKCYJNY PRZYKŁAD DEMO — terminy, usługi, ceny i statusy są demonstracyjne.</section>' if draft.demo_example else ""
    if draft.template_id == "offer.private":
        offer = draft.offer_data or OfferData()
        blocks = demo + f'<section class="block offer-cover">{photo(offer.cover_asset_id, offer.cover_position, draft.title)}<div><p class="eyebrow">WYPRAWA NA TWOICH ZASADACH</p><h1>{text(draft.title)}</h1><p>{text(date_label(draft))}</p><p>{text(" · ".join(trip.destinations))} · {trip.duration_days} dni</p></div></section>'
        blocks += section("Podróż w skrócie", offer.summary or trip.description or "Podsumowanie do uzupełnienia")
        blocks += listing("Dlaczego ten kierunek", offer.highlights)
        for asset_id in offer.photo_asset_ids:
            blocks += f'<section class="block offer-photo">{photo(asset_id, ImagePosition(), draft.title)}</section>'
        blocks += program(draft)
        blocks += section("Zakwaterowanie", offer.accommodation or "Standard noclegów do potwierdzenia", "logistics")
        blocks += section("Transport", offer.transport or "Transport do potwierdzenia", "logistics")
        blocks += listing("W cenie", offer.included) + listing("Poza ceną", offer.excluded)
        if offer.concept_only:
            pricing = "WERSJA KONCEPCYJNA BEZ WYCENY. Cena i warunki zostaną ustalone osobno."
        elif offer.price.status == "unknown" or offer.price.amount is None:
            pricing = "Cena do ustalenia. Dokument nie jest wycenioną ofertą."
        else:
            prefix = "FIKCYJNA CENA DEMO — " if offer.price.status == "example" else "Cena potwierdzona przez organizatora — "
            amount = f"{offer.price.amount:,.2f}".replace(",", " ").replace(".", ",")
            pricing = f"{prefix}{amount} {offer.price.currency} / {'osobę' if offer.price.unit == 'person' else 'grupę'}."
            pricing += f"\nZałożona liczba uczestników: {offer.price.participant_count or 'do ustalenia'}."
        blocks += section("Cena i założenia", pricing + "\n" + offer.price.assumptions, "price-section")
        blocks += section("Zaplanujmy Twoją podróż", offer.cta or "Kontakt / CTA do uzupełnienia", "cta")
        classification = "DLA KLIENTA · WERSJA ROBOCZA"
    else:
        pilot = draft.pilot_data or PilotData()
        blocks = demo + section(draft.title, f"{date_label(draft)}\nPilot: {pilot.leader or 'do ustalenia'}\nLiczba uczestników: {pilot.participant_count or 'do ustalenia'}\nZbiórka: {pilot.meeting or 'do ustalenia'}\nAktualizacja: {draft.updated_at:%d.%m.%Y %H:%M} UTC · rewizja {draft.revision}", "operations-summary")
        blocks += listing("Kontakty organizacyjne", [f"{c.label}: {c.value}" for c in pilot.contacts])
        for group, label in (("flights","Przeloty"),("transfers","Transfery"),("accommodations","Noclegi — zestawienie"),("activity_bookings","Rezerwacje atrakcji")):
            entries = getattr(pilot, group)
            blocks += ''.join(operational_entry(label, entry) for entry in entries) if entries else section(label, "Do ustalenia / do potwierdzenia")
        blocks += program(draft, operational=True)
        blocks += ''.join(operational_entry("Sprawy do potwierdzenia", item) for item in pilot.open_items) if pilot.open_items else section("Sprawy do potwierdzenia", "Brak wpisanych spraw — sprawdź kompletność logistyki.")
        if pilot.internal_notes:
            blocks += section("Notatki wewnętrzne pilota", pilot.internal_notes, "keep-with-previous")
        if draft.editorial_notes:
            blocks += section("Notatka redakcyjna wewnętrzna", draft.editorial_notes, "keep-with-previous")
        classification = "WEWNĘTRZNE · ROBOCZY"
    if draft.demo_example:
        classification += " · FIKCYJNE DEMO"
    label = f"{draft.document_id[:8]} · rew. {draft.revision} · {draft.template_id} {draft.template_version} · dane r{trip.revision}"
    return render_shell(draft.title, blocks, issues, variant=draft.template_id.replace('.', '-'), revision_label=label, classification=classification, data_origin=draft.data_origin)
