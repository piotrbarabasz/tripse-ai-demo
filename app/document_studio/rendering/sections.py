"""Section presentation on the existing paginated HTML/print shell; no data fetching."""
from datetime import timezone
from zoneinfo import ZoneInfo
from app.document_studio.models import OfferData, OfferDetails, PilotData, ImagePosition
from app.document_studio.templates import TEMPLATES
from app.document_studio.sections import section_issues
from app.document_studio.marketing import build_marketing, Issue
from app.document_studio.rendering import render_shell, marketing_blocks, render_marketing
from app.document_studio.rendering.components import text, photo
from app.document_studio.rendering.trip_documents import section, listing, program, operational_entry, operational_entries, chunks, render_trip_document
from app.document_studio.trip_documents import trip_document_issues, date_label


def document_issues(draft, assets):
    if draft.template_id not in TEMPLATES or draft.confidentiality != TEMPLATES[draft.template_id].confidentiality:
        raise ValueError("Nieprawidłowy szablon lub poufność dokumentu")
    if draft.template_id == "marketing.collection":
        campaign = draft.campaign_snapshot.model_copy(deep=True)
        campaign.layout_variant = draft.layout_variant
        return build_marketing(campaign, draft.campaign_trip_snapshots, assets).issues + section_issues(draft, assets)
    issues = trip_document_issues(draft, assets)
    details = draft.offer_details or OfferDetails()
    if draft.template_id == "offer.self_guide" and not details.support:
        issues.append(Issue(severity="error", field_path="offer_details.support", message="Uzupełnij zakres wsparcia Self-Guide."))
    if draft.template_id == "offer.school" and (not details.age_group or details.group_size is None):
        issues.append(Issue(severity="error", field_path="offer_details", message="Ustal wiek i liczebność grupy szkolnej."))
    if draft.template_id == "offer.incentive" and details.hotel.status != "confirmed":
        issues.append(Issue(severity="warning", field_path="offer_details.hotel", message="Nocleg nie został potwierdzony — standard i dostępność do uzgodnienia."))
    return issues


def table(title, columns, rows):
    if not rows:
        return section(title, "Do uzupełnienia")
    return f'<section class="block operation-entry"><h2>{text(title)}</h2><table><thead><tr>' + ''.join(f'<th>{text(c)}</th>' for c in columns) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{text(c)}</td>' for c in row) + '</tr>' for row in rows) + '</tbody></table></section>'


def schedule_order(entry):
    return entry.start_local.replace(tzinfo=ZoneInfo(entry.time_zone)).astimezone(timezone.utc).timestamp() if entry.start_local else float('inf')


def pricing(offer):
    if offer.concept_only:
        return "WERSJA KONCEPCYJNA BEZ WYCENY. Cena i warunki zostaną ustalone osobno."
    if offer.price.amount is None or offer.price.status == "unknown":
        return "Cena do ustalenia. Dokument nie jest wycenioną ofertą."
    label = "FIKCYJNA CENA DEMO" if offer.price.status == "example" else "Cena potwierdzona przez organizatora"
    amount = f"{offer.price.amount:,.2f}".replace(",", " ").replace(".", ",")
    return f"{label} — {amount} {offer.price.currency} / {'osobę' if offer.price.unit == 'person' else 'grupę'}.\nZałożona liczba uczestników: {offer.price.participant_count or 'do ustalenia'}.\n{offer.price.assumptions}"


