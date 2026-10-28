"""DOC-FLOW-004: real Chromium, isolated cloud adapters, explicit saves and retries."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import pytest
from playwright.sync_api import expect,sync_playwright


def run_flow():
    from test_cloud_demo import cloud_demo,ORIGIN
    out=ROOT/'local-data/creation-flow-qa';out.mkdir(parents=True,exist_ok=True)
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv('PLANNING_MODE','mock')
        for key in ('K_SERVICE','OPENAI_API_KEY','GOOGLE_MAPS_API_KEY','GOOGLE_PLACES_API_KEY','GOOGLE_ROUTES_API_KEY'):
            patch.delenv(key,raising=False)
        demo=cloud_demo.__wrapped__(patch)
        with demo.client() as api,sync_playwright() as p:
            sources=[]
            for title,category in [('Wyjazd — żółte góry','private'),('Szkolna wyprawa','school')]:
                r=api.post('/api/document-studio/trips',json={'title':title,'data_origin':'business','categories':[category],
                    'destinations':['Region testowy'],'duration_days':2,'days':[{'day_number':i,'title':f'Program dnia {i}',
                        'public_description':'Syntetyczny opis dnia','stops':[{'name':'Punkt testowy'}]} for i in (1,2)]})
                r.raise_for_status();sources.append(r.json())
            browser=p.chromium.launch();context=browser.new_context(viewport={'width':1440,'height':1000});page=context.new_page()
            errors=[];external=[];requests=[];fault=None;accept_dialog=True;dialogs=[]
            def route_request(route):
                nonlocal fault
                req=route.request;path=req.url.removeprefix(ORIGIN)
                if not req.url.startswith(ORIGIN+'/'):external.append(req.url);route.abort();return
                requests.append((req.method,path))
                if fault and req.method==fault['method'] and path==fault['path']:
                    selected=fault;fault=None
                    if selected.get('commit'):
                        response=api.request(req.method,req.url,headers=req.all_headers(),content=req.post_data_buffer)
                        assert response.status_code in (200,201),(response.status_code,response.text)
                    if selected.get('timeout'):
                        route.abort('timedout');return
                    route.fulfill(status=selected.get('status',503),content_type='application/json',body='{"detail":"controlled flow failure"}');return
                r=api.request(req.method,req.url,headers=req.all_headers(),content=req.post_data_buffer,follow_redirects=False)
                route.fulfill(status=r.status_code,headers={k:v for k,v in r.headers.items() if k not in {'content-length','content-encoding'}},body=r.content)
            context.route('**/*',route_request);page.on('pageerror',lambda error:errors.append(str(error)))
            def dialog(value):
                dialogs.append(value.type);value.accept() if accept_dialog else value.dismiss()
            page.on('dialog',dialog)
            def rows(kind):return api.get('/api/document-studio/'+kind).json()
            def catalog(template,variant=None):
                page.goto(ORIGIN+'/documents/demo#templates')
                if variant:page.locator('[data-create-template="'+template+'"]').locator('..').locator('select').select_option(variant)
                page.locator('[data-create-template="'+template+'"]').click();expect(page.locator('#source-form')).to_be_visible()
            # All supported widths, plus real type-screen evidence before selection.
            page.goto(ORIGIN+'/documents/demo#templates')
            expect(page.locator('[data-create-template]')).to_have_count(8)
            for width,height,label in [(1440,1000,'desktop'),(1280,900,'laptop'),(768,1024,'tablet'),(390,844,'mobile')]:
                page.set_viewport_size({'width':width,'height':height})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),label
                page.screenshot(path=str(out/f'01-type-{label}.png'),full_page=True)
            page.set_viewport_size({'width':1440,'height':1000})
            # A: one selected source, one creation despite a duplicate click.
            catalog('offer.private')
            expect(page.locator('#source-select')).to_have_value('')
            page.locator('#source-select').select_option(sources[0]['trip_id'])
            expect(page.locator('#source-summary')).to_contain_text('Dni z opisem: 2/2')
            page.screenshot(path=str(out/'02-source-desktop.png'),full_page=True)
            page.locator('#source-create').evaluate('(b)=>{b.click();b.click();}')
            expect(page.locator('#d-save')).to_be_visible();assert len(rows('drafts'))==1
            identifier=page.url.split('/')[-1];docurl='/api/document-studio/drafts/'+identifier
            assert api.get(docurl).json()['trip_snapshot']['revision']==1
            page.locator('[data-d-field="title"]').fill('Moja niezależna oferta')
            advanced=page.locator('.flow-options').filter(has=page.locator('.section-editor'))
            advanced.locator('summary').first.click();advanced.locator('summary').first.click()
            expect(page.locator('[data-d-field="title"]')).to_have_value('Moja niezależna oferta')
            page.locator('[data-d-field="offer_data.concept_only"]').check()
            page.locator('[data-d-field="offer_data.cta"]').fill('Syntetyczny kontakt do uzgodnienia')
            accept_dialog=False
            page.locator('[data-nav="trips"]').click();assert dialogs
            expect(page.locator('#d-save')).to_be_visible()
            accept_dialog=True
            page.locator('#document-review').click();expect(page.locator('#review-export')).to_be_visible()
            saved=api.get(docurl).json();assert saved['title']=='Moja niezależna oferta' and saved['document_status']=='draft'
            page.frame_locator('#review-preview').locator('#print-document').wait_for(state='attached')
            page.wait_for_function('document.querySelector("#review-preview").contentWindow.documentReady===true')
            expect(page.locator('#message')).to_be_hidden(timeout=10000)
            page.screenshot(path=str(out/'04-review-desktop.png'),full_page=True)
            with page.expect_popup() as popup:page.locator('#review-export').click()
            popup.value.wait_for_function('() => window.documentReady===true')
            assert popup.value.locator('#print-document').is_enabled();popup.value.close()
            page.locator('[data-go="drafts"]').click();expect(page.locator('#library-view')).to_be_visible()
            page.locator('[data-document-id="'+identifier+'"] [data-go^="edit-draft/"]').click()
            expect(page.locator('[data-d-field="title"]')).to_have_value(saved['title']);assert len(rows('drafts'))==1
            # E: stale document must not overwrite or navigate after a failed save.
            newer=api.put(docurl,json={'revision':saved['revision'],'title':'Inna zapisana zmiana'});newer.raise_for_status()
            page.locator('[data-d-field="title"]').fill('Niezapisana zmiana użytkownika')
            page.locator('#document-review').click();expect(page.locator('#message')).to_contain_text('zmieniły się')
            expect(page.locator('[data-d-field="title"]')).to_have_value('Niezapisana zmiana użytkownika')
            assert 'edit-draft/' in page.url and len(rows('drafts'))==1
            # B: prepare a real itinerary before source save / document creation.
            catalog('offer.self_guide');page.locator('.source-paths .source-new').click()
            page.locator('#source-title').fill('Nowy Self-Guide — program')
            page.locator('#source-destination').fill('Kierunek syntetyczny')
            before=len(rows('trips'));page.locator('#source-create').click()
            expect(page.locator('#save-trip')).to_be_visible();assert len(rows('trips'))==before and len(rows('drafts'))==1
            expect(page.locator('#flow-continue')).to_be_disabled()
            page.locator('[data-field="days.0.title"]').fill('Pierwszy dzień gotowego programu')
            page.locator('[data-field="days.0.public_description"]').fill('Opis przygotowany przed dokumentem.')
            page.locator('[data-add-stop="0"]').click();page.locator('[data-field="days.0.stops.0.name"]').fill('Własny punkt programu')
            # Lost successful source response must be resolved by stable-ID read-back.
            fault={'method':'POST','path':'/api/document-studio/trips','commit':True}
            page.locator('#save-trip').click();expect(page.locator('#flow-continue')).to_be_enabled()
            assert len(rows('trips'))==before+1 and len(rows('drafts'))==1
            source_id=page.url.split('/')[-1]
            page.reload();expect(page.locator('#flow-continue')).to_be_enabled()
            expect(page.locator('[data-field="days.0.stops.0.name"]')).to_have_value('Własny punkt programu')
            page.screenshot(path=str(out/'02-prepare-program.png'),full_page=True)
            # Explicit creation failure does not create a second Trip on retry.
            fault={'method':'POST','path':'/api/document-studio/drafts','commit':False}
            page.locator('#flow-continue').click();expect(page.locator('#message')).to_contain_text('controlled flow failure')
            assert len(rows('drafts'))==1
            page.locator('#flow-continue').click();expect(page.locator('#d-save')).to_be_visible()
            second=api.get('/api/document-studio/drafts/'+page.url.split('/')[-1]).json()
            assert second['trip_snapshot']['days'][0]['stops'][0]['name']=='Własny punkt programu'
            assert second['trip_snapshot']['trip_id']==source_id and len(rows('trips'))==before+1
            source=api.get('/api/document-studio/trips/'+source_id).json();source['days'][0]['stops'][0]['name']='Późniejsza zmiana źródła'
            api.put('/api/document-studio/trips/'+source_id,json=source).raise_for_status()
            assert api.get('/api/document-studio/drafts/'+second['document_id']).json()==second
            page.screenshot(path=str(out/'03-document-editor.png'),full_page=True)
            # D: a saved Trip enters the same chooser already selected.
            page.goto(ORIGIN+'/documents/demo#trips/'+source_id)
            page.locator('#create-draft').click();page.locator('[data-create-template="pilot.basic"]').click()
            expect(page.locator('#source-select')).to_have_count(0)
            expect(page.locator('#source-summary')).to_contain_text('Nowy Self-Guide')
            fault={'method':'POST','path':'/api/document-studio/drafts','commit':True}
            page.locator('#source-create').click();expect(page.locator('#d-save')).to_be_visible()
            assert len(rows('drafts'))==3  # ambiguous document success recovered, not repeated
            # C: Campaign is edited/saved first; document remains separate.
            catalog('marketing.collection','theme_collection');page.locator('.source-paths .source-new').click()
            page.locator('#source-title').fill('Kolekcja syntetyczna')
            page.locator('#source-theme').fill('Wspólny temat')
            page.locator('#source-trip-picker [data-source-filter="category"]').select_option('private')
            page.locator('#source-trips').select_option(sources[0]['trip_id'])
            page.locator('#source-trip-picker [data-source-filter="category"]').select_option('school')
            page.locator('#source-trips').select_option(sources[1]['trip_id'])
            expect(page.locator('#source-trip-picker .source-selected button')).to_have_count(2)
            campaigns_before=len(rows('campaigns'));page.locator('#source-create').click()
            expect(page.locator('#m-save')).to_be_visible();assert len(rows('campaigns'))==campaigns_before
            page.locator('[data-m-field="cta"]').fill('Kontakt kampanii — TEST')
            page.locator('[data-m-move="1,-1"]').click()
            fault={'method':'POST','path':'/api/document-studio/campaigns','commit':True,'timeout':True}
            page.locator('#m-save').click();expect(page.locator('#m-export')).to_be_enabled()
            assert len(rows('campaigns'))==campaigns_before+1 and len(rows('drafts'))==3
            campaign_id=page.url.split('/')[-1];source_campaign=api.get('/api/document-studio/campaigns/'+campaign_id).json()
            assert source_campaign['items'][0]['trip_id']==sources[1]['trip_id']
            page.locator('#m-export').click();expect(page.locator('#document-review')).to_be_visible()
            marketing_id=page.url.split('/')[-1]
            page.locator('[data-m-field="title"]').fill('Tytuł wyłącznie dokumentu')
            expect(page.locator('.flow-source-info')).to_contain_text('Kolekcja syntetyczna')
            page.locator('#document-review').click();expect(page.locator('#review-format')).to_be_visible()
            page.locator('#review-format').select_option('social')
            with page.expect_popup() as popup:page.locator('#review-export').click()
            popup.value.wait_for_function('() => window.documentReady===true')
            assert popup.value.locator('.sheet').first.evaluate('(el)=>[el.offsetWidth,el.offsetHeight]')==[1080,1350]
            popup.value.close()
            assert api.get('/api/document-studio/campaigns/'+campaign_id).json()==source_campaign
            assert api.get('/api/document-studio/drafts/'+marketing_id).json()['title']=='Tytuł wyłącznie dokumentu'
            # Back/Forward restore saved IDs/state, never another POST.
            count=len(rows('drafts'));page.evaluate('history.back()');expect(page.locator('#m-save')).to_be_visible()
            page.evaluate('history.forward()');expect(page.locator('#review-export')).to_be_visible()
            assert len(rows('drafts'))==count
            page.wait_for_function('document.querySelector("#review-preview").contentWindow.documentReady===true')
            expect(page.locator('#message')).to_be_hidden(timeout=10000)
            page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(out/'04-review-mobile.png'),full_page=True)
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            catalog('offer.school');assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.screenshot(path=str(out/'02-source-mobile.png'),full_page=True)
            # Pause saves only the source.
            page.locator('.source-paths .source-new').click();page.locator('#source-create').click()
            page.locator('#flow-pause').click();expect(page.locator('#source-library-filters')).to_be_visible()
            assert len(rows('drafts'))==count
            assert not errors,errors
            assert not external,external
            context.unroute_all(behavior='wait')
            browser.close()
    print('Creation flow PASS: existing/new Trip, prepared itinerary, explicit source saves, campaign/document independence, review A4/social, preselection, stale save, failure/retry/read-back, double submit, Back/Forward/reload, collapse and mobile; isolated adapters.')


if __name__=='__main__':run_flow()
