from datetime import date

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.document_studio.models import Campaign, CampaignItem, Stop, Trip, TripDay
from app.document_studio.repository import ConflictError, JsonRepository, StorageError
from app.main import create_app


def make_trip(**changes):
    values = dict(title="Podróż testowa — żółć i Þingvellir", duration_days=15,
                  days=[TripDay(day_number=i, title=f"Dzień {i}") for i in range(1, 16)])
    values.update(changes)
    return Trip(**values)


def client_for(tmp_path, **options):
    return TestClient(create_app(tmp_path / "planner.sqlite3", document_data_path=tmp_path / "documents"),
                      base_url="http://localhost", client=("127.0.0.1", 50000), **options)


def test_models_support_long_trips_and_unknown_values():
    trip = make_trip()
    assert len(Trip.model_validate_json(trip.model_dump_json()).days) == 15
    assert trip.start_date is None
    assert Stop(name="Atrakcja").estimated_visit_duration_min is None
    assert Stop(name="Atrakcja").verification_status == "unverified"
    assert len(make_trip(duration_days=40, days=[TripDay(day_number=i, title="Etap") for i in range(1, 41)]).days) == 40


@pytest.mark.parametrize("changes", [
    {"duration_days": 2}, {"title": "  "}, {"trip_id": "../escape"}, {"trip_id": "C:\\escape"},
    {"start_date": date(2027, 1, 2), "end_date": date(2027, 1, 1)},
    {"start_date": date(2027, 1, 1), "end_date": date(2027, 1, 2)},
    {"duration_days": 1, "days": [TripDay(day_number=2, title="Etap")]},
    {"duration_days": 2, "days": [TripDay(day_id="same", day_number=i, title="Etap") for i in (1, 2)]},
    {"duration_days": 2, "days": [TripDay(day_number=i, title="Etap", stops=[Stop(stop_id="same", name="Miejsce")]) for i in (1, 2)]},
    {"start_date": date(2027, 1, 1), "duration_days": 1, "days": [TripDay(day_number=1, title="Etap", date=date(2027, 1, 2))]},
])
def test_models_reject_inconsistent_data(changes):
    with pytest.raises(ValidationError):
        make_trip(**changes)


def test_campaign_can_reference_several_trips():
    campaign = Campaign(title="Kolekcja", items=[CampaignItem(trip_id=f"trip-{i}") for i in range(3)])
    assert len(campaign.items) == 3
    with pytest.raises(ValidationError):
        Campaign(title="Powtórzenia", items=[CampaignItem(trip_id="same")] * 2)
    with pytest.raises(ValidationError):
        Campaign(title="Pusta", items=[])


def test_json_roundtrip_restart_and_conflicts(tmp_path):
    repository = JsonRepository(tmp_path / "documents", tmp_path / "fixtures")
    repository.initialize()
    trip = repository.save("trips", make_trip(), create=True)
    reopened = JsonRepository(repository.root, repository.fixtures).get("trips", trip.trip_id)
    assert reopened == trip
    assert "Þingvellir" in (repository.root / "trips" / f"{trip.trip_id}.json").read_text(encoding="utf-8")
    assert repository.save("trips", trip).revision == 2
    with pytest.raises(ConflictError):
        repository.save("trips", trip)
    with pytest.raises(ConflictError):
        repository.save("trips", reopened, create=True)


def test_atomic_save_failure_preserves_previous_file(tmp_path, monkeypatch):
    repository = JsonRepository(tmp_path)
    trip = repository.save("trips", make_trip())
    original = (tmp_path / "trips" / f"{trip.trip_id}.json").read_bytes()
    trip.title = "Zmiana"
    def fail_replace(*args):
        raise OSError("Simulated write failure")
    monkeypatch.setattr("app.document_studio.repository.os.replace", fail_replace)
    with pytest.raises(StorageError):
        repository.save("trips", trip)
    assert (tmp_path / "trips" / f"{trip.trip_id}.json").read_bytes() == original
    assert not list((tmp_path / "trips").glob("*.tmp"))


