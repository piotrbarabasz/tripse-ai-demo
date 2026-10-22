"""Small, deterministic inbound gateway for the dedicated test session."""
import hashlib
import hmac
import json
import os
import re
from dataclasses import dataclass

from fastapi import APIRouter, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from app.db import Database


@dataclass(frozen=True)
class WahaSettings:
    hmac_key: str
    allowed_senders: frozenset[str]
    session: str = "default"

    @classmethod
    def from_env(cls):
        return cls(
            hmac_key=os.getenv("WAHA_WEBHOOK_HMAC_KEY", ""),
            allowed_senders=frozenset(
                value.strip() for value in os.getenv("WAHA_ALLOWED_SENDERS", "").split(",")
                if value.strip()
            ),
            session=os.getenv("WAHA_SESSION", "default"),
        )


def route_intent(text: str) -> str:
    # Deliberately small command vocabulary; no LLM or conversational state.
    if re.match(r"^trip\.create\s+\S", text, re.IGNORECASE):
        return "trip.create"
    if re.match(r"^(zaplanuj|plan)\b", text, re.IGNORECASE) and re.search(
        r"\b(wycieczk\w*|podróż\w*|trip|dni|dzień|days?|weekend)\b", text, re.IGNORECASE
    ):
        return "trip.create"
    return "unsupported"


def webhook_router(database: Database, settings: WahaSettings) -> APIRouter:
    router = APIRouter()

    @router.post("/api/webhooks/waha")
    async def receive(request: Request):
        if not settings.hmac_key:
            raise HTTPException(status_code=503, detail="WAHA webhook is not configured")
        # Verify exact bytes, not a parsed/re-serialized JSON representation.
        body = await request.body()
        signature = request.headers.get("X-Webhook-Hmac", "")
        expected = hmac.new(settings.hmac_key.encode(), body, hashlib.sha512).hexdigest()
        if (request.headers.get("X-Webhook-Hmac-Algorithm") != "sha512"
                or not re.fullmatch(r"[0-9a-f]{128}", signature)
                or not hmac.compare_digest(signature, expected)):
            raise HTTPException(status_code=401, detail="Invalid webhook authentication")
        try:
            event = json.loads(body)
        except (ValueError, UnicodeDecodeError):
            raise HTTPException(status_code=400, detail="Invalid JSON") from None
        if not isinstance(event, dict):
            raise HTTPException(status_code=400, detail="Expected a JSON object")
        if event.get("event") != "message" or event.get("session") != settings.session:
            return {"status": "ignored"}
        payload = event.get("payload")
        if not isinstance(payload, dict):
            return {"status": "ignored"}
        sender = payload.get("from")
        # Exact allowlist matching; no automatic resolution of phone numbers or LIDs.
        if (not isinstance(sender, str)
                or not re.fullmatch(r"\d+@(c\.us|lid)", sender)
                or sender not in settings.allowed_senders
                or payload.get("fromMe") is not False
                or payload.get("participant")
                or payload.get("hasMedia") is not False):
            return {"status": "ignored"}
        me = event.get("me")
        if isinstance(me, dict) and sender in (me.get("id"), me.get("lid")):
            return {"status": "ignored"}
        # WEBJS includes _data.type. Exclude non-text events even if they have a body.
        raw = payload.get("_data")
        if isinstance(raw, dict) and raw.get("type") not in (None, "chat"):
            return {"status": "ignored"}
        if payload.get("type") not in (None, "chat", "text"):
            return {"status": "ignored"}
        text = payload.get("body")
        message_id = payload.get("id")
        if (not isinstance(text, str) or not 1 <= len(text.strip()) <= 10000
                or not isinstance(message_id, str) or not 1 <= len(message_id) <= 512):
            return {"status": "ignored"}
        text = text.strip()
        if route_intent(text) == "unsupported":
            return {"status": "ignored", "intent": "unsupported"}
        trip_id, created = await run_in_threadpool(
            database.create_waha_trip, settings.session, message_id, sender, text
        )
        return {"status": "accepted" if created else "duplicate", "trip_id": trip_id}

    return router
