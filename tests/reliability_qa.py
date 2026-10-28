"""Real browser, isolated API and controlled delayed responses for TRIPSE-QA-001."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

import httpx
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def run():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    with tempfile.TemporaryDirectory(prefix='tripse-adversarial-') as tmp:
        env = dict(os.environ, CLOUD_FEATURE_MODE='local', PLANNING_MODE='mock',
                   DATABASE_PATH=str(Path(tmp)/'db.sqlite3'), DOCUMENT_STUDIO_DATA_PATH=str(Path(tmp)/'documents'))
        for key in ('K_SERVICE', 'DOCUMENT_STUDIO_DOCKER_LOCAL', 'OPENAI_API_KEY', 'GOOGLE_MAPS_API_KEY', 'GOOGLE_PLACES_API_KEY', 'GOOGLE_ROUTES_API_KEY'):
            env.pop(key, None)
        server = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(port), '--no-access-log'],
            cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        try:
            for _ in range(100):
                try:
                    if httpx.get(base+'/health', timeout=1).status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                time.sleep(.1)
            with httpx.Client(base_url=base, timeout=20) as api, sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.route('**/*', lambda route: route.continue_() if route.request.url.startswith(base+'/') else route.abort())
                for template, variant, prefix in [('offer.private','standard','d'), ('marketing.collection','new_trips','m')]:
                    response = api.post('/api/document-studio/drafts', json={'template_id':template, 'source_type':'trip' if prefix=='d' else 'campaign',
                        'source_id':'demo-canada' if prefix=='d' else 'demo-northern-journeys', 'layout_variant':variant})
                    response.raise_for_status()
                    doc = response.json()
                    url = base+'/api/document-studio/drafts/'+doc['document_id']
                    page.goto(base+'/documents/demo#edit-draft/'+doc['document_id'])
                    field = page.locator(f'[data-{prefix}-field="title"]')
                    expect(field).to_be_visible()
                    field.fill('BEFORE SAVE')
                    held = []
                    def delay(route):
                        if route.request.method == 'PUT':
                            held.append((route, route.fetch()))
                        else:
                            route.continue_()
                    page.route(url, delay)
                    page.locator(f'#{prefix}-save').click()
                    page.wait_for_function(f'document.querySelector("#{prefix}-save").disabled')
                    # Pump browser events until the intercepted request has committed.
                    for _ in range(100):
                        if held:
                            break
                        page.wait_for_timeout(20)
                    assert held
                    assert page.locator('#main').evaluate('(el) => el.inert'), 'Editing remains possible during save'
                    field.evaluate('(el) => el.focus()')
                    page.keyboard.type('LATE')
                    expect(field).to_have_value('BEFORE SAVE')
                    held[0][0].fulfill(response=held[0][1])
                    expect(page.locator(f'#{prefix}-save')).to_be_enabled()
                    page.unroute(url, delay)
                    assert api.get(url).json()['title'] == 'BEFORE SAVE'
                    # An explicit failed save must unlock inputs and preserve dirty edits.
                    field.fill('RETRY VALUE')
                    def fail(route):
                        if route.request.method == 'PUT':
                            route.fulfill(status=503, content_type='application/json', body='{"detail":"injected failure"}')
                        else:
                            route.continue_()
                    page.route(url, fail)
                    page.locator(f'#{prefix}-save').click()
                    expect(page.locator('#message')).to_contain_text('injected failure')
                    assert not page.locator('#main').evaluate('(el) => el.inert')
                    expect(field).to_have_value('RETRY VALUE')
                    page.unroute(url, fail)
                    page.locator(f'#{prefix}-save').click()
                    expect(page.locator('#message')).to_contain_text('Rewizja 3')
                    assert api.get(url).json()['title'] == 'RETRY VALUE'
                    page.reload()
                    expect(field).to_have_value('RETRY VALUE')
                # The source Trip editor has its own save implementation.
                source = api.post('/api/document-studio/trips', json={'title':'Source before save', 'duration_days':1,
                    'days':[{'day_number':1, 'title':'Synthetic day'}]}).json()
                source_url = base+'/api/document-studio/trips/'+source['trip_id']
                page.goto(base+'/documents/demo#trips/'+source['trip_id'])
                source_field = page.locator('[data-field="title"]')
                expect(source_field).to_be_visible()
                source_field.fill('Source saved')
                held_source = []
                def delay_source(route):
                    held_source.append((route, route.fetch()))
                page.route(source_url, delay_source)
                page.locator('#save-trip').click()
                for _ in range(100):
                    if held_source:
                        break
                    page.wait_for_timeout(20)
                assert held_source
                assert page.locator('#main').evaluate('(el) => el.inert'), 'Source editor allows late edits'
                held_source[0][0].fulfill(response=held_source[0][1])
                expect(page.locator('#save-trip')).to_be_enabled()
                page.unroute(source_url, delay_source)
                assert api.get(source_url).json()['title'] == 'Source saved'
                # A slow document fetch must not replace a newer library route.
                held = []
                def slow_open(route):
                    held.append((route, route.fetch()))
                page.route(url, slow_open)
                page.goto(base+'/documents/demo#templates')
                page.reload()
                expect(page.locator('.template-group')).to_have_count(3)
                page.evaluate('(id) => { location.hash = "edit-draft/" + id; }', doc['document_id'])
                for _ in range(100):
                    if held:
                        break
                    page.wait_for_timeout(20)
                assert held
                page.locator('[data-nav="drafts"]').click()
                expect(page.locator('#library-view')).to_be_visible()
                held[0][0].fulfill(response=held[0][1])
                # Wait for stale editor asset loading as well as its document request.
                page.wait_for_timeout(300)
                expect(page.locator('#library-view')).to_be_visible()
                page.unroute(url, slow_open)
                # A debounce from a detached filter form must not invalidate reset results.
                held_filters = []
                def hold_library(route):
                    if 'limit=25' in route.request.url:
                        held_filters.append((route, route.fetch()))
                    else:
                        route.continue_()
                page.route('**/api/document-studio/library?*', hold_library)
                page.locator('[data-library-filter="search"]').fill('detached search')
                page.locator('#library-reset').click()
                page.wait_for_timeout(400)
                for pending, response in held_filters:
                    pending.fulfill(response=response)
                expect(page.locator('.library-document')).to_have_count(2)
                page.unroute('**/api/document-studio/library?*', hold_library)
                trip = api.post('/api/document-studio/trips', json={'title':'15-day synthetic trip', 'duration_days':15,
                    'days':[{'day_number':i, 'title':f'Day {i}', 'public_description':'Synthetic itinerary'} for i in range(1,16)]}).json()
                doc = api.post('/api/document-studio/drafts', json={'template_id':'offer.self_guide',
                    'source_type':'trip', 'source_id':trip['trip_id']}).json()
                doc['sections'].append({'title':'Multiline content', 'kind':'text', 'order':99,
                    'body':'\n'.join('Line '+str(i) for i in range(160))})
                saved = api.put('/api/document-studio/drafts/'+doc['document_id'], json={
                    'revision':1, 'title':doc['title'], 'sections':doc['sections']})
                saved.raise_for_status()
                page.goto(base+'/api/document-studio/drafts/'+doc['document_id']+'/preview')
                page.wait_for_function('window.documentReady === true')
                layout = page.evaluate('window.layoutErrors')
                assert not layout, layout
                expect(page.locator('#print-document')).to_be_enabled()
                text = page.locator('#pages').inner_text()
                assert all('Line '+str(i) in text for i in range(160))
                artifacts = ROOT/'local-data'/'reliability-audit'
                artifacts.mkdir(parents=True, exist_ok=True)
                page.pdf(path=str(artifacts/'multiline-15-day.pdf'), print_background=True, prefer_css_page_size=True)
                from pypdf import PdfReader
                import re
                pdf_text = '\n'.join(p.extract_text() for p in PdfReader(artifacts/'multiline-15-day.pdf').pages)
                assert set(map(int, re.findall(r'Line (\d+)', pdf_text))) == set(range(160))
                assert not errors, errors
                page.unroute_all(behavior='wait')
                browser.close()
        finally:
            server.terminate()
            server.wait(timeout=10)
    print('Reliability browser PASS: delayed trip/marketing saves, keyboard lock, failure/retry/reload, stale route and filter debounce, 15-day multiline PDF with all 160 lines; isolated API.')


if __name__ == '__main__':
    run()
