import hashlib
import hmac
import json
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from fastapi.testclient import TestClient

from app.db import Database
from app.main import create_app
from app.messaging import WahaMessagingProvider
from app.waha import WahaSettings, route_intent
from app.worker import process_ack, process_next

KEY = "test-secret"
SENDER = "48123456789@c.us"
SETTINGS = WahaSettings(KEY, frozenset({SENDER}))


def event(**changes):
    payload = {
        "id": "false_48123456789@c.us_ABC", "from": SENDER,
        "fromMe": False, "hasMedia": False, "body": "Zaplanuj 2 dni w Karpaczu",
        "_data": {"type": "chat"},
    }
    payload.update(changes)
    return {"id": "evt_1", "event": "message", "session": "default", "payload": payload}


def signed(client, value, *, key=KEY):
    raw = json.dumps(value, ensure_ascii=False).encode()
    return client.post("/api/webhooks/waha", content=raw, headers={
        "Content-Type": "application/json", "X-Webhook-Hmac-Algorithm": "sha512",
        "X-Webhook-Hmac": hmac.new(key.encode(), raw, hashlib.sha512).hexdigest(),
    })


@pytest.fixture
def gateway(tmp_path):
    database = Database(tmp_path / "test.sqlite3")
    with TestClient(create_app(database.path, waha_settings=SETTINGS)) as client:
        yield client, database


class RecordingProvider:
    def __init__(self):
        self.messages = []

    def send_text(self, **message):
        self.messages.append(message)


def test_webhook_job_and_ack(gateway):
    client, database = gateway
    response = signed(client, event())
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    trip_id = response.json()["trip_id"]
    assert database.get_trip(trip_id)["status"] == "queued"
    assert process_next(database)
    provider = RecordingProvider()
    assert process_ack(database, provider)
    assert len(provider.messages) == 1
    assert provider.messages[0]["chat_id"] == SENDER
    assert trip_id in provider.messages[0]["text"]
    assert "MOCK" in provider.messages[0]["text"]
    assert process_ack(database, provider) is False


def test_duplicate_persists_across_restart(gateway):
    client, database = gateway
    first = signed(client, event()).json()
    repeated = event()
    repeated["id"] = "different-webhook-event-id"
    with TestClient(create_app(database.path, waha_settings=SETTINGS)) as restarted:
        second = signed(restarted, repeated).json()
    assert second == {"status": "duplicate", "trip_id": first["trip_id"]}
    assert process_next(database)
    assert process_next(database) is False
    provider = RecordingProvider()
    process_ack(database, provider)
    signed(client, repeated)
    assert process_ack(database, provider) is False


def test_concurrent_duplicate_is_atomic(gateway):
    _, database = gateway
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: database.create_waha_trip(
            "default", "same-id", SENDER, "Plan a trip"), range(8)))
    assert sum(created for _, created in results) == 1
    assert len({trip_id for trip_id, _ in results}) == 1


@pytest.mark.parametrize("headers", [
    {}, {"X-Webhook-Hmac": "bad", "X-Webhook-Hmac-Algorithm": "sha512"},
    {"X-Webhook-Hmac": "0" * 128, "X-Webhook-Hmac-Algorithm": "sha256"},
])
def test_unauthorized_headers(gateway, headers):
    client, database = gateway
    assert client.post("/api/webhooks/waha", json=event(), headers=headers).status_code == 401
    assert database.claim_next() is None


def test_tampered_body_and_wrong_secret(gateway):
    client, database = gateway
    assert signed(client, event(), key="wrong").status_code == 401
    raw = json.dumps(event()).encode()
    signature = hmac.new(KEY.encode(), raw, hashlib.sha512).hexdigest()
    assert client.post("/api/webhooks/waha", content=raw + b" ", headers={
        "X-Webhook-Hmac": signature, "X-Webhook-Hmac-Algorithm": "sha512"
    }).status_code == 401
    assert database.claim_next() is None


