from uuid import uuid4
from urllib.parse import urlsplit
import pytest
from fastapi.testclient import TestClient
from app.db import Database
from app.main import create_app
from app.demo import ChannelMessagingProvider
from app.demo_data import SCENARIOS, CASES, generate_demo
from app.planning_providers import PlanningError
from app.worker import process_ack, process_next, process_result

@pytest.mark.parametrize('key', SCENARIOS)
@pytest.mark.parametrize('case', CASES)
def test_scenarios(key,case):
    if case == 'failure':
        with pytest.raises(PlanningError): generate_demo('id',SCENARIOS[key]['text'],case)
        return
    result = generate_demo('id',SCENARIOS[key]['text'],case)
    assert result['is_mock'] and result['verification_status'] == 'unverified'
    assert all(p['source'] == 'demo_fixture' and p['verification_status'] == 'demo' for p in result['places'])
    assert result['days'][0]['routing_status'] == ('routing_failed' if case in ('routing','missing') else 'demo')
    if case in ('routing','missing'):
        assert result['days'][0]['demo_geometry'] is None
        assert result['days'][0]['drive_minutes'] is None
    if case == 'limit': assert any('daily_drive_limit_exceeded' in d['warnings'] for d in result['days'])

def test_unsupported_requests():
    for text in ('Zaplanuj 5 dni we Wrocławiu','Zaplanuj 2 dni w Tokio'):
        with pytest.raises(PlanningError): generate_demo('id',text)

@pytest.mark.parametrize('case',['success','delivery','expired','failure'])
def test_chat_worker_outbox(tmp_path,case,monkeypatch):
    db=Database(tmp_path/'test.sqlite3')
    conversation=str(uuid4())
    message=dict(conversation=conversation,message_id=str(uuid4()),text=SCENARIOS['mountains']['text'],case=case)
    class NoWaha:
        def send_text(self,**kwargs): raise AssertionError('Demo must never contact WAHA')
    provider=ChannelMessagingProvider(db,NoWaha())
    with TestClient(create_app(db.path)) as client:
        assert client.get('/demo/chat').status_code == 200
        accepted=client.post('/api/demo/messages',json=message).json()
        assert client.post('/api/demo/messages',json=message).json()['trip_id'] == accepted['trip_id']
        assert process_ack(db,provider)
        assert process_next(db)
        assert process_result(db,provider)
        data=client.get('/api/demo/conversations/'+conversation).json()
        assert len(data['jobs']) == 1
        assert len(data['messages']) == (1 if case=='delivery' else 2)
        if case=='delivery':
            with db.connect() as c: c.execute('UPDATE waha_results SET retry_after=0')
            assert process_result(db,provider)
            assert len(client.get('/api/demo/conversations/'+conversation).json()['messages']) == 2
        job=db.get_trip(accepted['trip_id'])
        if case!='failure':
            path=urlsplit(job['result']['viewer_url']).path
            assert client.get(path).status_code == (404 if case=='expired' else 200)
        else: assert job['status']=='failed'
        assert client.get('/api/demo/conversations/'+str(uuid4())).json() == {'messages':[],'jobs':[]}
        other={**message,'conversation':str(uuid4())}
        assert client.post('/api/demo/messages',json=other).json()['trip_id'] != accepted['trip_id']
        monkeypatch.setenv('PLANNING_MODE','live')
        assert client.get('/demo/chat').status_code == 404
        assert client.post('/api/demo/messages',json=message).status_code == 404
        assert client.get('/api/demo/conversations/'+conversation).status_code == 404
