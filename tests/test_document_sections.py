"""All template instances, compatibility, safety and completeness contracts."""
import copy
import json
from pathlib import Path

import pytest

from tests.test_document_studio import client_for
from app.document_studio.models import DocumentDraft, DocumentSection
from app.document_studio.templates import TEMPLATES


def create(client, template, source="demo-canada", variant="standard"):
    response = client.post('/api/document-studio/drafts', json={
        'template_id': template, 'source_type': 'campaign' if template == 'marketing.collection' else 'trip',
        'source_id': 'demo-northern-journeys' if template == 'marketing.collection' else source,
        'layout_variant': variant})
    assert response.status_code == 201, response.text
    return response.json()


def update(draft):
    keys = ('revision', 'title', 'sections', 'offer_data', 'offer_details', 'pilot_data', 'campaign_snapshot', 'day_overrides')
    return {key: draft[key] for key in keys}


@pytest.mark.parametrize('template', [key for key in TEMPLATES if key != 'marketing.collection'])
@pytest.mark.parametrize('days', [2, 10, 15])
def test_all_trip_templates_sections_persistence_independence_and_missing_data(tmp_path, template, days):
    with client_for(tmp_path) as client:
        trip = client.post('/api/document-studio/trips', json={'title': 'Żółte góry — szkic', 'duration_days': days,
            'days': [{'day_number': i+1, 'title': f'Dzień {i+1}', 'internal_notes': 'PRIVATE_NOTES',
                      'stops': [{'name': 'Atrakcja programu', 'source': 'PRIVATE_RESERVATION_SOURCE'}]} for i in range(days)]}).json()
        draft = create(client, template, trip['trip_id'])
        assert draft['sections'] and all(s['section_id'] for s in draft['sections'])
        assert draft['template_version'] == '0.4.0'
        assert draft['trip_snapshot']['start_date'] is None
        another = create(client, template, trip['trip_id'])
        body = update(draft)
        custom = DocumentSection(title='Własna sekcja — żółć', body='Własne informacje. '+('Długi opis. '*300), order=0).model_dump(mode='json')
        body['sections'].insert(0, custom)
        for index, section in enumerate(body['sections']): section['order'] = index
        body['sections'][1]['visible'] = False
        url = '/api/document-studio/drafts/'+draft['document_id']
        saved = client.put(url, json=body)
        assert saved.status_code == 200, saved.text
        assert saved.json()['revision'] == 2
        assert client.put(url, json=body).status_code == 409
        assert client.get('/api/document-studio/trips/'+trip['trip_id']).json() == trip
        assert client.get('/api/document-studio/drafts/'+another['document_id']).json() == another
        html = client.get(url+'/preview')
        assert html.status_code == 200, html.text
        assert 'DOKUMENT ROBOCZY' in html.text and 'Własna sekcja' in html.text
        assert 'Termin do ustalenia' in html.text or 'Do ustalenia' in html.text
        if template.startswith('offer.'):
            assert 'PRIVATE_NOTES' not in json.dumps(saved.json())
            assert 'PRIVATE_RESERVATION_SOURCE' not in json.dumps(saved.json())
        if template == 'offer.self_guide': assert 'BEZ PILOTA NA MIEJSCU' in html.text
        if template == 'offer.school': assert 'EDUKACJA / PRZYRODA / INTEGRACJA' in html.text
        if template == 'pilot.advanced':
            assert all(s['logistics']['drive_km'] is None for s in draft['sections'] if s['kind'] == 'logistics')
        if template == 'pilot.knowledge':
            assert len([s for s in draft['sections'] if s['kind'] == 'knowledge']) == days*3
            assert 'NIEZWERYFIKOWANE' in html.text
    with client_for(tmp_path) as restarted:
        reopened = restarted.get(url).json()
        assert reopened['sections'][0]['body'] == custom['body']
        assert reopened['sections'][1]['visible'] is False


