"""Offline cloud parity: real routers/models/validation and injected SDK boundaries."""
import copy
import io
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from google.api_core.exceptions import NotFound, PreconditionFailed, ServiceUnavailable
from PIL import Image

from app.cloud_access import CloudAccess, IAPVerifier
from app.cloud_jobs import CloudJobs, CloudTaskDispatcher, principal
from app.cloud_runtime import CloudComponents, DemoSettings
from app.document_studio.assets import AssetStore
from app.document_studio.cloud_storage import GCSRepository, GCSAssetBytes
from app.document_studio.models import Trip, TripDay
from app.document_studio.repository import ConflictError, StorageError
from app.main import create_app

ORIGIN = "https://tripse-ai-dev-example.run.app"
TASK_ACCOUNT = "tripse-ai-dev-tasks@tripse-test-123.iam.gserviceaccount.com"


class FakeBucket:
    def __init__(self):
        self.objects, self.lock, self.counter = {}, threading.RLock(), 0
        self.fail = False

    def blob(self, name):
        bucket = self
        class Blob:
            generation = None
            def download_as_bytes(self, **kwargs):
                if bucket.fail:
                    raise ServiceUnavailable("private storage error")
                with bucket.lock:
                    if name not in bucket.objects:
                        raise NotFound("absent")
                    data, self.generation = bucket.objects[name]
                    return data
            def upload_from_string(self, data, *, if_generation_match, **kwargs):
                if bucket.fail:
                    raise ServiceUnavailable("private storage error")
                with bucket.lock:
                    previous = bucket.objects.get(name, (None, 0))[1]
                    if previous != if_generation_match:
                        raise PreconditionFailed("generation changed")
                    bucket.counter += 1
                    self.generation = bucket.counter
                    bucket.objects[name] = (data.encode() if isinstance(data, str) else data, self.generation)
            def reload(self, **kwargs):
                self.download_as_bytes()
            def delete(self, *, if_generation_match, **kwargs):
                with bucket.lock:
                    if bucket.objects[name][1] != if_generation_match:
                        raise PreconditionFailed("changed")
                    del bucket.objects[name]
        return Blob()

    def list_blobs(self, *, prefix, **kwargs):
        if self.fail:
            raise ServiceUnavailable("private storage error")
        return [SimpleNamespace(name=name) for name in self.objects if name.startswith(prefix)]


class MemoryJobStore:
    def __init__(self):
        self.data, self.lock = {}, threading.RLock()
    def get(self, key):
        with self.lock:
            return copy.deepcopy(self.data.get(key))
    def mutate(self, key, operation):
        with self.lock:
            value, result = operation(self.get(key))
            if value is not None:
                self.data[key] = copy.deepcopy(value)
            return result
    def find(self, field, value):
        return copy.deepcopy([j for j in self.data.values() if j.get(field) == value])


class Dispatcher:
    def __init__(self):
        self.ids, self.fail = [], False
    def enqueue(self, trip_id, **kwargs):
        if self.fail:
            raise ServiceUnavailable("queue failed")
        self.ids.append(trip_id)


