"""Versioned, read-only recipes. GET builds snapshots without writing any storage."""
import json
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from uuid import NAMESPACE_URL, uuid5

from app.document_studio.models import DocumentDraft, now
from app.document_studio.repository import JsonRepository, ConflictError

FIXTURES = Path(__file__).resolve().parents[2] / "demo-fixtures" / "gt-v1"
LEGACY_IDS = {"trips": ["demo-iceland", "demo-canada", "demo-norway"],
              "campaigns": ["demo-northern-journeys"]}


def recipes():
    return json.loads((FIXTURES / "examples.json").read_text(encoding="utf-8"))


def recipe(identifier):
    return next((r for r in recipes() if r["example_id"] == identifier), None)


def protect_canonical(identifier):
    if identifier in {r["document_id"] for r in recipes()}:
        raise ValueError("Chroniony przykład DEMO. Utwórz kopię do edycji.")


def build_example(identifier, repository=None):
    from app.document_studio.service import DocumentService
    spec = recipe(identifier)
    if spec is None:
        raise KeyError(identifier)
    # Never read overlay sources when presenting the canonical example.
    sources = repository or JsonRepository(root=FIXTURES / "_no_overlays", fixtures=FIXTURES)
    request = SimpleNamespace(template_id=spec["template_id"], source_type=spec["source_type"],
        source_id=spec["source_id"], layout_variant=spec["layout_variant"],
        title=spec["title"], editorial_notes="Materiał syntetyczny; wymaga przeglądu TRIPSE.")
    draft = DocumentService(sources).create_draft(request, persist=False)
    data = draft.model_dump(mode="json")
    data.update(spec["fields"])
    data.update(document_id=spec["document_id"], demo_example=True, data_origin="demo",
        created_at="2026-10-28T00:00:00Z", updated_at="2026-10-28T00:00:00Z")
    # Role/day references are portable across deterministic section IDs.
    for index, section in enumerate(data["sections"]):
        section["section_id"] = uuid5(NAMESPACE_URL, f"gt-v1:{identifier}:{index}").hex
        patch = spec.get("section_fields", {}).get(section["role"], {})
        section.update(patch)
    return DocumentDraft.model_validate(data)


def catalog():
    result = []
    for spec in recipes():
        draft = build_example(spec["example_id"])
        result.append({k: spec[k] for k in ("example_id", "document_id", "template_id", "layout_variant", "source_type", "source_id", "title")} | {
            "section_count": len(draft.sections), "seed_status": "canonical_recipe", "data_origin": "demo"})
    return result


def copy_example(repository, identifier, operation_id, actor=None):
    canonical = build_example(identifier)
    copy_id = uuid5(NAMESPACE_URL, f"tripse-gt-copy:{identifier}:{operation_id}").hex
    try:
        existing = repository.get("drafts", copy_id)
        if existing.duplicated_from_document_id != canonical.document_id:
            raise ConflictError("Konflikt identyfikatora kopii")
        return existing
    except KeyError:
        pass
    copy = canonical.model_copy(deep=True)
    copy.document_id, copy.title = copy_id, canonical.title[:192] + " — kopia"
    copy.duplicated_from_document_id = canonical.document_id
    copy.created_at = copy.updated_at = now()
    copy.created_by = copy.updated_by = actor
    try:
        return repository.save("drafts", copy, create=True)
    except ConflictError:
        existing = repository.get("drafts", copy_id)
        if existing.duplicated_from_document_id != canonical.document_id:
            raise
        return existing


def comparable(value):
    return value.model_dump(mode="json", exclude={"created_at", "updated_at"})


def seed(repository, *, apply=False):
    """Create-only; independently resumable records. Every mismatch is a conflict."""
    report = []
    for kind in ("trips", "campaigns"):
        for path in sorted((FIXTURES / kind).glob("*.json")):
            from app.document_studio.repository import MODELS
            value = MODELS[kind][0].model_validate_json(path.read_bytes())
            report.append(_seed_one(repository, kind, path.stem, value, apply))
    for spec in recipes():
        value = build_example(spec["example_id"])
        report.append(_seed_one(repository, "drafts", value.document_id, value, apply))
    return report


def _seed_one(repository, kind, identifier, value, apply):
    try:
        existing = repository.get(kind, identifier)
        status = "verified" if comparable(existing) == comparable(value) else "conflict_preserved"
    except KeyError:
        status = "created" if apply else "would_create"
        if apply:
            try:
                repository.save(kind, value, create=True)
            except ConflictError:
                return _seed_one(repository, kind, identifier, value, False)
    return {"kind": kind, "id": identifier, "status": status}


def obsolete_inventory(repository):
    """No delete: origin/prefix cannot establish ownership, even at revision one."""
    result = []
    retired = json.loads((FIXTURES / "retired.json").read_text(encoding="utf-8"))
    for kind, identifiers in LEGACY_IDS.items():
        for identifier in identifiers:
            try:
                value = repository.get(kind, identifier)
                fingerprint = sha256(json.dumps(value.model_dump(mode="json", exclude={"updated_at", "revision"}),
                    sort_keys=True, ensure_ascii=True).encode()).hexdigest()
                matches = any(r["kind"] == kind and r["id"] == identifier and r["content_sha256"] == fingerprint for r in retired)
                classification = ("business_preserve" if value.data_origin == "business" else
                    "unknown_preserve" if value.data_origin == "unknown" else
                    "retired_fixture_content_equivalent" if matches else "edited_or_unattributed_demo_preserve")
                result.append({"kind": kind, "id": identifier, "status": "preserve_review_required",
                    "classification": classification, "matches_retired_content": matches,
                    "revision": value.revision, "data_origin": value.data_origin,
                    "reason": "Exact retired fixture ID; persisted content may be user-edited. No deletion authorized by provenance alone."})
            except KeyError:
                result.append({"kind": kind, "id": identifier, "status": "absent_in_selected_repository"})
    for draft in repository.list("drafts"):
        source = draft.trip_snapshot or draft.campaign_snapshot
        source_id = source.trip_id if draft.trip_snapshot else source.campaign_id
        if source_id in sum(LEGACY_IDS.values(), []) or draft.demo_example:
            result.append({"kind": "drafts", "id": draft.document_id, "status": "preserve_snapshot_and_history",
                           "reason": "Saved document/reference, regardless of origin or ID prefix"})
    return result
