# Application routing and navigation — 2026-10-28

Future routing is proposed in [ARCH-001 UI routing](ui/routing.md).
`/app` is not implemented; this current route inventory remains unchanged.

Canonical navigation is `/` → `/hub` → modules. `GET /` returns a relative
302 redirect with no-store caching; `/hub` renders directly. Planner UI is
`/planner`; its HTML, JavaScript and planning API are otherwise unchanged.
These are local changes for review, not a deployed release.

## Endpoint inventory before and after

L = local application; C = authenticated `cloud_demo`; R = `readonly_demo`.
Local public routes retain their existing access rules; “local guard” means the
unchanged `local_only` peer/Host/Origin/proxy checks. Every C route except health
passes signed IAP identity, exact Host and explicit membership checks; writes
add editor and exact Origin requirements. Internal jobs use the separate verified
task identity. R registers its own app and denies all non-GET/HEAD requests.

| HTTP / URL before → after | Handler / owner | Modes | Access / kind | Frontend dependency |
|---|---|---|---|---|
| GET `/`: planner → 302 `/hub` | formerly `viewer.create_page`; now `main.home` | L, C | L redirect has no private content; C authenticated; UI navigation | Homepage/bookmarks now open Hub |
| GET `/`: 307 `/hub` → 302 `/hub` | `cloud_preview.home` | R | public navigation | Preview Hub |
| GET `/hub`: unchanged, direct HTML | `hub.page`; `cloud_preview.hub` | L, C, R | L local guard; C authenticated; R public preview; UI | Three module cards; never self-redirects |
| GET `/planner`: new canonical path for existing form | `viewer.create_page` | L, C | L previously public planner; C authenticated; UI | `create.html`, `create.js`; Hub, simulator and Make helper link here |
| GET `/documents/demo`: unchanged | `document_studio.api.panel` | L, C | L local guard; C authenticated; UI | Hub → Studio → Hub |
| GET `/demo/chat`: unchanged | `demo.page` | L, C | mock only; L existing public route, C authenticated; UI | `demo.html`, `demo.js`; Hub and planner |
| POST `/api/trips`: unchanged | `main.create_trip` | L, C | L public API; C editor; API-only | Planner submission, Cloud idempotency key unchanged |
| GET `/api/trips/{trip_id}`: unchanged | `main.get_trip` | L, C | L public job API; C owner-scoped; API-only | Planner polling |
| GET `/trip/{token}`: unchanged | `viewer.page` | L, C | L public with valid unexpired bearer token; C also owner-scoped authenticated; read-only UI | Planner/chat result navigation; no Hub link |
| GET `/api/viewer/{token}`: unchanged | `viewer.data` | L, C | same token/identity boundary; read-only API | Viewer map/rendering; private request excluded |
| GET `/api/demo/scenarios`, `/api/demo/conversations/{conversation}`: unchanged | `demo.scenarios`, `demo.messages` | L, C | mock only; C membership/owner scope; API-only | Planner examples and chat polling |
| POST `/api/demo/messages`: unchanged | `demo.send` | L, C | mock only; C editor/owner scope; API-only | Simulator dedup/outbox workflow |
| POST `/api/webhooks/waha`: unchanged | `waha.receive` | L | existing HMAC/sender/session policy; public integration API | WAHA, never exposed in C or R |
| POST `/internal/jobs/{trip_id}`: unchanged | `main.process_cloud_job` | C | only signed dedicated task identity; internal API | Cloud Tasks OIDC/IAP, no human access |
| GET `/health`: unchanged | `main.health`; `cloud_preview.health` | L, C, R | app-level user-auth exception; cloud service still IAP-protected; probe API | Worker/browser readiness, Run and deployment checks |
| GET `/preview/planner`, `/preview/documents`, `/preview/documents/collection`: unchanged | `cloud_preview` | R | public read-only UI | Fixed reviewed fixtures; no writable planner |
| GET `/static/{path}`: unchanged | `main` StaticFiles | L, C | L public code assets; C authenticated; asset mount | Existing templates/assets retained; raw templates default to disabled Hub hint |
| GET `/static/cloud-preview.css`: unchanged | `cloud_preview.stylesheet` | R | sole allowed static preview asset | Preview stylesheet |
| GET `/documents/assets/{filename}`: unchanged | `document_studio.api.asset`; `cloud_preview.document_asset` | L, C, R | L local guard; C authenticated; R smaller explicit allowlist | Studio/Hub/preview CSS/JS |
| GET `/docs`, `/redoc`, `/openapi.json`: unchanged | FastAPI defaults | L | existing API reference UI/schema; absent in C/R | Developer use only |

