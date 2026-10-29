"""Ground Truth content, active catalogue, create-only seed, snapshots and both stores."""
import copy
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.document_studio.api import DraftUpdate
from app.document_studio.examples import (FIXTURES, build_example, catalog, copy_example,
    seed, obsolete_inventory, recipes)
from app.document_studio.models import DocumentDraft, RouteSummary, DayLogistics
from app.document_studio.repository import JsonRepository
from app.document_studio.cloud_storage import GCSRepository
from app.document_studio.service import DocumentService
from app.document_studio.rendering.sections import render_document, document_issues
from app.document_studio.assets import AssetStore
from tests.test_cloud_demo import FakeBucket, cloud_demo
from tests.test_document_studio import client_for


@pytest.fixture(params=['json', 'gcs'])
def store(request, tmp_path, monkeypatch):
    monkeypatch.delenv('DOCUMENT_STUDIO_FIXTURES_PATH', raising=False)
    repo = JsonRepository(tmp_path/'documents') if request.param == 'json' else GCSRepository(FakeBucket())
    repo.initialize()
    return repo


@pytest.mark.parametrize('identifier', [f'GT-DEMO-{i:02}' for i in range(1,10)])
def test_each_example_content_save_revision_reopen_independence(store, identifier):
    original = build_example(identifier)
    assert original == build_example(identifier)  # stable IDs and timestamps
    assert original.data_origin == 'demo' and original.demo_example
    assert original.document_status == 'draft'
    assert original.template_version == '0.5.0'
    assert all(s.visible for s in original.sections)
    html = render_document(original, AssetStore(store))
    assert 'PRZYKŁAD DEMO — DANE FIKCYJNE' in html
    assert original.title in html
    assert all(s.title in html for s in original.sections if s.role not in {'cover','collection'})
    assert not any(i.severity == 'error' for i in document_issues(original, AssetStore(store)))
    for token in ('reservation_pin','access_code','PRIVATE_MARKER','Lorem ipsum','Przykładowa atrakcja'):
        assert token not in html
    key = uuid4()
    saved = copy_example(store, identifier, key)
    assert copy_example(store, identifier, key) == saved
    assert saved.document_id != original.document_id and saved.revision == 1
    body = DraftUpdate(revision=1,title=saved.title,sections=copy.deepcopy(saved.sections))
    body.sections[0].body = 'Żółć — treść zmieniona wyłącznie w kopii'
    edited = DocumentService(store).update_draft(saved.document_id,body)
    assert edited.revision == 2
    assert store.get('drafts',saved.document_id) == edited
    assert store.get_revision(saved.document_id,1) == saved
    assert build_example(identifier) == original
    assert 'Żółć — treść' in render_document(edited,AssetStore(store))
    source = original.trip_snapshot or original.campaign_snapshot
    kind = 'trips' if original.trip_snapshot else 'campaigns'
    source_id = source.trip_id if original.trip_snapshot else source.campaign_id
    changed = store.get(kind,source_id);changed.title = 'Zmienione źródło'
    store.save(kind,changed)
    assert store.get('drafts',saved.document_id) == edited
    assert build_example(identifier) == original


def test_active_sources_and_manifest_are_exactly_versioned(tmp_path, monkeypatch):
    monkeypatch.delenv('DOCUMENT_STUDIO_FIXTURES_PATH',raising=False)
    repo = JsonRepository(tmp_path/'read-only')
    assert len(repo.list('trips')) == 5 and len(repo.list('campaigns')) == 2
    assert all(t.trip_id.startswith('gt-v1-') for t in repo.list('trips'))
    assert len(catalog()) == 9 and len({r['template_id'] for r in catalog()}) == 8
    assert len({r['source_id'] for r in catalog()[:7]}) == 5
    assert not repo.root.exists()
    for old in ['trips/demo-iceland.json','trips/demo-canada.json','trips/demo-norway.json','campaigns/demo-northern-journeys.json','document-presets/iceland.json']:
        assert not (FIXTURES.parent / old).exists()


def test_create_only_seed_partial_retry_conflict_preserved(store):
    before = seed(store)
    assert sum(r['status']=='would_create' for r in before)==9
    assert not store.list('drafts')
    first = seed(store,apply=True)
    assert sum(r['status']=='created' for r in first)==9
    assert all(r['status']=='verified' for r in seed(store,apply=True))
    doc=store.get('drafts','gt-demo-01');doc.title='Manually edited canonical collision'
    doc=store.save('drafts',doc)
    assert any(r['id']=='gt-demo-01' and r['status']=='conflict_preserved' for r in seed(store,apply=True))
    assert store.get('drafts',doc.document_id)==doc
    assert store.get_revision(doc.document_id,1).title != doc.title
    assert len(store.list('drafts'))==9
    # A partial run with one immutable record can safely resume.
    all_records=recipes()
    assert len(all_records)==9


