"""Explicit, stateless public runtime. Local routers are never registered here."""
import os
import re
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT.parent / "demo-fixtures" / "gt-v1"
VERSION_FILE = ROOT / "_build_version.txt"
DOCUMENT_ASSETS = {"brand-tokens.css", "marketing.css", "trip-documents.css", "print-export.js"}


@dataclass(frozen=True)
class CloudSettings:
    environment: str
    version: str
    service: str
    mode: str = "readonly_demo"

    @classmethod
    def from_env(cls):
        mode = os.getenv("CLOUD_FEATURE_MODE", "local")
        if mode == "local" and not os.getenv("K_SERVICE"):
            return None
        if mode not in {"readonly_demo", "cloud_demo"} or os.getenv("PLANNING_MODE") != "mock":
            raise ValueError("Cloud Run requires readonly_demo or cloud_demo and PLANNING_MODE=mock")
        environment = os.getenv("APP_ENV", "")
        if environment not in {"dev", "prod"}:
            raise ValueError("Cloud preview requires APP_ENV=dev or prod")
        service = os.getenv("K_SERVICE", f"tripse-ai-{environment}")
        if service != f"tripse-ai-{environment}":
            raise ValueError("Cloud service does not match APP_ENV")
        if any(os.getenv(key) for key in (
            "OPENAI_API_KEY", "GOOGLE_MAPS_API_KEY", "GOOGLE_PLACES_API_KEY", "GOOGLE_ROUTES_API_KEY",
            "WAHA_API_KEY", "WAHA_WEBHOOK_SECRET", "WAHA_WEBHOOK_HMAC_KEY",
        )):
            raise ValueError("Server provider credentials are forbidden in cloud mock modes")
        version = VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.exists() else "unversioned"
        expected = os.getenv("EXPECTED_IMAGE_SHA")
        if os.getenv("K_SERVICE") and (not re.fullmatch(r"[0-9a-f]{40}", version) or expected != version):
            raise ValueError("Cloud image must contain the expected commit SHA")
        return cls(environment, version, service, mode)


def page(title, content):
    return HTMLResponse(f'''<!doctype html><html lang="pl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)} — TRIPSE</title>
<link rel="stylesheet" href="/documents/assets/brand-tokens.css">
<link rel="stylesheet" href="/static/cloud-preview.css"></head><body>
<header><a href="/hub" class="brand">TRIPSE <span>AI HUB</span></a><span>Cloud preview · tylko odczyt</span></header>
<main><p class="eyebrow">DEMO / FIKCYJNE DANE</p><h1>{escape(title)}</h1>{content}</main>
<footer>Branding roboczy · Podgląd nie uruchamia AI, Google Maps ani WhatsApp.</footer></body></html>''')


