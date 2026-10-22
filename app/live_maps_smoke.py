"""Manually controlled paid smoke: exactly two Places searches and one Routes call.

Run `python -m app.live_maps_smoke`. Never called by pytest or application startup.
"""
import json
import os
import sys
from pathlib import Path

from app.planning_providers import GoogleMaps, PlanningError


def main():
    # This explicit local command loads .env without overriding exported values.
    path = Path(".env")
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    places_key = os.getenv("GOOGLE_PLACES_API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY")
    routes_key = os.getenv("GOOGLE_ROUTES_API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY")
    if not places_key or not routes_key:
        print("NOT VERIFIED: Google Places/Routes keys are not configured. No paid calls made.")
        return 0
    maps = GoogleMaps(places_key, routes_key)
    try:
        stops = [maps.resolve(query) for query in ("Wrocław, Poland", "Karpacz, Poland")]
        if any(stop is None for stop in stops):
            raise PlanningError("Smoke test place could not be resolved.")
        route = maps.route(stops)
        print(json.dumps({
            "verification_status": "verified", "source": "live_google_apis",
            "places": [stop.model_dump() for stop in stops],
            "distance_meters": route.distance_meters,
            "duration_seconds": route.duration_seconds,
            "polyline_present": bool(route.encoded_polyline),
        }, ensure_ascii=False))
        return 0
    except PlanningError as error:
        print("NOT VERIFIED: " + str(error))
        return 1


if __name__ == "__main__":
    sys.exit(main())
