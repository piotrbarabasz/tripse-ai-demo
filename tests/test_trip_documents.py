from datetime import datetime

import pytest
from pydantic import ValidationError

from app.document_studio.models import OperationalEntry, OfferPrice
from app.document_studio.rendering.trip_documents import chunks
from app.document_studio.trip_documents import OFFER_DAY_FIELDS, OFFER_STOP_FIELDS
from tests.test_document_studio import client_for


def create_draft(client, template, source="demo-iceland", demo=False):
    response = client.post("/api/document-studio/drafts",json={"template_id":template,"source_type":"trip","source_id":source,"demo_example":False})
    assert response.status_code == 201,response.text
    draft = response.json()
    if demo:
        from app.document_studio.examples import build_example
        recipe = build_example('GT-DEMO-01' if template == 'offer.private' else 'GT-DEMO-05')
        # Seed content through normal update, retaining the intentionally mutated legacy snapshot.
        if template == 'offer.private':
            body=update_body(draft);body['offer_data']=recipe.offer_data.model_dump(mode='json')
        else:
            body=update_body(draft);body['pilot_data']={'contacts':[{'label':'QA','value':'qa@example.invalid'}],'activity_bookings':[{'title':'Synthetic QA booking','status':'unknown'}]}
        saved=client.put('/api/document-studio/drafts/'+draft['document_id'],json=body)
        assert saved.status_code == 200,saved.text
        draft=saved.json()
    return draft


def update_body(draft):
    return {key:draft[key] for key in ("revision","title","date_label","editorial_notes","day_overrides","offer_data","pilot_data")}


def test_one_trip_two_documents_privacy_and_restart(tmp_path):
    private = "PRIVATE_INTERNAL_9831"
    with client_for(tmp_path) as client:
        trip = client.get("/api/document-studio/trips/demo-iceland").json()
        trip["days"][0]["internal_notes"] = private
        trip["days"][0]["stops"][0]["source"] = "PRIVATE_BOOKING_SOURCE_9831"
        original = client.put("/api/document-studio/trips/demo-iceland",json=trip).json()
        offer = create_draft(client,"offer.private",demo=True)
        pilot = create_draft(client,"pilot.basic",demo=True)
        assert offer["trip_snapshot"]["trip_id"] == pilot["trip_snapshot"]["trip_id"]
        assert offer["template_version"] == pilot["template_version"] == "0.5.0"
        assert offer["pilot_data"] is None
        assert offer["trip_snapshot"]["days"][0]["internal_notes"] == ""
        assert offer["trip_snapshot"]["days"][0]["stops"][0]["source"] is None
        assert pilot["trip_snapshot"]["days"][0]["internal_notes"] == private
        for key in ("reservation_pin", "access_code", "participants", "booking_reference", "contacts", "internal_notes"):
            assert key not in OFFER_DAY_FIELDS | OFFER_STOP_FIELDS
        edited=update_body(pilot)
        edited["pilot_data"]["activity_bookings"][0]["booking_reference"]="PRIVATE_BOOKING_REF_9831"
        edited["pilot_data"]["contacts"][0]["value"]="private-contact@example.invalid"
        assert client.put(f"/api/document-studio/drafts/{pilot['document_id']}",json=edited).status_code==200
        offer_url=f"/api/document-studio/drafts/{offer['document_id']}/preview"
        pilot_url=f"/api/document-studio/drafts/{pilot['document_id']}/preview"
        public=client.get(offer_url).text
        internal=client.get(pilot_url).text
        for marker in (private,"PRIVATE_BOOKING_SOURCE_9831","PRIVATE_BOOKING_REF_9831","private-contact@example.invalid","WEWNĘTRZNE / FIKCYJNE DEMO"):
            assert marker not in public
        assert private in internal and "PRIVATE_BOOKING_REF_9831" in internal
        assert "WEWNĘTRZNE" in internal and "FIKCYJNA CENA DEMO" in public
        edited=update_body(offer)
        edited["title"]="Własna oferta — żółć i góry"
        edited["day_overrides"]=[{"day_id":original["days"][0]["day_id"],"title":"Tytuł tylko w ofercie","description":"Opis redakcyjny"}]
        saved=client.put(f"/api/document-studio/drafts/{offer['document_id']}",json=edited)
        assert saved.status_code==200,saved.text
        assert saved.json()["revision"]==3
        assert client.put(f"/api/document-studio/drafts/{offer['document_id']}",json=edited).status_code==409
        assert client.get("/api/document-studio/trips/demo-iceland").json()==original
        assert "Tytuł tylko w ofercie" not in client.get(pilot_url).text
        assert client.get(pilot_url,headers={"Origin":"https://evil.example"}).status_code==403
        assert client.get(pilot_url,headers={"X-Forwarded-For":"127.0.0.1"}).status_code==403
        assert client.get(offer_url+"?output_format=social").status_code==422
    with client_for(tmp_path) as restarted:
        assert restarted.get(f"/api/document-studio/drafts/{offer['document_id']}").json()["revision"]==3
        assert "Opis redakcyjny" in restarted.get(offer_url).text
        assert "PRIVATE_BOOKING_REF_9831" in restarted.get(pilot_url).text


