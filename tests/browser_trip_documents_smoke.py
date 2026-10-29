"""Full local DEMO-03 browser/print QA. Outputs stay in local-data/trip-documents-qa/."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

import httpx
from playwright.sync_api import expect, sync_playwright
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]


def run():
    import os
    os.environ['DOCUMENT_STUDIO_FIXTURES_PATH']=str(ROOT/'tests/fixtures/legacy-demo')  # explicit historical regression dataset
    artifacts=ROOT/'local-data'/'trip-documents-qa'
    artifacts.mkdir(parents=True,exist_ok=True)
    with socket.socket() as listener:
        listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
    base=f'http://127.0.0.1:{port}'
    with tempfile.TemporaryDirectory(prefix='tripse-trip-documents-') as temporary:
        env=dict(os.environ,PLANNING_MODE='mock',DATABASE_PATH=str(Path(temporary)/'planner.sqlite3'),DOCUMENT_STUDIO_DATA_PATH=str(Path(temporary)/'documents'))
        env.pop('DOCUMENT_STUDIO_DOCKER_LOCAL',None)
        process=None
        def start():
            server=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port),'--no-access-log'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            for _ in range(100):
                try:
                    if httpx.get(base+'/health',timeout=1).status_code==200:return server
                except httpx.TransportError:pass
                if server.poll() is not None:raise RuntimeError('QA server exited')
                time.sleep(.1)
            server.terminate();server.wait(timeout=10);raise RuntimeError('QA server readiness timeout')
        try:
            process=start()
            api=httpx.Client(base_url=base,timeout=20)
            trip=api.get('/api/document-studio/trips/demo-iceland').json()
            trip['days'][0]['internal_notes']='PRIVATE_PILOT_NOTE_7391'
            trip['days'][0]['stops'][0]['source']='PRIVATE_PROVIDER_CONTACT_7391'
            trip=api.put('/api/document-studio/trips/demo-iceland',json=trip).json()
            with sync_playwright() as playwright:
                browser=playwright.chromium.launch()
                page=browser.new_page(viewport={'width':1440,'height':1000})
                errors=[];requests=[];report=[];saved_ids=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.on('request',lambda request:requests.append(request.url))
                page.on('dialog',lambda dialog:dialog.accept())
                def ready(target):
                    target.wait_for_function('() => window.documentReady === true')
                    assert target.evaluate('window.layoutErrors')==[],target.evaluate('window.layoutErrors')
                    expect(target.locator('#print-document')).to_be_enabled()
                    assert target.evaluate('[...document.querySelectorAll(".page-body")].every(el=>el.scrollHeight <= el.clientHeight+1)')
                def pdf(target,name,internal=False,last_day=None):
                    ready(target)
                    path=artifacts/(name+'.pdf')
                    count=target.locator('.sheet').count()
                    target.pdf(path=str(path),prefer_css_page_size=True,print_background=True)
                    reader=PdfReader(path)
                    assert len(reader.pages)==count,(name,len(reader.pages),count)
                    text='\n'.join(p.extract_text() for p in reader.pages)
                    assert all('TRIPSE' in p.extract_text() for p in reader.pages)
                    assert abs(float(reader.pages[0].mediabox.width)-595.28)<2
                    if internal:
                        assert all('WEWNĘTRZNE' in p.extract_text() for p in reader.pages)
                    else:
                        assert 'PRIVATE_PILOT_NOTE_7391' not in text
                        assert 'PRIVATE_PROVIDER_CONTACT_7391' not in text
                        assert 'PRIVATE_RESERVATION_7391' not in text
                        assert 'pilot-private@example.invalid' not in text
                    if last_day:assert f'Dzień {last_day}' in text
                    report.append({'name':name,'pages':count})
                    return text
                for template in ('offer.private','pilot.basic'):
                    page.goto(base+'/documents/demo#trips/demo-iceland')
                    page.locator('#create-draft').click()
                    page.locator('[data-create-template="'+template+'"]').click()
                    page.locator('#source-create').click()
                    expect(page.locator("#d-save")).to_be_visible()
                    from legacy_document_content import initialize_legacy_demo
                    initialize_legacy_demo(api,page.evaluate('location.hash').split('/')[-1])
                    page.reload()
                    expect(page.locator('#d-save')).to_be_visible()
                    document_id=page.evaluate('location.hash').split('/')[-1]
                    saved_ids.append(document_id)
                    page.locator('[data-d-field="title"]').fill('Islandia Road Trip — oferta żółć i góry' if template=='offer.private' else 'Islandia Road Trip — rozpiska pilota')
                    page.locator('[data-d-field="day_overrides.0.description"]').fill('Opis zmieniony wyłącznie w dokumencie. Żółte góry, fiordy i wodospady.')
                    if template=='pilot.basic':
                        page.locator('[data-d-field="pilot_data.activity_bookings.0.booking_reference"]').fill('PRIVATE_RESERVATION_7391')
                        page.locator('[data-d-field="pilot_data.contacts.0.value"]').fill('pilot-private@example.invalid')
                        page.locator('[data-d-add="transfers"]').click()
                        page.locator('[data-d-remove="transfers.1"]').click()
                        page.locator('[data-d-field="pilot_data.schedule.0.start_local"]').fill('2027-06-01T11:30')
                    page.locator('#d-save').click()
                    expect(page.locator('#message')).to_contain_text('Dokument zapisany')
                    expect(page.locator('#d-revision')).to_have_text('3')
                    page.screenshot(path=str(artifacts/(template+'-editor.png')),full_page=True)
                    page.locator('#document-review').click()
                    with page.expect_popup() as popup:page.locator('#review-export').click()
                    preview=popup.value
                    text=pdf(preview,template+'-iceland-10',template=='pilot.basic',10)
                    assert 'Opis zmieniony wyłącznie w dokumencie' in text
                    if template=='offer.private':assert 'FIKCYJNA CENA DEMO' in text
                    else:
                        assert 'PRIVATE_PILOT_NOTE_7391' in text
                        assert 'PRIVATE_RESERVATION_7391' in text
                        assert '11:30' in text and 'Atlantic/Reykjavik' in text
                    preview.locator('.sheet-wrap').first.screenshot(path=str(artifacts/(template+'-cover.png')))
                    preview.evaluate('window.print=()=>window.printInvoked=true')
                    preview.locator('#print-document').click();assert preview.evaluate('window.printInvoked')
                    preview.close()
                assert api.get('/api/document-studio/trips/demo-iceland').json()==trip
                # API setup of boundary scenarios; same renderer and actual browser printing.
                for count in (2,15):
                    payload={'title':f'Próba {count} dni — polskie ąęłóśźż','duration_days':count,'days':[{'day_number':i,'title':f'Dzień próby {i}','public_description':'Przykładowy program dnia.'} for i in range(1,count+1)]}
                    source=api.post('/api/document-studio/trips',json=payload).json()
                    for template in ('offer.private','pilot.basic'):
                        response=api.post('/api/document-studio/drafts',json={'template_id':template,'source_type':'trip','source_id':source['trip_id']})
                        response.raise_for_status();draft=response.json()
                        if template=='offer.private':
                            draft['offer_data'].update(cta='Kontakt dla klienta')
                            blocked=api.post('/api/document-studio/trip-documents/validate',json={'draft':draft}).json()
                            assert any(i['field_path']=='offer_data.price' and i['severity']=='error' for i in blocked)
                            draft['offer_data']['concept_only']=True
                        else:
                            draft['pilot_data'].update(leader='Pilot testowy — fikcyjny',contacts=[{'label':'Koordynator','value':'qa@example.invalid'}])
                        if count==2:
                            draft['day_overrides']=[{'day_id':source['days'][0]['day_id'],'description':'Początek długiego opisu. '+('Żółte góry i spokojne jeziora. '*100)+' KONIEC_DLUGIEGO_OPISU_7391'}]
                        body={k:draft[k] for k in ('revision','title','date_label','editorial_notes','day_overrides','offer_data','pilot_data')}
                        result=api.put('/api/document-studio/drafts/'+draft['document_id'],json=body);result.raise_for_status()
                        page.goto(base+'/api/document-studio/drafts/'+draft['document_id']+'/preview')
                        text=pdf(page,f'{template}-{count}-days',template=='pilot.basic',count)
                        if count==2:assert 'KONIEC_DLUGIEGO_OPISU_7391' in text
                        if template=='offer.private':
                            assert 'WERSJA KONCEPCYJNA BEZ WYCENY' in text
                            assert 'Standard noclegów do potwierdzenia' in text
                        else:assert 'KRYTYCZNE' in text
                # Reopen saved draft after the real server process restarts.
                process.terminate();process.wait(timeout=10);process=start()
                page.goto(base+'/documents/demo#edit-draft/'+saved_ids[0])
                expect(page.locator('[data-d-field="title"]')).to_have_value('Islandia Road Trip — oferta żółć i góry')
                expect(page.locator('[data-d-field="day_overrides.0.description"]')).to_contain_text('Opis zmieniony wyłącznie w dokumencie')
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.screenshot(path=str(artifacts/'editor-mobile.png'),full_page=True)
                assert not errors,errors
                assert all(url.startswith(base+'/') for url in requests),requests
                browser.close();api.close()
                (artifacts/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        finally:
            if process and process.poll() is None:process.terminate();process.wait(timeout=10)
    print('Trip document QA PASS: Iceland -> two editable documents -> six actual PDFs; 2/10/15 days, long copy, missing hotel and price, Polish text, private-data isolation, local hours, revision, mobile and actual restart.')


if __name__=='__main__':run()
