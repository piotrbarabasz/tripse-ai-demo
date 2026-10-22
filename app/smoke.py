"""Repeatable deployed API smoke. Live mode spends at most one normal planning job."""
import argparse
import json
import ssl
import time
from urllib.parse import urlsplit

import httpx

SCENARIO = "Zaplanuj 2 dni: Wrocław → Karpacz → Szklarska Poręba → Wrocław. Natura, maksymalnie 3 godziny jazdy dziennie."


def run(client, *, expect_mode, trip_id=None, timeout=240):
    health = client.get("/health")
    health.raise_for_status()
    assert health.json()["generation_mode"] == expect_mode, "Selected mode differs from --expect-mode"
    root = client.get("/")
    assert root.status_code == 200 and 'id="trip-form"' in root.text, "Browser fallback unavailable"
    for path in ("/trip/invalid", "/api/viewer/invalid"):
        assert client.get(path).status_code == 404, "Invalid viewer token was not rejected"
    auth = client.post("/api/webhooks/waha", json={})
    assert auth.status_code in (401, 503), "Unsigned webhook was not rejected"
    for path in ("/api/sessions", "/dashboard", "/config/"):
        assert client.get(path).status_code == 404, "Administration path was exposed"
    assert client.post("/api/sendText", json={}).status_code == 404, "WAHA send endpoint was exposed"
    if trip_id is None:
        created = client.post("/api/trips", json={"text": SCENARIO})
        assert created.status_code == 202, "Trip was not accepted"
        trip_id = created.json()["trip_id"]
    deadline = time.monotonic() + timeout
    while True:
        response = client.get("/api/trips/" + trip_id)
        response.raise_for_status()
        job = response.json()
        assert job["status"] in ("queued", "running", "completed", "failed")
        if job["status"] in ("completed", "failed"):
            break
        assert time.monotonic() < deadline, "Job did not reach a terminal status in time"
        time.sleep(1)
    assert job["status"] == "completed", job.get("error") or "Job failed"
    plan = job["result"]
    assert len(plan["days"]) == 2, "Expected two days"
    assert plan["is_mock"] is (expect_mode == "mock"), "Result mode is incorrect"
    viewer_url = plan["viewer_url"]
    assert urlsplit(viewer_url).scheme == client.base_url.scheme, "Viewer URL scheme differs from deployment"
    assert urlsplit(viewer_url).netloc == urlsplit(str(client.base_url)).netloc, "Viewer URL origin is misconfigured"
    path = urlsplit(viewer_url).path
    page = client.get(path)
    assert page.status_code == 200 and "text/html" in page.headers["content-type"], "Viewer unavailable"
    data = client.get(path.replace("/trip/", "/api/viewer/"))
    assert data.status_code == 200
    assert "request_text" not in data.json()["plan"], "Private request was exposed"
    for day in plan["days"]:
        if expect_mode == "live":
            assert day["routing_status"] == "verified", f"Day {day['number']} route is unverified"
            assert day["distance_meters"] is not None and day["duration_seconds"] is not None
            assert day["encoded_polyline"], "Route geometry missing"
            link = urlsplit(day["google_maps_url"] or "")
            assert link.scheme == "https" and link.netloc == "www.google.com" and link.path == "/maps/dir/"
        else:
            assert day["routing_status"] == "unverified"
            assert day["distance_km"] is None and day["drive_minutes"] is None
    if expect_mode == "live":
        assert plan["verification_status"] == "verified" and not plan["unresolved_places"]
        assert len(plan["places"]) >= 4, "Demo needs at least four matched places"
    return {"api_worker_viewer": "PASS", "trip_id": trip_id, "viewer_url": viewer_url,
            "webhook_authentication": "PASS" if auth.status_code == 401 else "NOT VERIFIED (webhook disabled)",
            "private_admin_paths": "PASS",
            "real_route_calculations": "PASS" if expect_mode == "live" else "NOT VERIFIED (mock mode)",
            "live_browser_map": "NOT VERIFIED (open viewer in a browser)",
            "whatsapp_delivery": "NOT VERIFIED (confirm on the test phone)"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--expect-mode", choices=("live", "mock"), required=True)
    parser.add_argument("--ca-cert", help="Local Caddy root certificate; never disables TLS verification")
    parser.add_argument("--trip-id", help="Check an existing WhatsApp/API job instead of creating a new one")
    args = parser.parse_args()
    verify = ssl.create_default_context(cafile=args.ca_cert) if args.ca_cert else True
    try:
        with httpx.Client(base_url=args.base_url.rstrip("/"), verify=verify, timeout=15, trust_env=False) as client:
            report = run(client, expect_mode=args.expect_mode, trip_id=args.trip_id)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (AssertionError, httpx.HTTPError, ValueError, KeyError, TypeError) as error:
        # Provider errors are already sanitized by the worker. Never print response bodies/headers.
        print("FAIL: " + (str(error) if isinstance(error, AssertionError) else type(error).__name__))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
