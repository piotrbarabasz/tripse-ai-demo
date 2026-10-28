"""DOC-UX-002: additive source metadata, snapshots and legacy clients."""
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.document_studio.models import Trip, Campaign, DocumentDraft
from app.document_studio.api import DraftRequest
from app.document_studio.repository import JsonRepository
from app.document_studio.service import DocumentService
from app.document_studio.library import DocumentLibrary, LibraryMutation
from tests.test_cloud_demo import cloud_demo
from tests.test_document_studio import client_for


@pytest.fixture(params=['json', 'gcs'])
def source_client(request, tmp_path):
    return client_for(tmp_path) if request.param == 'json' else request.getfixturevalue('cloud_demo').client()


@pytest.mark.parametrize('categories', [['private'], ['self_guide','group'], ['school','incentive','other'], ['private','private']])
def test_categories_round_trip_and_legacy_put_preserves_them(source_client, categories):
    with source_client as client:
        created = client.post('/api/document-studio/trips', json={'title':'Źródło — żółć', 'categories':categories, 'data_origin':'business'}).json()
        assert created['categories'] == list(dict.fromkeys(categories))
        path = '/api/document-studio/trips/' + created['trip_id']
        legacy = {k:v for k,v in created.items() if k not in {'categories','data_origin'}}
        legacy['title'] = 'Edytowane przez starego klienta'
        updated = client.put(path, json=legacy)
        assert updated.status_code == 200
        assert updated.json()['categories'] == created['categories']
        assert updated.json()['data_origin'] == 'business' and updated.json()['revision'] == 2
        assert client.put(path, json=legacy).status_code == 409
        value = updated.json();value['categories'] = []
        assert client.put(path, json=value).json()['categories'] == []
        assert client.get(path).json()['revision'] == 3


@pytest.mark.parametrize('field,value', [('categories',['pilot']),('categories',['marketing']),('categories',['invalid']),('data_origin','verified')])
def test_unknown_categories_and_origins_rejected(source_client, field, value):
    with source_client as client:
        assert client.post('/api/document-studio/trips', json={'title':'Invalid',field:value}).status_code == 422


def test_legacy_models_and_explicit_demo_fixtures():
    assert Trip(title='Legacy').categories == []
    assert Trip(title='Legacy').data_origin == 'unknown'
    assert Campaign(title='Legacy', items=[{'trip_id':'legacy'}]).data_origin == 'unknown'
    repo = JsonRepository()
    for kind in ('trips','campaigns'):
        for path in (repo.fixtures/kind).glob('*.json'):
            model = Trip if kind=='trips' else Campaign
            value = model.model_validate_json(path.read_bytes())
            assert value.data_origin == 'demo'
            if kind=='trips':assert value.categories == []  # no country/name inference


@pytest.mark.parametrize('origin', ['business','demo','synthetic_test','unknown'])
def test_source_origin_propagates_but_saved_snapshots_stay_independent(source_client, origin):
    with source_client as client:
        trip = client.post('/api/document-studio/trips', json={'title':'Origin source', 'categories':['group'], 'data_origin':origin}).json()
        campaign = client.post('/api/document-studio/campaigns', json={'title':'Origin campaign', 'data_origin':origin, 'items':[{'trip_id':trip['trip_id']}]}).json()
        templates = client.get('/api/document-studio/templates').json()
        drafts = []
        for template in templates:
            for variant in template['layout_variants']:
                response = client.post('/api/document-studio/drafts', json={'template_id':template['template_id'],
                    'source_type':template['source_type'], 'source_id':campaign['campaign_id'] if template['source_type']=='campaign' else trip['trip_id'], 'layout_variant':variant})
                assert response.status_code == 201, response.text
                draft = response.json();drafts.append(draft)
                assert draft['data_origin'] == origin
                snapshot = draft['trip_snapshot'] or draft['campaign_trip_snapshots'][0]
                assert snapshot['categories'] == ['group'] and snapshot['data_origin'] == origin
        trip.update(categories=['private','school'],data_origin='business',title='Classified source')
        assert client.put('/api/document-studio/trips/'+trip['trip_id'], json=trip).status_code == 200
        for draft in drafts:
            assert client.get('/api/document-studio/drafts/'+draft['document_id']).json() == draft
        legacy_campaign = {k:v for k,v in campaign.items() if k!='data_origin'}
        saved = client.put('/api/document-studio/campaigns/'+campaign['campaign_id'], json=legacy_campaign)
        assert saved.status_code == 200 and saved.json()['data_origin'] == origin
        copied = client.post('/api/document-studio/library/'+drafts[0]['document_id']+'/duplicate', json={'revision':1,'operation_id':str(uuid4())}).json()
        assert copied['data_origin'] == origin and copied['trip_snapshot'] == drafts[0]['trip_snapshot']
        legacy = dict(drafts[0]);legacy.pop('data_origin')
        assert DocumentDraft.model_validate(legacy).data_origin == 'unknown'


