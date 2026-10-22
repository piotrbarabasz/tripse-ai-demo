import json
import time
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from fastapi.testclient import TestClient

from app.db import Database
from app.main import create_app
from app.planning import TripPipeline
from app.planning_models import TripPlan
from app.planning_providers import GoogleMaps, OpenAIPlanner, PlanningError
from app.worker import process_ack, process_next, process_result

TEXT = "Zaplanuj 2 dni: Wrocław → Karpacz → Szklarska Poręba → Wrocław. Natura, maksymalnie 3 godziny jazdy dziennie."
DRAFT = {
    "requirements": {"start": "Wrocław", "end": "Wrocław", "days": 2,
                     "required_places": ["Karpacz", "Szklarska Poręba"],
                     "preferences": ["natura"], "max_daily_drive_min": 180},
    "candidates": [{"query": "Wang Church Karpacz Poland", "day": 1},
                   {"query": "Kamieńczyk waterfall parking Szklarska Poręba Poland", "day": 2}],
}


def pipeline(*, missing=None, route_failure=False, duration="7200s", draft=None, openai_status="completed"):
    requests = []

    def handler(request):
        body = json.loads(request.content)
        requests.append((request, body))
        if request.url.host == "api.openai.com":
            assert body["text"]["format"]["strict"] is True
            assert body["store"] is False
            schema = json.dumps(body["text"]["format"]["schema"])
            for forbidden in ("distance_meters", "drive_minutes", "place_id", "lat", "lng"):
                assert f'"{forbidden}"' not in schema
            return httpx.Response(200, json={"status": openai_status, "output": [
                {"type": "message", "content": [{"type": "output_text", "text": json.dumps(draft or DRAFT)}]}
            ]})
        if request.url.host == "places.googleapis.com":
            assert request.headers["X-Goog-FieldMask"] == "places.id,places.displayName,places.location"
            query = body["textQuery"]
            if query == missing:
                return httpx.Response(200, json={"places": []})
            # Explicitly synthetic coordinates and IDs supplied by the mocked Google API.
            return httpx.Response(200, json={"places": [{
                "id": "fake-id-" + query, "displayName": {"text": query},
                "location": {"latitude": 50.0, "longitude": 15.0},
            }]})
        assert request.url.host == "routes.googleapis.com"
        assert body["travelMode"] == "DRIVE"
        assert "placeId" in body["origin"]
        assert isinstance(body["intermediates"], list)
        if route_failure:
            return httpx.Response(503, json={"error": {"message": "provider error"}})
        return httpx.Response(200, json={"routes": [{"distanceMeters": 100000, "duration": duration,
                                                   "polyline": {"encodedPolyline": "synthetic-test-polyline"}}]})

    transport = httpx.MockTransport(handler)
    return TripPipeline(OpenAIPlanner("fake-key", "gpt-4o-mini", transport),
                        GoogleMaps("fake-places-key", "fake-routes-key", transport)), requests


def test_mocked_pipeline_success_and_contract():
    generate, calls = pipeline()
    result = TripPlan.model_validate(generate("trip-id", TEXT))
    assert not result.is_mock
    assert result.verification_status == "verified"
    assert result.requirements.max_daily_drive_min == 180
    assert result.requirements.preferences == ["natura"]
    assert len(result.days) == 2
    assert len(result.places) == 5
    assert all(place.source == "google_places" for place in result.places)
    assert result.days[0].stops[0].name == "Wrocław"
    assert result.days[1].stops[-1].name == "Wrocław"
    assert result.days[0].stops[-1] == result.days[1].stops[0]
    for day in result.days:
        assert day.distance_meters == 100000
        assert day.duration_seconds == 7200
        assert day.distance_km == 100
        assert day.drive_minutes == 120
        assert day.encoded_polyline == "synthetic-test-polyline"
        link = parse_qs(urlsplit(day.google_maps_url).query)
        assert link["api"] == ["1"]
        assert link["origin_place_id"] == [day.stops[0].place_id]
        assert link["destination_place_id"] == [day.stops[-1].place_id]
    assert len([r for r, _ in calls if r.url.host == "api.openai.com"]) == 1
    assert len([r for r, _ in calls if r.url.host == "places.googleapis.com"]) == 5
    assert len([r for r, _ in calls if r.url.host == "routes.googleapis.com"]) == 2


def test_invalid_optional_place_is_not_put_on_map():
    missing = DRAFT["candidates"][0]["query"]
    generate, _ = pipeline(missing=missing)
    result = generate("id", TEXT)
    assert result["verification_status"] == "partial"
    assert result["unresolved_places"][0]["query"] == missing
    assert all(stop["query"] != missing for day in result["days"] for stop in day["stops"])
    assert "unresolved_place" in " ".join(result["warnings"])


@pytest.mark.parametrize("missing", ["Wrocław", "Karpacz", "Szklarska Poręba"])
def test_unresolved_required_place_prevents_misleading_full_route(missing):
    generate, _ = pipeline(missing=missing)
    result = generate("id", TEXT)
    assert result["verification_status"] != "verified"
    day = result["days"][1 if missing == "Szklarska Poręba" else 0]
    assert day["routing_status"] == "unverified"
    assert day["distance_km"] is None
    assert day["duration_seconds"] is None
    assert day["google_maps_url"] is None


def test_routing_failure_is_explicit():
    generate, _ = pipeline(route_failure=True)
    result = generate("id", TEXT)
    for day in result["days"]:
        assert day["routing_status"] == "routing_failed"
        assert "route_calculation_failed" in day["warnings"]
        for field in ("distance_km", "distance_meters", "drive_minutes", "duration_seconds", "encoded_polyline"):
            assert day[field] is None
        # A Maps URL is a fresh directions request, not a verified route/polyline.
        assert day["google_maps_url"].startswith("https://www.google.com/maps/dir/")


