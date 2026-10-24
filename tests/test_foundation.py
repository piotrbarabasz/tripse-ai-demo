from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db import Database
from app.main import create_app
from app.worker import process_next


@pytest.fixture
def setup(tmp_path):
    path = tmp_path / "tripse.sqlite3"
    with TestClient(create_app(path)) as client:
        yield client, Database(path)


def test_health(setup):
    client, _ = setup
    assert client.get("/health").json() == {"status": "ok", "generation_mode": "mock"}


def test_trip_lifecycle_and_persistence(setup):
    client, database = setup
    request = "Zaplanuj 2 dni: Wrocław → Karpacz → Wrocław."
    response = client.post("/api/trips", json={"text": request})
    assert response.status_code == 202
    trip_id = response.json()["trip_id"]
    assert response.headers["location"] == f"/api/trips/{trip_id}"
    queued = client.get(response.headers["location"]).json()
    assert queued["status"] == "queued"
    assert queued["request_text"] == request
    assert queued["result"] is None
    assert queued["error"] is None

    def generator(trip_id, text):
        assert database.get_trip(trip_id)["status"] == "running"
        from app.generator import generate_mock_trip
        return generate_mock_trip(trip_id, text)

    assert process_next(Database(database.path), generator)
    with TestClient(create_app(database.path)) as restarted_client:
        completed = restarted_client.get(f"/api/trips/{trip_id}").json()
    assert completed["status"] == "completed"
    assert completed["error"] is None
    result = completed["result"]
    assert result["is_mock"] is True
    assert result["verification_status"] == "unverified"
    assert result["request_text"] == request
    for day in result["days"]:
        assert day["routing_status"] == "demo"
        assert day["stops"]
        assert all(p["source"] == "demo_fixture" for p in day["stops"])
        assert day["drive_minutes"] > 0
        assert day["distance_km"] > 0
        assert day["demo_geometry"]
        for field in ("encoded_polyline", "google_maps_url"):
            assert day[field] is None
    assert process_next(database) is False


def test_worker_failure_does_not_block_next_job(setup):
    client, database = setup
    failed_id = client.post("/api/trips", json={"text": "Zaplanuj 2 dni we Wrocławiu"}).json()["trip_id"]

    def broken_generator(*args):
        raise RuntimeError("private error details")

    assert process_next(database, broken_generator)
    failed = client.get(f"/api/trips/{failed_id}").json()
    assert failed["status"] == "failed"
    assert failed["result"] is None
    assert failed["error"] == "Trip generation failed. See worker logs."
    next_id = database.create_trip("Zaplanuj 2 dni we Wrocławiu")
    assert process_next(database)
    assert database.get_trip(next_id)["status"] == "completed"


def test_interrupted_job_recovery_and_exclusive_claim(setup):
    _, database = setup
    trip_id = database.create_trip("Zaplanuj 2 dni we Wrocławiu")
    assert database.claim_next()["trip_id"] == trip_id
    other_connection = Database(database.path)
    assert other_connection.claim_next() is None
    other_connection.recover_interrupted()
    assert database.get_trip(trip_id)["status"] == "queued"
    assert process_next(other_connection)
    assert database.get_trip(trip_id)["status"] == "completed"


@pytest.mark.parametrize("payload", [{}, {"text": ""}, {"text": "  "}, {"text": "x" * 10001}, {"text": 5}])
def test_invalid_requests(setup, payload):
    client, database = setup
    assert client.post("/api/trips", json=payload).status_code == 422
    assert database.claim_next() is None


def test_unknown_trip(setup):
    client, _ = setup
    assert client.get(f"/api/trips/{uuid4()}").status_code == 404
    assert client.get("/api/trips/not-a-uuid").status_code == 422
