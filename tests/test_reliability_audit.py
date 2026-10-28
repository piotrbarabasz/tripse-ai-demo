"""Adversarial reproductions for TRIPSE-QA-001; no external services."""
import io

import pytest
from PIL import Image

from app.document_studio.assets import AssetStore
from app.document_studio.cloud_storage import GCSRepository, GCSAssetBytes
from app.document_studio.repository import JsonRepository, StorageError
from tests.test_cloud_demo import FakeBucket, cloud_demo
from tests.test_document_library import create
from tests.test_document_studio import client_for
from app.document_studio.library import DocumentLibrary, StatusMutation, LibraryMutation
from uuid import uuid4
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier


@pytest.mark.parametrize('cloud', [False, True])
def test_ambiguous_asset_metadata_commit_keeps_referenced_bytes(tmp_path, monkeypatch, cloud):
    bucket = FakeBucket()
    repo = GCSRepository(bucket) if cloud else JsonRepository(tmp_path / 'documents')
    assets = AssetStore(repo, GCSAssetBytes(bucket) if cloud else None)
    original = repo.save

    def timeout_after_commit(*args, **kwargs):
        original(*args, **kwargs)
        raise StorageError('response lost after metadata committed')

    monkeypatch.setattr(repo, 'save', timeout_after_commit)
    image = io.BytesIO()
    Image.new('RGB', (12, 10), 'orange').save(image, 'PNG')
    with pytest.raises(StorageError):
        assets.upload(image.getvalue(), 'image/png', 'test.png', True)
    committed = repo.list('assets')
    assert len(committed) == 1
    metadata, content = assets.get(committed[0].asset_id)
    raw = content if cloud else content.read_bytes()
    with Image.open(io.BytesIO(raw)) as decoded:
        assert decoded.size == (12, 10)


def test_source_section_cannot_bind_to_dynamic_logistics_role(tmp_path):
    with client_for(tmp_path) as client:
        doc = client.post('/api/document-studio/drafts', json={
            'template_id': 'pilot.advanced', 'source_type': 'trip', 'source_id': 'demo-canada'}).json()
        section = next(s for s in doc['sections'] if s['kind'] == 'logistics')
        section['kind'], section['logistics'] = 'source', None
        response = client.post('/api/document-studio/trip-documents/preview', json={'draft': doc})
        assert response.status_code == 422
        response = client.put('/api/document-studio/drafts/' + doc['document_id'], json={
            'revision': 1, 'title': doc['title'], 'sections': doc['sections']})
        assert response.status_code == 422
        assert client.get('/api/document-studio/drafts/' + doc['document_id']).json()['revision'] == 1


def test_status_retry_with_changed_payload_is_not_reported_as_success(tmp_path):
    repo = JsonRepository(tmp_path / 'documents')
    doc = create(repo)
    library = DocumentLibrary(repo)
    operation = uuid4()
    first = StatusMutation(revision=1, operation_id=operation, document_status='ready')
    library.transition(doc.document_id, first, 'status')
    from app.document_studio.repository import ConflictError
    with pytest.raises(ConflictError):
        library.transition(doc.document_id, StatusMutation(revision=1, operation_id=operation,
            document_status='in_review'), 'status')


@pytest.fixture(params=['json', 'gcs'])
def audit_store(request, tmp_path):
    bucket = FakeBucket()
    factory = (lambda: JsonRepository(tmp_path / 'documents')) if request.param == 'json' else lambda: GCSRepository(bucket)
    return SimpleNamespace(repo=factory(), factory=factory, bucket=bucket, kind=request.param)


@pytest.mark.parametrize('kind', ['archive', 'restore', 'status', 'duplicate'])
def test_library_retry_after_lost_commit_response(audit_store, monkeypatch, kind):
    repo = audit_store.repo
    doc = create(repo)
    library = DocumentLibrary(repo)
    if kind == 'restore':
        doc = library.transition(doc.document_id, LibraryMutation(revision=1, operation_id=uuid4()), 'archive')
    mutation = (StatusMutation(revision=doc.revision, operation_id=uuid4(), document_status='ready')
                if kind == 'status' else LibraryMutation(revision=doc.revision, operation_id=uuid4()))
    original = repo.save
    def lost_response(*args, **kwargs):
        original(*args, **kwargs)
        raise StorageError('committed, response lost')
    monkeypatch.setattr(repo, 'save', lost_response)
    def execute():
        return library.duplicate(doc.document_id, mutation) if kind == 'duplicate' else library.transition(doc.document_id, mutation, kind)
    with pytest.raises(StorageError):
        execute()
    monkeypatch.setattr(repo, 'save', original)
    result = execute()
    assert execute() == result
    assert result.revision == (1 if kind == 'duplicate' else doc.revision + 1)
    assert len(repo.list_documents()) == (2 if kind == 'duplicate' else 1)
    assert repo.get_revision(doc.document_id, 1).title == doc.title


def test_two_repository_instances_race_one_winner(audit_store):
    repo = audit_store.repo
    doc = create(repo)
    barrier = Barrier(2)
    def edit(title):
        candidate = doc.model_copy(deep=True)
        candidate.title = title
        barrier.wait(timeout=5)
        from app.document_studio.repository import ConflictError
        try:
            return audit_store.factory().save('drafts', candidate).title
        except ConflictError:
            return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(edit, ['winner A', 'winner B']))
    assert results.count('conflict') == 1
    current = repo.get('drafts', doc.document_id)
    assert current.revision == 2 and current.title in results
    assert repo.get_revision(doc.document_id, 1) == doc
    assert [r.revision for r in repo.list_revisions(doc.document_id)] == [2, 1]