@pytest.fixture
def cloud_demo(monkeypatch):
    values = dict(CLOUD_FEATURE_MODE="cloud_demo", APP_ENV="dev", GCP_PROJECT_ID="tripse-test-123",
        GCP_PROJECT_NUMBER="123456789", PUBLIC_BASE_URL=ORIGIN,
        GCP_DOCUMENT_BUCKET="tripse-test-123-tripse-ai-dev-documents",
        GCP_FIRESTORE_DATABASE="tripse-ai-dev",
        GCP_TASK_QUEUE="projects/tripse-test-123/locations/europe-central2/queues/tripse-ai-dev",
        GCP_TASK_ACCOUNT=TASK_ACCOUNT, IAP_OAUTH_CLIENT_ID="123-example.apps.googleusercontent.com",
        DEMO_EDITORS="editor@example.com|other@example.com", DEMO_READERS="reader@example.com")
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("K_SERVICE", raising=False)
    monkeypatch.delenv("GOOGLE_MAPS_BROWSER_KEY", raising=False)
    bucket, store, dispatcher = FakeBucket(), MemoryJobStore(), Dispatcher()
    def verify(assertion):
        if assertion not in {"editor", "other", "reader", "stranger", "task"}:
            raise ValueError("bad signature")
        return {"email": TASK_ACCOUNT if assertion == "task" else f"{assertion}@example.com", "sub": assertion}
    def components():
        repo = GCSRepository(bucket)
        return CloudComponents(repo, AssetStore(repo, GCSAssetBytes(bucket)), CloudJobs(store, dispatcher),
            CloudAccess(ORIGIN, frozenset({"reader@example.com"}),
                        frozenset({"editor@example.com", "other@example.com"}), verify, TASK_ACCOUNT))
    def client(identity="editor"):
        headers = {"Origin": ORIGIN}
        if identity:
            headers["x-goog-iap-jwt-assertion"] = identity
        return TestClient(create_app(cloud_components=components()), base_url=ORIGIN, headers=headers)
    return SimpleNamespace(client=client, bucket=bucket, store=store, dispatcher=dispatcher, components=components)


@pytest.mark.parametrize("path", ["/", "/planner", "/hub", "/documents/demo", "/api/document-studio/trips", "/documents/assets/studio.js",
    "/static/viewer.js", "/api/trips/00000000-0000-0000-0000-000000000000", "/api/demo/scenarios", "/trip/invalid"])
def test_anonymous_and_forged_headers_denied(cloud_demo, path):
    with cloud_demo.client(None) as c:
        assert c.get(path, headers={"x-goog-authenticated-user-email": "accounts.google.com:editor@example.com"}).status_code == 401
        assert c.get(path, headers={"x-goog-iap-jwt-assertion": "forged"}).status_code == 401
        assert c.get("/health").status_code == 200


def test_access_roles_origin_host_and_task_boundary(cloud_demo):
    with cloud_demo.client("reader") as c:
        assert c.get("/documents/demo").status_code == 200
        assert c.post("/api/document-studio/trips", json={}).status_code == 403
    with cloud_demo.client("stranger") as c:
        assert c.get("/hub").status_code == 403
    with cloud_demo.client() as c:
        assert c.post("/api/document-studio/trips", headers={"origin": "https://evil.example"}, json={}).status_code == 403
        del c.headers["origin"]
        assert c.post("/api/trips", json={"text": "test"}).status_code == 403
        assert c.get("/hub", headers={"host": "evil.example"}).status_code == 400
        assert c.get("/hub", headers={"sec-fetch-site": "cross-site"}).status_code == 403
        assert c.post(f"/internal/jobs/{uuid4()}").status_code == 403
    with cloud_demo.client("task") as c:
        assert c.get("/hub").status_code == 403
        assert c.post(f"/internal/jobs/{uuid4()}").status_code == 200


@pytest.mark.parametrize("identity", ["editor", "reader"])
def test_authenticated_home_and_module_navigation(cloud_demo, identity):
    with cloud_demo.client(identity) as client:
        root = client.get("/", follow_redirects=False)
        assert root.status_code == 302 and root.headers["location"] == "/hub"
        assert root.headers["cache-control"] == "private, no-store"
        response = client.get("/")
        assert response.status_code == 200 and len(response.history) == 1
        assert 'id="planner-link" href="/planner"' in response.text
        for path in ("/hub", "/planner", "/demo/chat", "/documents/demo"):
            for _ in range(2):
                page = client.get(path, follow_redirects=False)
                assert page.status_code == 200 and "location" not in page.headers
                assert page.headers["cache-control"] == "private, no-store"
        for path in ("/planner", "/demo/chat"):
            page = client.get(path)
            assert 'data-hub-navigation="enabled"' in page.text
            assert 'href="/hub"' in page.text
            assert "script-src 'self'" in page.headers["content-security-policy"]
        assert client.post("/api/trips", json={"text": "test"}).status_code == (403 if identity == "reader" else 202)
    with cloud_demo.client("stranger") as client:
        for path in ("/", "/hub", "/planner"):
            assert client.get(path, follow_redirects=False).status_code == 403


