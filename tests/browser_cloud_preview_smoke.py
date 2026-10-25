"""Local desktop/mobile/print QA; no GCP, credentials, worker or writable storage."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import httpx
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    artifacts = ROOT / "local-data/cloud-preview-qa"
    artifacts.mkdir(parents=True, exist_ok=True)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    env = {k:v for k,v in os.environ.items() if k.upper() in {"SYSTEMROOT","WINDIR","PATH","TEMP","TMP","HOME","USERPROFILE","LOCALAPPDATA"}}
    env.update(APP_ENV="dev", CLOUD_FEATURE_MODE="readonly_demo", PLANNING_MODE="mock")
    server = subprocess.Popen([sys.executable,"-m","uvicorn","app.main:app","--host","127.0.0.1","--port",str(port),"--no-access-log"],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            if server.poll() is not None:raise RuntimeError("API exited")
            try:
                if httpx.get(base+"/health",timeout=1).status_code==200:break
            except httpx.TransportError:pass
            time.sleep(.1)
        else:raise RuntimeError("Readiness timeout")
        with sync_playwright() as p:
            browser=p.chromium.launch()
            page=browser.new_page(viewport={"width":1440,"height":1000})
            errors=[];urls=[]
            page.on("pageerror",lambda error:errors.append(str(error)))
            page.on("request",lambda request:urls.append(request.url))
            for width in (1440,768,390,320):
                page.set_viewport_size({"width":width,"height":900})
                for path in ("/hub","/preview/planner","/preview/planner?scenario=ojcow","/preview/documents"):
                    page.goto(base+path)
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"),(width,path)
                    for link in page.locator("a[href]").all():
                        href=link.get_attribute("href")
                        if href.startswith("/"):assert page.request.get(base+href).status==200,href
                page.goto(base+"/hub")
                page.screenshot(path=str(artifacts/f"hub-{width}.png"),full_page=True)
            page.set_viewport_size({"width":1440,"height":1000})
            for variant in ("new_trips","theme_collection"):
                page.goto(base+"/preview/documents/collection?variant="+variant)
                expect(page.locator("#print-document")).to_be_enabled(timeout=15000)
                assert page.locator(".sheet").count()>0
                page.screenshot(path=str(artifacts/f"{variant}.png"),full_page=True)
                page.pdf(path=str(artifacts/f"{variant}.pdf"),prefer_css_page_size=True,print_background=True)
                page.set_viewport_size({"width":390,"height":844})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                page.set_viewport_size({"width":1440,"height":1000})
            assert all(url.startswith(base) for url in urls),urls
            assert not errors,errors
            browser.close()
        print("Cloud preview browser PASS: 4 viewports, links, 2 PDF variants, no external requests")
    finally:
        server.terminate();server.wait(timeout=15)


if __name__=="__main__":main()