The Document Studio API remains owned by `document_studio.api`, available only
in L (local guard) and C (members read; editors write with exact Origin).
All paths/methods below are unchanged; R does not register them:

| HTTP | API URL(s) | Frontend use |
|---|---|---|
| GET | `/api/document-studio/templates` | Template catalogue |
| GET, POST | `/api/document-studio/trips`, `/api/document-studio/campaigns`, `/api/document-studio/drafts` | Lists and creation |
| GET, PUT | `/api/document-studio/trips/{identifier}`, `/api/document-studio/campaigns/{identifier}`, `/api/document-studio/drafts/{identifier}` | Load/save with revision conflicts |
| GET, POST | `/api/document-studio/assets` | Image library/upload |
| GET | `/api/document-studio/assets/{identifier}/content` | Private image bytes |
| POST | `/api/document-studio/trip-documents/validate`, `/api/document-studio/trip-documents/preview` | Offer/pilot validation/rendering |
| POST | `/api/document-studio/marketing/validate`, `/api/document-studio/marketing/preview` | Marketing validation/rendering |
| GET | `/api/document-studio/campaigns/{identifier}/preview`, `/api/document-studio/drafts/{identifier}/preview` | Export/preview |

No API alias, catch-all redirect, duplicate planner handler or second planner UI
was introduced. Exact canonical paths return HTML without redirects. Existing
FastAPI trailing-slash normalization remains: e.g. `/planner/` redirects once
(307) to `/planner`; use canonical links. Caddy accepts exact `/planner` only.

## Navigation visibility and security

The backend emits only a fixed `data-hub-navigation="enabled"` or `"disabled"`
hint in planner/chat HTML. It enables the hint for authenticated cloud composition
or a local request that passes the existing Studio/Hub local guard. The external
`module-nav.js` reads that hint rather than guessing authorization from hostname.
Direct static templates default to disabled. CSP and security headers are retained;
no inline script or raw environment value is injected.

This is a convenience hint, not an access control. Hub/Studio still authorize
every request. The public token viewer and invalid-token page have no private Hub
navigation. Mock/live simulator guards, token expiry/ownership, API payloads,
idempotency, storage, map behavior and task authentication are unchanged.

## Direct local, HTTPS proxy and cloud boundaries

| Entry point | Homepage / modules | Security boundary |
|---|---|---|
| Direct `http://localhost:8000` | `/` → `/hub`; all permitted local modules; planner `/planner` | Local Hub/Studio require trusted peer and Host with no proxy headers |
| Existing local HTTPS Caddy, e.g. `https://localhost:8443` | `/planner`, public token viewers and planning API remain allowed; `/` redirects to `/hub`, which returns proxy 404 | Caddy does not forward `/hub`, Studio, simulator/demo API or internal jobs; forwarded headers also fail the backend local guard |
| Authenticated Cloud Run `run.app` | `/` → authenticated `/hub`; `/planner`, Studio and mock simulator | Existing IAP + signed identity + memberships/editor/Origin checks apply; no Caddy or hostname-based navigation exception |
| Readonly preview | `/` → `/hub`; only `/preview/*` examples | Separate read-only app; `/planner`, private APIs and writable modules absent |