def test_shared_studio_restart_upload_snapshots_conflict(cloud_demo):
    trip = Trip(title="15 day editor trip", duration_days=15,
                days=[TripDay(day_number=i, title=f"Day {i}", internal_notes="PRIVATE_OPS") for i in range(1, 16)])
    with cloud_demo.client() as c:
        for path in ("/hub", "/documents/demo", "/documents/assets/trip-editor.js", "/demo/chat", "/planner"):
            assert c.get(path).status_code == 200
        assert c.post("/api/document-studio/trips", json=trip.model_dump(mode="json")).status_code == 201
        edited = trip.model_dump(mode="json") | {"title": "Saved cloud trip"}
        assert c.put(f"/api/document-studio/trips/{trip.trip_id}", json=edited).status_code == 200
        assert c.put(f"/api/document-studio/trips/{trip.trip_id}", json=edited).status_code == 409
        drafts = []
        for template in ("offer.private", "pilot.basic"):
            r = c.post("/api/document-studio/drafts", json={"template_id": template, "source_type": "trip", "source_id": trip.trip_id})
            assert r.status_code == 201, r.text
            draft = r.json()
            assert len(draft["trip_snapshot"]["days"]) == 15
            preview = c.get(f"/api/document-studio/drafts/{draft['document_id']}/preview")
            assert preview.status_code == 200
            if template == "offer.private":
                assert "PRIVATE_OPS" not in preview.text
                assert all(not d["internal_notes"] for d in draft["trip_snapshot"]["days"])
            drafts.append(draft)
        photo = io.BytesIO()
        Image.new("RGB", (20, 12), "red").save(photo, "PNG")
        r = c.post("/api/document-studio/assets?filename=photo.png&rights_confirmed=true", content=photo.getvalue(), headers={"content-type": "image/png"})
        assert r.status_code == 201, r.text
        asset_id = r.json()["asset_id"]
        image = c.get(f"/api/document-studio/assets/{asset_id}/content")
        assert image.content.startswith(b"\x89PNG")
        assert image.headers["cache-control"] == "private, no-store"
        campaign = {"title": "Cloud campaign", "items": [{"trip_id": trip.trip_id, "image_asset_id": asset_id}]}
        r = c.post("/api/document-studio/campaigns", json=campaign)
        assert r.status_code == 201, r.text
        for output in ("a4", "social"):
            assert c.get(f"/api/document-studio/campaigns/{r.json()['campaign_id']}/preview?output_format={output}").status_code == 200
    # Reconstruct the complete app/repositories, retaining only external stores.
    with cloud_demo.client() as reopened:
        saved = reopened.get(f"/api/document-studio/trips/{trip.trip_id}").json()
        assert saved["title"] == "Saved cloud trip" and saved["revision"] == 2
        assert reopened.get(f"/api/document-studio/assets/{asset_id}/content").content == image.content
        assert len(reopened.get("/api/document-studio/drafts").json()) == 2


def test_gcs_fixture_overlay_corruption_and_unavailable(cloud_demo):
    repo = cloud_demo.components().repository
    original = repo.get("trips", "demo-iceland")
    saved = repo.save("trips", original)
    assert saved.revision == original.revision + 1
    assert repo.get("trips", "demo-iceland").revision == saved.revision
    cloud_demo.bucket.objects["documents/trips/demo-iceland.json"] = (b"broken", 99)
    with pytest.raises(StorageError):
        repo.get("trips", "demo-iceland")
    cloud_demo.bucket.fail = True
    with cloud_demo.client() as c:
        r = c.get("/api/document-studio/trips")
        assert r.status_code == 503 and "private storage error" not in r.text