@pytest.mark.parametrize('variant', ['new_trips', 'theme_collection'])
def test_marketing_draft_edits_are_snapshot_local_and_use_both_formats(tmp_path, variant):
    with client_for(tmp_path) as client:
        original = client.get('/api/document-studio/campaigns/demo-northern-journeys').json()
        draft = create(client, 'marketing.collection', variant=variant)
        body = update(draft)
        body['campaign_snapshot']['items'].reverse()
        body['campaign_snapshot']['leader'] = 'Prowadzący do uzgodnienia'
        body['campaign_snapshot']['items'][0]['leader'] = 'Pilot do uzgodnienia'
        body['sections'].append(DocumentSection(title='Dodatkowe korzyści', kind='list', items=['Żółć / test'], order=9).model_dump(mode='json'))
        url = '/api/document-studio/drafts/'+draft['document_id']
        r = client.put(url,json=body)
        assert r.status_code == 200, r.text
        assert client.get('/api/document-studio/campaigns/demo-northern-journeys').json() == original
        for format in ('a4', 'social'):
            html = client.get(url+'/preview?output_format='+format)
            assert html.status_code == 200 and 'Dodatkowe korzyści' in html.text
            assert 'Prowadzący do uzgodnienia' in html.text and 'Pilot do uzgodnienia' in html.text
            assert f'format-{format}' in html.text
        body['revision'] = 2
        body['campaign_snapshot']['items'].pop()
        assert client.put(url, json=body).status_code == 200


def test_required_sections_cannot_be_deleted_hidden_or_reset_to_legacy(tmp_path):
    with client_for(tmp_path) as client:
        draft = create(client, 'offer.private')
        draft['offer_data'].update(concept_only=True, cta='Kontakt do uzupełnienia')
        for mode in ('hidden', 'deleted', 'wrong_kind'):
            value = copy.deepcopy(draft)
            if mode == 'deleted': value['sections'] = []
            elif mode == 'hidden': value['sections'][0]['visible'] = False
            else: value['sections'][0]['kind'] = 'text'
            issues = client.post('/api/document-studio/trip-documents/validate', json={'draft': value}).json()
            assert any(i['severity'] == 'error' and i['field_path'] == 'sections' for i in issues)
            preview = client.post('/api/document-studio/trip-documents/preview', json={'draft': value})
            assert 'data-valid="false"' in preview.text
        body = update(draft); body['sections'] = None
        assert client.put('/api/document-studio/drafts/'+draft['document_id'], json=body).status_code == 422


