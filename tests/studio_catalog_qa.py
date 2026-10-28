"""Catalogue/editor/print acceptance on real cloud routers with isolated fake stores."""
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pytest
from playwright.sync_api import expect, sync_playwright
from pypdf import PdfReader


def run_catalog():
    from test_cloud_demo import cloud_demo, ORIGIN
    artifacts = ROOT/'local-data'/'studio-catalog-qa'
    artifacts.mkdir(parents=True, exist_ok=True)
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv('PLANNING_MODE','mock')
        for key in ('K_SERVICE','OPENAI_API_KEY','GOOGLE_MAPS_API_KEY','GOOGLE_PLACES_API_KEY','GOOGLE_ROUTES_API_KEY','WAHA_API_KEY','WAHA_WEBHOOK_HMAC_KEY'):
            patch.delenv(key,raising=False)
        demo=cloud_demo.__wrapped__(patch)
        with demo.client() as client, sync_playwright() as p:
            browser=p.chromium.launch()
            context=browser.new_context(viewport={'width':1440,'height':1000})
            errors=[];external=[]
            def route_request(route):
                request=route.request
                if not request.url.startswith(ORIGIN+'/'):
                    external.append(request.url);route.abort();return
                r=client.request(request.method,request.url,headers=request.all_headers(),content=request.post_data_buffer,follow_redirects=False)
                headers={k:v for k,v in r.headers.items() if k not in {'content-length','content-encoding'}}
                route.fulfill(status=r.status_code,headers=headers,body=r.content)
            context.route('**/*',route_request)
            page=context.new_page()
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('dialog',lambda dialog:dialog.accept())
            page.goto(ORIGIN+'/hub')
            page.locator('#documents-link').click()
            expect(page.locator('.template-group')).to_have_count(3)
            expect(page.locator('.template-card')).to_have_count(8)
            page.screenshot(path=str(artifacts/'catalog-desktop.png'),full_page=True)
            cases=[('offer.private','standard'),('offer.self_guide','standard'),('offer.school','standard'),('offer.incentive','standard'),('pilot.basic','standard'),('pilot.advanced','standard'),('pilot.knowledge','standard'),('marketing.collection','new_trips'),('marketing.collection','theme_collection')]
            for template,variant in cases:
                page.goto(ORIGIN+'/documents/demo#templates')
                card=page.locator('[data-create-template="'+template+'"]').locator('..')
                if template=='marketing.collection':card.locator('select').select_option(variant)
                page.locator('[data-create-template="'+template+'"]').click()
                expect(page.locator('#source-form')).to_be_visible()
                if template=='offer.private':
                    page.locator('#source-select').select_option('new')
                    page.locator('#source-title').fill('Żółte góry — dwa dni')
                    page.locator('#source-days').fill('2')
                elif template!='marketing.collection':page.locator('#source-select').select_option('demo-canada' if template in {'pilot.advanced','pilot.knowledge'} else 'demo-iceland')
                page.locator('#source-create').click()
                save='#m-save' if template=='marketing.collection' else '#d-save'
                expect(page.locator(save)).to_be_visible(timeout=20000)
                document_id=page.url.split('/')[-1]
                if template=='marketing.collection':
                    expect(page.locator('[data-m-field="layout_variant"]')).to_have_value(variant)
                if template=='offer.private':
                    page.locator('[data-d-field="offer_data.concept_only"]').check()
                    page.locator('[data-d-field="offer_data.cta"]').fill('Kontakt do uzupełnienia')
                # Add, edit, reorder, hide and restore sections without changing source data.
                kinds=('text','list','table','callout','day','image','gallery') if template=='offer.private' else ('text','list','table')
                for kind in kinds:
                    page.locator('#s-new-kind').select_option(kind)
                    page.locator('#s-add').click()
                before=page.locator('.section-editor [data-section-id]').count()
                page.locator('#s-new-kind').select_option('callout');page.locator('#s-add').click()
                page.locator('.section-editor [data-section-id]').last.locator('[data-s-remove]').click()
                assert page.locator('.section-editor [data-section-id]').count()==before
                section=page.locator('.section-editor [data-section-id]').filter(has=page.locator('input[value="Tekst"]'))
                section_id=section.get_attribute('data-section-id')
                section=page.locator('[data-section-id="'+section_id+'"]')
                section.locator('input[data-s-field$=".title"]').fill('Własne informacje — żółć')
                section.locator('textarea[data-s-field$=".body"]').fill('MARKER_BEGIN '+('Długi opis o górach i podróży. '*90)+' MARKER_END')
                page.locator('textarea[data-s-field$=".items"]').fill('Pierwszy punkt — żółć\nDrugi punkt')
                page.locator('textarea[data-s-field$=".rows"]').fill('Pierwsza komórka\tDruga komórka — żółć')
                if template=='offer.private':
                    import io
                    from PIL import Image
                    buffer=io.BytesIO();Image.new('RGB',(20,12),'orange').save(buffer,'PNG')
                    page.locator('#s-file').set_input_files({'name':'test.png','mimeType':'image/png','buffer':buffer.getvalue()})
                    page.locator('#s-rights').check();page.locator('#s-upload').click()
                    page.wait_for_function('document.querySelector("#s-upload")?.disabled === false')
                    assets=client.get('/api/document-studio/assets').json()
                    assert assets
                    gallery=page.locator('.section-editor [data-section-id]').filter(has=page.locator('input[value="Galeria"]'))
                    gallery.locator('[data-s-image-add]').click()
                    gallery.locator('select[data-s-field$=".asset_id"]').select_option(assets[-1]['asset_id'])
                # Move the custom text above other custom sections, then hide/restore it.
                section.locator('[data-s-move$=",-1"]').click()
                section=page.locator('[data-section-id="'+section_id+'"]')
                checkbox=section.locator('input[type="checkbox"]')
                checkbox.uncheck();checkbox.check()
                page.locator(save).click()
                expect(page.locator('#message')).to_contain_text('zapisan',timeout=15000)
                editor_body=page.locator('[data-section-id="'+section_id+'"] textarea[data-s-field$=".body"]')
                editor_body.fill(editor_body.input_value()+' SECOND_SAVE')
                with page.expect_response(lambda r:r.url.endswith('/drafts/'+document_id) and r.request.method=='PUT') as second:
                    page.locator(save).click()
                assert second.value.status==200 and second.value.json()['revision']==3
                page.reload()
                expect(page.locator(save)).to_be_visible(timeout=20000)
                expect(page.locator('input[data-s-field$=".title"]').filter(visible=True).last).to_be_visible()
                saved=client.get('/api/document-studio/drafts/'+document_id).json()
                assert saved['layout_variant']==variant
                assert any(s['title']=='Własne informacje — żółć' and 'MARKER_END' in s['body'] and 'SECOND_SAVE' in s['body'] and s['visible'] for s in saved['sections'])
                preview=context.new_page()
                preview.goto(ORIGIN+'/api/document-studio/drafts/'+document_id+'/preview')
                preview.wait_for_function('window.documentReady === true',timeout=20000)
                assert preview.evaluate('window.layoutErrors')==[],(template,preview.evaluate('window.layoutErrors'))
                assert preview.locator('#print-document').is_enabled(),template
                assert preview.evaluate('[...document.querySelectorAll(".page-body")].every(x=>x.scrollHeight<=x.clientHeight+1)'),template
                path=artifacts/(template+'-'+variant+'.pdf')
                preview.pdf(path=str(path),prefer_css_page_size=True,print_background=True)
                reader=PdfReader(path)
                text='\n'.join(p.extract_text() for p in reader.pages)
                assert 'MARKER_BEGIN' in text and 'MARKER_END' in text,template
                assert 'ROBOCZY' in text or 'ROBOCZA' in text
                assert abs(float(reader.pages[0].mediabox.width)-595.28)<2
                if template=='marketing.collection':
                    preview.goto(ORIGIN+'/api/document-studio/drafts/'+document_id+'/preview?output_format=social')
                    preview.wait_for_function('window.documentReady === true')
                    assert preview.evaluate('window.layoutErrors')==[]
                if template=='pilot.advanced':preview.screenshot(path=str(artifacts/'advanced-preview.png'))
                preview.close()
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),template
                page.set_viewport_size({'width':1440,'height':1000})
            page.goto(ORIGIN+'/documents/demo#templates')
            for width in (390,320):
                page.set_viewport_size({'width':width,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.screenshot(path=str(artifacts/'catalog-mobile.png'),full_page=True)
            assert not errors,errors
            assert not external,external
            browser.close()
    print('Catalogue QA PASS: all eight IDs / both marketing variants; typed sections, persistence, 2/10/15 days, A4 PDF text retention, social layout, mobile; no external calls.')


if __name__=='__main__':run_catalog()
