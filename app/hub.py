"""Local demo navigation. No jobs, document imports or new integrations."""
import os
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from app.document_studio.api import local_only

HUB_PAGE = Path(__file__).parent / "hub_frontend" / "index.html"


def hub_router():
    router = APIRouter(dependencies=[Depends(local_only)])

    @router.get("/hub", response_class=HTMLResponse, include_in_schema=False)
    def page():
        mock = os.getenv("PLANNING_MODE", "live") == "mock"
        # Only controlled constants are substituted, never raw environment values.
        values = {
            "MODE": "MOCK" if mock else "LIVE",
            "PLANNER_BADGE": "Przykładowe trasy · mock" if mock else "Tryb live · skonfigurowane usługi",
            "PLANNER_NOTE": "Gotowe scenariusze i schematyczna mapa. Bez wywołań AI i Google." if mock else "Formularz korzysta z konfiguracji AI i map. To szkic wymagający przeglądu.",
            "CHAT_HREF": "/demo/chat" if mock else "#demo-mode",
            "CHAT_CTA": "Otwórz symulator" if mock else "Jak włączyć symulator",
            "CHAT_BADGE": "Lokalny symulator · mock" if mock else "Symulator wymaga trybu mock",
            "CONFIG_HIDDEN": "hidden" if mock else "",
        }
        html = HUB_PAGE.read_text(encoding="utf-8")
        for key, value in values.items():
            html = html.replace("{{" + key + "}}", value)
        return HTMLResponse(html, headers={
            "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY", "Referrer-Policy": "same-origin",
            "Content-Security-Policy": "default-src 'none'; style-src 'self'; img-src 'self'; script-src 'none'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
        })

    return router
