"""DOC-FLOW-005: visible responsibilities, excluded controls and navigation."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pytest
from playwright.sync_api import expect,sync_playwright


def audit_before():
    from test_cloud_demo import cloud_demo,ORIGIN
    out=ROOT/'local-data'/'flow-structure-qa';out.mkdir(parents=True,exist_ok=True)
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv('PLANNING_MODE','mock')
        demo=cloud_demo.__wrapped__(patch)
        with demo.client() as api,sync_playwright() as p:
            browser=p.chromium.launch();page=browser.new_page(viewport={'width':1440,'height':1000})
            def proxy(route):
                req=route.request
                assert req.url.startswith(ORIGIN+'/')
                r=api.request(req.method,req.url,content=req.post_data_buffer,headers=req.all_headers())
                route.fulfill(status=r.status_code,headers={k:v for k,v in r.headers.items() if k not in {'content-length','content-encoding'}},body=r.content)
            page.route('**/*',proxy)
            page.goto(ORIGIN+'/documents/demo#templates')
            page.locator('[data-create-template="offer.self_guide"]').click()
            expect(page.locator('#source-select')).to_be_visible()
            assert page.locator('#source-select option[value="new"]').count()==1
            expect(page.locator('#source-picker .source-new')).to_be_visible()
            page.locator('#source-picker .source-new').click()
            expect(page.locator('#new-source')).to_be_visible()
            expect(page.locator('#source-select')).to_be_visible()
            expect(page.locator('#source-picker [data-source-filter="origin"]')).to_be_visible()
            page.screenshot(path=str(out/'before-self-guide-desktop.png'),full_page=True)
            page.set_viewport_size({'width':390,'height':844})
            page.screenshot(path=str(out/'before-self-guide-mobile.png'),full_page=True)
            result={'baseline':'b15388f','duplicate_create_controls':2,'existing_selector_visible_with_new_form':True,
                    'origin_filter_visible_with_new_form':True,'select_size':page.locator('#source-select').get_attribute('size')}
            (out/'before.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
            page.unroute_all(behavior='wait');browser.close()
    print('BEFORE reproduced: two create-new controls; existing selector and administrative filters alongside new-trip form.')



def run_structure():
    from test_cloud_demo import cloud_demo,ORIGIN
    out=ROOT/'local-data'/'flow-structure-qa';out.mkdir(parents=True,exist_ok=True)
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv('PLANNING_MODE','mock')
        for key in ('K_SERVICE','OPENAI_API_KEY','GOOGLE_MAPS_API_KEY','GOOGLE_PLACES_API_KEY','GOOGLE_ROUTES_API_KEY'):
            patch.delenv(key,raising=False)
        demo=cloud_demo.__wrapped__(patch)
        with demo.client() as api,demo.client('reader') as reader,sync_playwright() as p:
            browser=p.chromium.launch();context=browser.new_context(viewport={'width':1440,'height':1000});page=context.new_page()
            errors=[];requests=[];identity=api;accept=True;empty_sources=True
            def proxy(route):
                req=route.request
                assert req.url.startswith(ORIGIN+'/'),req.url
                requests.append((req.method,req.url))
                if empty_sources and req.method=='GET' and req.url in [ORIGIN+'/api/document-studio/trips',ORIGIN+'/api/document-studio/campaigns']:
                    route.fulfill(status=200,content_type='application/json',body='[]');return
                r=identity.request(req.method,req.url,content=req.post_data_buffer,headers=req.all_headers(),follow_redirects=False)
                route.fulfill(status=r.status_code,headers={k:v for k,v in r.headers.items() if k not in {'content-length','content-encoding'}},body=r.content)
            context.route('**/*',proxy);page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('dialog',lambda d:d.accept() if accept else d.dismiss())
            def go(path):page.goto(ORIGIN+'/documents/demo#'+path)
            def photo(name):
                expect(page.locator('#message')).to_be_hidden(timeout=12000)
                page.screenshot(path=str(out/(name+'.png')),full_page=True)
            def absent(*selectors):
                for selector in selectors:expect(page.locator(selector)).to_have_count(0)
            def catalog(template,variant='standard'):
                go('templates');expect(page.locator('[data-create-template]')).to_have_count(8)
                if template=='marketing.collection':page.locator('.catalog-variant').select_option(variant)
                page.locator('[data-create-template="'+template+'"]').click();expect(page.locator('#source-form')).to_be_visible()
            def extras(host='#source-picker'):page.locator(host+' .source-advanced').evaluate('(el)=>el.open=true')
            def drafts():return api.get('/api/document-studio/drafts').json()
            go('drafts');expect(page.locator('#library-view')).to_be_visible()
            expect(page.locator('.library-document')).to_have_count(0)
            expect(page.locator('#library-view [data-go="templates"]')).to_be_visible();photo('00-empty-documents')
            go('templates');expect(page.locator('[data-create-template]')).to_have_count(8);photo('01-landing-and-types')
            absent('#source-select','#source-title','[data-source-filter]','#review-export')
            # No saved business sources: existing route has a truthful empty selection, one new path.
            catalog('offer.self_guide');expect(page.locator('#source-select')).to_have_value('')
            expect(page.locator('#source-create')).to_be_disabled();expect(page.locator('.source-new:visible')).to_have_count(1)
            absent('option[value="new"]','#new-source','#template')
            assert page.locator('#source-select').get_attribute('size') is None
            expect(page.locator('[data-source-filter="origin"]')).to_be_hidden()
            photo('02-empty-existing')
            # Basic new form has no competing existing selector or filters.
            page.locator('.source-new').click();expect(page.locator('#source-title')).to_be_visible()
            absent('#source-select','#source-picker','[data-source-filter]','#template')
            expect(page.locator('#source-title')).to_have_attribute('required','')
            expect(page.locator('#source-origin')).to_be_hidden();photo('03-new-self-guide')
            empty_sources=False
            page.locator('#source-title').fill('Nowy Self-Guide QA')
            page.locator('#source-destination').fill('Region próbny')
            # Changing paths respects dirty state, rejected Back keeps values.
            accept=False;page.locator('.source-paths button').first.click()
            expect(page.locator('#source-title')).to_have_value('Nowy Self-Guide QA')
            accept=True;before=len(drafts());page.locator('#source-create').click()
            expect(page.locator('#save-trip')).to_be_visible();absent('#template','#source-select')
            page.locator('[data-field="days.0.public_description"]').fill('Program opracowany przed dokumentem.')
            page.locator('[data-add-stop="0"]').click();page.locator('[data-field="days.0.stops.0.name"]').fill('Punkt QA')
            expect(page.locator('#flow-continue')).to_be_disabled();photo('04-trip-preparation')
            page.locator('#save-trip').click();expect(page.locator('#flow-continue')).to_be_enabled()
            tid=page.url.split('/')[-1];assert len(drafts())==before
            page.reload();expect(page.locator('#flow-continue')).to_be_enabled()
            # A new path after saving must allocate a new Trip, never reuse the saved ID.
            page.locator('.back').click();page.locator('[data-go="create-document/offer.self_guide/standard"]').click()
            page.locator('.source-new').click();expect(page.locator('#source-title')).to_have_value('Nowa wycieczka')
            page.locator('#source-title').fill('Osobny nowy program QA');page.locator('#source-create').click()
            expect(page.locator('#save-trip')).to_be_visible()
            page.locator('#flow-pause').click();expect(page.locator('#source-library-filters')).to_be_visible()
            saved_sources=api.get('/api/document-studio/trips').json()
            assert next(t for t in saved_sources if t['title']=='Osobny nowy program QA')['trip_id']!=tid
            assert len(drafts())==before
            go('prepare-trip/offer.self_guide/standard/'+tid);expect(page.locator('#flow-continue')).to_be_enabled()
            page.locator('#flow-continue').click();expect(page.locator('#d-save')).to_be_visible()
            absent('#source-select','#template','#d-export','[data-source-filter]')
            docid=page.url.split('/')[-1];assert len(drafts())==before+1
            page.wait_for_function('document.querySelector("#d-preview").contentWindow.documentReady===true')
            expect(page.frame_locator('#d-preview').locator('#print-document')).to_be_hidden()
            assert page.locator('.trip-document-controls').evaluate('el=>getComputedStyle(el).maxHeight')=='none'
            photo('05-document-editor')
            page.locator('[data-d-field="offer_data.concept_only"]').check()
            page.locator('[data-d-field="offer_data.cta"]').fill('Kontakt QA')
            page.locator('#document-review').click();expect(page.locator('#review-export')).to_be_visible()
            page.wait_for_function('document.querySelector("#review-preview").contentWindow.documentReady===true')
            absent('#template','#source-select','#source-title','#d-save')
            expect(page.frame_locator('#review-preview').locator('#print-document')).to_be_hidden()
            photo('06-review')
            with page.expect_popup() as popup:page.locator('#review-export').click()
            popup.value.wait_for_function('()=>window.documentReady===true');popup.value.close()
            page.locator('[data-go="drafts"]').click();expect(page.locator('#library-view')).to_be_visible();photo('07-library')
            page.locator('[data-document-id="'+docid+'"] [data-go^="edit-draft/"]').click();expect(page.locator('#d-save')).to_be_visible()
            assert len(drafts())==before+1
            # Fixed Trip: choose type once, confirm without search, including deep link/reload.
            go('trips/'+tid);expect(page.locator('#create-draft')).to_be_visible();absent('#template')
            page.locator('#create-draft').click();expect(page.locator('[data-create-template]')).to_have_count(7)
            page.locator('[data-create-template="offer.private"]').click()
            expect(page.locator('#source-summary')).to_contain_text('Nowy Self-Guide QA')
            absent('#source-picker','#source-select','.source-new')
            page.reload();expect(page.locator('#source-create')).to_be_enabled();absent('#source-select')
            photo('08-fixed-trip')
            page.locator('#edit-source').click();expect(page.locator('#save-trip')).to_be_visible()
            absent('#template','#source-select')
            page.locator('.back').click();expect(page.locator('#source-summary')).to_contain_text('Nowy Self-Guide QA')
            absent('#source-select')
            page.locator('#source-create').click();expect(page.locator('#d-save')).to_be_visible()
            assert drafts()[-1] is not None
            # Many/category/origin cases keep filtering logic, without automatic choice.
            extra_trips=[]
            for i in range(14):
                result=api.post('/api/document-studio/trips',json={'title':f'Zestaw QA {i}','categories':[] if i==0 else ['private'],
                    'data_origin':'synthetic_test' if i==1 else 'demo' if i==2 else 'business'})
                result.raise_for_status();extra_trips.append(result.json())
            page.reload();expect(page.locator('#d-save')).to_be_visible()
            catalog('offer.incentive');expect(page.locator('#source-select')).to_have_value('')
            expect(page.locator('#source-picker .source-result-state')).to_contain_text('Brak wycieczek')
            extras();page.locator('[data-source-filter="unassigned"]').check()
            assert page.locator('#source-select option').count()>1
            page.locator('[data-source-filter="all"]').check();page.locator('[data-source-filter="origin"]').select_option('synthetic_test')
            assert page.locator('#source-select option').count()==2
            expect(page.locator('[data-source-filter="demo"]')).to_be_hidden()
            page.locator('[data-source-filter="origin"]').select_option('demo')
            assert page.locator('#source-select option').count()>=2
            page.locator('[data-source-filter="origin"]').select_option('regular')
            page.locator('#source-picker .source-advanced').evaluate('(el)=>el.open=false')
            page.locator('[data-source-filter="search"]').focus();page.keyboard.press('Tab')
            assert page.evaluate('document.activeElement.tagName')=='SUMMARY'
            page.keyboard.press('Tab')
            assert page.evaluate('document.activeElement.id')=='source-select'
            expect(page.locator('.source-filter-summary')).to_contain_text('wszystkie kategorie')
            photo('09-existing-many')
            page.set_viewport_size({'width':390,'height':844});photo('10-existing-mobile')
            assert page.locator('#source-select').bounding_box()['height']<70
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.set_viewport_size({'width':1440,'height':1000})
            # Campaign creation is separate from Campaign selection and document editing.
            catalog('marketing.collection','theme_collection');page.locator('.source-new').click()
            expect(page.locator('#source-trip-picker')).to_be_visible();absent('#source-picker','#source-select')
            page.locator('#source-title').fill('Kolekcja strukturalna QA')
            page.locator('#source-theme').fill('Temat QA');page.locator('#source-trips').select_option([tid,extra_trips[0]['trip_id']])
            expect(page.locator('#source-trip-picker .source-selected button')).to_have_count(2)
            photo('11-new-campaign');page.locator('#source-create').click();expect(page.locator('#m-save')).to_be_visible()
            absent('[data-m-field="layout_variant"]','#template')
            page.locator('[data-m-field="cta"]').fill('Kontakt kolekcji QA')
            page.locator('#m-save').click();expect(page.locator('#m-export')).to_be_enabled()
            cid=page.url.split('/')[-1];campaign=api.get('/api/document-studio/campaigns/'+cid).json()
            expect(page.locator('#m-validation')).not_to_contain_text('Uzupełnij CTA')
            expect(page.frame_locator('#m-preview').locator('#print-document')).to_be_hidden()
            assert page.locator('.marketing-controls').evaluate('el=>getComputedStyle(el).maxHeight')=='none'
            photo('12-campaign-preparation');page.locator('#m-export').click();expect(page.locator('#document-review')).to_be_visible()
            mid=page.url.split('/')[-1]
            absent('#m-trip-picker','#m-add','[data-m-field="layout_variant"]','#m-export')
            page.locator('[data-m-field="title"]').fill('Niezależny dokument QA')
            page.locator('#document-review').click();expect(page.locator('#review-format')).to_be_visible()
            page.locator('#review-format').select_option('social')
            page.wait_for_function('document.querySelector("#review-preview").contentWindow.documentReady===true')
            assert api.get('/api/document-studio/campaigns/'+cid).json()==campaign
            count=len(drafts());page.evaluate('history.back()');expect(page.locator('#m-save')).to_be_visible()
            page.evaluate('history.forward()');expect(page.locator('#review-export')).to_be_visible()
            assert len(drafts())==count
            # Existing Campaign is a Campaign picker, never single-Trip controls.
            catalog('marketing.collection','new_trips');absent('[data-source-filter="category"]','#source-trip-picker')
            page.locator('#source-select').select_option(cid);page.locator('#source-create').click()
            expect(page.locator('#m-save')).to_be_visible();absent('#m-trip-picker')
            assert api.get('/api/document-studio/drafts/'+page.url.split('/')[-1]).json()['layout_variant']=='new_trips'
            go('campaigns/'+cid);page.locator('#create-draft').click()
            expect(page.locator('[data-create-template]')).to_have_count(1)
            page.locator('.catalog-variant').select_option('theme_collection')
            page.locator('[data-create-template="marketing.collection"]').click()
            expect(page.locator('#source-summary')).to_contain_text('Kolekcja strukturalna QA');absent('#source-select','#source-picker')
            # Standalone new campaign does not select a document type or create a draft.
            go('campaigns');expect(page.locator('[data-go="campaigns/new"]')).to_be_visible()
            count=len(drafts());page.locator('[data-go="campaigns/new"]').click()
            expect(page.locator('#source-title')).to_be_visible();absent('.flow-progress','[data-create-template]','#source-select')
            page.locator('#source-trips').select_option(tid);page.locator('#source-create').click()
            expect(page.locator('#m-save')).to_be_visible();absent('.flow-progress')
            expect(page.locator('.back')).to_have_attribute('data-go','campaigns')
            page.locator('#m-save').click();expect(page.locator('#message')).to_contain_text('Kampania zapisana')
            assert len(drafts())==count
            # Archived documents offer preview/restore, not editable content.
            value=api.get('/api/document-studio/drafts/'+mid).json()
            api.post('/api/document-studio/library/'+mid+'/archive',json={'revision':value['revision'],'operation_id':__import__('uuid').uuid4().hex}).raise_for_status()
            go('edit-draft/'+mid);expect(page.locator('h1')).to_have_text('Nie udało się otworzyć danych')
            absent('#m-save','#source-select')
            # Reader sees saved documents, preview/history and no mutation controls.
            identity=reader;go('');page.reload();expect(page.locator('#library-view')).to_be_visible()
            absent('[data-library-action]','.library-status','#library-view [data-go="templates"]')
            expect(page.locator('[data-nav="templates"]')).to_be_hidden()
            go('edit-draft/'+mid);expect(page.locator('#review-export')).to_be_visible()
            absent('#m-save','#document-review','#source-select');expect(page.locator('#review-validation')).to_contain_text('tylko do odczytu')
            assert reader.post('/api/document-studio/drafts',json={}).status_code==403
            assert not errors,errors
            (out/'after.json').write_text(json.dumps({'journeys':7,'source_paths_mutually_exclusive':True,'fixed_source_no_picker':True,
                'reader_no_mutations':True,'external_requests':0,'page_errors':errors,'screenshots':len(list(out.glob('*.png')))},indent=2),encoding='utf-8')
            context.unroute_all(behavior='wait');browser.close()
    print('Flow structure PASS: 7 journeys, empty/one/many/category/origin sources, mutually exclusive paths, fixed IDs, no duplicate controls, document-specific editors, standalone campaigns, keyboard/mobile, reader restrictions; isolated adapters.')


if __name__=='__main__':
    audit_before() if '--before' in sys.argv else run_structure()
