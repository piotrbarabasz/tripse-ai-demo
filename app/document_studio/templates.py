"""Template configuration contains no storage-specific logic or PDF renderer."""
from app.document_studio.models import DocumentTemplate


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
TEMPLATES["marketing.collection"].template_version = "0.2.0"
TEMPLATES["offer.private"].template_version = "0.3.0"
TEMPLATES["pilot.basic"].template_version = "0.3.0"
