"""Synthetic wire regression fixtures from real FastAPI routes, temporary data only."""
import argparse
import io
import json
from fastapi.testclient import TestClient
from PIL import Image
from scripts.export_openapi import ROOT, isolated_app

OUTPUT = ROOT / "docs/api/fixtures.json"


def fixture_text():
    with isolated_app() as app, TestClient(app, base_url="http://localhost", client=("127.0.0.1", 50000)) as client:
        def get(path):
            response = client.get(path)
            response.raise_for_status()
            return response.json()

        def post(path, **kwargs):
            response = client.post(path, **kwargs)
            response.raise_for_status()
            return response.json()

        accepted = post("/api/trips", json={"text": "Synthetic contract trip"})
        job = get(f"/api/trips/{accepted['trip_id']}")
        trip = post("/api/document-studio/trips", json={"trip_id": "synthetic-trip", "title": "Synthetic source"})
        draft = post("/api/document-studio/drafts", json={
            "document_id": "synthetic-draft", "template_id": "offer.private", "source_type": "trip", "source_id": trip["trip_id"],
        })
        operation = {"revision": draft["revision"], "operation_id": "00000000-0000-4000-8000-000000000002"}
        status = post("/api/document-studio/library/synthetic-draft/status", json={**operation, "document_status": "in_review"})
        duplicate = post("/api/document-studio/library/synthetic-draft/duplicate", json={**operation, "revision": status["revision"]})
        historical = get("/api/document-studio/library/synthetic-draft/revisions/1")
        conflict = client.put("/api/document-studio/drafts/synthetic-draft", json={"revision": 1, "title": "Stale write"})
        assert conflict.status_code == 409
        image = io.BytesIO()
        Image.new("RGB", (2, 2), "white").save(image, format="PNG")
        asset = post("/api/document-studio/assets?filename=synthetic.png&rights_confirmed=true", content=image.getvalue(), headers={"content-type": "image/png"})
        preview = client.get("/api/document-studio/drafts/synthetic-draft/preview")
        assert preview.status_code == 200 and preview.headers["content-type"].startswith("text/html")
        downloaded = client.get(f"/api/document-studio/assets/{asset['asset_id']}/content")
        assert downloaded.status_code == 200 and downloaded.headers["content-type"] == "image/png"
        values = dict(accepted=accepted, job=job, trip=trip, draft=draft, historical=historical,
                      status=status, duplicate=duplicate, asset=asset, access=get("/api/document-studio/access"),
                      templates=get("/api/document-studio/templates"), library=get("/api/document-studio/library"),
                      revisions=get("/api/document-studio/library/synthetic-draft/revisions"), health=get("/health"))

    # Normalize only random IDs/timestamps, never contract fields, nulls or arrays.
    section_ids = {section["section_id"]: f"synthetic-section-{index}" for index, section in enumerate(draft["sections"], 1)}

    def normalize(value):
        if isinstance(value, list):
            return [normalize(item) for item in value]
        if isinstance(value, dict):
            return {key: ("2026-10-31T00:00:00Z" if key in {"created_at", "updated_at"} else normalize(item)) for key, item in value.items()}
        if value == accepted["trip_id"]:
            return "00000000-0000-4000-8000-000000000001"
        if value == asset["asset_id"]:
            return "synthetic-asset"
        if isinstance(value, str) and value in section_ids:
            return section_ids[value]
        return value
    return json.dumps(normalize(values), ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = fixture_text()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != content:
            parser.exit(1, "Wire fixture drift: run python -m scripts.export_api_fixtures\n")
    else:
        OUTPUT.write_text(content, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