def bound_content(draft, item, assets, output_format="a4"):
    spec = next(s for s in TEMPLATES[draft.template_id].default_sections if s.role == item.role)
    key, title = spec.binding, item.title
    trip = draft.trip_snapshot
    offer, details, pilot = draft.offer_data or OfferData(), draft.offer_details or OfferDetails(), draft.pilot_data or PilotData()
    if key == "collection":
        campaign = draft.campaign_snapshot.model_copy(deep=True)
        campaign.title, campaign.layout_variant = draft.title, draft.layout_variant
        return marketing_blocks(build_marketing(campaign, draft.campaign_trip_snapshots, assets), output_format)
    if key == "cover":
        lead = "BEZ PILOTA NA MIEJSCU · SELF-GUIDE" if draft.template_id == "offer.self_guide" else TEMPLATES[draft.template_id].name
        if draft.template_id == "offer.school":
            lead += " · EDUKACJA / PRZYRODA / INTEGRACJA"
        result = f'<section class="block offer-cover">{photo(offer.cover_asset_id, offer.cover_position, draft.title) if draft.template_id.startswith("offer.") else ""}<div><p class="eyebrow">{text(lead)}</p><h1>{text(draft.title)}</h1><p>{text(date_label(draft))}</p><p>{text(" · ".join(trip.destinations))} · {trip.duration_days} dni</p></div></section>'
        return result
    if key == "program":
        return section(title, "Program ze snapshotu wycieczki") + program(draft, operational=draft.template_id.startswith("pilot."))
    if key == "price":
        return section(title, pricing(offer), "price-section")
    if key == "route":
        rows = []
        for day in trip.days:
            log = next((s.logistics for s in draft.sections or [] if s.day_id == day.day_id and s.logistics), None)
            events = sorted((e for e in pilot.schedule if e.day_id == day.day_id), key=schedule_order)
            window = ' – '.join(v.strftime('%H:%M') for v in ([events[0].start_local, events[-1].end_local] if events else []) if v) or 'Do ustalenia'
            metrics = ' / '.join(str(getattr(log, k)) if log and getattr(log, k) is not None else 'Do ustalenia' for k in ('drive_km', 'walk_km'))
            hotels = ', '.join(e.title for e in pilot.accommodations if e.day_id == day.day_id) or 'Do ustalenia / koniec podróży'
            rows.append([f"{day.day_number} · {log.date if log and log.date else day.date or 'Termin do ustalenia'}", day.title, metrics, window, hotels])
        return table(title, ["Dzień / data", "Trasa", "Km auto / pieszo (szacunek)", "Godziny lokalne", "Nocleg"], rows)
    if key == "route_summary":
        route = details.route_summary
        return section(title, f"Start: {route.start or 'Do ustalenia'}\nMeta: {route.end or 'Do ustalenia'}\nRegiony: {', '.join(route.regions) or 'Do ustalenia'}\nIntensywność: {route.intensity or 'Do ustalenia'}\nJazda km: {route.drive_km if route.drive_km is not None else 'Do ustalenia'}\nPieszo km: {route.walk_km if route.walk_km is not None else 'Do ustalenia'}\nWeryfikacja: {route.verification_status}\nŹródło: {route.source or 'Pomiar do wykonania'}")
    if key == "team_group":
        return section(title, f"Założona liczebność zespołu: {details.group_size or 'Do ustalenia'}\nStandard i potrzeby: {details.hotel.name_or_standard or 'Do uzgodnienia'}")
    if key == "pilot_group":
        return section(title, f"Pilot: {pilot.leader or 'Do ustalenia'}\nGrupa: {pilot.participant_count or 'Do ustalenia'}\nZbiórka: {pilot.meeting or 'Do ustalenia'}")
    if key == "contacts":
        return listing(title, [f"{c.label}: {c.value}" for c in pilot.contacts])
    if key in {"flights", "transfers", "accommodations", "activity_bookings", "open_items"}:
        return operational_entries(title, getattr(pilot, key)) if getattr(pilot, key) else section(title, "Do ustalenia / do potwierdzenia")
    if key == "internal_notes":
        return section(title, pilot.internal_notes or "Do uzupełnienia")
    if key == "self_guide":
        return section(title, "Samodzielna podróż bez pilota na miejscu. Zakres organizacji, materiałów i wsparcia wymaga uzgodnienia.")
    if key == "school_group":
        return section(title, f"Sugerowany wiek: {details.age_group or 'Do ustalenia'}\nLiczebność: {details.group_size or 'Do ustalenia'}\nTermin: {date_label(draft)}")
    if key in {"education", "nature", "integration"}:
        return listing(title, [g.description + (" · " + next(d.title for d in trip.days if d.day_id == g.day_id) if g.day_id else " · Powiązanie z programem do uzupełnienia") + (" · " + next(s.name for d in trip.days for s in d.stops if s.stop_id == g.stop_id) if g.stop_id else "") for g in details.goals if g.pillar == key])
    if key == "hotel":
        hotel = details.hotel
        lines = [hotel.name_or_standard or 'Standard noclegów do potwierdzenia', f"Status: {hotel.status} — dostępność do uzgodnienia", hotel.location, hotel.room_types, ', '.join(hotel.amenities), hotel.common_spaces, hotel.conference_rooms]
        result = section(title, '\n'.join(value for value in lines if value), "hotel-feature")
        return result + ''.join(f'<section class="block offer-photo">{photo(a, ImagePosition(), title)}</section>' for a in hotel.photo_asset_ids)
    value = getattr(offer, key, None) if key in {"summary", "highlights", "accommodation", "transport", "included", "excluded", "cta"} else getattr(details, key, "")
    if key == "summary":
        value = value or trip.description
    if key == "accommodation":
        value = value or "Standard noclegów do potwierdzenia"
    result = listing(title, value) if isinstance(value, list) else section(title, value or "Do uzupełnienia", "cta" if key == "cta" else "")
    if key == "highlights":
        result += ''.join(f'<section class="block offer-photo">{photo(a, ImagePosition(), title)}</section>' for a in offer.photo_asset_ids)
    return result


