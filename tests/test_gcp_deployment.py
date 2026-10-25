import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from scripts.gcp import deployment as deploy
from scripts.gcp.deployment_contract import ROOT, image_tag, load_config, load_pair


@pytest.fixture
def config_dir(tmp_path):
    for environment in ("dev", "prod"):
        content = (ROOT / f"infra/gcp/.env.{environment}.example").read_text().replace("GCP_PROJECT_ID=", "GCP_PROJECT_ID=tripse-test-123")
        (tmp_path / f".env.{environment}").write_text(content)
    return tmp_path


def test_pair_and_runtime_whitelist(config_dir):
    dev, prod = (load_pair(e, config_dir) for e in ("dev", "prod"))
    assert dev.image == prod.image
    assert dev.runtime_account != prod.runtime_account
    assert dev["GCP_SERVICE_NAME"] != prod["GCP_SERVICE_NAME"]
    assert set(dev.runtime("a"*40)) == {"APP_ENV", "PLANNING_MODE", "CLOUD_FEATURE_MODE", "EXPECTED_IMAGE_SHA"}


@pytest.mark.parametrize("old,new", [
    ("APP_ENV=dev", "APP_ENV=prod"), ("PLANNING_MODE=mock", "PLANNING_MODE=live"),
    ("GCP_MIN_INSTANCES=0", "GCP_MIN_INSTANCES=1"), ("GCP_MAX_INSTANCES=1", "GCP_MAX_INSTANCES=100"),
    ("GCP_PROJECT_ID=tripse-test-123", "GCP_PROJECT_ID=$(secret)"),
    ("GCP_REGION=europe-central2", "GCP_REGION=../x"),
    ("GCP_PUBLIC_ACCESS=true", "GCP_PUBLIC_ACCESS=yes"),
    ("APP_ENV=dev", "APP_ENV=dev\nAPP_ENV=dev"),
    ("APP_ENV=dev", "APP_ENV=dev\nOPENAI_API_KEY=secret-never-logged"),
])
def test_bad_config(config_dir, old, new):
    path = config_dir / ".env.dev"
    path.write_text(path.read_text().replace(old,new))
    with pytest.raises(ValueError) as error:
        load_pair("dev",config_dir)
    assert "secret-never-logged" not in str(error.value)


def test_pair_rejects_cross_project(config_dir):
    path = config_dir / ".env.prod"
    path.write_text(path.read_text().replace("tripse-test-123", "tripse-other-123"))
    with pytest.raises(ValueError, match="share"):
        load_pair("prod", config_dir)


@pytest.mark.parametrize("tag", ["latest", "main", "abc1234", "A"*40, "a"*39, "a"*41, "../x"])
def test_image_tags(tag):
    with pytest.raises(ValueError):
        image_tag(tag)


def test_resource_ownership():
    with pytest.raises(ValueError):
        deploy.assert_owned({"app":"other"})
    with pytest.raises(ValueError):
        deploy.assert_owned(deploy.LABELS | {"environment":"dev"}, environment="prod")
    deploy.assert_owned(deploy.LABELS | {"environment":"prod"}, environment="prod")


def test_native_error_code_preserved(monkeypatch):
    monkeypatch.setattr(deploy.subprocess, "run", lambda *a,**kw: SimpleNamespace(returncode=17, stdout=b"", stderr=b"secret"))
    with pytest.raises(deploy.CommandError) as error:
        deploy.run(["gcloud", "projects", "describe"])
    assert error.value.code == 17
    assert "secret" not in str(error.value)


def test_prod_explicit_tag_no_build(config_dir, monkeypatch):
    monkeypatch.setattr(deploy, "offline_runtime", lambda *args: None)
    with pytest.raises(ValueError, match="explicit"):
        deploy.main(["deploy", "--environment", "prod", "--config-dir", str(config_dir)])
    with pytest.raises(ValueError, match="Build once"):
        deploy.main(["build", "--environment", "prod", "--config-dir", str(config_dir)])


def test_dry_run_never_calls_gcloud(config_dir, monkeypatch, capsys):
    monkeypatch.setattr(deploy, "offline_runtime", lambda *args: None)
    monkeypatch.setattr(deploy, "Gcloud", lambda *a: pytest.fail("DryRun contacted GCP"))
    deploy.main(["deploy", "--environment", "prod", "--image-tag", "a"*40, "--config-dir", str(config_dir), "--dry-run"])
    assert "No GCP calls" in capsys.readouterr().out


def test_context_only_committed_allowlist():
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    files = dict(deploy.source_files(sha))
    assert "Dockerfile" in files and "app/main.py" in files
    assert all(not name.startswith(("local-data/", "data/", "docs/", "tests/", "scripts/")) for name in files)
    assert not any(".env" in Path(name).parts for name in files)
    assert not any("document-presets" in name for name in files)