def test_corrupt_and_stale_local_cache_recovers(tmp_path):
    repo = JsonRepository(tmp_path / 'documents')
    doc = create(repo)
    path = repo._path(repo.root, 'drafts', doc.document_id)
    cache = repo._metadata_path(path)
    for raw in ('{bad json', '[]', '{"stamp":null}', '{}'):
        cache.write_text(raw, encoding='utf-8')
        assert repo.list_documents()[0].title == doc.title
    import json
    value = json.loads(cache.read_text(encoding='utf-8'))
    value['stamp'] = [0, 0, 0]
    value['document']['title'] = 'stale cached title'
    cache.write_text(json.dumps(value), encoding='utf-8')
    assert repo.list_documents()[0].title == doc.title


def test_legacy_lifecycle_without_invented_history(audit_store):
    repo = audit_store.repo
    doc = create(repo)
    raw = doc.model_dump(mode='json')
    for field in ('document_status', 'archived_at', 'created_by', 'updated_by',
                  'duplicated_from_document_id', 'last_library_operation', 'sections', 'offer_details'):
        raw.pop(field)
    import json
    if audit_store.kind == 'json':
        repo._path(repo.root, 'drafts', doc.document_id).write_text(json.dumps(raw), encoding='utf-8')
    else:
        name = repo._name('drafts', doc.document_id)
        repo.bucket.objects[name] = (json.dumps(raw).encode(), repo.bucket.objects[name][1])
        repo.bucket.metadata[name] = {}
    legacy = repo.get('drafts', doc.document_id)
    assert legacy.sections is None and legacy.created_by is None
    library = DocumentLibrary(repo)
    assert [r.revision for r in repo.list_revisions(doc.document_id)] == [1]
    copy = library.duplicate(doc.document_id, LibraryMutation(revision=1, operation_id=uuid4()))
    assert copy.sections is None and copy.trip_snapshot == legacy.trip_snapshot
    archived = library.transition(doc.document_id, LibraryMutation(revision=1, operation_id=uuid4()), 'archive')
    assert repo.get_revision(doc.document_id, 1) == legacy
    restored = library.transition(doc.document_id, LibraryMutation(revision=archived.revision, operation_id=uuid4()), 'restore')
    from app.document_studio.api import DraftUpdate
    from app.document_studio.service import DocumentService
    updated = DocumentService(repo).update_draft(doc.document_id, DraftUpdate(revision=restored.revision, title='Legacy edited'))
    assert updated.sections is None and updated.revision == 4


def test_all_library_mutations_and_history_enforce_cloud_boundaries(cloud_demo):
    with cloud_demo.client() as client:
        doc = client.post('/api/document-studio/drafts', json={'template_id':'pilot.basic', 'source_type':'trip', 'source_id':'demo-canada'}).json()
        identifier = doc['document_id']
        path = '/api/document-studio/library/' + identifier
        payload = {'revision':1, 'operation_id':str(uuid4())}
        for origin in ('https://attacker.invalid', 'null', ''):
            assert client.post(path+'/archive', json=payload, headers={'origin':origin}).status_code == 403
        assert client.get(path+'/revisions', headers={'host':'attacker.invalid'}).status_code == 400
    for identity, expected in [('reader',403), (None,401), ('stranger',403)]:
        with cloud_demo.client(identity) as client:
            for action in ('archive','restore','duplicate','status'):
                body = dict(payload, **({'document_status':'ready'} if action=='status' else {}))
                assert client.post(path+'/'+action, json=body).status_code == expected
            if identity != 'reader':
                for suffix in ('/revisions', '/revisions/1', '/revisions/1/preview'):
                    assert client.get(path+suffix).status_code == expected


def test_multiline_chunking_preserves_text_in_printable_blocks():
    from app.document_studio.rendering.trip_documents import chunks
    value = '\n'.join('Żółć ' + str(i) for i in range(160))
    parts = chunks(value)
    assert ''.join(parts) == value
    assert all(part.count('\n') <= 16 for part in parts)


@pytest.mark.parametrize('template,variant', [('offer.private','standard'), ('offer.self_guide','standard'),
    ('offer.school','standard'), ('offer.incentive','standard'), ('marketing.collection','new_trips'), ('marketing.collection','theme_collection')])
def test_manipulated_client_preview_does_not_render_internal_snapshot_fields(tmp_path, template, variant):
    with client_for(tmp_path) as client:
        doc = client.post('/api/document-studio/drafts', json={'template_id':template,
            'source_type':'campaign' if template=='marketing.collection' else 'trip',
            'source_id':'demo-northern-journeys' if template=='marketing.collection' else 'demo-canada',
            'layout_variant':variant}).json()
        snapshots = doc['campaign_trip_snapshots'] if doc['campaign_snapshot'] else [doc['trip_snapshot']]
        for trip in snapshots:
            trip['days'][0]['internal_notes'] = 'INTERNAL-SECRET-MUST-NOT-PRINT'
        doc['title'] = '<img src=x onerror=alert(1)> Żółć'
        response = client.post('/api/document-studio/trip-documents/preview', json={'draft':doc})
        assert response.status_code == 200
        assert 'INTERNAL-SECRET-MUST-NOT-PRINT' not in response.text
        assert '<img src=x' not in response.text and '&lt;img' in response.text