def test_cloud_composition_never_initializes_local_storage(cloud_demo, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Cloud attempted to initialize local persistent storage")
    monkeypatch.setattr("app.db.Database.__init__", forbidden)
    monkeypatch.setattr("app.document_studio.repository.JsonRepository.initialize", forbidden)
    with cloud_demo.client() as c:
        assert c.get("/hub").status_code == 200
        assert c.post("/api/webhooks/waha", json={}).status_code == 404


def test_stable_outbox_ids_when_earlier_job_finishes_later(cloud_demo):
    from app.demo_data import SCENARIOS
    conversation = str(uuid4())
    with cloud_demo.client() as c:
        ids = [c.post("/api/demo/messages", json={"conversation": conversation, "message_id": str(uuid4()),
                    "text": SCENARIOS["ojcow"]["text"]}).json()["trip_id"] for _ in range(2)]
        before = c.get(f"/api/demo/conversations/{conversation}").json()["messages"]
    with cloud_demo.client("task") as task:
        task.post(f"/internal/jobs/{ids[0]}")
    with cloud_demo.client() as c:
        after = c.get(f"/api/demo/conversations/{conversation}").json()["messages"]
    assert {m["id"]: m["text"] for m in before}.items() <= {m["id"]: m["text"] for m in after}.items()
    assert len({m["id"] for m in after}) == 3


def test_two_gcs_writers_race_at_generation_precondition(cloud_demo):
    repo = cloud_demo.components().repository
    trip = repo.save("trips", Trip(title="Concurrent"), create=True)
    barrier, read = threading.Barrier(2), repo._read
    def together(*args):
        result = read(*args)
        barrier.wait(timeout=5)
        return result
    repo._read = together
    def save():
        try:
            return repo.save("trips", trip).revision
        except ConflictError:
            return "conflict"
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: save(), range(2)))
    assert sorted(map(str, results)) == ["2", "conflict"]


def test_cloud_jobs_mock_status_dedup_isolation_restart_tokens(cloud_demo, monkeypatch):
    from app.demo_data import SCENARIOS
    monkeypatch.setattr("app.planning.configured_generator", lambda: pytest.fail("paid provider construction"))
    conversation, event = str(uuid4()), str(uuid4())
    message = {"conversation": conversation, "message_id": event, "text": SCENARIOS["mountains"]["text"]}
    with cloud_demo.client() as c:
        first = c.post("/api/demo/messages", json=message)
        assert first.status_code == 202
        trip_id = first.json()["trip_id"]
        assert c.post("/api/demo/messages", json=message).json()["status"] == "duplicate"
        assert c.get(f"/api/trips/{trip_id}").json()["status"] == "queued"
    with cloud_demo.client("task") as task:
        assert task.post(f"/internal/jobs/{trip_id}").status_code == 200
        assert task.post(f"/internal/jobs/{trip_id}").status_code == 200
    with cloud_demo.client() as c:
        job = c.get(f"/api/trips/{trip_id}").json()
        assert job["status"] == "completed" and job["result"]["is_mock"]
        url = job["result"]["viewer_url"].removeprefix(ORIGIN)
        token = url.split("/")[-1]
        assert c.get(url).status_code == 200
        data = c.get(f"/api/viewer/{token}").json()
        assert "request_text" not in data["plan"] and data["maps"]["browser_key"] == ""
        assert c.get("/trip/invalid").status_code == 404
        messages = c.get(f"/api/demo/conversations/{conversation}").json()
        assert len(messages["messages"]) == 2 and len(messages["jobs"]) == 1
        assert c.get(f"/api/demo/conversations/{uuid4()}").json() == {"messages": [], "jobs": []}
    with cloud_demo.client("other") as other:
        assert other.get(f"/api/trips/{trip_id}").status_code == 404
        assert other.get(f"/api/viewer/{token}").status_code == 404
        assert other.get(f"/api/demo/conversations/{conversation}").json() == {"messages": [], "jobs": []}
        assert other.post("/api/demo/messages", json=message).json()["trip_id"] != trip_id
    cloud_demo.store.data[trip_id]["viewer_expires_at"] = 0
    with cloud_demo.client() as c:
        assert c.get(f"/api/viewer/{token}").status_code == 404


