"""Complete gateway-to-result contract with mocked external HTTP providers."""
import hashlib
import hmac
import json
from urllib.parse import urlsplit

import httpx
import pytest
from fastapi.testclient import TestClient

from app.db import Database
from app.main import create_app
from app.messaging import WahaMessagingProvider
from app.planning_providers import GoogleMaps, OpenAIPlanner
from app.waha import WahaSettings
from app.worker import process_ack, process_next, process_result

TEXT = "Zaplanuj 2 dni: Wrocław → Karpacz → Szklarska Poręba → Wrocław. Natura, maksymalnie 3 godziny jazdy dziennie."


@pytest.mark.parametrize("provider_fails", [False, True])
def test_complete_signed_webhook_to_viewer_and_outbound(tmp_path, monkeypatch, provider_fails):
    import app.planning as planning
    monkeypatch.setenv("PLANNING_MODE", "live")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-openai-key")
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "synthetic-server-key")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://demo.example.test")
    sender, secret = "48123456789@c.us", "synthetic-webhook-key"
    database = Database(tmp_path / "integration.sqlite3")
    sent, routes = [], []
    trip_ids = []

    def external(request):
        body = json.loads(request.content)
        if request.url.host == "waha":
            assert request.url.path == "/api/sendText"
            assert request.headers["X-Api-Key"] == "synthetic-waha-key"
            assert body["chatId"] == sender
            sent.append(body)
            return httpx.Response(201, json={"id": "synthetic-outbound-id"})
        assert database.get_trip(trip_ids[0])["status"] == "running"
        if request.url.host == "api.openai.com":
            if provider_fails:
                return httpx.Response(403, json={"error": {"message": "not authorized"}})
            draft = {"requirements": {"start": "Wrocław", "end": "Wrocław", "days": 2,
                     "required_places": ["Karpacz", "Szklarska Poręba"], "preferences": ["natura"],
                     "max_daily_drive_min": 180}, "candidates": [
                         {"query": "Wang Church Karpacz Poland", "day": 1},
                         {"query": "Kamieńczyk parking Szklarska Poręba Poland", "day": 2}]}
            return httpx.Response(200, json={"status": "completed", "output": [{"type": "message", "content": [
                {"type": "output_text", "text": json.dumps(draft)}]}]})
        if request.url.host == "places.googleapis.com":
            return httpx.Response(200, json={"places": [{"id": "synthetic-" + body["textQuery"],
                "displayName": {"text": body["textQuery"]}, "location": {"latitude": 50, "longitude": 15}}]})
        assert request.url.host == "routes.googleapis.com"
        routes.append(body)
        return httpx.Response(200, json={"routes": [{"distanceMeters": 150000, "duration": "10801s",
                                                   "polyline": {"encodedPolyline": "synthetic-polyline"}}]})

    transport = httpx.MockTransport(external)
    monkeypatch.setattr(planning, "OpenAIPlanner", lambda key, model: OpenAIPlanner(key, model, transport))
    monkeypatch.setattr(planning, "GoogleMaps", lambda places, routes: GoogleMaps(places, routes, transport))
    provider = WahaMessagingProvider("http://waha:3000", "synthetic-waha-key", transport)
    event = {"event": "message", "session": "default", "id": "envelope-1", "payload": {
        "id": "incoming-unique-id", "from": sender, "fromMe": False, "hasMedia": False,
        "body": TEXT, "_data": {"type": "chat"}}}
    raw = json.dumps(event, ensure_ascii=False).encode()
    headers = {"X-Webhook-Hmac-Algorithm": "sha512",
               "X-Webhook-Hmac": hmac.new(secret.encode(), raw, hashlib.sha512).hexdigest()}
    with TestClient(create_app(database.path, waha_settings=WahaSettings(secret, frozenset({sender})))) as client:
        assert client.post("/api/webhooks/waha", content=raw).status_code == 401
        accepted = client.post("/api/webhooks/waha", content=raw, headers=headers).json()
        assert accepted["status"] == "accepted"
        trip_ids.append(accepted["trip_id"])
        assert database.get_trip(trip_ids[0])["status"] == "queued"
        assert client.post("/api/webhooks/waha", content=raw, headers=headers).json()["status"] == "duplicate"
        assert process_ack(database, provider)
        assert trip_ids[0] in sent[0]["text"]
        assert process_next(database)
        job = client.get("/api/trips/" + trip_ids[0]).json()
        assert job["status"] == ("failed" if provider_fails else "completed")
        assert process_result(database, provider)
        assert len(sent) == 2
        if provider_fails:
            assert "failed" in sent[1]["text"]
            assert job["result"] is None
        else:
            result = job["result"]
            assert len(routes) == 2
            assert all("daily_drive_limit_exceeded" in day["warnings"] for day in result["days"])
            assert all(day["google_maps_url"].startswith("https://www.google.com/maps/dir/") for day in result["days"])
            url = result["viewer_url"]
            assert url in sent[1]["text"]
            assert "driving limit exceeded" in sent[1]["text"]
            path = urlsplit(url).path
            assert client.get(path).status_code == 200
            data = client.get(path.replace("/trip/", "/api/viewer/")).json()
            assert data["plan"]["trip_id"] == trip_ids[0]
        assert not process_result(database, provider)
        assert not process_next(database)
        assert client.post("/api/webhooks/waha", content=raw, headers=headers).json()["trip_id"] == trip_ids[0]
        with database.connect() as connection:
            assert connection.execute("SELECT COUNT(*) FROM trips").fetchone()[0] == 1


def test_browser_fallback_served():
    # Endpoint behavior is exercised through a temporary database, never paid APIs.
    from tempfile import TemporaryDirectory
    from pathlib import Path
    with TemporaryDirectory() as directory, TestClient(create_app(Path(directory) / "db.sqlite3")) as client:
        response = client.get("/planner")
        assert response.status_code == 200
        assert 'id="trip-form"' in response.text
        assert "Zaplanuj 2 dni" in response.text
        assert client.get("/static/create.js").status_code == 200