def test_official_hmac_vector():
    # Copied protocol test vector from WAHA's official events documentation.
    raw = b'{"event":"message","session":"default","engine":"WEBJS"}'
    assert hmac.new(b"my-secret-key", raw, hashlib.sha512).hexdigest() == (
        "208f8a55dde9e05519e898b10b89bf0d0b3b0fdf11fdbf09b6b90476301b98d8097"
        "c462b2b17a6ce93b6b47a136cf2e78a33a63f6752c2c1631777076153fa89"
    )


@pytest.mark.parametrize("changes", [
    {"from": "48999999999@c.us"}, {"from": "123@g.us"},
    {"from": "status@broadcast"}, {"from": "123@newsletter"},
    {"fromMe": True}, {"fromMe": "false"}, {"fromMe": None},
    {"hasMedia": True}, {"hasMedia": None}, {"participant": "123@c.us"},
    {"body": "hello"}, {"body": ""}, {"body": 123}, {"body": "x" * 10001},
    {"id": ""}, {"id": None}, {"_data": {"type": "location"}},
    {"_data": {"type": "vcard"}}, {"type": "image"},
])
def test_ignored_messages(gateway, changes):
    client, database = gateway
    assert signed(client, event(**changes)).json()["status"] == "ignored"
    assert database.claim_next() is None
    assert database.claim_ack() is None


@pytest.mark.parametrize("change", [
    {"event": "message.any"}, {"event": "session.status"}, {"session": "other"},
    {"payload": None}, {"me": {"id": SENDER}},
])
def test_ignored_events(gateway, change):
    client, database = gateway
    value = event()
    value.update(change)
    assert signed(client, value).json()["status"] == "ignored"
    assert database.claim_next() is None


def test_deny_all_and_disabled(tmp_path):
    for settings, expected in [
        (WahaSettings(KEY, frozenset()), 200), (WahaSettings("", frozenset({SENDER})), 503)
    ]:
        with TestClient(create_app(tmp_path / "db.sqlite3", waha_settings=settings)) as client:
            response = signed(client, event())
            assert response.status_code == expected
            if expected == 200:
                assert response.json()["status"] == "ignored"


@pytest.mark.parametrize("text,expected", [
    ("trip.create Karpacz", "trip.create"), ("Zaplanuj wycieczkę w góry", "trip.create"),
    ("Plan a 2 day trip", "trip.create"), ("hello", "unsupported"),
    ("trip.create", "unsupported"), ("cancel my trip", "unsupported"),
    ("Zaplanuj spotkanie", "unsupported"),
])
def test_intent_router(text, expected):
    assert route_intent(text) == expected


def test_provider_contract():
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(201, json={"id": "sent-id"})

    provider = WahaMessagingProvider("http://waha:3000", "api-key", httpx.MockTransport(handle))
    provider.send_text(session="default", chat_id=SENDER, text="ack")
    assert str(requests[0].url) == "http://waha:3000/api/sendText"
    assert requests[0].headers["X-Api-Key"] == "api-key"
    assert json.loads(requests[0].content) == {"session": "default", "chatId": SENDER, "text": "ack"}


def test_offline_waha_preserves_job_and_retries_ack(gateway):
    client, database = gateway
    trip_id = signed(client, event()).json()["trip_id"]

    def offline(request):
        raise httpx.ConnectError("WAHA offline", request=request)

    provider = WahaMessagingProvider("http://waha:3000", "key", httpx.MockTransport(offline))
    assert process_ack(database, provider)
    assert database.get_trip(trip_id)["status"] == "queued"
    assert database.claim_ack() is None  # Backoff prevents a hot retry loop.
    response = client.post("/api/trips", json={"text": "Independent API trip"})
    assert response.status_code == 202
    assert client.get("/health").status_code == 200
    assert process_next(database)
    assert process_next(database)
    assert database.get_trip(trip_id)["status"] == "completed"
    with database.connect() as connection:
        connection.execute("UPDATE waha_messages SET retry_after = 0")
    working = RecordingProvider()
    assert process_ack(database, working)
    assert len(working.messages) == 1
    assert process_ack(database, working) is False


def test_interrupted_ack_recovers(gateway):
    client, database = gateway
    signed(client, event())
    assert database.claim_ack() is not None
    assert database.claim_ack() is None
    database.recover_interrupted()
    assert process_ack(database, RecordingProvider())