def test_queue_failure_idempotent_retry_and_planner_contract(cloud_demo):
    from app.demo_data import SCENARIOS
    text = SCENARIOS["ojcow"]["text"]
    headers = {"Idempotency-Key": str(uuid4())}
    cloud_demo.dispatcher.fail = True
    with cloud_demo.client() as c:
        assert c.post("/api/trips", json={"text": text}, headers=headers).status_code == 503
        assert len(cloud_demo.store.data) == 1
        cloud_demo.dispatcher.fail = False
        accepted = c.post("/api/trips", json={"text": text}, headers=headers)
        assert accepted.status_code == 202
        assert len(cloud_demo.store.data) == 1
        assert accepted.headers["location"].endswith(accepted.json()["trip_id"])
        assert c.post("/api/trips", json={"text": "different"}, headers=headers).status_code == 409
        assert c.post("/api/trips", json={"text": text}).status_code == 202
        assert c.post("/api/trips", json={"text": text}, headers={"Idempotency-Key": "invalid"}).status_code == 422


@pytest.mark.parametrize("case", ["success", "failure", "expired", "delivery", "missing", "routing", "limit"])
def test_job_cases_and_bounded_lease_retry(cloud_demo, case):
    from app.demo_data import SCENARIOS
    with cloud_demo.client() as c:
        r = c.post("/api/demo/messages", json={"conversation": str(uuid4()), "message_id": str(uuid4()),
            "text": SCENARIOS["coast"]["text"], "case": case})
        trip_id = r.json()["trip_id"]
    with cloud_demo.client("task") as c:
        first = c.post(f"/internal/jobs/{trip_id}")
        assert first.status_code == (503 if case == "delivery" else 200)
        if case == "delivery":
            assert c.post(f"/internal/jobs/{trip_id}").status_code == 200
    job = cloud_demo.store.data[trip_id]
    assert job["status"] == ("failed" if case == "failure" else "completed")
    if case == "expired":
        assert job["viewer_expires_at"] == 0


def test_active_lease_exhaustion_and_operator_recovery(cloud_demo):
    from app.demo_data import SCENARIOS
    with cloud_demo.client() as c:
        trip_id = c.post("/api/trips", headers={"Idempotency-Key": str(uuid4())}, json={"text": SCENARIOS["ojcow"]["text"]}).json()["trip_id"]
    job = cloud_demo.store.data[trip_id]
    job.update(status="running", lease_until=time.time() + 100, attempts=1)
    with cloud_demo.client("task") as c:
        assert c.post(f"/internal/jobs/{trip_id}").status_code == 503
        job.update(lease_until=0, attempts=3)
        assert c.post(f"/internal/jobs/{trip_id}").status_code == 200
    assert cloud_demo.store.data[trip_id]["status"] == "failed"


