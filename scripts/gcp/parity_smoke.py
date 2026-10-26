"""Operator-run DEV cloud_demo acceptance. Never deploys or calls paid providers.

Read-only by default. --allow-writes creates clearly named synthetic documents,
an image and mock jobs in DEV; it deliberately does not delete persisted data.
Token comes from CLOUD_DEMO_SMOKE_TOKEN in the shell, not argv or dotenv.
"""
import argparse
import io
import json
import os
from pathlib import Path
import time
from uuid import uuid4
from urllib.error import HTTPError
from urllib.request import Request, build_opener, HTTPRedirectHandler

from scripts.gcp.deployment_contract import ROOT, load_pair


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Acceptance:
    def __init__(self, origin, token):
        self.origin, self.token = origin, token
        self.opener = build_opener(NoRedirect())

    def call(self, path, *, method="GET", payload=None, raw=None, headers=None, authenticated=True, expected=200):
        request_headers = {"Origin": self.origin} | (headers or {})
        if authenticated:
            request_headers["Authorization"] = "Bearer " + self.token
        if payload is not None:
            raw = json.dumps(payload).encode()
            request_headers["Content-Type"] = "application/json"
        try:
            with self.opener.open(Request(self.origin + path, data=raw, method=method, headers=request_headers), timeout=30) as response:
                status, data = response.status, response.read()
        except HTTPError as error:
            status, data = error.code, error.read()
        expected = {expected} if isinstance(expected, int) else expected
        if status not in expected:
            raise ValueError(f"DEV acceptance failed: {method} {path} status {status}")
        return json.loads(data) if data.startswith((b"{", b"[")) else data

    def read_only(self, environment):
        health = self.call("/health")
        if any(health.get(key) != value for key, value in {
            "feature_mode": "cloud_demo", "generation_mode": "mock", "environment": environment,
            "storage": "gcs_firestore",
        }.items()):
            raise ValueError("Expected authenticated mock cloud_demo runtime")
        for path in ("/hub", "/documents/demo", "/api/document-studio/trips", "/api/document-studio/templates", "/api/demo/scenarios"):
            self.call(path)
            self.call(path, authenticated=False, expected={302, 303, 401, 403})

    def writes(self):
        from PIL import Image
        from app.document_studio.models import Trip, TripDay
        trip = Trip(title=f"CLOUD-PARITY synthetic DEV {uuid4().hex[:8]}", duration_days=15,
                    days=[TripDay(day_number=i, title=f"Synthetic day {i}", internal_notes="PARITY_PRIVATE_OPS") for i in range(1, 16)])
        base = "/api/document-studio"
        saved = self.call(base + "/trips", method="POST", payload=trip.model_dump(mode="json"), expected=201)
        self.call(base + f"/trips/{trip.trip_id}", method="PUT", payload=saved)
        self.call(base + f"/trips/{trip.trip_id}", method="PUT", payload=saved, expected=409)
        if self.call(base + f"/trips/{trip.trip_id}")["revision"] != 2:
            raise ValueError("Revision/read-back mismatch")
        for template in ("offer.private", "pilot.basic"):
            draft = self.call(base + "/drafts", method="POST", payload={"template_id": template, "source_type": "trip", "source_id": trip.trip_id}, expected=201)
            preview = self.call(base + f"/drafts/{draft['document_id']}/preview")
            if template == "offer.private" and b"PARITY_PRIVATE_OPS" in preview:
                raise ValueError("Offer exposed internal data")
        image = io.BytesIO()
        Image.new("RGB", (32, 20), "blue").save(image, "PNG")
        asset = self.call(base + "/assets?filename=synthetic.png&rights_confirmed=true", method="POST", raw=image.getvalue(), headers={"Content-Type": "image/png"}, expected=201)
        self.call(base + f"/assets/{asset['asset_id']}/content")
        campaign = self.call(base + "/campaigns", method="POST", payload={"title": trip.title, "items": [{"trip_id": trip.trip_id, "image_asset_id": asset["asset_id"]}]}, expected=201)
        for output in ("a4", "social"):
            self.call(base + f"/campaigns/{campaign['campaign_id']}/preview?output_format={output}")
        scenarios = self.call("/api/demo/scenarios")["scenarios"]
        accepted = self.call("/api/trips", method="POST", payload={"text": scenarios[0]["text"]}, headers={"Idempotency-Key": str(uuid4())}, expected=202)
        self.wait(accepted["trip_id"])
        conversation = str(uuid4())
        message = {"conversation": conversation, "message_id": str(uuid4()), "text": scenarios[0]["text"]}
        accepted = self.call("/api/demo/messages", method="POST", payload=message, expected=202)
        duplicate = self.call("/api/demo/messages", method="POST", payload=message, expected=202)
        if duplicate["trip_id"] != accepted["trip_id"] or duplicate["status"] != "duplicate":
            raise ValueError("Simulator deduplication failed")
        self.wait(accepted["trip_id"])
        if len(self.call(f"/api/demo/conversations/{conversation}")["messages"]) != 2:
            raise ValueError("Simulator response missing")
        expired = self.call("/api/demo/messages", method="POST", payload=message | {"message_id": str(uuid4()), "case": "expired"}, expected=202)
        self.wait(expired["trip_id"], expired=True)
        self.call("/api/viewer/invalid", expected=404)
        print(f"DEV synthetic trip for restart/read-back check: {trip.trip_id}")
        return {"trip_id": trip.trip_id, "campaign_id": campaign["campaign_id"], "asset_id": asset["asset_id"]}

    def wait(self, trip_id, *, expired=False):
        for _ in range(60):
            job = self.call(f"/api/trips/{trip_id}")
            if job["status"] == "failed":
                raise ValueError("Mock job failed; inspect DEV logs")
            if job["status"] == "completed":
                if not job["result"].get("is_mock"):
                    raise ValueError("Expected mock result")
                token = job["result"]["viewer_url"].split("/")[-1]
                self.call(f"/api/viewer/{token}", expected=404 if expired else 200)
                self.call(f"/trip/{token}", expected=404 if expired else 200)
                return
            time.sleep(2)
        raise ValueError("Mock job timed out; inspect task IAP/lease/queue configuration")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-dir", type=Path, default=ROOT)
    parser.add_argument("--allow-writes", action="store_true")
    args = parser.parse_args()
    config = load_pair("dev", args.config_dir)
    if config["CLOUD_FEATURE_MODE"] != "cloud_demo":
        parser.error("DEV must explicitly select cloud_demo")
    token = os.getenv("CLOUD_DEMO_SMOKE_TOKEN")
    if not token:
        parser.error("CLOUD_DEMO_SMOKE_TOKEN required in shell")
    acceptance = Acceptance(config["PUBLIC_BASE_URL"], token)
    acceptance.read_only("dev")
    if args.allow_writes:
        acceptance.writes()
    print("DEV parity smoke PASS; browser PDF, runtime restart, cross-user/environment denial and backup restore require operator acceptance")


if __name__ == "__main__":
    main()
