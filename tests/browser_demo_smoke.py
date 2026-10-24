"""Run against the local mock API and worker: python tests/browser_demo_smoke.py."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

def run():
    artifacts=Path('data/demo-screenshots')
    artifacts.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page(viewport={'width':1440,'height':1000})
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        requests=[]
        page.on('request',lambda request:requests.append(request.url))
        for scenario,count in [('Karkonosze',2),('Ojców',1),('Trójmiasto',2)]:
            page.goto('http://localhost:8000/demo/chat')
            page.locator('#new-chat').click()
            page.get_by_role('button',name=scenario).click()
            page.locator('#send').click()
            link=page.locator('#messages a')
            expect(link).to_be_visible(timeout=20000)
            page.locator('#replay').click()
            expect(page.locator('#messages')).to_contain_text('Duplikat zdarzenia')
            if scenario=='Karkonosze': page.screenshot(path=str(artifacts/'chat-desktop.png'),full_page=True)
            link.click()
            expect(page.locator('.day-card')).to_have_count(count)
            expect(page.locator('#map svg')).to_be_visible()
            expect(page.locator('.drive-stats').first).to_contain_text('km')
            expect(page.locator('#map svg polyline')).to_have_count(count)
            page.locator('.day-button').first.click()
            expect(page.locator('.day-card').first).to_have_class('day-card selected')
            page.locator('#show-all').click()
            before=page.locator('#map svg').get_attribute('viewBox')
            page.get_by_role('button',name='Powiększ',exact=True).click()
            assert before!=page.locator('#map svg').get_attribute('viewBox')
            page.get_by_role('button',name='Dopasuj mapę',exact=True).click()
            page.locator('#map svg g[role=button] circle').first.click()
            expect(page.locator('.demo-point-info')).not_to_contain_text('Kliknij punkt')
            if scenario=='Karkonosze':
                page.screenshot(path=str(artifacts/'map-desktop.png'),full_page=True)
                page.set_viewport_size({'width':390,'height':844})
                page.screenshot(path=str(artifacts/'map-mobile.png'),full_page=True)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.set_viewport_size({'width':1440,'height':1000})
        for case in ('missing','routing','limit','failure','expired','delivery'):
            page.goto('http://localhost:8000/demo/chat')
            page.locator('#new-chat').click()
            page.locator('#case').select_option(case)
            page.locator('#send').click()
            if case=='failure':
                expect(page.locator('#messages')).to_contain_text('Symulowana awaria',timeout=20000)
                continue
            link=page.locator('#messages a')
            expect(link).to_be_visible(timeout=45000)
            link.click()
            if case=='expired':
                expect(page.locator('h1')).to_have_text('This plan link is unavailable.')
            elif case in ('missing','routing'):
                expect(page.locator('#map svg polyline')).to_have_count(1)
                expect(page.locator('.drive-stats').first).to_contain_text('niedostępne')
                if case=='missing': expect(page.locator('#warning-list')).to_contain_text('Nieznalezione miejsce')
            elif case=='limit': expect(page.locator('.day-warnings').first).to_contain_text('Przekroczony limit')
        page.set_viewport_size({'width':390,'height':844})
        page.goto('http://localhost:8000/demo/chat')
        page.screenshot(path=str(artifacts/'chat-mobile.png'),full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert not errors, errors
        assert all(url.startswith('http://localhost:8000/') for url in requests), requests
        browser.close()
    print('Demo browser smoke PASS: three trips, chat, duplicate, map interactions, mobile, failures, expiry and delivery retry. No external requests.')

if __name__=='__main__': run()
