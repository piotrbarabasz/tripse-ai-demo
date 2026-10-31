"""Read-only React endpoints preserve stored heads/snapshots/history under existing guards."""
from hashlib import sha256
import pytest
from fastapi.testclient import TestClient
from app.document_studio.repository import JsonRepository
from app.main import create_app
from tests.react_document_fixtures import seed_documents
from tests.test_cloud_demo import cloud_demo


def snapshot(root):
    return {str(path.relative_to(root)): sha256(path.read_bytes()).hexdigest() for path in root.rglob("*.json")}


def test_local_catalog_pages_metadata_history_and_previews_do_not_change_documents(tmp_path):
    root = tmp_path / "documents"
    seed_documents(JsonRepository(root, tmp_path / "empty-fixtures"))
    before = snapshot(root)
    with TestClient(create_app(tmp_path / "jobs.sqlite3", document_data_path=root),
                    base_url="http://localhost", client=("127.0.0.1", 1)) as client:
        templates = client.get("/api/document-studio/templates").json()
        assert len(templates) == 8 and all("description" in template for template in templates)
        first = client.get("/api/document-studio/library?sort=title&direction=asc&limit=25").json()
        second = client.get("/api/document-studio/library?sort=title&direction=asc&limit=25&offset=25").json()
        assert first["total"] == second["total"] == 27
        assert len(first["items"]) == 25 and first["has_more"]
        assert len(second["items"]) == 2 and not second["has_more"]
        assert all("trip_snapshot" not in item and "pilot_data" not in item for item in first["items"])
        rows = client.get("/api/document-studio/library/react-qa-00/revisions").json()
        assert [row["revision"] for row in rows] == [2, 1]
        assert client.get("/api/document-studio/library/react-qa-00/revisions/1/preview").headers["content-type"].startswith("text/html")
        assert client.get("/api/document-studio/drafts/react-qa-00/preview").status_code == 200
        assert client.get("/api/document-studio/library?archived=only").json()["total"] == 1
        assert client.get("/api/document-studio/library?search=QA%2000").json()["total"] == 1
        assert client.get("/api/document-studio/library/missing/revisions").status_code == 404
    assert snapshot(root) == before


@pytest.mark.parametrize("identity,can_edit", [("editor", True), ("reader", False)])
def test_cloud_read_contracts_preserve_data_and_capability_boundary(cloud_demo, identity, can_edit):
    seed_documents(cloud_demo.components().repository, count=9)
    before = dict(cloud_demo.bucket.objects)
    with cloud_demo.client(identity) as client:
        assert client.get("/api/document-studio/access").json() == {"can_edit": can_edit}
        for path in ("/api/document-studio/templates", "/api/document-studio/library", "/api/document-studio/library/react-qa-00/revisions", "/api/document-studio/library/react-qa-00/revisions/1/preview"):
            response = client.get(path)
            assert response.status_code == 200
            assert response.headers["cache-control"] == "private, no-store"
            assert response.headers["x-frame-options"] == "DENY"
    assert cloud_demo.bucket.objects == before
