import httpx
import pytest


@pytest.fixture(autouse=True)
def isolated_providers(monkeypatch):
    # Unit tests must never spend money, even if the developer has real keys set.
    monkeypatch.setenv("PLANNING_MODE", "mock")
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://localhost:8000")
    for key in ("OPENAI_API_KEY", "GOOGLE_MAPS_API_KEY", "GOOGLE_PLACES_API_KEY", "GOOGLE_ROUTES_API_KEY"):
        monkeypatch.delenv(key, raising=False)

    def disallow_network(*args, **kwargs):
        raise AssertionError("Real network access is forbidden in unit tests. Use MockTransport.")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", disallow_network)