def test_typed_sections_validate_sources_program_and_html_escape(tmp_path):
    with client_for(tmp_path) as client:
        draft = create(client,'pilot.knowledge')
        knowledge = next(s for s in draft['sections'] if s['knowledge'])
        knowledge['knowledge']['verification_status'] = 'verified'
        assert client.post('/api/document-studio/trip-documents/preview',json={'draft':draft}).status_code == 422
        knowledge['knowledge']['sources']=[{'reference':'Dokładne źródło — strona 10', 'checked_on':'2026-10-28'}]
        knowledge['body']='<script>alert("x")</script>'
        r=client.post('/api/document-studio/trip-documents/preview',json={'draft':draft})
        assert r.status_code==200 and '&lt;script&gt;' in r.text and '<script>alert' not in r.text
        knowledge['knowledge']['stop_ids']=['outside-program']
        assert client.post('/api/document-studio/trip-documents/preview',json={'draft':draft}).status_code==422
        with pytest.raises(ValueError): DocumentSection(kind='table',title='Tabela',columns=['A','B'],rows=[['Niepełny wiersz']])
        private=create(client,'offer.school');private['pilot_data']={'leader':'FORBIDDEN'}
        assert client.post('/api/document-studio/trip-documents/preview',json={'draft':private}).status_code==422
        advanced=create(client,'pilot.advanced')
        day_id=advanced['trip_snapshot']['days'][0]['day_id']
        body=update(advanced)
        body['pilot_data']['schedule']=[
            {'title':'LATER_SCHEDULE','day_id':day_id,'start_local':'2027-06-01T15:00:00','time_zone':'America/Vancouver'},
            {'title':'EARLIER_SCHEDULE','day_id':day_id,'start_local':'2027-06-01T09:00:00','time_zone':'America/Vancouver'}]
        log=next(s['logistics'] for s in body['sections'] if s['kind']=='logistics')
        log.update(date='2027-06-01',walk_km=0,drive_km=None,plan_b='Alternatywa do uzgodnienia')
        url='/api/document-studio/drafts/'+advanced['document_id']
        saved=client.put(url,json=body)
        assert saved.status_code==200,saved.text
        html=client.get(url+'/preview').text
        content=html.split('<div id="source-blocks" hidden>',1)[1]
        assert content.index('EARLIER_SCHEDULE')<content.index('LATER_SCHEDULE')
        assert 'America/Vancouver' in html and 'Alternatywa do uzgodnienia' in html
        assert next(s['logistics'] for s in saved.json()['sections'] if s['kind']=='logistics')['drive_km'] is None
        source=client.get('/api/document-studio/trips/demo-canada').json()
        source['days'][0]['title']='D'*200
        assert client.put('/api/document-studio/trips/demo-canada',json=source).status_code==200
        assert create(client,'pilot.advanced')['sections']


def test_legacy_draft_read_preview_and_additive_edit(tmp_path):
    with client_for(tmp_path) as client:
        draft=create(client,'offer.private')
        draft.pop('sections');draft.pop('offer_details');draft['template_version']='0.3.0'
        DocumentDraft.model_validate(draft)
        path=tmp_path/'documents'/'drafts'/(draft['document_id']+'.json')
        # client_for's repository lives under tmp_path / studio (inspect actual folder).
        matches=[path];assert path.exists()
        matches[0].write_text(json.dumps(draft),encoding='utf-8')
        url='/api/document-studio/drafts/'+draft['document_id']
        assert client.get(url).json()['sections'] is None
        assert client.get(url+'/preview').status_code==200
        initialized=client.post('/api/document-studio/trip-documents/initialize',json={'draft':client.get(url).json()}).json()
        assert initialized['sections'] and initialized['offer_details']
        assert client.put(url,json=update(initialized)).status_code==200


def test_cloud_section_assets_use_private_adapter_and_reader_write_denial(cloud_demo):
    import io
    from PIL import Image
    with cloud_demo.client() as client:
        photo = io.BytesIO(); Image.new('RGB',(8,8),'orange').save(photo,'PNG')
        uploaded = client.post('/api/document-studio/assets?filename=test.png&rights_confirmed=true',content=photo.getvalue(),headers={'content-type':'image/png'})
        assert uploaded.status_code == 201
        asset_id = uploaded.json()['asset_id']
        draft = create(client, 'offer.incentive')
        body = update(draft)
        body['sections'].append(DocumentSection(kind='gallery',title='Zdjęcia',images=[{'asset_id':asset_id}],order=99).model_dump(mode='json'))
        body['offer_details']['hotel']['photo_asset_ids']=[asset_id]
        url='/api/document-studio/drafts/'+draft['document_id']
        saved=client.put(url,json=body)
        assert saved.status_code==200,saved.text
        assert asset_id in client.get(url+'/preview').text
    with cloud_demo.client('reader') as client:
        assert client.put(url,json=update(saved.json())).status_code==403
    with cloud_demo.client(None) as client:
        assert client.get(url+'/preview').status_code==401
        assert client.get('/api/document-studio/assets/'+asset_id+'/content').status_code==401


# Reuse the existing private GCS/Firestore fixture, not a parallel cloud harness.
from tests.test_cloud_demo import cloud_demo
