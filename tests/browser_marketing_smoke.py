"""Local Chromium QA for marketing.collection, including print output.

Run: python tests/browser_marketing_smoke.py
PDFs and screenshots are gitignored in local-data/marketing-qa/.
Playwright and pypdf are development tools only, never server dependencies.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

import httpx
from PIL import Image, ImageDraw
from playwright.sync_api import expect, sync_playwright
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]


def run():
    import os
    os.environ['DOCUMENT_STUDIO_FIXTURES_PATH']=str(ROOT/'tests/fixtures/legacy-demo')  # explicit historical regression dataset
    artifacts = ROOT / "local-data" / "marketing-qa"
    artifacts.mkdir(parents=True, exist_ok=True)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory(prefix="tripse-marketing-") as temporary:
        env = dict(os.environ, PLANNING_MODE="mock", DATABASE_PATH=str(Path(temporary) / "planner.sqlite3"),
                   DOCUMENT_STUDIO_DATA_PATH=str(Path(temporary) / "documents"))
        env.pop("DOCUMENT_STUDIO_DOCKER_LOCAL",None)
        process = None

        def start():
            server = subprocess.Popen([sys.executable,"-m","uvicorn","app.main:app","--host","127.0.0.1","--port",str(port),"--no-access-log"],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
            for _ in range(100):
                try:
                    if httpx.get(base+"/health",timeout=1).status_code==200:return server
                except httpx.TransportError:pass
                if server.poll() is not None:raise RuntimeError("QA server exited")
                time.sleep(.1)
            server.terminate();server.wait(timeout=10)
            raise RuntimeError("QA server readiness timeout")

        try:
            process=start()
            api=httpx.Client(base_url=base,timeout=20)
            # Own neutral test illustration, not a photograph of a destination.
            illustration=Image.new("RGB",(1200,700),"#cddfd7")
            draw=ImageDraw.Draw(illustration)
            draw.polygon([(0,700),(520,100),(900,700)],fill="#799e8b")
            draw.polygon([(480,700),(940,230),(1200,700)],fill="#a4c0ae")
            image_path=Path(temporary)/"neutral-test-illustration.png"
            illustration.save(image_path)
            upload=api.post('/api/document-studio/assets?filename=neutral-test-illustration.png&rights_confirmed=true',content=image_path.read_bytes(),headers={"Content-Type":"image/png"})
            upload.raise_for_status();asset=upload.json()['asset_id']
            trip_ids=[]
            for i in range(8):
                response=api.post('/api/document-studio/trips',json={"title":f"Kierunek {i+1} — żółte góry i jeziora", "destinations":["Region demonstracyjny"]})
                response.raise_for_status();trip_ids.append(response.json()['trip_id'])
            with sync_playwright() as playwright:
                browser=playwright.chromium.launch()
                page=browser.new_page(viewport={"width":1440,"height":1050})
                errors=[];requests=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.on('request',lambda request:requests.append(request.url))
                page.on('dialog',lambda dialog:dialog.accept())
                results=[]

                def ready(target):
                    target.wait_for_function('() => window.documentReady === true')
                    assert target.evaluate('window.layoutErrors')==[],target.evaluate('window.layoutErrors')
                    assert target.locator('#print-document').is_enabled()
                    assert target.evaluate('[...document.querySelectorAll(".page-body")].every(x=>x.scrollHeight <= x.clientHeight+1)')

                for variant in ('new_trips','theme_collection'):
                    for count in (1,3,8):
                        payload={"title":"Północne inspiracje — kolekcja 2027", "season":"Wiosna / lato 2027 — DEMO", "theme":"Góry, jeziora i przestrzeń", "description":"Podróż zaczyna się od ciekawości. Fikcyjne kierunki do prezentacji układu.", "cta":"Zaplanuj z nami kolejną podróż · kontakt@example.invalid", "layout_variant":variant,"hero_asset_id":asset,"items":[{"trip_id":trip_ids[i],"short_hook":"Przestrzeń, natura i czas na odkrywanie. Przykład redakcyjnego opisu kierunku.","highlights":["Góry","Jeziora","Mała grupa — propozycja"],"badge":"pilot" if i%2 else "new","image_asset_id":asset if i%2==0 else None} for i in range(count)]}
                        if count==8:
                            payload['items'][0]['display_title']=("Bardzo długa nazwa wyprawy przez góry, doliny i jeziora — żółć i Þingvellir. "*3)[:200]
                            payload['items'][0]['short_hook']=("Rozbudowany opis fikcyjnego kierunku. "*15)[:500]
                        response=api.post('/api/document-studio/campaigns',json=payload);response.raise_for_status()
                        campaign_id=response.json()['campaign_id']
                        page.goto(base+f'/api/document-studio/campaigns/{campaign_id}/preview')
                        ready(page)
                        expect(page.locator('.trip-card')).to_have_count(count)
                        page_count=page.locator('.sheet').count()
                        pdf_path=artifacts/f'{variant}-{count}-a4.pdf'
                        page.pdf(path=str(pdf_path),prefer_css_page_size=True,print_background=True)
                        reader=PdfReader(pdf_path)
                        assert len(reader.pages)==page_count,(variant,count,len(reader.pages),page_count)
                        pdf_text='\n'.join(p.extract_text() for p in reader.pages)
                        assert 'kontakt@example.invalid' in pdf_text
                        assert 'Termin do ustalenia' in pdf_text
                        assert 'żół' in pdf_text or 'Północne' in pdf_text
                        assert all('TRIPSE' in p.extract_text() for p in reader.pages)
                        assert abs(float(reader.pages[0].mediabox.width)-595.28)<2
                        results.append({"variant":variant,"trips":count,"format":"a4","pages":page_count})
                        if count==3:
                            page.locator('.sheet-wrap').first.screenshot(path=str(artifacts/f'{variant}-a4.png'))
                            page.goto(base+f'/api/document-studio/campaigns/{campaign_id}/preview?output_format=social')
                            ready(page)
                            dimensions=page.locator('.sheet').first.evaluate('(el)=>[el.offsetWidth,el.offsetHeight]')
                            assert dimensions==[1080,1350],dimensions
                            social_pdf=artifacts/f'{variant}-3-social.pdf'
                            page.pdf(path=str(social_pdf),prefer_css_page_size=True,print_background=True)
                            social_reader=PdfReader(social_pdf)
                            assert len(social_reader.pages)==page.locator('.sheet').count()
                            assert abs(float(social_reader.pages[0].mediabox.width)-810)<2
                            page.locator('.sheet-wrap').first.screenshot(path=str(artifacts/f'{variant}-social.png'))
                            # Verify the export button invokes browser printing.
                            page.evaluate('window.print=()=>window.printInvoked=true')
                            page.locator('#print-document').click()
                            assert page.evaluate('window.printInvoked')
                        else:
                            page.goto(base+f'/api/document-studio/campaigns/{campaign_id}/preview?output_format=social')
                            ready(page)
                            expect(page.locator('.trip-card')).to_have_count(count)
                # Long, divisible cards must paginate without losing or repeating highlights.
                huge=api.post('/api/document-studio/campaigns',json={"title":"Zbyt obszerna karta", "cta":"Kontakt", "items":[{"trip_id":trip_ids[0],"highlights":[f"EDGEH{i:03d} "+"Bardzo długi wyróżnik "*8 for i in range(80)]}]}).json()
                page.goto(base+f"/api/document-studio/campaigns/{huge['campaign_id']}/preview")
                page.wait_for_function('() => window.documentReady === true')
                ready(page)
                assert page.locator('.sheet').count()>1
                long_pdf=artifacts/'long-highlights-a4.pdf'
                page.pdf(path=str(long_pdf),prefer_css_page_size=True,print_background=True)
                long_text='\n'.join(p.extract_text() for p in PdfReader(long_pdf).pages)
                import re
                assert sorted(re.findall(r'EDGEH\d{3}',long_text))==[f'EDGEH{i:03d}' for i in range(80)]
                page.goto(base+'/documents/demo#marketing/demo-northern-journeys')
                expect(page.locator('[data-m-item]')).to_have_count(3)
                page.locator('[data-m-field="title"]').fill('Moja zapisana kolekcja — żółć')
                page.locator('[data-m-field="layout_variant"]').select_option('theme_collection')
                page.locator('[data-m-field="theme"]').fill('Góry i woda')
                page.locator('[data-m-move="2,-1"]').click()
                page.locator('[data-m-remove="1"]').click()
                page.locator('#m-trip-picker .source-advanced').evaluate('(el)=>el.open=true')
                page.locator('#m-trip-picker [data-source-filter="demo"]').check()
                page.locator('#m-add-trip').select_option('demo-norway')
                page.locator('#m-add').click()
                expect(page.locator('[data-m-item]')).to_have_count(3)
                page.locator('#m-file').set_input_files(image_path)
                page.locator('#m-rights').check()
                page.locator('#m-upload').click()
                expect(page.locator('[data-m-field="hero_asset_id"]')).not_to_have_value('')
                selected=page.locator('[data-m-field="hero_asset_id"]').input_value()
                page.locator('[data-m-field="items.0.image_asset_id"]').select_option(selected)
                page.locator('[data-m-field="items.0.image_position.x"]').evaluate('(el)=>{el.value=25;el.dispatchEvent(new Event("input",{bubbles:true}));}')
                page.locator('#m-save').click()
                expect(page.locator('#message')).to_have_text('Kampania zapisana.')
                page.screenshot(path=str(artifacts/'editor-desktop.png'),full_page=True)
                page.locator('#m-export').click()
                page.locator('.catalog-variant').select_option('theme_collection')
                page.locator('[data-create-template="marketing.collection"]').click()
                page.locator('#source-create').click()
                expect(page.locator('#document-review')).to_be_visible()
                page.locator('#document-review').click()
                with page.expect_popup() as popup:
                    page.locator('#review-export').click()
                preview=popup.value
                ready(preview)
                assert '/api/document-studio/library/'+page.url.split('/')[-1]+'/revisions/' in preview.url
                preview.close()
                page.goto(base+'/documents/demo#marketing/demo-northern-journeys')
                expect(page.locator('#campaign-origin')).to_have_count(1)
                # Missing CTA is a visible blocking validation error, not a crash.
                page.locator('[data-m-field="cta"]').fill('')
                expect(page.locator('#m-validation')).to_contain_text('Uzupełnij CTA')
                frame=page.frame_locator('#m-preview')
                expect(frame.locator('#print-document')).to_be_disabled()
                page.locator('[data-m-field="cta"]').fill('Kontakt po restarcie')
                page.locator('#m-save').click()
                expect(page.locator('#message')).to_have_text('Kampania zapisana.')
                page.set_viewport_size({"width":390,"height":844})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.screenshot(path=str(artifacts/'editor-mobile.png'),full_page=True)
                process.terminate();process.wait(timeout=10);process=start()
                page.goto(base+'/documents/demo#marketing/demo-northern-journeys')
                expect(page.locator('[data-m-field="title"]')).to_have_value('Moja zapisana kolekcja — żółć')
                expect(page.locator('[data-m-field="items.0.image_asset_id"]')).to_have_value(selected)
                expect(page.locator('[data-m-field="items.0.image_position.x"]')).to_have_value('25')
                expect(page.locator('[data-m-field="cta"]')).to_have_value('Kontakt po restarcie')
                assert not errors,errors
                assert all(url.startswith(base+'/') for url in requests),requests
                browser.close()
                (artifacts/'report.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
                api.close()
        finally:
            if process and process.poll() is None:process.terminate();process.wait(timeout=10)
    print('Marketing QA PASS: 1/3/8 trips in both variants; eight real browser PDFs; page count, A4/social dimensions, Polish text, images, editing, order, crops, missing CTA, mobile, process restart; no external requests.')


if __name__=='__main__':run()
