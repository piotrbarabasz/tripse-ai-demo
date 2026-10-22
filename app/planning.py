import os
from urllib.parse import urlencode

from app.planning_models import TripDay, TripPlan, UnresolvedPlace
from app.planning_providers import GoogleMaps, OpenAIPlanner, PlanningError


def directions_url(stops):
    if len(stops) < 2:
        return None
    params = {"api": "1", "travelmode": "driving", "origin": stops[0].name,
              "origin_place_id": stops[0].place_id, "destination": stops[-1].name,
              "destination_place_id": stops[-1].place_id}
    if len(stops) > 2:
        params["waypoints"] = "|".join(p.name for p in stops[1:-1])
        params["waypoint_place_ids"] = "|".join(p.place_id for p in stops[1:-1])
    return "https://www.google.com/maps/dir/?" + urlencode(params)


class TripPipeline:
    def __init__(self, planner, maps):
        self.planner, self.maps = planner, maps

    def __call__(self, trip_id: str, text: str) -> dict:
        draft = self.planner.draft(text)
        brief = draft.requirements
        if not brief.start or not brief.end or brief.days not in (1, 2):
            raise PlanningError("Please specify start, end and a duration of 1 or 2 days.")
        if any(candidate.day > brief.days for candidate in draft.candidates):
            raise PlanningError("Suggested stop falls outside the requested trip duration.")
        # Required places preserve their order. Day buckets are intentionally simple.
        buckets = [[] for _ in range(brief.days)]
        key = lambda value: value.strip().casefold()
        endpoints = {key(brief.start), key(brief.end)}
        required = list({key(query): query.strip() for query in brief.required_places
                         if key(query) not in endpoints}.values())
        for index, query in enumerate(required):
            buckets[min(index * brief.days // max(len(required), 1), brief.days - 1)].append(query)
        queries = {key(query): query.strip() for query in [brief.start, brief.end, *required]}
        if any(not query for query in queries.values()) or len(queries) > 8:
            raise PlanningError("The brief must contain at most 8 unique locations, including start and end.")
        warnings = ["Draft only: Places search matches require relevance review; no opening hours, "
                    "walking access, seasonal availability or visit durations are verified.",
                    "Driving durations are Google Routes estimates without live traffic. "
                    "Day grouping is not optimized and does not guarantee the driving limit."]
        for candidate in draft.candidates:
            if key(candidate.query) in queries:
                continue
            if len(queries) >= 8:
                warnings.append("candidate_limit: additional suggested stops were omitted.")
                break
            queries[key(candidate.query)] = candidate.query.strip()
            buckets[candidate.day - 1].append(candidate.query.strip())
        resolved, unresolved = {}, []
        for query_key, query in queries.items():
            try:
                place = self.maps.resolve(query)
                reason = "No Google Places match."
            except PlanningError as error:
                place, reason = None, str(error)
            resolved[query_key] = place
            if place is None:
                unresolved.append(UnresolvedPlace(query=query, reason=reason))
                warnings.append(f"unresolved_place: {query}")
        days, previous = [], resolved[key(brief.start)]
        end = resolved[key(brief.end)]
        for index, queries_for_day in enumerate(buckets):
            day = TripDay(number=index + 1, stops=[])
            if previous is not None:
                day.stops.append(previous)
            for query in queries_for_day:
                place = resolved[key(query)]
                if place is None:
                    day.warnings.append(f"unresolved_place: {query}")
                elif not day.stops or place.place_id != day.stops[-1].place_id:
                    day.stops.append(place)
            if index == brief.days - 1 and end is not None:
                if not day.stops or end.place_id != day.stops[-1].place_id:
                    day.stops.append(end)
            # Never calculate a misleading route with a missing endpoint/required place.
            missing_required = any(resolved[key(query)] is None for query in queries_for_day if query in required)
            can_route = (previous is not None and len(day.stops) >= 2 and not missing_required
                         and (index != brief.days - 1 or end is not None))
            if can_route:
                day.google_maps_url = directions_url(day.stops)
                try:
                    route = self.maps.route(day.stops)
                    day.routing_status = "verified"
                    day.distance_meters = route.distance_meters
                    day.duration_seconds = route.duration_seconds
                    day.distance_km = route.distance_meters / 1000
                    day.drive_minutes = route.duration_seconds / 60
                    day.encoded_polyline = route.encoded_polyline
                    if brief.max_daily_drive_min is not None and route.duration_seconds > brief.max_daily_drive_min * 60:
                        day.warnings.append("daily_drive_limit_exceeded")
                except PlanningError:
                    day.routing_status = "routing_failed"
                    day.warnings.append("route_calculation_failed")
            else:
                day.warnings.append("route_unverified: insufficient stops or an unresolved required endpoint/place.")
            days.append(day)
            previous = day.stops[-1] if day.stops else None
        verified_routes = sum(day.routing_status == "verified" for day in days)
        status = "verified" if verified_routes == brief.days and not unresolved else (
            "partial" if verified_routes or any(resolved.values()) else "unverified")
        for day in days:
            warnings.extend(f"day_{day.number}: {warning}" for warning in day.warnings)
        # Deduplicate Google IDs, even if different searches matched the same place.
        places = {place.place_id: place for place in resolved.values() if place is not None}
        plan = TripPlan(trip_id=trip_id, title=f"{brief.days} day trip: {brief.start} → {brief.end}",
                        verification_status=status, requirements=brief, places=list(places.values()),
                        unresolved_places=unresolved, days=days, warnings=warnings)
        return plan.model_dump(mode="json")


def configured_generator():
    mode = os.getenv("PLANNING_MODE", "live")
    if mode == "mock":
        from app.generator import generate_mock_trip
        return generate_mock_trip
    if mode != "live":
        raise PlanningError("PLANNING_MODE must be live or mock.")
    openai_key = os.getenv("OPENAI_API_KEY", "")
    places_key = os.getenv("GOOGLE_PLACES_API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY", "")
    routes_key = os.getenv("GOOGLE_ROUTES_API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not all((openai_key, places_key, routes_key)):
        raise PlanningError("Live planning requires OPENAI_API_KEY and Google Places/Routes API keys. "
                            "Configure keys or explicitly select PLANNING_MODE=mock.")
    return TripPipeline(OpenAIPlanner(openai_key, os.getenv("OPENAI_MODEL", "gpt-4o-mini")),
                        GoogleMaps(places_key, routes_key))