def test_crash_retries_are_bounded_and_stale_completion_is_fenced(cloud_demo, monkeypatch):
    from app.demo_data import SCENARIOS
    from app.worker import generate_job_result
    with cloud_demo.client() as c:
        trip_id = c.post("/api/trips", headers={"Idempotency-Key": str(uuid4())},
            json={"text": SCENARIOS["ojcow"]["text"]}).json()["trip_id"]
    def interrupted(*args):
        raise RuntimeError("PRIVATE_PROVIDER_ERROR")
    monkeypatch.setattr("app.worker.generate_job_result", interrupted)
    with cloud_demo.client("task") as c:
        for _ in range(3):
            r = c.post(f"/internal/jobs/{trip_id}")
            assert r.status_code == 503 and "PRIVATE_PROVIDER_ERROR" not in r.text
            cloud_demo.store.data[trip_id]["lease_until"] = 0
        assert c.post(f"/internal/jobs/{trip_id}").status_code == 200
    assert cloud_demo.store.data[trip_id]["status"] == "failed"
    with cloud_demo.client() as c:
        new_id = c.post("/api/trips", headers={"Idempotency-Key": str(uuid4())},
            json={"text": SCENARIOS["ojcow"]["text"]}).json()["trip_id"]
    def stale(job, case):
        cloud_demo.store.data[new_id].update(lease_id="replacement-processor", status="running")
        return generate_job_result(job, case)
    monkeypatch.setattr("app.worker.generate_job_result", stale)
    with cloud_demo.client("task") as c:
        assert c.post(f"/internal/jobs/{new_id}").status_code == 200
    current = cloud_demo.store.data[new_id]
    assert current["status"] == "running" and current["result_json"] is None


def test_task_dispatch_uses_iap_oidc_and_named_dedup():
    calls = []
    from google.api_core.exceptions import AlreadyExists
    def create_task(**kwargs):
        calls.append(kwargs)
        if len(calls) > 1:
            raise AlreadyExists("duplicate")
    dispatcher = CloudTaskDispatcher(SimpleNamespace(create_task=create_task), "projects/p/locations/r/queues/q", ORIGIN, TASK_ACCOUNT, "oauth-client")
    dispatcher.enqueue("job")
    dispatcher.enqueue("job")
    task = calls[0]["request"]["task"]
    assert task["http_request"]["oidc_token"] == {"service_account_email": TASK_ACCOUNT, "audience": "oauth-client"}
    assert task["http_request"]["url"] == ORIGIN + "/internal/jobs/job"
    assert calls[0]["request"]["task"]["name"] == calls[1]["request"]["task"]["name"]


@pytest.mark.parametrize("change", [{"aud": "wrong"}, {"iss": "evil"}, {"exp": 1}, {"sub": None}, {"iat": time.time() + 10000}])
def test_real_iap_signature_claim_validation(change):
    private = ec.generate_private_key(ec.SECP256R1())
    verifier = IAPVerifier("expected-audience")
    verifier.keys = SimpleNamespace(get_signing_key_from_jwt=lambda _: SimpleNamespace(key=private.public_key()))
    claims = dict(aud="expected-audience", iss="https://cloud.google.com/iap", sub="subject", email="editor@example.com", exp=time.time() + 60, iat=time.time())
    valid = jwt.encode(claims, private, algorithm="ES256", headers={"kid": "test"})
    assert verifier(valid)["sub"] == "subject"
    invalid = jwt.encode(claims | change, private, algorithm="ES256", headers={"kid": "test"})
    with pytest.raises(jwt.InvalidTokenError):
        verifier(invalid)
    forged = jwt.encode(claims, ec.generate_private_key(ec.SECP256R1()), algorithm="ES256")
    with pytest.raises(jwt.InvalidSignatureError):
        verifier(forged)


@pytest.mark.parametrize("key,value", [("GCP_FIRESTORE_DATABASE", "tripse-ai-prod"), ("GCP_DOCUMENT_BUCKET", "prod"),
    ("GCP_TASK_QUEUE", "projects/p/locations/r/queues/prod"), ("GCP_TASK_ACCOUNT", "wrong@example.com"),
    ("PUBLIC_BASE_URL", "http://localhost"), ("DEMO_EDITORS", ""), ("IAP_OAUTH_CLIENT_ID", ""),
    ("FIRESTORE_EMULATOR_HOST", "localhost:8080"), ("PLANNING_MODE", "live"), ("OPENAI_API_KEY", "fake")])
def test_cloud_demo_configuration_fails_closed(cloud_demo, monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    with pytest.raises(ValueError):
        create_app(cloud_components=cloud_demo.components())