@pytest.mark.parametrize("duration,expected", [("10800s", False), ("10800.001s", True)])
def test_limit_compares_unrounded_seconds(duration, expected):
    generate, _ = pipeline(duration=duration)
    result = generate("id", TEXT)
    assert ("daily_drive_limit_exceeded" in result["days"][0]["warnings"]) is expected


def test_candidate_budget_caps_google_requests():
    draft = json.loads(json.dumps(DRAFT))
    draft["candidates"] = [{"query": f"attraction-{i}", "day": 1 + i % 2} for i in range(8)]
    generate, calls = pipeline(draft=draft)
    result = generate("id", TEXT)
    assert len(result["places"]) == 8
    assert len([r for r, _ in calls if r.url.host == "places.googleapis.com"]) == 8


@pytest.mark.parametrize("change", [
    {"place_id": "LLM-invented"}, {"lat": 50}, {"drive_minutes": 20},
])
def test_llm_cannot_smuggle_map_facts(change):
    draft = json.loads(json.dumps(DRAFT))
    draft["candidates"][0].update(change)
    generate, calls = pipeline(draft=draft)
    with pytest.raises(PlanningError):
        generate("id", TEXT)
    assert len(calls) == 1


@pytest.mark.parametrize("response", [
    {"routes": []}, {"routes": [{"distanceMeters": 100, "duration": "1s"}]},
    {"routes": [{"distanceMeters": -1, "duration": "1s", "polyline": {"encodedPolyline": "abc"}}]},
    {"routes": [{"distanceMeters": 100, "duration": "NaNs", "polyline": {"encodedPolyline": "abc"}}]},
])
def test_bad_google_route_data_never_becomes_zero(response):
    maps = GoogleMaps("key", "key", httpx.MockTransport(lambda _: httpx.Response(200, json=response)))
    from app.planning_models import Place
    p = Place(query="a", place_id="a", name="a", lat=1, lng=2)
    with pytest.raises(PlanningError):
        maps.route([p, p])


def test_worker_persistence_viewer_and_whatsapp_summary(tmp_path):
    path = tmp_path / "db.sqlite3"
    generate, _ = pipeline(duration="10801s")
    with TestClient(create_app(path)) as client:
        database = Database(path)
        trip_id, _ = database.create_waha_trip("default", "message-id", "tester@c.us", TEXT)
        assert process_next(database, generate)
        job = client.get(f"/api/trips/{trip_id}").json()
        assert job["status"] == "completed"
        result = job["result"]
        TripPlan.model_validate(result)
        token = result["viewer_url"].rsplit("/", 1)[1]
        assert len(token) == 43
        assert result["viewer_expires_at"] > time.time()
        assert process_result(database, None) is False  # Acknowledgement must precede result.

        class Provider:
            def __init__(self):
                self.messages = []

            def send_text(self, **kwargs):
                self.messages.append(kwargs["text"])

        provider = Provider()
        process_ack(database, provider)
        assert process_result(database, provider)
        assert "driving limit exceeded" in provider.messages[-1]
        assert result["viewer_url"] in provider.messages[-1]
        assert process_result(database, provider) is False
    with TestClient(create_app(path)) as restarted:
        page = restarted.get("/trip/" + token)
        assert page.status_code == 200
        assert "text/html" in page.headers["Content-Type"]
        view = restarted.get("/api/viewer/" + token)
        assert view.status_code == 200
        assert view.headers["Cache-Control"] == "no-store"
        assert "request_text" not in view.json()["plan"]
        assert "sender" not in view.json()["plan"]
        assert restarted.get("/trip/" + "x" * 43).status_code == 404
        assert restarted.post("/trip/" + token, json={}).status_code == 405
        with database.connect() as connection:
            connection.execute("UPDATE trip_viewers SET expires_at = 0")
        assert restarted.get("/trip/" + token).status_code == 404


def test_worker_missing_keys_fails_explicitly(tmp_path, monkeypatch):
    monkeypatch.setenv("PLANNING_MODE", "live")
    database = Database(tmp_path / "db.sqlite3")
    database.initialize()
    trip_id = database.create_trip(TEXT)
    assert process_next(database)
    job = database.get_trip(trip_id)
    assert job["status"] == "failed"
    assert "requires OPENAI_API_KEY" in job["error"]
    assert job["result"] is None


def test_openai_incomplete_output_fails_worker(tmp_path):
    database = Database(tmp_path / "db.sqlite3")
    database.initialize()
    trip_id = database.create_trip(TEXT)
    generate, calls = pipeline(openai_status="incomplete")
    assert process_next(database, generate)
    assert database.get_trip(trip_id)["status"] == "failed"
    assert "OpenAI" in database.get_trip(trip_id)["error"]
    assert len(calls) == 1


def test_result_retry_and_recovery_do_not_repeat_planning(tmp_path):
    database = Database(tmp_path / "db.sqlite3")
    database.initialize()
    generate, calls = pipeline()
    trip_id, _ = database.create_waha_trip("default", "id", "tester", TEXT)
    process_next(database, generate)

    class Provider:
        def send_text(self, **kwargs):
            pass

    class Offline:
        def send_text(self, **kwargs):
            raise RuntimeError("offline")

    process_ack(database, Provider())
    assert process_result(database, Offline())
    assert database.claim_result() is None
    with database.connect() as connection:
        connection.execute("UPDATE waha_results SET retry_after = 0")
    assert database.claim_result() is not None
    database.recover_interrupted()
    assert process_result(database, Provider())
    assert not process_next(database, generate)
    assert len(calls) == 8
    assert database.get_trip(trip_id)["status"] == "completed"