def test_legacy_classification_report_is_read_only_and_requires_structural_evidence(tmp_path):
    from scripts.classify_source_origins import candidates
    repo = JsonRepository(tmp_path/'documents', fixtures=tmp_path/'no-fixtures')
    valid = Trip(title='CLOUD-PARITY synthetic DEV old', duration_days=15, days=[{
        'day_number':i,'title':f'Synthetic day {i}','internal_notes':'PARITY_PRIVATE_OPS'} for i in range(1,16)])
    named_only = Trip(title='CLOUD-PARITY synthetic DEV real-business-name')
    for trip in (valid,named_only):repo.save('trips',trip,create=True)
    campaign = repo.save('campaigns',Campaign(title=valid.title,items=[{'trip_id':valid.trip_id}]),create=True)
    draft = DocumentService(repo).create_draft(DraftRequest(template_id='pilot.basic',source_type='trip',source_id=valid.trip_id))
    before = {str(p):p.read_bytes() for p in repo.root.rglob('*') if p.is_file()}
    report = candidates(repo)
    assert report['dry_run'] and {r['id'] for r in report['candidates']} == {valid.trip_id,campaign.campaign_id}
    assert all(r['requires_operator_review'] for r in report['candidates'])
    assert before == {str(p):p.read_bytes() for p in repo.root.rglob('*') if p.is_file()}
    assert repo.get('drafts',draft.document_id) == draft


def test_parity_creation_tags_entire_document_scenario_without_live_calls(tmp_path, monkeypatch):
    from scripts.gcp.parity_smoke import Acceptance
    acceptance = Acceptance('http://localhost','unused')
    with client_for(tmp_path) as client:
        def call(path, *, method='GET', payload=None, expected=200, **kwargs):
            if path.startswith('/api/document-studio/'):
                response = client.request(method,path,json=payload,content=kwargs.get('raw'),headers=kwargs.get('headers'))
                assert response.status_code == expected, response.text
                return response.json() if response.headers.get('content-type','').startswith('application/json') else response.content
            if path=='/api/demo/scenarios':return {'scenarios':[{'text':'mock'}]}
            if path.startswith('/api/demo/conversations/'):return {'messages':[{},{}]}
            if method=='POST':return {'trip_id':'synthetic-job','status':'duplicate'}
            if path=='/api/viewer/invalid':return b''
            pytest.fail('Unexpected external path: '+path)
        monkeypatch.setattr(acceptance,'call',call)
        monkeypatch.setattr(acceptance,'wait',lambda *args,**kwargs:None)
        acceptance.writes()
        for kind in ('trips','campaigns','drafts'):
            rows = client.get('/api/document-studio/'+kind).json()
            synthetic = [r for r in rows if r.get('title','').startswith('CLOUD-PARITY')]
            assert synthetic and all(r['data_origin']=='synthetic_test' for r in synthetic)
