"""Narrow offline regressions for IAP JWT URL scope and safe failure metadata."""
import io
import json
from email.message import Message
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest

from scripts.gcp import smoke_auth
from scripts.gcp.parity_smoke import Acceptance
from tests.test_github_cicd import ORIGIN


@pytest.mark.parametrize("headers,expected", [
    (None, ["iap_generated=false", "www_auth_scheme=absent_or_other", "redirect=false"]),
    ({"WWW-Authenticate": 'Bearer error="invalid_token", error_description="private-body-and-token"',
      "Location": "https://accounts.google.com/?private-code", "Set-Cookie": "private-cookie",
      "X-Goog-IAP-Generated-Response": "true"},
     ["iap_generated=true", "www_auth_scheme=bearer", "www_auth_error=invalid_token", "redirect=true"]),
    ({"WWW-Authenticate": 'private-scheme error="private_value"', "X-Goog-IAP-Generated-Response": "private-header"},
     ["www_auth_scheme=absent_or_other", "www_auth_error=absent_or_other", "iap_generated=false"]),
])
def test_safe_auth_metadata_never_returns_raw_header_values(headers, expected):
    output = smoke_auth.safe_auth_metadata(headers)
    assert all(value in output for value in expected)
    assert "private" not in output and "https://" not in output and "Set-Cookie" not in output


def test_acceptance_http_failure_reports_metadata_and_never_body_or_credential(capsys):
    headers = Message()
    headers["WWW-Authenticate"] = 'Bearer error="invalid_token", error_description="private-credential"'
    headers["X-Goog-IAP-Generated-Response"] = "true"
    def request(req, **kwargs):
        assert req.get_header("Authorization") == "Bearer private-jwt"
        assert req.get_header("Origin") == ORIGIN
        raise HTTPError(req.full_url, 401, "Unauthorized", headers, io.BytesIO(b"private response body"))
    acceptance = Acceptance(ORIGIN, "private-jwt")
    acceptance.opener = SimpleNamespace(open=request)
    with pytest.raises(ValueError, match="GET /health status 401") as error:
        acceptance.call("/health")
    assert "iap_generated=true" in str(error.value) and "www_auth_error=invalid_token" in str(error.value)
    assert "private" not in str(error.value) + capsys.readouterr().out


def test_existing_readonly_health_is_not_treated_as_cloud_acceptance(monkeypatch):
    acceptance = Acceptance(ORIGIN, "unused")
    monkeypatch.setattr(acceptance, "call", lambda *_: {"feature_mode": "readonly_demo", "environment": "dev", "generation_mode": "mock", "storage": "fixtures_readonly"})
    with pytest.raises(ValueError, match="Expected authenticated mock cloud_demo runtime"):
        acceptance.read_only("dev")


def test_iap_redirect_is_not_followed_or_treated_as_authenticated_health():
    acceptance = Acceptance(ORIGIN, "private-jwt")
    def request(req, **kwargs):
        raise HTTPError(req.full_url, 302, "Redirect", {"Location": "https://accounts.google.com/?private-code"}, io.BytesIO(b"private body"))
    acceptance.opener = SimpleNamespace(open=request)
    with pytest.raises(ValueError, match="status 302") as error:
        acceptance.call("/health")
    assert "redirect=true" in str(error.value) and "private" not in str(error.value)


@pytest.mark.parametrize("origin", [ORIGIN + "/", ORIGIN + "/health", ORIGIN + "/*", ORIGIN + "?query=x", "https://evil.example", ORIGIN + ".evil.example"])
def test_audience_cannot_expand_to_unreviewed_host_or_input_path(monkeypatch, origin):
    monkeypatch.setenv("GCP_SMOKE_ACCOUNT", "tripse-ai-dev-ci-probe@tripse-ai.iam.gserviceaccount.com")
    class G:
        config = {"APP_ENV": "dev", "GCP_PROJECT_ID": "tripse-ai"}
        def __call__(self, *args):
            pytest.fail("Invalid origin must fail before credential access")
    with pytest.raises(ValueError, match="Invalid probe origin"):
        smoke_auth.probe_token(G(), origin, iap=True)


def documented_iap_url_match(audience, url):
    """Test model of Google's exact-URL / terminal /* contract, not a verifier."""
    return url.startswith(audience[:-1]) if audience.endswith("/*") else url == audience


@pytest.mark.parametrize("path", ["/health", "/hub", "/api/document-studio/trips",
                                 "/documents/assets/studio.js", "/api/demo/scenarios"])
def test_minted_iap_jwt_authorizes_acceptance_paths_under_documented_url_contract(monkeypatch, path):
    monkeypatch.setenv("GCP_SMOKE_ACCOUNT", "tripse-ai-dev-ci-probe@tripse-ai.iam.gserviceaccount.com")
    signed = {}
    def sign(request, **kwargs):
        signed.update(json.loads(json.loads(request.data)["payload"]))
        return io.BytesIO(b'{"signedJwt":"synthetic-probe-token"}')
    monkeypatch.setattr(smoke_auth, "urlopen", sign)
    class G:
        config = {"APP_ENV": "dev", "GCP_PROJECT_ID": "tripse-ai"}
        def __call__(self, *args):
            return "synthetic-access-token"
    token = smoke_auth.probe_token(G(), ORIGIN, iap=True)
    # Bare-origin audiences from the original implementation cannot authorize
    # this path. An exact /health audience cannot serve the whole browser suite.
    assert not documented_iap_url_match(ORIGIN, ORIGIN + path)
    assert documented_iap_url_match(ORIGIN + "/health", ORIGIN + path) == (path == "/health")
    class Response(io.BytesIO):
        status = 200
        headers = {}
    def serve(request, **kwargs):
        assert request.get_header("Authorization") == "Bearer synthetic-probe-token"
        if not documented_iap_url_match(signed["aud"], request.full_url):
            raise HTTPError(request.full_url, 401, "Unauthorized", {}, io.BytesIO())
        return Response(b'{"status":"ok"}')
    acceptance = Acceptance(ORIGIN, token)
    acceptance.opener = SimpleNamespace(open=serve)
    assert acceptance.call(path) == {"status": "ok"}


@pytest.mark.parametrize("url", [ORIGIN + ".evil.example/health", ORIGIN + ":443/health",
                               "https://another-service.run.app/health", "http://" + ORIGIN.removeprefix("https://") + "/health"])
def test_documented_path_wildcard_does_not_authorize_other_origins(url):
    assert not documented_iap_url_match(ORIGIN + "/*", url)
