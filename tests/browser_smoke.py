"""Headless UI smoke with a local DB and Google Maps test double; no paid calls.

Run from repo root: .venv/Scripts/python tests/browser_smoke.py
"""
import copy
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from playwright.sync_api import expect, sync_playwright
from app.db import Database
from app.planning import directions_url
from app.planning_models import Place


MAPS_DOUBLE = r"""
window.mapTest = {markers: [], lines: [], fits: []};
const testState = window.mapTest;
class Bounds {
  constructor() { this.points = []; }
  extend(p) { this.points.push(p); return this; }
  isEmpty() { return this.points.length === 0; }
}
class TestMap {
  constructor(node) { node.textContent = 'Google Maps test double — no external API requests'; }
  fitBounds(bounds) { testState.fits.push(bounds.points.length); }
  getZoom() { return 7; }
  setZoom() {}
}
class Marker {
  constructor(options) { Object.assign(this, options); testState.markers.push(this); }
}
class Line {
  constructor(options) { this.options = options; testState.lines.push(this); }
  setOptions(options) { Object.assign(this.options, options); }
  addListener() {}
}
window.google = {maps: {Map: TestMap, LatLngBounds: Bounds, Polyline: Line,
  marker: {AdvancedMarkerElement: Marker},
  event: {addListenerOnce: (_, name, callback) => callback()},
  geometry: {encoding: {decodePath: () => [
    {lat: () => 50, lng: () => 15}, {lat: () => 51, lng: () => 16}
  ]}}
}};
window.tripseMapsReady();
"""


def seed(database):
    # Synthetic API fixture only. These values are never used as a real itinerary.
    places = [Place(query=name, name=name, place_id=f"synthetic-place-{i}", lat=50 + i / 10, lng=15 + i / 10)
              for i, name in enumerate(["Wrocław", "Karpacz", "Wang Church", "Szklarska Poręba", "Kamieńczyk parking"])]
    days = []
    for number, stops in enumerate([places[:3], [places[2], *places[3:], places[0]]], 1):
        days.append({"number": number, "stops": [p.model_dump() for p in stops],
                     "routing_status": "verified", "drive_minutes": 124.5, "distance_km": 145.7,
                     "encoded_polyline": "synthetic-geometry", "warnings": [],
                     "google_maps_url": directions_url(stops)})
    plan = {"title": "2 days in the Karkonosze", "is_mock": False,
            "verification_status": "verified", "days": days,
            "requirements": {"days": 2, "preferences": ["Nature"], "max_daily_drive_min": 180},
            "warnings": ["Draft only. Opening hours and seasonal access are unverified."]}
    trip_id = database.create_trip("PRIVATE REQUEST MUST NOT BE SHARED")
    database.claim_next()
    token = secrets.token_urlsafe(32)
    database.finish(trip_id, result=plan, viewer_token=token, viewer_expires_at=time.time() + 600)
    expired_id = database.create_trip("expired")
    database.claim_next()
    expired = secrets.token_urlsafe(32)
    database.finish(expired_id, result=plan, viewer_token=expired, viewer_expires_at=0)
    return token, expired, plan


