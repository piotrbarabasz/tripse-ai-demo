import httpx
import pytest

from app.generator import generate_mock_trip
from app.smoke import run


@pytest.mark.parametrize("mode", ["mock", "live"])
def test_smoke_never_claims_real_routes_for_mock_or_partial_results(mode):
    plan = generate_mock_trip("id", "Zaplanuj 2 dni we Wrocławiu")
    plan["viewer_url"] = "https://demo.example.test/trip/" + "x" * 43
    if mode == "live":
        plan["is_mock"] = False
        plan["verification_status"] = "partial"

    def handler(request):
        path = request.url.path
        if path == "/health":
            return httpx.Response(200, json={"status": "ok", "generation_mode": mode})
        if path == "/":
            return httpx.Response(302, headers={"location": "/hub"})
        if path == "/planner":
            return httpx.Response(200, text='<form id="trip-form"></form>')
        if path == "/api/webhooks/waha":
            return httpx.Response(401)
        if path == "/api/trips" and request.method == "POST":
            return httpx.Response(202, json={"trip_id": "id"})
        if path == "/api/trips/id":
            return httpx.Response(200, json={"status": "completed", "result": plan})
        if path == "/trip/" + "x" * 43:
            return httpx.Response(200, text="<html></html>", headers={"Content-Type": "text/html"})
        if path == "/api/viewer/" + "x" * 43:
            return httpx.Response(200, json={"plan": {k: v for k, v in plan.items() if k != "request_text"}})
        return httpx.Response(404)

    with httpx.Client(base_url="https://demo.example.test", transport=httpx.MockTransport(handler)) as client:
        if mode == "live":
            with pytest.raises(AssertionError, match="route is unverified"):
                run(client, expect_mode=mode)
        else:
            report = run(client, expect_mode=mode)
            assert report["api_worker_viewer"] == "PASS"
            assert report["real_route_calculations"].startswith("NOT VERIFIED")
