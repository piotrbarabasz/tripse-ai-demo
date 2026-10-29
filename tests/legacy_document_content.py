"""Historical-content regression setup via ordinary API, never application code."""
import json
from datetime import datetime, timedelta
from pathlib import Path


def initialize_legacy_demo(client, identifier):
    response=client.get('/api/document-studio/drafts/'+identifier);response.raise_for_status()
    draft=response.json();trip=draft['trip_snapshot']
    preset=json.loads((Path(__file__).parent/'fixtures/legacy-demo/document-presets/iceland.json').read_text(encoding='utf-8'))
    body={'revision':draft['revision'],'title':draft['title'],'date_label':preset['date_label']}
    if draft['template_id']=='offer.private':body['offer_data']=preset['offer_data']
    else:
        pilot=preset['pilot_data']
        pilot['accommodations']=[{'day_id':d['day_id'],'title':'Historical synthetic accommodation','status':'planned'} for d in trip['days'][:-1]]
        pilot['schedule']=[{'day_id':d['day_id'],'title':d['title'],'start_local':(datetime(2027,6,1,9)+timedelta(days=i)).isoformat(),'time_zone':'Atlantic/Reykjavik','status':'planned'} for i,d in enumerate(trip['days'])]
        pilot['activity_bookings']=[{'day_id':trip['days'][0]['day_id'],'title':'Historical synthetic booking','status':'unknown'}]
        body['pilot_data']=pilot
    saved=client.put('/api/document-studio/drafts/'+identifier,json=body);saved.raise_for_status()
    return saved.json()
