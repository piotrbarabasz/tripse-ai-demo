"""CI-001: cache inputs, unconditional installs, original gates and safe summaries."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SETUP = "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"


def workflow(name):
    return yaml.load((ROOT / ".github/workflows" / name).read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


@pytest.fixture(params=[("ci.yml", "checks"), ("delivery.yml", "dev"), ("delivery.yml", "prod")])
def job(request):
    filename, identifier = request.param
    return workflow(filename)["jobs"][identifier]


def test_pip_cache_in_each_independent_runner_keeps_install_on_miss_and_hit(job):
    setup = next(s for s in job["steps"] if s.get("uses") == SETUP)
    assert setup["id"] == "python"
    assert setup["with"] == {"python-version": "3.12", "cache": "pip",
        "cache-dependency-path": "requirements.txt\nrequirements-dev.txt\n"}
    install = next(s for s in job["steps"] if s.get("run") == "make install-dev")
    assert "if" not in setup and "if" not in install  # no warm-cache shortcut
    assert job["steps"].index(setup) < job["steps"].index(install)
    assert not any(s.get("uses", "").startswith("actions/cache@") for s in job["steps"])


@pytest.mark.parametrize("changed", ["requirements.txt", "requirements-dev.txt"])
def test_each_requirements_file_is_a_content_sensitive_cache_input(job, changed, tmp_path):
    # Input contract only: setup-python owns hashFiles(), restore keys and storage.
    setup = next(s for s in job["steps"] if s.get("uses") == SETUP)
    paths = setup["with"]["cache-dependency-path"].splitlines()
    for name in paths:
        (tmp_path / name).write_bytes((ROOT / name).read_bytes())
    def fingerprint():
        return hashlib.sha256(b"".join(hashlib.sha256((tmp_path / name).read_bytes()).digest() for name in sorted(paths))).digest()
    before = fingerprint()
    path = tmp_path / changed
    path.write_bytes(path.read_bytes() + b"\n# CI-001 invalidation probe\n")
    assert fingerprint() != before
    assert "-r requirements.txt" in (tmp_path / "requirements-dev.txt").read_text()


def test_ci_retains_complete_commands_and_no_cloud_credentials():
    ci = workflow("ci.yml")
    assert set(ci["jobs"]) == {"checks"}
    assert ci["permissions"] == {"contents": "read"}
    job = ci["jobs"]["checks"]
    assert job["permissions"] == {"contents": "read"}
    commands = [s["run"] for s in job["steps"] if "run" in s]
    assert commands[:-1] == ["make install-dev", "npm ci",
        ".venv/bin/python -m scripts.export_openapi --check\n.venv/bin/python -m scripts.export_api_fixtures --check\nnpm --prefix frontend run api:check\n",
        "npm run typecheck", "npm run lint",
        "npm run test", "npm run build", "make test", ".venv/bin/python -m scripts.gcp.ci offline",
        ".venv/bin/python -m playwright install --with-deps chromium", "make test-browser", "git diff --check"]
    assert not any("google-github-actions/" in s.get("uses", "") for s in job["steps"])
    assert not any("secrets." in str(s) for s in job["steps"])


def test_frontend_checks_use_locked_loopback_app_toolchain_in_same_unprivileged_job():
    job = workflow("ci.yml")["jobs"]["checks"]
    setup = next(s for s in job["steps"] if s.get("uses", "").startswith("actions/setup-node@"))
    assert setup["with"] == {"node-version-file": "frontend/.nvmrc", "package-manager-cache": "false"}
    assert "if" not in setup
    for command in ("npm ci", "npm run typecheck", "npm run lint", "npm run test", "npm run build"):
        step = next(s for s in job["steps"] if s.get("run") == command)
        assert step["working-directory"] == "frontend"
        assert "if" not in step and "continue-on-error" not in step
        assert job["steps"].index(setup) < job["steps"].index(step)


@pytest.mark.parametrize("outcome,expected", [("true", "Exact dependency-key hit (warm)"),
    ("false", "No exact hit: cold miss, fallback restore"), ("", "Cache outcome unavailable"),
    ("$(echo SENSITIVE_CANARY)", "Cache outcome unavailable")])
def test_summary_handles_setup_failure_and_untrusted_values_without_leaking(job, outcome, expected, tmp_path):
    summary = next(s for s in job["steps"] if s.get("name") == "Summarize pip cache and native timings")
    assert summary["if"] == "always()"
    assert summary["env"] == {"PIP_CACHE_HIT": "${{ steps.python.outputs.cache-hit }}"}
    bash = shutil.which("bash")
    if os.name == "nt":
        candidate = Path("C:/Program Files/Git/bin/bash.exe")
        bash = str(candidate) if candidate.is_file() else None
    if not bash:
        pytest.skip("Bash required to execute the Ubuntu workflow summary locally")
    target = tmp_path / "summary.md"
    script = tmp_path / "summary.sh"
    script.write_text(summary["run"], encoding="utf-8", newline="\n")
    env = dict(os.environ, PIP_CACHE_HIT=outcome, GITHUB_STEP_SUMMARY=target.as_posix(), SECRET_TOKEN="SENSITIVE_CANARY")
    result = subprocess.run([bash, script.as_posix()], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    content = target.read_text(encoding="utf-8")
    assert expected in content and "native Actions job/step" in content
    assert "SENSITIVE_CANARY" not in content + result.stdout + result.stderr
    assert result.stdout == ""
