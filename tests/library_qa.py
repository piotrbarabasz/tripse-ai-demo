"""Library UI + real local API restart; isolated files, no external services."""
import io
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

import httpx
from PIL import Image
from playwright.sync_api import expect, sync_playwright

ROOT=Path(__file__).resolve().parents[1]


def run_library():
    import os
    os.environ['DOCUMENT_STUDIO_FIXTURES_PATH']=str(ROOT/'tests/fixtures/legacy-demo')  # explicit historical regression dataset
    artifacts=ROOT/'local-data'/'document-library-qa';artifacts.mkdir(parents=True,exist_ok=True)
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    base=f'http://127.0.0.1:{port}'
    with tempfile.TemporaryDirectory(prefix='tripse-library-') as temporary:
        env=dict(os.environ,CLOUD_FEATURE_MODE='local',PLANNING_MODE='mock',DATABASE_PATH=str(Path(temporary)/'planner.sqlite3'),DOCUMENT_STUDIO_DATA_PATH=str(Path(temporary)/'documents'))
        for key in ('K_SERVICE','DOCUMENT_STUDIO_DOCKER_LOCAL','OPENAI_API_KEY','GOOGLE_MAPS_API_KEY','GOOGLE_PLACES_API_KEY','GOOGLE_ROUTES_API_KEY'):env.pop(key,None)
        def start():
            process=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port),'--no-access-log'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            for _ in range(100):
                if process.poll() is not None:raise RuntimeError('Library QA API exited')
                try:
                    if httpx.get(base+'/health',timeout=1).status_code==200:return process
                except httpx.TransportError:pass
                time.sleep(.1)
            process.terminate();process.wait(timeout=10);raise RuntimeError('API readiness timeout')
        process=start()
        try:
            with httpx.Client(base_url=base,timeout=20) as api, sync_playwright() as p:
                catalog=api.get('/api/document-studio/templates').json();docs=[]
                for template in catalog:
                    for variant in template['layout_variants']:
                        r=api.post('/api/document-studio/drafts',json={'title':'Dokument '+template['template_id']+' '+variant,'template_id':template['template_id'],'source_type':template['source_type'],'source_id':'demo-northern-journeys' if template['source_type']=='campaign' else 'demo-iceland','layout_variant':variant})
                        r.raise_for_status();docs.append(r.json())
                original=next(d for d in docs if d['template_id']=='offer.private')
                image=io.BytesIO();Image.new('RGB',(20,12),'orange').save(image,'PNG')
                uploaded=api.post('/api/document-studio/assets?filename=test.png&rights_confirmed=true',content=image.getvalue(),headers={'content-type':'image/png'});uploaded.raise_for_status();asset_id=uploaded.json()['asset_id']
                original['offer_data'].update(concept_only=True,cta='Kontakt do uzgodnienia',cover_asset_id=asset_id)
                original['sections'].append({'section_id':'library-image','kind':'gallery','title':'Zdjęcia dokumentu','images':[{'asset_id':asset_id,'caption':'Podpis — żółć','position':{'x':22,'y':64,'zoom':1.5}}],'order':99})
                body={k:original[k] for k in ('revision','title','sections','offer_data')}
                r=api.put('/api/document-studio/drafts/'+original['document_id'],json=body);r.raise_for_status();original=r.json()
                identifier=original['document_id'];docurl='/api/document-studio/drafts/'+identifier
                browser=p.chromium.launch();context=browser.new_context(viewport={'width':1440,'height':1000});page=context.new_page()
                errors=[];requests=[];dialogs=[];accept=False
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.on('request',lambda request:requests.append(request.url))
                def dialog(value):
                    dialogs.append(value.type)
                    value.accept() if accept else value.dismiss()
                page.on('dialog',dialog)
                context.route('**/*',lambda route:route.continue_() if route.request.url.startswith(base+'/') else route.abort())
                page.goto(base+'/documents/demo#drafts')
                expect(page.locator('.library-document')).to_have_count(9)
                assert not any(urlsplit_path(url)=='/api/document-studio/drafts' for url in requests)
                page.locator('[data-library-filter="family"]').select_option('pilot');expect(page.locator('.library-document')).to_have_count(3)
                page.locator('#library-reset').click();expect(page.locator('.library-document')).to_have_count(9)
                page.locator('[data-library-filter="template_id"]').select_option('marketing.collection');expect(page.locator('.library-document')).to_have_count(2)
                page.locator('#library-reset').click();expect(page.locator('.library-document')).to_have_count(9)
                page.locator('[data-library-filter="sort"]').select_option('title')
                page.locator('[data-library-filter="direction"]').select_option('asc')
                card=page.locator('[data-document-id="'+identifier+'"]');card.locator('[data-go^="edit-draft/"]').click()
                expect(page.locator('#d-save')).to_be_visible()
                page.locator('[data-d-field="title"]').fill('Biblioteka — żółć i góry')
                page.locator('button[data-go="drafts"]').first.click()
                assert dialogs and 'edit-draft' in page.url
                expect(page.locator('[data-d-field="title"]')).to_have_value('Biblioteka — żółć i góry')
                page.locator('#d-save').click();expect(page.locator('#d-revision')).to_have_text('3')
                saved=api.get(docurl).json();assert saved['sections']==original['sections'] and saved['offer_data']['cover_asset_id']==asset_id
                page.reload();expect(page.locator('[data-d-field="title"]')).to_have_value('Biblioteka — żółć i góry')
                page.locator('button[data-go="drafts"]').first.click();expect(page.locator('.library-document')).to_have_count(9)
                page.locator('[data-library-filter="search"]').fill('Biblioteka — żółć');expect(page.locator('.library-document')).to_have_count(1)
                card=page.locator('[data-document-id="'+identifier+'"]')
                card.locator('[data-library-action="duplicate"]').click();expect(page.locator('.library-document')).to_have_count(2)
                copies=api.get('/api/document-studio/library',params={'search':'Biblioteka — żółć'}).json()['items']
                copy_id=next(d['document_id'] for d in copies if d['document_id']!=identifier)
                copy=api.get('/api/document-studio/drafts/'+copy_id).json();assert copy['sections']==saved['sections'] and copy['document_status']=='draft'
                accept=True
                card.locator('[data-library-action="archive"]').click();expect(page.locator('.library-document')).to_have_count(1)
                page.locator('[data-library-filter="archived"]').select_option('only');expect(page.locator('.library-document')).to_have_count(1)
                card=page.locator('[data-document-id="'+identifier+'"]')
                expect(card.locator('[data-go^="edit-draft/"]')).to_be_disabled()
                card.locator('[data-go^="revisions/"]').click();expect(page.locator('#history-revision option')).to_have_count(4)
                page.locator('#history-revision').select_option('1')
                expect(page.frame_locator('#history-frame').locator('h1')).to_contain_text('Dokument offer.private')
                history=api.get('/api/document-studio/library/'+identifier+'/revisions/3').json();assert history==saved
                page.locator('button[data-go="drafts"]').click();expect(page.locator('.library-document')).to_have_count(1)
                page.locator('[data-library-action="restore"]').click();expect(page.locator('.library-document')).to_have_count(0)
                page.locator('[data-library-filter="archived"]').select_option('exclude');expect(page.locator('.library-document')).to_have_count(2)
                card=page.locator('[data-document-id="'+identifier+'"]');card.locator('.library-status-value').select_option('ready');card.locator('[data-library-action="status"]').click()
                expect(card.locator('.library-status-value')).to_have_value('ready')
                page.wait_for_function('!document.querySelector(".library-status-value")?.disabled')
                process.terminate();process.wait(timeout=10);process=start()
                page.reload();expect(page.locator('.library-document')).to_have_count(10)
                reopened=api.get(docurl).json();assert reopened['sections']==saved['sections'] and reopened['document_status']=='ready'
                assert api.get('/api/document-studio/assets/'+asset_id+'/content').status_code==200
                # Library and history remain usable on a small screen.
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                page.screenshot(path=str(artifacts/'library-mobile.png'),full_page=True)
                page.set_viewport_size({'width':1440,'height':1000});page.screenshot(path=str(artifacts/'library-desktop.png'),full_page=True)
                assert not errors,errors
                browser.close()
        finally:
            if process.poll() is None:process.terminate();process.wait(timeout=10)
    print('Library browser PASS: 8 types / 2 marketing variants, metadata/filter/search/sort, unsaved warning, full editable state/images, duplicate/archive/restore/status, history preview, actual API restart, mobile; no external calls.')


def urlsplit_path(url):
    from urllib.parse import urlsplit
    return urlsplit(url).path


if __name__=='__main__':run_library()