@pytest.mark.parametrize("identifier", ["../x", "..", "a/b", "a\\b", "C:\\temp", "a.json", "", "CON:", "CON", "com1", "LPT9"])
def test_repository_rejects_unsafe_ids(tmp_path, identifier):
    with pytest.raises(ValueError):
        JsonRepository(tmp_path).get("trips", identifier)


def test_repository_validates_before_writing_and_detects_corruption(tmp_path):
    repository = JsonRepository(tmp_path)
    trip = make_trip()
    trip.duration_days = 2
    with pytest.raises(ValidationError):
        repository.save("trips", trip)
    assert not list(tmp_path.rglob("*.json"))
    trip = repository.save("trips", make_trip())
    path = tmp_path / "trips" / f"{trip.trip_id}.json"
    path.write_text('{"broken":', encoding="utf-8")
    with pytest.raises(StorageError):
        repository.get("trips", trip.trip_id)


def test_fixture_overlay_does_not_modify_fixture(tmp_path):
    repository = JsonRepository(tmp_path)
    trip = repository.get("trips", "demo-iceland")
    fixture = repository.fixtures / "trips" / "demo-iceland.json"
    before = fixture.read_bytes()
    trip.title = "Lokalna Islandia"
    repository.save("trips", trip)
    assert fixture.read_bytes() == before
    assert JsonRepository(tmp_path).get("trips", trip.trip_id).title == "Lokalna Islandia"
    assert len(repository.list("trips")) == 3
    assert {p.name for p in tmp_path.iterdir()} == {"trips"}


def test_api_persistence_campaign_draft_and_planner_isolation(tmp_path):
    with client_for(tmp_path) as client:
        assert client.get("/documents/demo").status_code == 200
        assert client.get("/documents/assets/studio.js").status_code == 200
        assert client.get("/documents/assets/secret.json").status_code == 404
        assert len(client.get("/api/document-studio/templates").json()) == 8
        fixtures = client.get("/api/document-studio/trips").json()
        assert sorted(t["duration_days"] for t in fixtures) == [5, 10, 15]
        payload = make_trip().model_dump(mode="json")
        payload["days"][0]["internal_notes"] = "Notatka wyłącznie dla pilota"
        payload["days"][0]["stops"] = [Stop(name="Testowa atrakcja").model_dump(mode="json")]
        response = client.post("/api/document-studio/trips", json=payload)
        assert response.status_code == 201, response.text
        saved = response.json()
        trip_id = saved["trip_id"]
        assert len(saved["days"]) == 15
        saved["title"] = "Nowy tytuł"
        updated = client.put(f"/api/document-studio/trips/{trip_id}", json=saved)
        assert updated.status_code == 200
        assert updated.json()["revision"] == 2
        assert client.put(f"/api/document-studio/trips/{trip_id}", json=saved).status_code == 409
        campaign = client.post("/api/document-studio/campaigns", json={"title":"Wiele wycieczek", "items":[{"trip_id":t} for t in (trip_id,"demo-iceland","demo-canada")]})
        assert campaign.status_code == 201
        campaign_id = campaign.json()["campaign_id"]
        assert len(campaign.json()["items"]) == 3
        draft_ids = []
        for template, source_type, source_id, variant in [
            ("offer.private","trip",trip_id,"standard"),
            ("pilot.basic","trip",trip_id,"standard"),
            ("marketing.collection","campaign",campaign_id,"theme_collection"),
        ]:
            draft = client.post("/api/document-studio/drafts",json={"template_id":template,"source_type":source_type,"source_id":source_id,"layout_variant":variant,"editorial_notes":"Uwagi robocze"})
            assert draft.status_code == 201, draft.text
            data = draft.json()
            draft_ids.append(data["document_id"])
            snapshots = [data["trip_snapshot"]] if data["trip_snapshot"] else data["campaign_trip_snapshots"]
            assert snapshots[0]["days"][0]["internal_notes"] == ("Notatka wyłącznie dla pilota" if template == "pilot.basic" else "")
            assert data["template_version"] == "0.4.0"
        changed = updated.json()
        changed["title"] = "Późniejsza edycja"
        assert client.put(f"/api/document-studio/trips/{trip_id}",json=changed).status_code == 200
        # The original planner still owns /api/trips and its SQLite jobs.
        assert client.get(f"/api/trips/{trip_id}").status_code == 404
        planner = client.post("/api/trips", json={"text":"Zaplanuj 2 dni we Wrocławiu"})
        assert planner.status_code == 202
        planner_id = planner.json()["trip_id"]
        assert client.get(f"/api/document-studio/trips/{planner_id}").status_code == 404
    with client_for(tmp_path) as restarted:
        assert restarted.get(f"/api/document-studio/trips/{trip_id}").json()["title"] == "Późniejsza edycja"
        assert len(restarted.get(f"/api/document-studio/campaigns/{campaign_id}").json()["items"]) == 3
        draft = restarted.get(f"/api/document-studio/drafts/{draft_ids[0]}").json()
        assert draft["trip_snapshot"]["title"] == "Nowy tytuł"
        assert draft["trip_snapshot"]["revision"] == 2
        assert draft["editorial_notes"] == "Uwagi robocze"
        assert restarted.get(f"/api/trips/{planner_id}").json()["status"] == "queued"
    assert (tmp_path / "documents" / "assets").is_dir()
    assert not list((tmp_path / "documents").rglob("*.sqlite3"))


