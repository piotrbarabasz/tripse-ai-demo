"""Demo channel with durable, conversation-scoped outbox. Disabled in live mode."""
import os
from uuid import UUID
from typing import Literal
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from app.demo_data import SCENARIOS, CASES
from app.viewer import module_page
from app.waha import route_intent

def enabled():
    return os.getenv('PLANNING_MODE', 'live') == 'mock'

def initialize(connection):
    connection.execute('CREATE TABLE IF NOT EXISTS demo_options (trip_id TEXT PRIMARY KEY, scenario TEXT NOT NULL)')
    connection.execute('CREATE TABLE IF NOT EXISTS demo_progress (trip_id TEXT PRIMARY KEY, stage TEXT NOT NULL)')
    connection.execute('CREATE TABLE IF NOT EXISTS demo_outbox (id INTEGER PRIMARY KEY, conversation TEXT NOT NULL, text TEXT NOT NULL, UNIQUE(conversation, text))')

def options(database, trip_id):
    return database.demo_options(trip_id)

def progress(database, trip_id, stage):
    database.demo_progress(trip_id, stage)

class DemoMessagingProvider:
    def __init__(self, database): self.database = database
    def send_text(self, *, session, chat_id, text):
        self.database.demo_send(chat_id, text)

class ChannelMessagingProvider:
    def __init__(self, database, waha):
        self.demo, self.waha = DemoMessagingProvider(database), waha
    def send_text(self, *, session, chat_id, text):
        provider = self.demo if session == 'demo' else self.waha
        provider.send_text(session=session,chat_id=chat_id,text=text)

class Message(BaseModel):
    conversation: UUID
    message_id: UUID
    text: str = Field(min_length=1,max_length=10000)
    case: Literal['success','limit','missing','routing','failure','delivery','expired'] = 'success'

def demo_router(database, *, cloud_mode=False):
    router = APIRouter()
    def guard():
        if not enabled(): raise HTTPException(404, 'Demo niedostępne')

    @router.get('/demo/chat', response_class=HTMLResponse)
    def page(request: Request):
        guard()
        return module_page("demo.html", request, cloud_mode=cloud_mode)

    @router.get('/api/demo/scenarios')
    def scenarios():
        guard()
        return {'scenarios':[dict(id=k,name=v['name'],text=v['text']) for k,v in SCENARIOS.items()], 'cases':CASES}

    @router.post('/api/demo/messages',status_code=202)
    def send(message: Message):
        guard()
        if route_intent(message.text.strip()) != 'trip.create':
            raise HTTPException(422,'Rozpocznij od „Zaplanuj …” lub wybierz gotowy przykład.')
        # Include conversation in dedup key to isolate clients even with equal event IDs.
        sender = str(message.conversation)
        event_id = sender + ':' + str(message.message_id)
        trip_id, created = database.create_waha_trip('demo',event_id,sender,message.text.strip(), demo_case=message.case)
        return {'trip_id':trip_id,'status':'accepted' if created else 'duplicate'}

    @router.get('/api/demo/conversations/{conversation}')
    def messages(conversation: UUID):
        guard()
        return database.demo_conversation(str(conversation))
    return router