def render_section(draft, item, assets, output_format="a4"):
    title = item.title
    if item.kind == "source":
        return bound_content(draft, item, assets, output_format) + (section(title + " — uwagi", item.body) if item.body else "")
    result = section(title, item.body or "Do uzupełnienia", "day-section" if item.kind == "day" else "info-callout" if item.kind == "callout" else "")
    if item.kind == "list":
        return listing(title, item.items) + (section("Uwagi", item.body) if item.body else "")
    if item.kind == "table":
        return table(title, item.columns, item.rows) + (section("Uwagi", item.body) if item.body else "")
    if item.kind in {"image", "gallery"}:
        result = section(title, item.body) if item.body else ""
        for index, image in enumerate(item.images or [None]):
            heading = f'<h2>{text(title)}</h2>' if not item.body and index == 0 else ""
            caption = f'<p class="photo-caption">{text(image.caption)}</p>' if image and image.caption else ""
            result += f'<section class="block offer-photo">{heading}{photo(image.asset_id if image else None, image.position if image else ImagePosition(), title)}{caption}</section>'
    if item.kind == "logistics":
        day = next(d for d in draft.trip_snapshot.days if d.day_id == item.day_id)
        log, pilot = item.logistics, draft.pilot_data or PilotData()
        result = section(title, f"Data: {log.date or day.date or 'Do ustalenia'}\nTrasa: {log.route_start or 'Do ustalenia'} → {log.route_end or 'Do ustalenia'}\nStrefa: {log.time_zone or 'Do ustalenia'}\n{item.body or day.public_description}", "day-section")
        result += listing("Atrakcje programu", [s.name for s in day.stops])
        result += table("Czasy i dystanse — planowane", ["Parametr", "Wartość"], [[label, str(getattr(log, key)) if getattr(log, key) is not None else 'Do ustalenia'] for key, label in (("drive_km", "Jazda km"), ("walk_km", "Pieszo km"), ("elevation_gain_m", "Przewyższenie m"), ("drive_minutes", "Czas jazdy min"), ("activity_minutes", "Aktywności min"))])
        entries = [e for e in sorted(pilot.schedule, key=schedule_order) if e.day_id == day.day_id]
        result += operational_entries("Harmonogram chronologiczny", entries) if entries else section("Harmonogram", "Godziny i postoje do ustalenia")
        hotels = [e for e in pilot.accommodations if e.entry_id == log.accommodation_entry_id or e.day_id == day.day_id]
        result += ''.join(operational_entry("Nocleg", h) for h in hotels) or section("Nocleg", "Nocleg nie został potwierdzony")
        result += section("Weryfikacja metryk", f"{log.verification_status} · {log.source or 'Pomiar do wykonania; wartości nie są potwierdzone'}")
        result += section("Notatki organizacyjne", log.organizational_notes or "Do uzupełnienia") + section("Ryzyka i plan B", log.plan_b or "Do uzupełnienia")
    if item.kind == "knowledge":
        knowledge = item.knowledge
        status = "ZWERYFIKOWANE — według wskazanych źródeł" if knowledge.verification_status == "verified" else "NIEZWERYFIKOWANE — materiał roboczy"
        result = section(title, status + "\n" + (item.body or "Treść do opracowania ze źródłami"), "day-section")
        day = next(d for d in draft.trip_snapshot.days if d.day_id == item.day_id)
        result += listing("Miejsca z programu", [s.name for s in day.stops if s.stop_id in knowledge.stop_ids])
        for key, label in (("facts", "Najważniejsze informacje / fakty"), ("history", "Historia regionu"), ("geology_nature", "Geologia i przyroda"), ("culture", "Kultura i zwyczaje"), ("connection", "Co łączy miejsca?"), ("observations", "Na co zwrócić uwagę?"), ("stories", "Ciekawostki i historie dla grupy"), ("pilot_notes", "Dodatkowe informacje dla pilota")):
            if getattr(knowledge, key):
                result += section(label, getattr(knowledge, key))
        result += listing("Źródła i daty sprawdzenia", [s.reference + " · " + str(s.checked_on or 'Data sprawdzenia do uzupełnienia') for s in knowledge.sources])
    if item.day_id and item.kind in {"logistics", "knowledge"}:
        day = next(d for d in draft.trip_snapshot.days if d.day_id == item.day_id)
        result = result.replace('<section class="block', f'<section data-context="Dzień {day.day_number}" class="block')
    return result


