"""Offline illustrative scenarios, never presented as verified Google facts."""
import re
import unicodedata
from app.planning_models import TripPlan
from app.planning_providers import PlanningError

SCENARIOS = {
 "mountains": {"name": "Karkonosze · 2 dni", "text": "Zaplanuj 2 dni: Wrocław → Karpacz → Szklarska Poręba → Wrocław. Natura, maksymalnie 3 godziny jazdy dziennie.", "preferences": ["natura"], "days": [[0,1,2],[2,3,4,0]], "metrics": [[130,145],[165,175]], "places": [["Wrocław",51.1079,17.0385,"Początek i koniec wycieczki."],["Karpacz",50.775,15.756,"Spacer po górskiej miejscowości."],["Świątynia Wang",50.7778,15.7244,"Przykładowy przystanek przy świątyni."],["Szklarska Poręba",50.8257,15.5227,"Baza na spacer w Karkonoszach."],["Wodospad Szklarki",50.8296,15.5558,"Pomysł na spacer; dostęp wymaga sprawdzenia."]]},
 "ojcow": {"name": "Ojców · 1 dzień", "text": "Zaplanuj 1 dzień: Kraków → Ojców → Kraków. Natura, maksymalnie 2 godziny jazdy dziennie.", "preferences": ["natura","krótki wyjazd"], "days": [[0,1,2,3,0]], "metrics": [[70,100]], "places": [["Kraków",50.0647,19.945,"Początek i koniec wycieczki."],["Ojców",50.2106,19.8293,"Spacer po Dolinie Prądnika."],["Brama Krakowska",50.1964,19.8316,"Formacje skalne; fragment pieszy."],["Pieskowa Skała",50.2445,19.7795,"Przykładowy przystanek przy zamku."]]},
 "coast": {"name": "Trójmiasto · 2 dni", "text": "Zaplanuj 2 dni: Gdańsk → Sopot → Gdynia → Gdańsk. Rodzinny wyjazd, maksymalnie 2 godziny jazdy dziennie.", "preferences": ["rodzina","spokojne tempo"], "days": [[0,1,2],[2,3,4,0]], "metrics": [[25,55],[50,90]], "places": [["Gdańsk",54.352,18.6466,"Spacer po Głównym Mieście."],["Park Oliwski",54.4115,18.558,"Spokojny spacer rodzinny."],["Sopot",54.4416,18.5601,"Spacer nad morzem; nocleg nie jest rezerwowany."],["Gdynia",54.5189,18.5305,"Spacer po nabrzeżu."],["Orłowo",54.4793,18.5629,"Przykładowy przystanek nad morzem."]]}
}
CASES = {"success":"Pełny plan", "limit":"Przekroczony limit jazdy", "missing":"Nieznalezione miejsce", "routing":"Błąd trasy", "failure":"Awaria planowania", "delivery":"Ponowienie wysyłki", "expired":"Wygasły link"}

def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.lower().replace('ł','l')) if not unicodedata.combining(c))

def choose(text):
    value = normalized(text)
    for key, words in [("mountains",("wroclaw","karpacz","szklarska")),("ojcow",("krakow","ojcow")),("coast",("gdansk","sopot","gdynia"))]:
        if any(word in value for word in words): return key
    return None

def generate_demo(trip_id, text, case="success"):
    key = choose(text)
    if not key:
        raise PlanningError("Demo obsługuje Karkonosze, Ojców i Trójmiasto. Wybierz gotowy przykład ze strony głównej.")
    spec = SCENARIOS[key]
    days_match = re.search(r'(\d+)\s*(?:dni|dzien|days?)', normalized(text))
    if days_match and int(days_match[1]) != len(spec['days']):
        raise PlanningError(f"Ten przykład obejmuje {len(spec['days'])} dni. Demo nie układa dowolnych tras; wybierz gotową prośbę.")
    if case == 'failure': raise PlanningError("Symulowana awaria planowania. Wybierz Pełny plan i spróbuj ponownie.")
    places = [dict(query=p[0], place_id=f"demo:{key}:{i}", name=p[0], lat=p[1], lng=p[2], description=p[3], source="demo_fixture", verification_status="demo") for i,p in enumerate(spec['places'])]
    match = re.search(r'(\d+)\s*godzin', normalized(text))
    limit = 60 if case == 'limit' else int(match[1])*60 if match else 180
    days, unresolved = [], []
    for index, indices in enumerate(spec['days']):
        stops = [places[i] for i in indices]
        km, minutes = spec['metrics'][index]
        day = dict(number=index+1, stops=stops, routing_status="demo", distance_meters=km*1000, duration_seconds=minutes*60, distance_km=km, drive_minutes=minutes, demo_geometry=[[p['lng'],p['lat']] for p in stops], warnings=["Linia jest schematem, nie przebiegiem drogi. Czasy i dystanse są przykładowe."])
        if minutes > limit: day['warnings'].append('daily_drive_limit_exceeded')
        if index == 0 and case in ('missing','routing'):
            day.update(routing_status="routing_failed", distance_meters=None, duration_seconds=None, distance_km=None, drive_minutes=None, demo_geometry=None)
            day['warnings'].append('route_calculation_failed')
            if case == 'missing':
                removed = day['stops'].pop(1)
                unresolved.append(dict(query=removed['name'],reason="Symulowany brak wyniku wyszukiwania."))
        days.append(day)
    used = {p['place_id'] for day in days for p in day['stops']}
    plan = TripPlan(trip_id=trip_id,title=spec['name'],generation_mode="mock",is_mock=True,verification_status="unverified",
        requirements=dict(start=places[0]['name'],end=places[0]['name'],days=len(days),required_places=[],preferences=spec['preferences'],max_daily_drive_min=limit),
        places=[p for p in places if p['place_id'] in used],unresolved_places=unresolved,days=days,
        warnings=["DEMO — dane przykładowe. Bez wywołań OpenAI i Google. Miejsca, godziny otwarcia i dostępność nie są zweryfikowane."])
    result = plan.model_dump(mode='json')
    result.update(request_text=text,demo_scenario=key)
    return result
