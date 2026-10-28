"""Read-only HTML viewer and token-protected data; no server keys reach the browser."""
import os
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

STATIC_DIR = Path(__file__).parent / "static"
PRIVATE_HEADERS = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
                   "X-Frame-Options": "DENY", "Referrer-Policy": "strict-origin"}
CSP = (
    "default-src 'self'; script-src 'self' https://maps.googleapis.com https://maps.gstatic.com; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "img-src 'self' data: blob: https://*.googleapis.com https://*.gstatic.com "
    "https://*.google.com https://*.googleusercontent.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "connect-src 'self' https://*.googleapis.com https://*.gstatic.com https://*.google.com; "
    "frame-src https://www.google.com; worker-src 'self' blob:; "
    "object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
)


def browser_config():
    key = os.getenv("GOOGLE_MAPS_BROWSER_KEY", "")
    # Fail closed if a native deployment accidentally reuses a server credential.
    server_keys = {os.getenv(name) for name in (
        "GOOGLE_MAPS_API_KEY", "GOOGLE_PLACES_API_KEY", "GOOGLE_ROUTES_API_KEY", "OPENAI_API_KEY"
    )}
    if key in server_keys:
        key = ""
    return {"browser_key": key, "map_id": os.getenv("GOOGLE_MAPS_MAP_ID", "DEMO_MAP_ID")}


def module_page(filename, request, *, cloud_mode=False):
    """Navigation hint only: reuse the server's local guard or authenticated runtime."""
    from app.document_studio.api import local_only
    if not cloud_mode:
        try:
            local_only(request)
        except HTTPException:
            allowed = False
        else:
            allowed = True
    else:
        # The cloud boundary verifies signed identity and membership before routing.
        allowed = True
    html = (STATIC_DIR / filename).read_text(encoding="utf-8")
    if allowed:
        html = html.replace('data-hub-navigation="disabled"', 'data-hub-navigation="enabled"')
    return HTMLResponse(html, headers={**PRIVATE_HEADERS, "Content-Security-Policy": CSP})


def viewer_router(database, *, cloud_mode=False):
    router = APIRouter()

    def lookup(token):
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
            return None
        return database.get_viewer(token)

    @router.get("/planner", response_class=HTMLResponse)
    def create_page(request: Request):
        return module_page("create.html", request, cloud_mode=cloud_mode)

    @router.get("/trip/{token}", response_class=HTMLResponse)
    def page(token: str):
        valid = lookup(token) is not None
        filename = "viewer.html" if valid else "viewer-error.html"
        return HTMLResponse((STATIC_DIR / filename).read_text(encoding="utf-8"),
                            status_code=200 if valid else 404,
                            headers={**PRIVATE_HEADERS, "Content-Security-Policy": CSP})

    @router.get("/api/viewer/{token}")
    def data(token: str):
        result = lookup(token)
        if result is None:
            raise HTTPException(status_code=404, detail="Plan link not found or expired",
                                headers=PRIVATE_HEADERS)
        public_plan = {key: value for key, value in result.items()
                       if key not in ("request_text", "viewer_url")}
        return JSONResponse({"plan": public_plan, "maps": browser_config()},
                            headers={**PRIVATE_HEADERS, "Referrer-Policy": "no-referrer"})

    return router