def test_deploy_pins_digest_and_separate_runtime(config_dir, monkeypatch, tmp_path):
    config = load_pair("prod", config_dir)
    calls = []
    class Fake:
        def __init__(self): self.config = config
        def __call__(self,*args,**kwargs):
            calls.append(args)
            if args[:3] == ("run","services","get-iam-policy"):
                return {"bindings":[{"role":"roles/run.invoker","members":["allUsers"]}]}
            if args[:2] == ("run","deploy"):
                env_arg = next(arg for arg in args if arg.startswith("--env-vars-file="))
                assert json.loads(Path(env_arg.split("=",1)[1]).read_text()) == config.runtime("a"*40)
    monkeypatch.setattr(deploy, "repository", lambda g: True)
    monkeypatch.setattr(deploy, "check_release_source", lambda sha: None)
    monkeypatch.setattr(deploy, "service", lambda g: True)
    monkeypatch.setattr(deploy, "check_act_as", lambda *a: None)
    monkeypatch.setattr(deploy, "digest", lambda *a: "sha256:"+"b"*64)
    monkeypatch.setattr(deploy, "deployed_state", lambda *a: {"url":"https://tripse-ai-prod.example.run.app"})
    monkeypatch.setattr(deploy, "smoke", lambda *a,**kw: calls.append(("smoke", kw.get("private",False))))
    monkeypatch.setattr(deploy, "ROOT", tmp_path)
    deploy.deploy(Fake(), "a"*40)
    args = next(c for c in calls if c[:2] == ("run","deploy"))
    assert f"--image={config.image}@sha256:{'b'*64}" in args
    assert "--port=8000" in args and "--min-instances=0" in args
    assert "--no-allow-unauthenticated" in args
    private_index=calls.index(("smoke",True))
    public_index=next(i for i,c in enumerate(calls) if c[:3]==("run","services","add-iam-policy-binding"))
    assert private_index<public_index<calls.index(("smoke",False))
    remove_index=next(i for i,c in enumerate(calls) if c[:3]==("run","services","remove-iam-policy-binding"))
    assert remove_index<calls.index(args)
    assert not any("builds" in c or "config" in c for c in calls)
    assert (tmp_path / ".gcp-state/prod.json").exists()
    assert not (tmp_path / ".gcp-state/dev.json").exists()
    calls.clear()
    def failed_smoke(*args,**kwargs):
        raise ValueError("Fixture smoke deliberately failed")
    monkeypatch.setattr(deploy,"smoke",failed_smoke)
    with pytest.raises(ValueError,match="deliberately failed"):
        deploy.deploy(Fake(),"a"*40)
    assert not any(c[:3]==("run","services","add-iam-policy-binding") for c in calls)


def test_url_validation():
    for value in ("http://a.run.app", "https://evil.com", "https://a.run.app/../x", "https://a.run.app@evil.com"):
        with pytest.raises(ValueError):
            deploy.validate_url(value)


def test_cannot_deploy_old_local_only_commit():
    sha = "462476001b6c3dac60ad15333631726729ad422c"
    with pytest.raises(ValueError, match="predates"):
        deploy.check_release_source(sha)


def test_setup_idempotent_and_no_delete(config_dir, monkeypatch):
    config = load_pair("dev", config_dir)
    calls=[]
    class Fake:
        def __init__(self): self.config=config
        def __call__(self,*args,**kwargs):
            calls.append(args)
            if args[:2] == ("services","list"): return "\n".join(deploy.APIS)
            if args[:3] == ("iam","service-accounts","list"):
                return [{"email":f"tripse-ai-{name}@tripse-test-123.iam.gserviceaccount.com","displayName":f"TRIPSE managed {name}"} for name in ("build","dev","prod")]
            if args[:2] == ("projects","get-iam-policy"):
                return {"bindings":[{"role":"roles/cloudbuild.builds.builder","members":[f"serviceAccount:{config.build_account}"]}]}
            pytest.fail(f"Unexpected mutation: {args[:3]}")
    monkeypatch.setattr(deploy,"CONFIG_DIR",config_dir)
    monkeypatch.setattr(deploy,"check_region",lambda g:None)
    monkeypatch.setattr(deploy,"repository",lambda g:True)
    monkeypatch.setattr(deploy,"service",lambda g:None)
    monkeypatch.setattr(deploy,"Gcloud",lambda c:Fake())
    deploy.setup(Fake())
    assert not any("delete" in c or "create" in c or "enable" in c for c in calls)


def test_smoke_rejects_wrong_environment(config_dir, monkeypatch):
    config=load_pair("dev",config_dir)
    class Response:
        status=200
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self):return b'{"status":"ok","environment":"prod"}'
    monkeypatch.setattr(deploy,"urlopen",lambda *a,**kw:Response())
    with pytest.raises(ValueError,match="mismatch"):
        deploy.smoke(SimpleNamespace(config=config),{"url":"https://test.run.app","image_sha":"a"*40})


def test_powershell_syntax():
    if not deploy.shutil.which("powershell"):
        pytest.skip("Windows PowerShell not installed")
    script = "$bad = $false; Get-ChildItem scripts/gcp/*.ps1 | ForEach-Object { $t = $null; $e = $null; [System.Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$t, [ref]$e) | Out-Null; if ($e.Count) { $bad = $true } }; if ($bad) { exit 1 }"
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], cwd=ROOT, check=True, capture_output=True)