def test_api_rejects_invalid_data_and_sources(tmp_path):
    with client_for(tmp_path) as client:
        assert client.post("/api/document-studio/trips",json={"title":""}).status_code == 422
        assert client.post("/api/document-studio/trips",json={"trip_id":"../outside","title":"X"}).status_code == 422
        assert client.get("/api/document-studio/trips/missing").status_code == 404
        assert client.get("/api/document-studio/trips/bad.id").status_code == 422
        assert client.post("/api/document-studio/campaigns",json={"title":"X","items":[{"trip_id":"missing"}]}).status_code == 404
        payload = {"template_id":"bad","source_type":"trip","source_id":"demo-iceland"}
        assert client.post("/api/document-studio/drafts",json=payload).status_code == 422
        payload["template_id"] = "marketing.collection"
        assert client.post("/api/document-studio/drafts",json=payload).status_code == 422
        payload.update(template_id="pilot.basic",source_id="missing")
        assert client.post("/api/document-studio/drafts",json=payload).status_code == 404
        payload.update(source_id="demo-iceland",layout_variant="invented")
        assert client.post("/api/document-studio/drafts",json=payload).status_code == 422


@pytest.mark.parametrize("headers", [
    {"Host":"evil.example"}, {"Origin":"https://evil.example"}, {"Origin":"null"},
    {"X-Forwarded-For":"127.0.0.1"}, {"Forwarded":"for=127.0.0.1"}, {"Sec-Fetch-Site":"cross-site"},
])
def test_local_access_rejects_foreign_origins_and_proxies(tmp_path, headers):
    with client_for(tmp_path) as client:
        for path in ("/documents/demo", "/documents/assets/studio.js", "/api/document-studio/trips", "/api/document-studio/drafts"):
            assert client.get(path,headers=headers).status_code == 403


def test_remote_peer_cannot_open_studio(tmp_path):
    app = create_app(tmp_path / "db.sqlite3", document_data_path=tmp_path / "documents")
    with TestClient(app, base_url="http://localhost", client=("203.0.113.7",1234)) as client:
        assert client.get("/documents/demo").status_code == 403


def test_explicit_docker_access_still_rejects_proxy(tmp_path, monkeypatch):
    monkeypatch.setenv("DOCUMENT_STUDIO_DOCKER_LOCAL","1")
    app = create_app(tmp_path / "db.sqlite3", document_data_path=tmp_path / "documents")
    with TestClient(app, base_url="http://localhost:8000", client=("172.18.0.1",1234)) as client:
        assert client.get("/documents/demo").status_code == 200
        assert client.get("/documents/demo",headers={"X-Forwarded-For":"203.0.113.7"}).status_code == 403


def test_corrupt_file_returns_controlled_error(tmp_path):
    repository = JsonRepository(tmp_path / "documents")
    repository.initialize()
    (repository.root / "trips" / "demo-iceland.json").write_text('{}',encoding="utf-8")
    with client_for(tmp_path) as client:
        response = client.get("/api/document-studio/trips/demo-iceland")
        assert response.status_code == 503
        assert str(tmp_path) not in response.text