def render_document(draft, assets, output_format="a4"):
    if draft.sections is None and draft.template_id not in {"offer.private", "pilot.basic", "marketing.collection"}:
        from app.document_studio.sections import default_sections
        draft = draft.model_copy(deep=True)
        draft.sections = default_sections(draft)
    issues = document_issues(draft, assets)
    if output_format not in {"a4", "social"} or output_format == "social" and draft.template_id != "marketing.collection":
        raise ValueError("Ten typ dokumentu obsługuje format A4")
    if draft.sections is None:
        if draft.template_id != "marketing.collection":
            return render_trip_document(draft, assets)
        campaign = draft.campaign_snapshot.model_copy(deep=True)
        campaign.title, campaign.layout_variant = draft.title, draft.layout_variant
        return render_marketing(build_marketing(campaign, draft.campaign_trip_snapshots, assets), output_format, data_origin=draft.data_origin)
    blocks = section("DOKUMENT ROBOCZY", "Do przeglądu i uzupełnienia. Podgląd ani PDF roboczy nie oznacza zatwierdzenia dokumentu.", "demo-banner")
    if draft.template_id == "offer.self_guide":
        blocks += section("SELF-GUIDE — BEZ PILOTA NA MIEJSCU", "Zakres organizacji, wsparcia i ewentualnego briefingu wymaga osobnego uzgodnienia.", "demo-banner")
    if draft.template_id == "offer.school":
        blocks += section("EDUKACJA / PRZYRODA / INTEGRACJA", "Cele i ich powiązanie z programem wymagają uzupełnienia.", "demo-banner")
    if draft.demo_example:
        blocks += section("PRZYKŁAD DEMO — DANE FIKCYJNE", "Terminy, usługi, ceny i statusy są demonstracyjne. FIKCYJNY PRZYKŁAD DEMO.", "demo-banner")
    for item in sorted(draft.sections, key=lambda s: s.order):
        if item.visible:
            blocks += render_section(draft, item, assets, output_format)
    classification = "WEWNĘTRZNE · ROBOCZY" if draft.template_id.startswith("pilot.") else "MARKETING · WERSJA ROBOCZA" if draft.template_id == "marketing.collection" else "DLA KLIENTA · WERSJA ROBOCZA"
    return render_shell(draft.title, blocks, issues, output_format, draft.template_id.replace('.', '-'),
        f"{draft.document_id[:8]} · rew. {draft.revision} · {draft.template_id} {draft.template_version} · dane r{(draft.trip_snapshot or draft.campaign_snapshot).revision}", classification,
        draft_export=draft.template_id not in {"offer.private", "pilot.basic", "marketing.collection"}, data_origin=draft.data_origin)
