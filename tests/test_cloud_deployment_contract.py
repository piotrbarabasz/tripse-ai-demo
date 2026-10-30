from types import SimpleNamespace
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit

import pytest

from scripts.gcp.deployment_contract import ROOT, load_pair
from scripts.gcp import deployment
from test_cloud_demo import cloud_demo, ORIGIN


@pytest.fixture
def demo_configs(tmp_path):
    for environment in ("dev", "prod"):
        source = (ROOT / f"infra/gcp/.env.{environment}.example").read_text(encoding="utf-8")
        source = source.replace("GCP_PROJECT_ID=", "GCP_PROJECT_ID=tripse-test-123", 1)
        source = source.replace("GCP_PUBLIC_ACCESS=true", "GCP_PUBLIC_ACCESS=false")
        source = source.replace("CLOUD_FEATURE_MODE=readonly_demo", "CLOUD_FEATURE_MODE=cloud_demo")
        source += f"""
GCP_PROJECT_NUMBER=123456789
PUBLIC_BASE_URL=https://tripse-ai-{environment}-example.run.app
IAP_OAUTH_CLIENT_ID=123-example.apps.googleusercontent.com
DEMO_EDITORS=operator@example.com
DEMO_READERS=
GCP_DOCUMENT_BUCKET=tripse-test-123-tripse-ai-{environment}-documents
GCP_FIRESTORE_DATABASE=tripse-ai-{environment}
GCP_TASK_QUEUE=projects/tripse-test-123/locations/europe-central2/queues/tripse-ai-{environment}
GCP_TASK_ACCOUNT=tripse-ai-{environment}-tasks@tripse-test-123.iam.gserviceaccount.com
"""
        (tmp_path / f".env.{environment}").write_text(source, encoding="utf-8")
    return tmp_path


def test_private_mode_config_runtime_and_isolation(demo_configs):
    dev, prod = (load_pair(environment, demo_configs) for environment in ("dev", "prod"))
    assert dev.runtime("a" * 40)["GCP_FIRESTORE_DATABASE"] == "tripse-ai-dev"
    assert prod.runtime("a" * 40)["GCP_FIRESTORE_DATABASE"] == "tripse-ai-prod"
    assert dev.demo_settings().audience.endswith("/services/tripse-ai-dev")
    assert dev.demo_settings().editors == {"operator@example.com"}
    deployment.offline_runtime(dev)
    with pytest.raises(ValueError, match="readonly_demo"):
        deployment.publish(SimpleNamespace(config=dev), {})


@pytest.mark.parametrize("old,new", [
    ("GCP_PUBLIC_ACCESS=false", "GCP_PUBLIC_ACCESS=true"),
    ("GCP_FIRESTORE_DATABASE=tripse-ai-dev", "GCP_FIRESTORE_DATABASE=tripse-ai-prod"),
    ("GCP_PROJECT_NUMBER=123456789", "GCP_PROJECT_NUMBER=wrong"),
    ("DEMO_EDITORS=operator@example.com", "DEMO_EDITORS="),
    ("PLANNING_MODE=mock", "PLANNING_MODE=live"),
])
def test_cloud_config_fail_closed(demo_configs, old, new):
    path = demo_configs / ".env.dev"
    path.write_text(path.read_text().replace(old, new))
    with pytest.raises(ValueError):
        load_pair("dev", demo_configs)


def test_pinned_separate_browser_secret_reference(demo_configs):
    path = demo_configs / ".env.dev"
    source = path.read_text()
    reference = "projects/tripse-test-123/secrets/tripse-ai-dev-maps-browser/versions/1"
    path.write_text(source + "GCP_BROWSER_MAPS_SECRET=" + reference + "\nGOOGLE_MAPS_MAP_ID=DEMO_MAP_ID\n")
    config = load_pair("dev", demo_configs)
    assert "GCP_BROWSER_MAPS_SECRET" not in config.runtime("a" * 40)
    assert config.runtime("a" * 40)["GOOGLE_MAPS_MAP_ID"] == "DEMO_MAP_ID"
    for invalid in (reference.replace("dev", "prod"), reference.replace("/1", "/latest"), "raw-api-key"):
        path.write_text(source + "GCP_BROWSER_MAPS_SECRET=" + invalid + "\n")
        with pytest.raises(ValueError):
            load_pair("dev", demo_configs)


def test_cloud_deploy_requires_smoke_token_before_mutations(demo_configs, monkeypatch):
    monkeypatch.delenv("CLOUD_DEMO_SMOKE_TOKEN", raising=False)
    config = load_pair("dev", demo_configs)
    with pytest.raises(ValueError, match="SMOKE_TOKEN"):
        deployment.deploy(SimpleNamespace(config=config), "a" * 40)


