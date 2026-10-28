"""Template configuration contains no storage-specific logic or PDF renderer."""
from app.document_studio.models import DocumentTemplate, SectionSpec


def template(id, name, family, audience, confidentiality, description):
    return DocumentTemplate(
        template_id=id, name=name, family=family, audience=audience,
        confidentiality=confidentiality, description=description,
        source_type="campaign" if family == "marketing" else "trip",
        layout_variants=["new_trips", "theme_collection"] if family == "marketing" else ["standard"],
    )


TEMPLATES = {t.template_id: t for t in [
    template("offer.private", "Wyjazd indywidualny", "offer", "Klient prywatny", "client", "Program i opis indywidualnego wyjazdu."),
    template("offer.self_guide", "Self-Guide", "offer", "Podróżnik samodzielny", "client", "Wyjazd bez pilota; zakres wsparcia wymaga ustalenia."),
    template("offer.school", "Wycieczka szkolna", "offer", "Szkoła", "client", "Program edukacyjny i integracyjny."),
    template("offer.incentive", "Wyjazd firmowy / incentive", "offer", "Firma", "client", "Program wyjazdu zespołowego."),
    template("marketing.collection", "Nowości / kolekcje", "marketing", "Odbiorca marketingu", "public", "Kolekcja wielu kierunków z jednej kampanii."),
    template("pilot.basic", "Rozpiska podstawowa", "pilot", "Pilot", "internal_restricted", "Skrót programu dla pilota. Logistyka do uzupełnienia."),
    template("pilot.advanced", "Rozpiska zaawansowana", "pilot", "Pilot", "internal_restricted", "Wielodniowy program. Harmonogram i ryzyka do uzupełnienia."),
    template("pilot.knowledge", "Materiały merytoryczne", "pilot", "Pilot", "internal", "Miejsca programu jako baza do opracowania wiedzy ze źródłami."),
]}

# Presentation definitions; document instances hold independent editable sections.
SECTION_DEFINITIONS = {
    "offer.private": [
        ("cover", "Okładka", "cover"), ("summary", "Podsumowanie wyprawy", "summary"),
        ("highlights", "Najważniejsze atrakcje i wyróżniki", "highlights"),
        ("program", "Program dzień po dniu", "program"), ("accommodation", "Zakwaterowanie", "accommodation"),
        ("transport", "Transport", "transport"), ("included", "Świadczenia w cenie", "included"),
        ("excluded", "Świadczenia poza ceną", "excluded"), ("price", "Cena i warunki", "price"), ("cta", "Kontakt / CTA", "cta")],
    "offer.self_guide": [
        ("cover", "Self-Guide — bez pilota na miejscu", "cover"),
        ("how", "Jak działa Self-Guide?", "self_guide"), ("scope", "Organizacja po stronie TRIPSE", "organization_scope"),
        ("own", "Co klient organizuje samodzielnie?", "self_arrangements"), ("program", "Program dzień po dniu", "program"),
        ("transport", "Transport i przemieszczanie się", "transport"), ("accommodation", "Zakwaterowanie", "accommodation"),
        ("materials", "Materiały i mapy dla uczestników", "materials"), ("support", "Zakres wsparcia", "support"),
        ("briefing", "Briefing online — do uzgodnienia", "online_briefing"), ("included", "Świadczenia w cenie", "included"),
        ("excluded", "Świadczenia poza ceną", "excluded"), ("price", "Wycena i warunki", "price"), ("cta", "Kontakt", "cta")],
    "offer.school": [
        ("cover", "Wycieczka szkolna", "cover"), ("group", "Informacje o grupie", "school_group"),
        ("education", "Edukacja", "education"), ("nature", "Przyroda", "nature"), ("integration", "Integracja", "integration"),
        ("program", "Program wycieczki", "program"), ("activities", "Aktywności i warsztaty", "workshops"),
        ("transport", "Transport", "transport"), ("accommodation", "Wyżywienie i zakwaterowanie", "accommodation"),
        ("supervision", "Organizacja i odpowiedzialność opiekunów", "supervision"),
        ("included", "Świadczenia w cenie", "included"), ("excluded", "Poza ceną", "excluded"),
        ("price", "Cena i warunki", "price"), ("cta", "Kontakt", "cta")],
    "offer.incentive": [
        ("cover", "Wyjazd firmowy / incentive", "cover"), ("summary", "Cel wyjazdu dla zespołu", "summary"),
        ("highlights", "Najważniejsze doświadczenia", "highlights"), ("program", "Program dzień po dniu", "program"),
        ("hotel", "Hotel / nocleg / infrastruktura obiektu", "hotel"), ("team", "Integracja i team building", "team_building"),
        ("workshops", "Szkolenia, warsztaty i spotkania", "workshops"), ("meals", "Posiłki i wydarzenia wieczorne", "meals_events"),
        ("transport", "Transport i logistyka", "transport"), ("included", "W cenie", "included"), ("excluded", "Poza ceną", "excluded"),
        ("variants", "Warianty", "variants"), ("price", "Wycena i warunki", "price"), ("cta", "Kontakt", "cta")],
    "pilot.basic": [
        ("cover", "Informacje o wyjeździe", "cover"), ("group", "Pilot i grupa", "pilot_group"),
        ("flights", "Przyloty / wyloty", "flights"), ("transfers", "Transfery i punkty zbiórki", "transfers"),
        ("accommodations", "Noclegi", "accommodations"), ("bookings", "Rezerwacje atrakcji", "activity_bookings"),
        ("program", "Program każdego dnia", "program"), ("contacts", "Kontakty organizacyjne", "contacts"),
        ("open", "Sprawy do potwierdzenia", "open_items"), ("notes", "Notatki pilota", "internal_notes")],
    "pilot.advanced": [
        ("cover", "Metryka wyjazdu", "cover"), ("route", "Tabela całej trasy", "route"),
        ("flights", "Transport i loty", "flights"), ("transfers", "Transfery", "transfers"),
        ("accommodations", "Noclegi i rezerwacje", "accommodations"), ("bookings", "Rezerwacje atrakcji", "activity_bookings"),
        ("contacts", "Kontakty organizacyjne", "contacts"), ("open", "Sprawy do potwierdzenia", "open_items")],
    "pilot.knowledge": [("cover", "Materiały merytoryczne — program i źródła", "cover")],
    "marketing.collection": [("collection", "Kolekcja wyjazdów", "collection")],
}
for identifier, definitions in SECTION_DEFINITIONS.items():
    TEMPLATES[identifier].template_version = "0.4.0"
    TEMPLATES[identifier].default_sections = [SectionSpec(role=role, title=title, binding=binding,
        required=role not in {"team", "workshops", "meals", "notes", "briefing"}) for role, title, binding in definitions]