def create_preview_app(settings):
    app = FastAPI(title="TRIPSE Cloud Preview", docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def readonly(request, call_next):
        if request.method not in {"GET", "HEAD"}:
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "Cloud preview is read only"}, status_code=403)
        response = await call_next(request)
        response.headers.update({
            "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY",
            "Referrer-Policy": "same-origin", "Cache-Control": "no-store",
            "Content-Security-Policy": "default-src 'none'; style-src 'self' 'unsafe-inline'; img-src 'self'; script-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
        })
        return response

    @app.get("/health")
    def health():
        return {"status": "ok", "environment": settings.environment, "generation_mode": "mock",
                "feature_mode": "readonly_demo", "image_version": settings.version,
                "service": settings.service, "storage": "fixtures_readonly"}

    @app.get("/")
    def home():
        return RedirectResponse("/hub", status_code=302)

    @app.get("/hub")
    def hub():
        return page("Twoja podróż zaczyna się tutaj", '''<p class="lead">Poznaj gotowe przykłady TRIPSE. Edycja i integracje są dostępne wyłącznie w lokalnym demo.</p>
<div class="cards"><section><span class="symbol" aria-hidden="true">↗</span><h2>AI Trip Planner &amp; Maps</h2><p>Trzy przykładowe programy i schematyczne mapy. Bez tworzenia zadań.</p><a class="button" href="/preview/planner">Zobacz gotowe trasy →</a></section>
<section><span class="symbol" aria-hidden="true">▤</span><h2>Document Studio</h2><p>Marketingowa kolekcja kierunków w dwóch kompozycjach. Bez danych operacyjnych.</p><a class="button" href="/preview/documents">Zobacz kolekcje →</a></section>
<section id="unavailable"><span class="symbol" aria-hidden="true">◌</span><h2>WhatsApp Assistant</h2><p>Niedostępny w cloud preview. Wymaga autoryzacji, trwałej kolejki i workera.</p><span class="badge">Dostępny w lokalnym demo</span></section></div>
<aside><h2>Od pomysłu do dokumentu</h2><p>Wiadomość → planowanie → mapa → dokument to kierunek rozwoju. Moduły nie tworzą jeszcze jednej automatyzacji.</p></aside>''')

    @app.get("/preview/planner")
    def planner(scenario: Literal["mountains", "ojcow", "coast"] = "mountains"):
        from app.demo_data import SCENARIOS
        spec = SCENARIOS[scenario]
        links = " · ".join(f'<a href="/preview/planner?scenario={key}">{escape(value["name"])}</a>' for key, value in SCENARIOS.items())
        locations = spec["places"]
        xmin, xmax = min(p[2] for p in locations), max(p[2] for p in locations)
        ymin, ymax = min(p[1] for p in locations), max(p[1] for p in locations)
        coordinates = [(45 + (p[2]-xmin)/max(xmax-xmin, .01)*710, 225-(p[1]-ymin)/max(ymax-ymin, .01)*170) for p in locations]
        dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7"/><text x="{x:.1f}" y="{y-15:.1f}">{i}</text>' for i, (x,y) in enumerate(coordinates, 1))
        points = " ".join(f"{x:.1f},{y:.1f}" for x,y in coordinates)
        days = "".join(f'<section><h2>Dzień {i}</h2><ol>{"".join(f"<li>{escape(locations[j][0])} — {escape(locations[j][3])}</li>" for j in indices)}</ol></section>' for i,indices in enumerate(spec["days"], 1))
        return page(spec["name"], f'<nav aria-label="Scenariusze">{links}</nav><p>Mapa schematyczna: linie nie przedstawiają dróg. Dostępność miejsc wymaga sprawdzenia.</p><svg viewBox="0 0 820 270" role="img" aria-label="Schemat położenia przykładowych miejsc"><polyline points="{points}"/>{dots}</svg><div class="cards">{days}</div>')

    @app.get("/preview/documents")
    def documents():
        return page("Kolekcje podróży 2027 — DEMO", '''<p class="lead">Nowe kierunki i inspiracje górskie. Dane są fikcyjne. Neutralne placeholdery zastępują fotografie.</p>
<div class="cards"><section><h2>Nowe wyprawy</h2><p>Przejrzysta kolekcja kart kierunków.</p><a class="button" href="/preview/documents/collection?variant=new_trips">Podgląd A4 i druk →</a></section>
<section><h2>Kolekcja tematyczna</h2><p>Wspólny temat z większą sekcją otwierającą.</p><a class="button" href="/preview/documents/collection?variant=theme_collection">Podgląd A4 i druk →</a></section></div>
<aside>Edycja, uploady, oferty prywatne i materiały pilota są niedostępne w publicznym podglądzie.</aside>''')

    @app.get("/preview/documents/collection", response_class=HTMLResponse)
    def collection(variant: Literal["new_trips", "theme_collection"] = "new_trips"):
        from app.document_studio.models import Campaign, Trip
        from app.document_studio.marketing import build_marketing
        from app.document_studio.rendering import render_marketing
        # Fixed, reviewed fixture IDs only. No local repository, drafts or upload directory.
        campaign = Campaign.model_validate_json((FIXTURES / f"campaigns/gt-v1-{variant}.json").read_text(encoding="utf-8"))
        trips = [Trip.model_validate_json((FIXTURES / "trips" / (item.trip_id + ".json")).read_text(encoding="utf-8")) for item in campaign.items]
        campaign.layout_variant = variant
        campaign.hero_asset_id = None
        for item in campaign.items:
            item.image_asset_id = None
        return HTMLResponse(render_marketing(build_marketing(campaign, trips, None, "Fikcyjny przykład · cloud preview")))

    @app.get("/documents/assets/{filename}")
    def document_asset(filename: str):
        if filename not in DOCUMENT_ASSETS:
            raise HTTPException(404)
        return FileResponse(ROOT / "document_studio/frontend" / filename)

    @app.get("/static/cloud-preview.css")
    def stylesheet():
        return FileResponse(ROOT / "static/cloud-preview.css")

    return app