@pytest.mark.parametrize("environment,existing", [("dev", True), ("prod", False), ("prod", True)])
def test_cloud_deploy_pins_private_image_iap_and_secret_reference(demo_configs, monkeypatch, tmp_path, environment, existing):
    config = load_pair(environment, demo_configs)
    config.values["GCP_BROWSER_MAPS_SECRET"] = f"projects/tripse-test-123/secrets/tripse-ai-{environment}-maps-browser/versions/1"
    calls = []
    def g(*args, **kwargs):
        calls.append(args)
        if args[:3] == ("run", "services", "get-iam-policy"):
            return {"bindings": [{"role": "roles/run.invoker", "members": [
                "serviceAccount:service-123456789@gcp-sa-iap.iam.gserviceaccount.com"]}]}
        if args[:2] == ("run", "deploy"):
            path = next(a.split("=", 1)[1] for a in args if a.startswith("--env-vars-file="))
            assert json.loads(Path(path).read_text()) == config.runtime("a" * 40)
    g.config = config
    monkeypatch.setenv("CLOUD_DEMO_SMOKE_TOKEN", "offline-secret-token")
    monkeypatch.setattr(deployment, "check_release_source", lambda _: {name: b"" for name in (
        "app/cloud_runtime.py", "app/cloud_access.py", "app/cloud_jobs.py", "app/document_studio/cloud_storage.py")})
    monkeypatch.setattr(deployment, "repository", lambda _: True)
    monkeypatch.setattr(deployment, "service", lambda _: {"metadata": {"annotations": {
        "run.googleapis.com/iap-enabled": "true"}}} if existing else None)
    monkeypatch.setattr(deployment, "check_act_as", lambda *a: None)
    monkeypatch.setattr(deployment, "digest", lambda *a: "sha256:" + "b" * 64)
    monkeypatch.setattr(deployment, "deployed_state", lambda *a: {"url": ORIGIN})
    monkeypatch.setattr(deployment, "smoke", lambda *a, **k: None)
    monkeypatch.setattr(deployment, "publish", lambda *a: pytest.fail("Authenticated app published"))
    monkeypatch.setattr(deployment, "ROOT", tmp_path)
    deployment.deploy(g, "a" * 40)
    args = next(c for c in calls if c[:2] == ("run", "deploy"))
    assert "--invoker-iam-check" in args
    if environment == "dev":
        assert "--iap" not in args and "--no-iap" not in args and "--no-allow-unauthenticated" not in args
    else:
        assert "--iap" in args and "--no-allow-unauthenticated" in args
    assert f"--image={config.image}@sha256:{'b' * 64}" in args
    assert f"--set-secrets=GOOGLE_MAPS_BROWSER_KEY=projects/tripse-test-123/secrets/tripse-ai-{environment}-maps-browser:1" in args
    assert "--clear-secrets" not in args
    assert not any("--no-invoker-iam-check" in c or "offline-secret-token" in str(c) for c in calls)


@pytest.mark.parametrize("secret,allowed", [("tripse-ai-dev-maps-browser", True), ("tripse-ai-prod-maps-browser", False),
    ("projects/123456789/secrets/tripse-ai-dev-maps-browser", True),
    ("projects/999999999/secrets/tripse-ai-dev-maps-browser", False)])
def test_existing_browser_secret_alias_can_rotate_without_trusting_other_resources(demo_configs, secret, allowed):
    config = load_pair("dev", demo_configs)
    value = {"metadata": {"name": "tripse-ai-dev", "labels": deployment.LABELS | {"environment": "dev"}},
        "spec": {"template": {"metadata": {"annotations": {"run.googleapis.com/secrets": "alias:" + secret}},
            "spec": {"containers": [{"env": [{"name": "GOOGLE_MAPS_BROWSER_KEY", "valueFrom": {"secretKeyRef": {"name": "alias", "key": "2"}}}]}]}}}}
    def g(*args, **kwargs):
        return [value]
    g.config = config
    if allowed:
        assert deployment.service(g) == value
    else:
        with pytest.raises(ValueError, match="secret references"):
            deployment.service(g)


@pytest.mark.parametrize("anonymous_ok", [False, True])
def test_authenticated_smoke_rejects_login_html_success(cloud_demo, demo_configs, monkeypatch, anonymous_ok):
    config = load_pair("dev", demo_configs)
    monkeypatch.setenv("CLOUD_DEMO_SMOKE_TOKEN", "offline-token")
    with cloud_demo.client() as client:
        class Opener:
            def open(self, request, **kwargs):
                authenticated = request.get_header("Authorization") == "Bearer offline-token"
                if not authenticated:
                    if anonymous_ok:
                        return Response(200, b"login HTML is not API success")
                    raise HTTPError(request.full_url, 302, "IAP login", {}, None)
                response = client.get(urlsplit(request.full_url).path)
                return Response(response.status_code, response.content)
        class Response:
            def __init__(self, status, content): self.status, self.content = status, content
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return self.content
        def opener(handler):
            assert handler.redirect_request(None, None, 302, "", {}, "https://other.example") is None
            return Opener()
        monkeypatch.setattr(deployment, "build_opener", opener)
        state = {"url": ORIGIN, "image_sha": client.get("/health").json()["image_version"]}
        if anonymous_ok:
            with pytest.raises(ValueError, match="Anonymous denial"):
                deployment.cloud_demo_smoke(SimpleNamespace(config=config), state)
        else:
            deployment.cloud_demo_smoke(SimpleNamespace(config=config), state)