Caddy now explicitly permits `/planner` to preserve the previously exposed root
planner. Public viewers, job polling, `POST /api/trips` and HMAC webhook matching
are unchanged. It deliberately does not expose the private Hub. This means a
public-proxy homepage is not a working private-module launcher; open `/planner`
there or use direct trusted local access / authenticated Cloud Run for Hub.
Do not remove forwarded headers or broaden the allowlist to bypass that boundary.

## Validation and operator follow-up

`python -m pytest -q` in the repository virtual environment: **637 passed**,
one existing Starlette/AnyIO deprecation warning. Regressions cover exact 302s,
single-hop navigation, direct/refresh URLs, mock-only simulator, cloud anonymous /
forged/nonmember rejection, reader/editor rules, readonly isolation, token/API
contracts, Caddy allowlist and forwarded-header/remote-peer denial.

Browser smoke passed: `browser_hub_smoke.py`, `browser_cloud_demo_smoke.py`,
`browser_cloud_preview_smoke.py`, `browser_smoke.py`. These cover local API/worker
flows, cloud Hub returns on `run.app`, Studio save/reload and PDF previews,
planner/chat → viewer, readonly navigation and token/map regression. Cloud browser
tests use injected stores and intercepted requests, not deployed IAP. Because
Playwright only routes the first URL of a redirected request, the offline cloud
harness checks the 302 through TestClient then opens its destination; local and
readonly browser servers exercise actual HTTP redirects. No live providers used.

Live Caddy HTTPS validation was unavailable: Docker's Linux-engine pipe was
absent and no standalone Caddy executable was installed. Proxy assertions are
configuration/backend tests, not a claim of an end-to-end TLS test. Before using
the proxy, start the existing Docker setup and verify `/planner` plus a valid
viewer, API submission/polling, and denial of `/hub`, Studio and internal jobs
with the trusted local CA. Do not trigger a paid live job for a routing check.
No IAM/IAP, Terraform, deployment settings or storage changes are needed.

No deployment, commit or push was performed. Existing cloud releases keep their
old navigation until this change is reviewed and delivered through the existing
approved workflow. See [ADR-0013](adr/0013-canonical-hub-navigation.md) for the
replacement of ADR-0008's root-preservation decision.

## Files changed

- Application and local tooling: `Caddyfile`, `app/cloud_preview.py`, `app/demo.py`, `app/hub_frontend/index.html`, `app/main.py`, `app/smoke.py`, `app/static/create.html`, `app/static/demo.html`, `app/static/module-nav.js`, `app/viewer.py`, `scripts/dev.py`.
- Tests and browser harnesses: `tests/browser_cloud_demo_smoke.py`, `tests/browser_cloud_preview_smoke.py`, `tests/browser_hub_smoke.py`, `tests/browser_smoke.py`, `tests/test_cloud_demo.py`, `tests/test_cloud_preview.py`, `tests/test_hub.py`, `tests/test_integration.py`, `tests/test_makefile.py`, `tests/test_smoke.py`.
- Documentation and decision history: `DEV_DEPLOY.md`, `README.md`, `docs/DEMO_SPEC.md`, `docs/DEPLOY_GCP.md`, `docs/HUB.md`, `docs/MAKEFILE.md`, `docs/MOCK_DEMO.md`, `docs/ROUTING.md`, `docs/adr/0008-local-demo-hub.md`, `docs/adr/0012-github-actions-delivery.md`, `docs/adr/0013-canonical-hub-navigation.md`, `docs/adr/README.md`.

Final checks: offline GitHub delivery source/preview contracts passed; 13 ADR
metadata/numbering/supersession checks and 94 relative Markdown references passed;
`git diff --check` passed. No dependency, workflow, IAM/IAP, Terraform or storage
schema changes. All 33 changed/new files remain uncommitted.
