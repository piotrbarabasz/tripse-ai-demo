"""Private, prefix-scoped compiled SPA. No legacy/API fallback or identity logic."""
import re
import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse

PACKAGED_DIST = Path(__file__).parent / "spa_dist"
LOCAL_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
NONCE_MARKER = "__TRIPSE_STYLE_NONCE__"
CSP = ("default-src 'none'; script-src 'self'; style-src 'self'{style_nonce}; "
       "connect-src 'self'; img-src 'self'; font-src 'self'; object-src 'none'; "
       "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")


def register_spa(app, *, access_policy, directory=None):
    # An unbuilt source checkout keeps all legacy functionality available. Only
    # requests for the SPA entry return 503 until npm run build is performed.
    root = Path(directory) if directory is not None else (PACKAGED_DIST if PACKAGED_DIST.is_dir() else LOCAL_DIST)
    router = APIRouter(prefix="/app", dependencies=[Depends(access_policy)], include_in_schema=False)

    @app.middleware("http")
    async def spa_headers(request, call_next):
        response = await call_next(request)
        if request.url.path == "/app" or request.url.path.startswith("/app/"):
            response.headers.setdefault("Cache-Control", "private, no-store")
            response.headers.setdefault("Content-Security-Policy", CSP.format(style_nonce=""))
            response.headers.update({"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY",
                                     "Referrer-Policy": "no-referrer"})
        return response

    def entry():
        try:
            html = (root / "index.html").read_text(encoding="utf-8")
        except OSError:
            raise HTTPException(503, "Application frontend is not built") from None
        if html.count(NONCE_MARKER) != 1:
            raise HTTPException(503, "Application frontend build is incompatible")
        nonce = secrets.token_urlsafe(24)
        return HTMLResponse(html.replace(NONCE_MARKER, nonce), headers={
            "Cache-Control": "private, no-store",
            "Content-Security-Policy": CSP.format(style_nonce=f" 'nonce-{nonce}'"),
        })

    @router.api_route("", methods=["GET", "HEAD"])
    @router.api_route("/", methods=["GET", "HEAD"])
    def home():
        return entry()

    @router.api_route("/{path:path}", methods=["GET", "HEAD"])
    def resource(path: str, request: Request):
        parts = path.split("/")
        if any(p in {"", ".", ".."} or re.search(r"[\\:%\x00-\x1f]", p) for p in parts):
            raise HTTPException(404)
        if parts[0] == "assets":
            target = (root / path).resolve()
            if not target.is_relative_to(root.resolve()) or not target.is_relative_to((root / "assets").resolve()) or not target.is_file():
                raise HTTPException(404)
            hashed = re.fullmatch(r"[\w.-]+-[\w-]{8,}\.(js|css)", target.name, flags=re.ASCII)
            return FileResponse(target, headers={
                # cloud_boundary deliberately overrides this with private no-store.
                "Cache-Control": "private, max-age=31536000, immutable" if hashed else "private, no-store",
            })
        # Only extensionless HTML navigations get the React not-found view. Fetch,
        # missing static files, chunks and reserved assets never become index.html.
        if any("." in p for p in parts) or "text/html" not in request.headers.get("accept", ""):
            raise HTTPException(404)
        if request.headers.get("sec-fetch-dest", "document") != "document":
            raise HTTPException(404)
        return entry()

    app.include_router(router)