def run():
    artifacts = ROOT / "local-data" / "viewer-qa"
    artifacts.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        database = Database(Path(directory) / "browser.sqlite3")
        database.initialize()
        token, expired, plan = seed(database)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        base = f"http://127.0.0.1:{port}"
        env = dict(os.environ, DATABASE_PATH=str(database.path), GOOGLE_MAPS_BROWSER_KEY="fake-browser-key",
                   GOOGLE_MAPS_MAP_ID="DEMO_MAP_ID", GOOGLE_MAPS_API_KEY="private-server-key",
                   OPENAI_API_KEY="private-openai-key")
        with (artifacts / "server.log").open("w") as log:
            server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                                       "--port", str(port)], cwd=ROOT, env=env, stdout=log, stderr=log,
                                      creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            try:
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                for _ in range(60):
                    try:
                        opener.open(base + "/health", timeout=1).close()
                        break
                    except OSError:
                        time.sleep(.2)
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    context = browser.new_context(viewport={"width": 1440, "height": 1000})

                    def route_external(route):
                        if route.request.url.startswith(base):
                            route.continue_()
                        elif route.request.url.startswith("https://maps.googleapis.com/maps/api/js?"):
                            route.fulfill(content_type="text/javascript", body=MAPS_DOUBLE)
                        else:
                            route.abort()

                    context.route("**/*", route_external)
                    page = context.new_page()
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto(base + "/trip/" + token)
                    expect(page.locator(".day-card")).to_have_count(2)
                    expect(page.locator("#map-status")).to_be_hidden()
                    assert page.evaluate("window.mapTest.markers.length") == 5
                    assert page.evaluate("window.mapTest.lines.length") == 2
                    assert page.evaluate("window.mapTest.fits.length") >= 1
                    assert page.get_by_role("link", name="Open Day 1 in Google Maps").get_attribute("href").startswith("https://www.google.com/maps/dir/")
                    assert page.get_by_role("link", name="Open Day 2 in Google Maps").get_attribute("href").startswith("https://www.google.com/maps/dir/")
                    page.get_by_role("button", name="Highlight Day 2 on map").click()
                    assert page.evaluate("window.mapTest.lines[1].options.strokeWeight") == 7
                    assert page.evaluate("window.mapTest.lines[0].options.strokeOpacity") == .25
                    expect(page.locator('[data-day="2"]')).to_have_class("day-card selected")
                    page.get_by_role("button", name="Wszystkie dni").click()
                    assert page.evaluate("window.mapTest.lines[0].options.strokeOpacity") == .95
                    left = page.locator(".itinerary").bounding_box()
                    right = page.locator(".map-panel").bounding_box()
                    assert right["x"] > left["x"] + left["width"]
                    page.screenshot(path=str(artifacts / "desktop.png"), full_page=True)
                    page.set_viewport_size({"width": 390, "height": 844})
                    left = page.locator(".itinerary").bounding_box()
                    right = page.locator(".map-panel").bounding_box()
                    assert right["y"] >= left["y"] + left["height"]
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                    page.screenshot(path=str(artifacts / "mobile.png"), full_page=True)

                    # Omit unverified map facts, metrics and unsafe external links.
                    partial = copy.deepcopy(plan)
                    partial["verification_status"] = "partial"
                    partial["days"][1].update(routing_status="routing_failed", drive_minutes=None,
                        distance_km=None, encoded_polyline=None, warnings=["route_calculation_failed"], google_maps_url="javascript:alert(1)")
                    partial["days"][1]["stops"].append({"name": "Unresolved location", "place_id": "bad",
                        "lat": 0, "lng": 0, "source": "google_places", "verification_status": "unresolved"})
                    partial["title"] = '<img src=x onerror="window.injected=true">'

                    def custom_data(route):
                        route.fulfill(json={"plan": partial, "maps": {"browser_key": "fake-browser-key"}})

                    page.route("**/api/viewer/*", custom_data)
                    page.reload()
                    expect(page.locator("#map-status")).to_be_hidden()
                    assert page.evaluate("window.mapTest.markers.length") == 5
                    assert page.evaluate("window.mapTest.lines.length") == 1
                    expect(page.locator('[data-day="2"] .drive-stats')).to_have_text("Czas i odległość niedostępne")
                    expect(page.locator('[data-day="2"] .route-badge')).to_have_text("Brak trasy")
                    expect(page.locator('[data-day="2"] a')).to_have_count(0)
                    assert page.locator("#trip-title img").count() == 0
                    assert page.evaluate("window.injected === undefined")
                    page.unroute("**/api/viewer/*", custom_data)

                    # API loading, error and retry states.
                    pending = []
                    page.route("**/api/viewer/*", lambda route: pending.append(route))
                    page.goto(base + "/trip/" + token, wait_until="domcontentloaded")
                    expect(page.locator("#page-message")).to_have_text("Loading your itinerary…")
                    page.wait_for_timeout(100)
                    pending[0].fulfill(status=503, json={})
                    expect(page.locator("#retry-plan")).to_be_visible()
                    page.unroute("**/api/viewer/*")
                    page.locator("#retry-plan").click()
                    expect(page.locator(".day-card")).to_have_count(2)

                    # Missing browser key leaves itinerary intact and makes no map request.
                    page.route("**/api/viewer/*", lambda route: route.fulfill(json={"plan": plan, "maps": {"browser_key": ""}}))
                    page.reload()
                    expect(page.locator("#map-status")).to_contain_text("not configured")
                    expect(page.locator(".day-card")).to_have_count(2)
                    page.unroute("**/api/viewer/*")

                    # Map load failures are separate from itinerary errors.
                    page.route("https://maps.googleapis.com/**", lambda route: route.abort())
                    page.reload()
                    expect(page.locator("#map-status")).to_contain_text("could not load")
                    expect(page.locator(".day-card")).to_have_count(2)
                    page.unroute("https://maps.googleapis.com/**")

                    # Authentication may fail after Google's initial loader callback.
                    page.route("https://maps.googleapis.com/**", lambda route: route.fulfill(
                        content_type="text/javascript", body=MAPS_DOUBLE + "\nsetTimeout(() => window.gm_authFailure(), 20);"))
                    page.reload()
                    expect(page.locator("#map-status")).to_contain_text("could not be authorized")
                    expect(page.locator(".day-card")).to_have_count(2)
                    page.unroute("https://maps.googleapis.com/**")

                    # Browser fallback uses the same create/status/viewer API flow.
                    page.route("**/api/trips", lambda route: route.fulfill(status=202, json={"trip_id": "browser-job", "status": "queued"}))
                    browser_result = {**plan, "viewer_url": base + "/trip/" + token}
                    page.route("**/api/trips/browser-job", lambda route: route.fulfill(json={"status": "completed", "result": browser_result}))
                    page.goto(base + "/planner")
                    expect(page.locator("#request-text")).to_contain_text("Zaplanuj 2 dni")
                    page.get_by_role("button", name="Przygotuj plan").click()
                    expect(page.locator("#open-trip")).to_be_visible()
                    page.locator("#open-trip").click()
                    expect(page.locator(".day-card")).to_have_count(2)

                    for invalid in (expired, "x" * 43, "malformed"):
                        response = page.goto(base + "/trip/" + invalid)
                        assert response.status == 404
                        expect(page.locator("h1")).to_have_text("This plan link is unavailable.")
                    assert not errors, errors
                    browser.close()
                    print("Browser smoke passed: desktop/mobile, routes/markers, day selection, token rejection, safe rendering, loading/retry and map failures. No external API calls.")
                    print("Screenshots:", artifacts)
            finally:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()


if __name__ == "__main__":
    run()