def test_operations_metrics_knowledge_and_variant_semantics():
    selfguide = build_example('GT-DEMO-02')
    assert selfguide.offer_details.route_summary.start=='Vancouver'
    assert selfguide.offer_details.route_summary.drive_km is None
    assert 'bez pilota' in selfguide.offer_details.self_arrangements.lower()
    school = build_example('GT-DEMO-03')
    assert {g.pillar for g in school.offer_details.goals}=={'education','nature','integration'}
    assert all(g.day_id and g.stop_id for g in school.offer_details.goals)
    incentive = build_example('GT-DEMO-04')
    assert incentive.offer_details.group_size==18 and incentive.offer_details.hotel.status=='proposed'
    pilot=build_example('GT-DEMO-06')
    assert len({e.travel_group for e in pilot.pilot_data.flights})==2
    assert all(e.status!='confirmed' and not e.booking_reference for group in ('flights','transfers','accommodations','activity_bookings','schedule','open_items') for e in getattr(pilot.pilot_data,group))
    assert len([e for e in pilot.pilot_data.schedule if e.day_id=='roadtrip-day-3'])==10
    logs=[s.logistics for s in pilot.sections if s.logistics]
    assert any(l.drive_km is None for l in logs) and any(l.drive_km==210 for l in logs)
    assert all(l.verification_status!='verified' for l in logs)
    knowledge=build_example('GT-DEMO-07')
    assert knowledge.pilot_data is None
    assert all(s.knowledge.verification_status=='unverified' and all(src.checked_on for src in s.knowledge.sources) for s in knowledge.sections if s.knowledge)
    a,b=build_example('GT-DEMO-08'),build_example('GT-DEMO-09')
    assert a.campaign_snapshot.campaign_id != b.campaign_snapshot.campaign_id
    assert a.layout_variant=='new_trips' and b.layout_variant=='theme_collection'
    assert all(i.publication_status=='draft' and i.leader is None for d in (a,b) for i in d.campaign_snapshot.items)


@pytest.mark.parametrize('model',[RouteSummary,DayLogistics])
def test_verified_route_requires_evidence_and_unknown_is_not_zero(model):
    assert model().drive_km is None
    with pytest.raises(ValidationError):model(verification_status='verified')
    with pytest.raises(ValidationError):model(drive_km=-1)


def test_partial_seed_resumes_without_duplicate_or_overwrite(store):
    first=build_example('GT-DEMO-01')
    store.save('drafts',first,create=True)
    report=seed(store,apply=True)
    assert sum(r['status']=='created' for r in report)==8
    assert store.get('drafts',first.document_id)==first
    assert all(r['status']=='verified' for r in seed(store))


def test_no_seed_at_startup_catalog_get_is_readonly_copy_and_api_guards(tmp_path, monkeypatch):
    monkeypatch.delenv('DOCUMENT_STUDIO_FIXTURES_PATH',raising=False)
    with client_for(tmp_path) as client:
        assert client.get('/api/document-studio/drafts').json()==[]
        assert len(client.get('/api/document-studio/examples').json())==9
        for i in range(1,10):
            assert client.get(f'/api/document-studio/examples/GT-DEMO-{i:02}/preview').status_code==200
        assert client.get('/api/document-studio/drafts').json()==[]
        op={'operation_id':str(uuid4())}
        first=client.post('/api/document-studio/examples/GT-DEMO-02/copy',json=op)
        assert first.status_code==201,first.text
        assert client.post('/api/document-studio/examples/GT-DEMO-02/copy',json=op).json()==first.json()
        assert client.post('/api/document-studio/examples/missing/copy',json=op).status_code==404
        assert client.post('/api/document-studio/examples/GT-DEMO-02/copy',json=op,headers={'Origin':'https://evil.invalid'}).status_code==403
        assert client.put('/api/document-studio/drafts/gt-demo-02',json={'revision':1,'title':'Mutation'}).status_code==422
        assert client.get('/api/document-studio/examples/GT-DEMO-01/preview?output_format=social').status_code==422
        old=client.post('/api/document-studio/drafts',json={'template_id':'offer.private','source_type':'trip','source_id':'gt-v1-iceland','demo_example':True})
        assert old.status_code==422


def test_cloud_reader_cannot_copy_and_editor_copy_is_audited(cloud_demo):
    op={'operation_id':str(uuid4())}
    with cloud_demo.client('reader') as client:
        assert client.get('/api/document-studio/examples').status_code==200
        assert client.post('/api/document-studio/examples/GT-DEMO-01/copy',json=op).status_code==403
    with cloud_demo.client() as client:
        copied=client.post('/api/document-studio/examples/GT-DEMO-01/copy',json=op)
        assert copied.status_code==201,copied.text
        assert copied.json()['created_by']



def test_obsolete_report_preserves_business_unknown_drafts_and_history(store):
    legacy=build_example('GT-DEMO-01').trip_snapshot.model_copy(deep=True)
    legacy.trip_id='demo-iceland';legacy.data_origin='business'
    store.save('trips',legacy,create=True)
    doc=copy_example(store,'GT-DEMO-01',uuid4())
    before=store.get('trips',legacy.trip_id)
    report=obsolete_inventory(store)
    assert any(r['id']==legacy.trip_id and r['status']=='preserve_review_required' for r in report)
    assert any(r['id']==doc.document_id and r['status']=='preserve_snapshot_and_history' for r in report)
    assert store.get('trips',legacy.trip_id)==before and store.get('drafts',doc.document_id)==doc
