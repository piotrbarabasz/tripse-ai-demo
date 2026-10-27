"""Resume accepted master evidence without bypassing attempt provenance."""
import copy
import io
import json
import zipfile

import pytest

from scripts.gcp import ci
from tests.test_github_cicd import SHA, proof


def evidence_api(monkeypatch, *, latest_attempt=1, job_attempt=1):
    record, run, artifact, jobs = proof()
    # Overall Delivery failed on PROD; the independently accepted DEV job passed.
    run.update(conclusion="failure", run_attempt=latest_attempt)
    jobs[0]["run_attempt"] = job_attempt
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as stream:
        stream.writestr("release.json", json.dumps(record))
    requests = []

    class API:
        def request(self, path, *, archive=False):
            requests.append(path)
            if path == "/actions/runs/123":
                return copy.deepcopy(run)
            if path == "/actions/artifacts/456":
                return copy.deepcopy(artifact)
            assert path == "/actions/artifacts/456/zip" and archive
            return globals_archive

        def pages(self, path, field):
            requests.append(path)
            assert path == f"/actions/runs/123/attempts/{latest_attempt}/jobs"
            assert field == "jobs"
            return copy.deepcopy(jobs)

    globals_archive = archive.getvalue()
    monkeypatch.setattr(ci, "GitHub", API)
    monkeypatch.setenv("CI_EVIDENCE_RUN_ID", "123")
    monkeypatch.setenv("CI_EVIDENCE_ARTIFACT_ID", "456")
    return requests


def test_manual_promotion_preserves_original_accepted_attempt(monkeypatch):
    requests = evidence_api(monkeypatch)
    # A separate dispatch has its own context; it does not increment source run.
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    monkeypatch.setenv("GITHUB_RUN_ID", "999")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    result = ci.release_proof("dev", SHA, "cloud_demo", production=True)
    assert result["accepted"] is True and result["run_id"] == 123
    assert "/actions/runs/123/attempts/1/jobs" in requests


def test_prod_only_rerun_cannot_reuse_older_attempt_artifact(monkeypatch):
    requests = evidence_api(monkeypatch, latest_attempt=2)
    with pytest.raises(ValueError, match="provenance"):
        ci.release_proof("dev", SHA, "cloud_demo", production=True)
    assert "/actions/runs/123/attempts/2/jobs" in requests


def test_successful_job_from_another_attempt_is_not_evidence(monkeypatch):
    evidence_api(monkeypatch, job_attempt=2)
    with pytest.raises(ValueError, match="Evidence job"):
        ci.release_proof("dev", SHA, "cloud_demo", production=True)
