"""Self-contained local Hub QA: python tests/browser_hub_smoke.py.

API and worker use temporary storage and explicit mock mode. Screenshots are
gitignored under local-data/hub-qa/. No external services are contacted.
"""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

import httpx
from playwright.sync_api import expect, sync_playwright

ROOT=Path(__file__).resolve().parents[1]


def run():
    artifacts=ROOT/'local-data'/'hub-qa';artifacts.mkdir(parents=True,exist_ok=True)
    with socket.socket() as listener:
        listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
    base=f'http://127.0.0.1:{port}'
    with tempfile.TemporaryDirectory(prefix='tripse-hub-') as temporary:
        env=dict(os.environ,PLANNING_MODE='mock',DATABASE_PATH=str(Path(temporary)/'planner.sqlite3'),DOCUMENT_STUDIO_DATA_PATH=str(Path(temporary)/'documents'),PUBLIC_BASE_URL=base,WORKER_POLL_SECONDS='0.1')
        env.pop('DOCUMENT_STUDIO_DOCKER_LOCAL',None)
        for key in ('OPENAI_API_KEY','GOOGLE_MAPS_API_KEY','GOOGLE_PLACES_API_KEY','GOOGLE_ROUTES_API_KEY','GOOGLE_MAPS_BROWSER_KEY'):
            env.pop(key,None)
        processes=[]
        def start(mode='mock'):
            active_env=dict(env,PLANNING_MODE=mode)
            kwargs=dict(cwd=ROOT,env=active_env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            server=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port),'--no-access-log'],**kwargs)
            processes.append(server)
            for _ in range(100):
                try:
                    if httpx.get(base+'/health',timeout=1).status_code==200:break
                except httpx.TransportError:pass
                if server.poll() is not None:raise RuntimeError('QA API exited')
                time.sleep(.1)
            else:raise RuntimeError('API readiness timeout')
            if mode=='mock':processes.append(subprocess.Popen([sys.executable,'-m','app.worker'],**kwargs))
        def stop():
            for process in processes:
                if process.poll() is None:process.terminate();process.wait(timeout=10)
            processes.clear()
        try:
            start()
            with sync_playwright() as playwright:
                browser=playwright.chromium.launch()
                page=browser.new_page(viewport={'width':1440,'height':1100})
                errors=[];requests=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.on('request',lambda request:requests.append(request.url))
                page.goto(base+'/')
                assert page.url == base+'/hub'
                expect(page.locator('.module-card')).to_have_count(3)
                expect(page.locator('#hub-title')).to_contain_text('Jedno miejsce startu')
                assert page.locator('#planner-link').get_attribute('href')=='/planner'
                assert page.locator('#documents-link').get_attribute('href')=='/documents/demo#templates'
                assert page.locator('#assistant-link').get_attribute('href')=='/demo/chat'
                page.keyboard.press('Tab')
                expect(page.locator('.skip-link')).to_be_focused()
                page.keyboard.press('Enter')
                expect(page.locator('#main')).to_be_focused()
                page.goto(base+'/hub')
                for _ in range(10):
                    page.keyboard.press('Tab')
                    if page.locator('#planner-link').evaluate('(el)=>el===document.activeElement'):break
                expect(page.locator('#planner-link')).to_be_focused()
                assert page.locator('#planner-link').evaluate('(el)=>getComputedStyle(el).outlineWidth')=='3px'
                page.locator('#planner-link').blur()
                page.screenshot(path=str(artifacts/'hub-desktop.png'),full_page=True)
                # Existing planner -> actual mock worker -> token-protected map.
                page.locator('#planner-link').click()
                expect(page.locator('#trip-form')).to_be_visible()
                assert page.url == base+'/planner'
                page.reload()
                expect(page.locator('#trip-form')).to_be_visible()
                expect(page.locator('#hub-return')).to_be_visible()
                page.get_by_role('button',name='Karkonosze',exact=False).click()
                page.locator('#submit-trip').click()
                expect(page.locator('#open-trip')).to_be_visible(timeout=20000)
                page.locator('#open-trip').click()
                expect(page.locator('.day-card')).to_have_count(2)
                expect(page.locator('#map svg')).to_be_visible()
                assert page.locator('a[href="/hub"]').count()==0
                page.goto(base+'/planner')
                page.locator('#hub-return').click()
                expect(page.locator('#modules')).to_be_visible()
                # Protected studio keeps its existing routes/data and has a return.
                page.locator('#documents-link').click()
                expect(page.locator('.template-card')).to_have_count(8)
                page.locator('.module-hub-link').click()
                expect(page.locator('.module-card')).to_have_count(3)
                # Existing chat workflow still creates a plan via the demo worker.
                page.locator('#assistant-link').click()
                expect(page.locator('#chat-form')).to_be_visible()
                page.locator('#send').click()
                expect(page.locator('#messages a')).to_be_visible(timeout=20000)
                page.locator('#hub-return').click()
                expect(page.locator('.module-card')).to_have_count(3)
                for width in (320,390,768,1024):
                    page.set_viewport_size({'width':width,'height':844})
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),width
                    for selector in ('#planner-link','#documents-link','#assistant-link'):
                        box=page.locator(selector).bounding_box()
                        assert box and box['width']>0 and box['height']>=44,(width,selector,box)
                page.set_viewport_size({'width':390,'height':844})
                page.screenshot(path=str(artifacts/'hub-mobile.png'),full_page=True)
                page.locator('#documents-link').click()
                expect(page.locator('.module-hub-link')).to_be_visible()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.screenshot(path=str(artifacts/'studio-mobile-return.png'))
                page.locator('.module-hub-link').click()
                page.emulate_media(reduced_motion='reduce')
                assert page.locator('.module-card').first.evaluate('(el)=>getComputedStyle(el).transitionDuration')=='0s'
                # Browser UI reflects the pre-existing live-mode guard; no enabling side effect.
                stop();start('live')
                page.goto(base+'/hub')
                expect(page.locator('#assistant-link')).to_have_text('Jak włączyć symulator')
                page.locator('#assistant-link').click()
                expect(page.locator('#demo-mode')).to_be_in_viewport()
                assert httpx.get(base+'/demo/chat').status_code==404
                page.screenshot(path=str(artifacts/'hub-live-mobile.png'),full_page=True)
                assert not errors,errors
                assert all(url.startswith(base+'/') for url in requests),requests
                browser.close()
        finally:stop()
    print('Hub browser PASS: three destinations and returns; real mock planner/chat worker flows; map unchanged; keyboard/skip/focus/reduced motion; 320/390/768/1024 mobile/tablet layouts; honest live-mode fallback; no external requests.')


if __name__=='__main__':run()