def test_missing_price_hotel_and_invalid_updates(tmp_path):
    with client_for(tmp_path) as client:
        offer=create_draft(client,"offer.private")
        offer["offer_data"]["cta"]="Kontakt publiczny"
        issues=client.post("/api/document-studio/trip-documents/validate",json={"draft":offer}).json()
        assert any(i["severity"]=="error" and i["field_path"]=="offer_data.price" for i in issues)
        offer["offer_data"]["concept_only"]=True
        issues=client.post("/api/document-studio/trip-documents/validate",json={"draft":offer}).json()
        assert not any(i["severity"]=="error" for i in issues)
        html=client.post("/api/document-studio/trip-documents/preview",json={"draft":offer}).text
        assert "WERSJA KONCEPCYJNA BEZ WYCENY" in html
        assert "Standard noclegów do potwierdzenia" in html
        pilot=create_draft(client,"pilot.basic")
        issues=client.post("/api/document-studio/trip-documents/validate",json={"draft":pilot}).json()
        assert any("KRYTYCZNE" in issue["message"] for issue in issues)
        body=update_body(offer)
        body["offer_data"]["booking_reference"]="FORBIDDEN"
        assert client.put(f"/api/document-studio/drafts/{offer['document_id']}",json=body).status_code==422
        body=update_body(offer)
        body["pilot_data"]={"leader":"Forbidden"}
        assert client.put(f"/api/document-studio/drafts/{offer['document_id']}",json=body).status_code==422
        body=update_body(offer)
        body["trip_snapshot"]={"title":"Cannot replace snapshot"}
        assert client.put(f"/api/document-studio/drafts/{offer['document_id']}",json=body).status_code==422
        body=update_body(offer)
        body["day_overrides"]=[{"day_id":"missing","title":"Wrong day"}]
        assert client.put(f"/api/document-studio/drafts/{offer['document_id']}",json=body).status_code==422


@pytest.mark.parametrize("source,count",[("demo-iceland",10),("demo-canada",15)])
def test_long_trips_and_html_escaping(tmp_path,source,count):
    with client_for(tmp_path) as client:
        draft=create_draft(client,"offer.private",source)
        draft["offer_data"].update(concept_only=True,cta="Kontakt")
        copy="<script>window.injected=true</script> " + "Żółte góry i jeziora. "*700
        draft["day_overrides"]=[{"day_id":draft["trip_snapshot"]["days"][0]["day_id"],"description":copy}]
        result=client.post("/api/document-studio/trip-documents/preview",json={"draft":draft})
        assert result.status_code==200,result.text
        assert f"Dzień {count} " in result.text
        assert "&lt;script&gt;" in result.text
        assert "<script>window.injected" not in result.text
        assert ''.join(chunks(copy))==copy


@pytest.mark.parametrize("changes",[
    {"start_local":datetime(2027,1,1,9)},
    {"time_zone":"Not/AZone"},
    {"status":"confirmed"},
    {"time_zone":"UTC","start_local":datetime(2027,1,1,10),"end_local":datetime(2027,1,1,9)},
])
def test_bad_operational_data(changes):
    with pytest.raises(ValidationError):
        OperationalEntry(title="Test",**changes)


def test_timezones_and_price_validation():
    event=OperationalEntry(title="Przykład",start_local=datetime(2027,6,1,8),end_local=datetime(2027,6,1,7),time_zone="Europe/Warsaw",end_time_zone="Atlantic/Reykjavik")
    assert event.start_local.hour==8 and event.end_local.hour==7
    with pytest.raises(ValidationError):OfferPrice(amount=-1)
    with pytest.raises(ValidationError):OfferPrice(amount="100",status="confirmed")


# Explicit historical regression sources; active catalogue is tested in test_gt_templates.py.
import pytest as _pytest
pytestmark = _pytest.mark.usefixtures("legacy_document_sources")
