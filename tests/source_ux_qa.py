"""DOC-UX-002: real Chromium behavior over isolated authenticated cloud routers."""
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import pytest
from playwright.sync_api import expect, sync_playwright


def run_sources():
    from test_cloud_demo import cloud_demo, ORIGIN
    artifacts=ROOT/'local-data'/'source-ux-qa';artifacts.mkdir(parents=True,exist_ok=True)
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv('PLANNING_MODE','mock')
        for key in ('K_SERVICE','OPENAI_API_KEY','GOOGLE_MAPS_API_KEY','GOOGLE_PLACES_API_KEY','GOOGLE_ROUTES_API_KEY'):
            patch.delenv(key,raising=False)
        demo=cloud_demo.__wrapped__(patch)
        with demo.client() as api, sync_playwright() as p:
            trips={}
            for key,title,categories,origin in [
                ('private','Żółte góry',['private'],'business'), ('self_guide','Samodzielna wyprawa',['self_guide'],'business'),
                ('school','Szkolna przygoda',['school'],'business'), ('incentive','Firmowy wyjazd',['incentive'],'business'),
                ('group','Grupa nad morzem',['group'],'business'), ('other','Inna podróż',['other'],'business'),
                ('multi','Kilka kategorii',['private','group'],'business'), ('unknown','Nieprzypisana podróż',[],'unknown'),
                ('demo','DEMO góry',['private'],'demo'), ('test','Automatyczny rekord QA',['private'],'synthetic_test'),
                ('named','CLOUD-PARITY synthetic DEV nazwa biznesowa',['private'],'business')]:
                r=api.post('/api/document-studio/trips',json={'title':title,'destinations':['Łódź'], 'categories':categories,'data_origin':origin,
                    'duration_days':2,'days':[{'day_number':i,'title':f'Dzień {i}'} for i in (1,2)]})
                r.raise_for_status();trips[key]=r.json()
            r=api.post('/api/document-studio/campaigns',json={'title':'Biznesowa kolekcja','data_origin':'business','items':[{'trip_id':trips['group']['trip_id']}]})
            r.raise_for_status();campaign=r.json()
            browser=p.chromium.launch();context=browser.new_context(viewport={'width':1440,'height':1000});page=context.new_page()
            errors=[];external=[];fail_draft=False;created_sources=[]
            def route_request(route):
                nonlocal fail_draft
                request=route.request
                if not request.url.startswith(ORIGIN+'/'):
                    external.append(request.url);route.abort();return
                if fail_draft and request.method=='POST' and request.url.endswith('/drafts'):
                    fail_draft=False
                    route.fulfill(status=503,content_type='application/json',body='{"detail":"injected draft failure"}');return
                response=api.request(request.method,request.url,headers=request.all_headers(),content=request.post_data_buffer,follow_redirects=False)
                if request.method=='POST' and request.url.endswith('/trips') and response.status_code==201:
                    created_sources.append(response.json())
                headers={k:v for k,v in response.headers.items() if k not in {'content-length','content-encoding'}}
                route.fulfill(status=response.status_code,headers=headers,body=response.content)
            context.route('**/*',route_request)
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('dialog',lambda dialog:dialog.accept())
            def chooser(template):
                page.goto(ORIGIN+'/documents/demo#templates')
                page.locator('[data-create-template="'+template+'"]').click()
                expect(page.locator('#source-form')).to_be_visible()
                page.locator('#source-picker .source-advanced').evaluate('(el)=>el.open=true')
            def ids(selector='#source-select'):
                return page.locator(selector+' option').evaluate_all('(options)=>options.map(o=>o.value)')
            for category in ('private','self_guide','school','incentive'):
                chooser('offer.'+category)
                expect(page.locator('#source-picker [data-source-filter="category"]')).to_have_value(category)
                expect(page.locator('#source-select')).to_have_value('')
                assert trips[category]['trip_id'] in ids() and trips['group']['trip_id'] not in ids()
                assert trips['demo']['trip_id'] not in ids() and trips['test']['trip_id'] not in ids()
            chooser('offer.private')
            assert trips['named']['trip_id'] in ids()  # no name-based exclusion
            expect(page.locator('#source-create')).to_be_disabled()
            page.locator('#source-picker [data-source-filter="all"]').check()
            page.locator('#source-select').select_option(trips['group']['trip_id'])
            page.locator('#source-picker [data-source-filter="search"]').fill('GRUPA')
            expect(page.locator('#source-select')).to_have_value(trips['group']['trip_id'])
            page.locator('#source-picker [data-source-filter="search"]').fill('zolte')
            assert trips['private']['trip_id'] in ids()
            expect(page.locator('#source-select')).to_have_value('')
            page.locator('#source-select').focus();page.keyboard.press('Home');page.keyboard.press('ArrowDown')
            expect(page.locator('#source-select')).to_have_value(trips['private']['trip_id'])
            page.locator('#source-picker [data-source-filter="search"]').fill('')
            page.locator('#source-picker [data-source-filter="all"]').uncheck()
            page.locator('#source-picker [data-source-filter="unassigned"]').check()
            assert trips['unknown']['trip_id'] in ids()
            page.locator('#source-picker [data-source-filter="demo"]').check()
            assert trips['demo']['trip_id'] in ids() and trips['test']['trip_id'] not in ids()
            page.locator('#source-picker [data-source-filter="test"]').check()
            assert trips['test']['trip_id'] in ids()
            page.locator('#source-picker [data-source-filter="all"]').check()
            page.locator('#source-select').select_option(trips['group']['trip_id'])
            page.locator('#source-create').click();expect(page.locator('#d-save')).to_be_visible()
            document_id=page.url.split('/')[-1]
            doc=api.get('/api/document-studio/drafts/'+document_id).json()
            assert doc['template_id']=='offer.private' and doc['trip_snapshot']['categories']==['group']
            for template in ('pilot.basic','pilot.advanced','pilot.knowledge'):
                chooser(template)
                assert all(trips[key]['trip_id'] in ids() for key in ('group','private','self_guide','school','incentive','unknown'))
                assert trips['test']['trip_id'] not in ids()
            chooser('offer.self_guide')
            page.locator('.source-paths .source-new').click()
            expect(page.locator('[name="source-categories"][value="self_guide"]')).to_be_checked()
            page.locator('.source-options').evaluate('(el)=>el.open=true')
            page.locator('[name="source-categories"][value="group"]').check()
            page.locator('#source-title').fill('Nowy Self-Guide — Żółć')
            expect(page.locator('#source-origin')).to_have_value('business')
            page.locator('#source-create').click();expect(page.locator('#save-trip')).to_be_visible()
            assert len(created_sources)==0
            page.locator('#save-trip').click();expect(page.locator('#flow-continue')).to_be_enabled()
            fail_draft=True;page.locator('#flow-continue').click()
            expect(page.locator('#message')).to_contain_text('injected draft failure')
            assert len(created_sources)==1
            assert created_sources[0]['trip_id'] in page.url
            page.locator('#flow-continue').click();expect(page.locator('#d-save')).to_be_visible()
            assert len(created_sources)==1
            source=created_sources[0];assert source['categories']==['self_guide','group']
            page.goto(ORIGIN+'/documents/demo#trips/'+source['trip_id'])
            expect(page.locator('[name="categories"][value="self_guide"]')).to_be_checked()
            page.locator('.source-options').evaluate('(el)=>el.open=true')
            page.locator('[name="categories"][value="school"]').check()
            page.locator('#save-trip').click();expect(page.locator('#message')).to_have_text('Program wycieczki zapisany.')
            page.reload();expect(page.locator('[name="categories"][value="school"]')).to_be_checked()
            assert api.get('/api/document-studio/trips/'+source['trip_id']).json()['categories']==['self_guide','school','group']
            chooser('marketing.collection')
            assert campaign['campaign_id'] in ids() and 'demo-northern-journeys' not in ids()
            expect(page.locator('#source-select')).to_have_value('')
            page.locator('#source-picker [data-source-filter="search"]').fill('Biznesowa')
            assert campaign['campaign_id'] in ids()
            page.locator('.source-paths .source-new').click();page.locator('#source-title').fill('Nowa kampania')
            page.locator('#source-trip-picker [data-source-filter="category"]').select_option('private')
            page.locator('#source-trips').select_option(trips['private']['trip_id'])
            page.locator('#source-trip-picker [data-source-filter="category"]').select_option('group')
            page.locator('#source-trips').select_option(trips['group']['trip_id'])
            expect(page.locator('#source-trip-picker .source-selected button')).to_have_count(2)
            page.locator('#source-create').click();expect(page.locator('#m-save')).to_be_visible()
            expect(page.locator('[data-m-item]')).to_have_count(2)
            assert trips['private']['trip_id'] not in ids('#m-add-trip')
            page.locator('#m-trip-picker [data-source-filter="category"]').select_option('school')
            page.locator('#m-trip-picker [data-source-filter="search"]').fill('Szkolna')
            page.locator('#m-add-trip').select_option(trips['school']['trip_id']);page.locator('#m-add').click()
            expect(page.locator('[data-m-item]')).to_have_count(3)
            expect(page.locator('#m-trip-picker [data-source-filter="category"]')).to_have_value('school')
            assert trips['school']['trip_id'] not in ids('#m-add-trip')
            page.locator('#m-save').click();expect(page.locator('#message')).to_have_text('Kampania zapisana.')
            campaign_id=page.url.split('/')[-1]
            saved=api.get('/api/document-studio/campaigns/'+campaign_id).json()
            assert saved['revision']==1 and len(saved['items'])==3
            page.reload();expect(page.locator('[data-m-item]')).to_have_count(3)
            page.goto(ORIGIN+'/documents/demo#trips')
            assert page.locator('[data-source-id="'+trips['test']['trip_id']+'"]').count()==0
            assert page.locator('[data-source-id="'+trips['demo']['trip_id']+'"]').count()==0
            assert page.locator('[data-source-id="'+trips['unknown']['trip_id']+'"]').count()==1
            page.locator('#source-library-filters [data-source-filter="search"]').fill('lodz')
            assert page.locator('[data-source-id="'+trips['private']['trip_id']+'"]').count()==1
            page.screenshot(path=str(artifacts/'sources-desktop.png'),full_page=True)
            page.set_viewport_size({'width':390,'height':844})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.screenshot(path=str(artifacts/'sources-mobile.png'),full_page=True)
            chooser('offer.private')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.screenshot(path=str(artifacts/'chooser-mobile.png'),full_page=True)
            assert not errors,errors
            assert not external,external
            browser.close()
    print('Source UX PASS: category preferences, all/unknown/demo/test, Polish search, keyboard, stable choice, cross-category draft, create/retry, multi-category persistence, campaigns/multi-selection/marketing, mobile; isolated cloud adapters.')


if __name__=='__main__':run_sources()
