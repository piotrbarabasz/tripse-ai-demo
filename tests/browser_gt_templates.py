"""DOC-TEMPLATES-006: real Chromium UI, nine editable copies, eleven actual PDFs.

Run python tests/browser_gt_templates.py. Both local HTTP/JSON and offline
authenticated fake GCS are exercised. No cloud resource or paid API is contacted.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'tests'))

import httpx
import pytest
from playwright.sync_api import expect, sync_playwright
from pypdf import PdfReader
from pdf_quality_qa import GEOMETRY, raster


def exercise(page, base, artifacts, *, export):
    results=[]
    edits={
        1:('d','offer_data.summary','QA: własne podsumowanie — żółć i góry'),
        2:('d','offer_details.route_summary.start','Vancouver — start kopii QA'),
        3:('d','offer_details.safety_requirements','QA: wymagania do uzgodnienia ze szkołą'),
        4:('d','offer_details.group_size','20'),
        5:('d','pilot_data.flights.0.travel_group','Grupa A — kopia QA'),
        6:('s','sections.11.logistics.drive_km','222.5'),
        7:('s','sections.3.knowledge.stories','Autorska narracja QA: Żółć i góry — przykład niezweryfikowany.'),
        8:('m','description','QA: Nowe kierunki 2027 — fikcyjna kolekcja.'),
        9:('m','theme','QA: Góry i obserwacje — kolekcja demonstracyjna.'),
    }
    for i,(prefix,path,value) in edits.items():
        if i<int(os.getenv('GT_QA_FIRST','1')):continue
        identifier=f'GT-DEMO-{i:02}'
        page.goto(base+'/documents/demo#examples')
        expect(page.locator('[data-example-id]')).to_have_count(9)
        page.locator(f'[data-example-id="{identifier}"] button').click()
        expect(page.locator('#copy-example')).to_be_visible()
        page.locator('#copy-example').click()
        save=page.locator('#m-save' if i>=8 else '#d-save')
        expect(save).to_be_visible()
        field=page.locator(f'[data-{prefix}-field="{path}"]')
        if prefix=='s':field.evaluate("el=>el.closest('details').open=true")
        assert field.input_value().strip(),(identifier,'seed field empty',path)
        field.fill(value)
        # Cover additional structured endpoints rather than just renaming documents.
        if i==2:page.locator('[data-d-field="offer_details.route_summary.drive_km"]').fill('1234.5')
        if i==6:page.locator('[data-d-field="pilot_data.schedule.0.details"]').fill('QA: zmieniony pierwszy segment osi czasu')
        save.click()
        expect(page.locator('#message')).to_contain_text('Dokument zapisany')
        doc_url=page.url;doc_id=doc_url.split('#edit-draft/')[1]
        page.reload()
        field=page.locator(f'[data-{prefix}-field="{path}"]')
        if prefix=='s':field.evaluate("el=>el.closest('details').open=true")
        expect(field).to_have_value(value)
        page.locator('#document-review').click()
        expect(page.locator('#review-export')).to_be_visible()
        page.screenshot(path=str(artifacts/(identifier+'-review.png')),full_page=True)
        record={'example_id':identifier,'document_id':doc_id,'store':'fake_gcs' if export else 'json','edit_save_reopen':'PASS','formats':[]}
        if export:
            with page.expect_popup() as popup:page.locator('#review-export').click()
            preview=popup.value
            for fmt in (['a4','social'] if i>=8 else ['a4']):
                if fmt=='social':preview.goto(base+'/api/document-studio/drafts/'+doc_id+'/preview?output_format=social')
                preview.wait_for_function('() => window.documentReady === true',timeout=60000)
                assert preview.evaluate('window.layoutErrors')==[],identifier
                expect(preview.locator('#print-document')).to_be_enabled()
                geometry=preview.evaluate(GEOMETRY)
                (artifacts/(identifier+'-'+fmt+'-geometry.json')).write_text(json.dumps(geometry),encoding='utf-8')
                for number,g in enumerate(geometry):
                    assert g['scrollOK'] and g['text'].strip() and not g['orphan'],(identifier,fmt,number)
                    for b in g['blocks']+g['cells']+g['textBoxes']:
                        assert b['y']>=g['body']['y']-1 and b['bottom']<=g['body']['bottom']+1,(identifier,'vertical',number,b,g['body'])
                        assert b['x']>=g['body']['x']-1 and b['right']<=g['body']['right']+1,(identifier,'horizontal',number,b,g['body'])
                    for a,b in zip(g['blocks'],g['blocks'][1:]):assert a['bottom']<=b['y']+1,(identifier,'overlap',number)
                name=identifier+'-'+fmt
                screen=artifacts/(name+'.png');preview.locator('.sheet').first.screenshot(path=str(screen))
                pdf=artifacts/(name+'.pdf');preview.pdf(path=str(pdf),prefer_css_page_size=True,print_background=True)
                reader=PdfReader(pdf);assert len(reader.pages)==len(geometry)
                texts=[p.extract_text() for p in reader.pages]
                assert all(t.strip() for t in texts)
                text='\n'.join(texts)
                assert 'DANE FIKCYJNE' in text and '\ufffd' not in text
                if i not in (4,6):assert ' '.join(value.split()) in ' '.join(text.split()),(identifier,'missing edited value')
                assert 'Lorem ipsum' not in text
                (artifacts/(name+'-text.txt')).write_text(text,encoding='utf-8')
                difference=raster(pdf,artifacts/(name+'-pages'),screen)
                record['formats'].append({'format':fmt,'pages':len(reader.pages),'pdf':str(pdf.relative_to(ROOT)),'preview_difference':difference,'geometry':'PASS'})
            preview.close()
        results.append(record)
    return results


def run():
    out=ROOT/'local-data/doc-templates-006-qa';out.mkdir(parents=True,exist_ok=True)
    results=[]
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv('PLANNING_MODE','mock')
        patch.delenv('DOCUMENT_STUDIO_FIXTURES_PATH',raising=False)
        for key in ('K_SERVICE','OPENAI_API_KEY','GOOGLE_MAPS_API_KEY','GOOGLE_PLACES_API_KEY','GOOGLE_ROUTES_API_KEY'):
            patch.delenv(key,raising=False)
        from test_cloud_demo import cloud_demo,ORIGIN
        demo=cloud_demo.__wrapped__(patch)
        with demo.client() as api,sync_playwright() as p:
            browser=p.chromium.launch();context=browser.new_context(viewport={'width':1440,'height':1000})
            errors=[];external=[]
            context.on('page',lambda page:page.on('pageerror',lambda e:errors.append(str(e))))
            def route_request(route):
                req=route.request
                if not req.url.startswith(ORIGIN+'/'):external.append(req.url);route.abort();return
                response=api.request(req.method,req.url,headers=req.all_headers(),content=req.post_data_buffer,follow_redirects=False)
                route.fulfill(status=response.status_code,headers={k:v for k,v in response.headers.items() if k.lower() not in {'content-length','content-encoding'}},body=response.content)
            context.route('**/*',route_request)
            page=context.new_page();page.on('dialog',lambda d:d.accept())
            results+=exercise(page,ORIGIN,out,export=True)
            assert not errors and not external,(errors,external)
            # Canonical examples are never persisted just by copying/viewing them.
            docs=api.get('/api/document-studio/drafts').json();assert len(docs)==9
            assert all(d['revision']==3 and d['data_origin']=='demo' for d in docs)
            browser.close()
        # Actual local HTTP server, isolated from the user's data path.
        with tempfile.TemporaryDirectory(prefix='tripse-gt-qa-') as temporary:
            with socket.socket() as listener:listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
            base=f'http://127.0.0.1:{port}'
            env=dict(os.environ,PLANNING_MODE='mock',CLOUD_FEATURE_MODE='local',DATABASE_PATH=str(Path(temporary)/'planner.sqlite3'),DOCUMENT_STUDIO_DATA_PATH=str(Path(temporary)/'documents'))
            env.pop('DOCUMENT_STUDIO_FIXTURES_PATH',None)
            process=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port),'--no-access-log'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            try:
                for _ in range(100):
                    if process.poll() is not None:raise RuntimeError('Local server exited')
                    try:
                        if httpx.get(base+'/health',timeout=1).status_code==200:break
                    except httpx.TransportError:pass
                    time.sleep(.1)
                with sync_playwright() as p:
                    browser=p.chromium.launch();page=browser.new_page(viewport={'width':1440,'height':1000});page.on('dialog',lambda d:d.accept())
                    results+=exercise(page,base,out,export=False)
                    browser.close()
            finally:process.terminate();process.wait(timeout=10)
    (out/'report.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print('GT templates PASS: 18 UI edit/save/reopen/review flows (JSON + fake GCS), 11 real PDFs, geometry/text/raster, no external requests.')


if __name__=='__main__':run()
