# UI routing and coexistence

FRONT-001A, 2026-10-31: standalone React routing is implemented. FastAPI routing,
static mounts, Caddy, authentication and legacy interfaces remain unchanged.
The [existing server route inventory](../ROUTING.md) is still authoritative.

| URL | Behavior in this stage |
| --- | --- |
| `/app`, `/app/` | Informative React Hub on the standalone Vite origin |
| `/app/planner`, `/app/documents` | Planned React views with full-page links to legacy tools |
| `/app/marketing`, `/app/automations`, `/app/assistant` | Explicitly planned modules; no business workflows |
| Unknown `/app/*` path | Client not-found view with recovery link |
| `/`, `/hub`, `/planner`, `/trip/{token}` | Existing FastAPI redirect/Hub/Planner/viewer retained |
| `/documents/demo` and hashes | Existing Studio retained, including library/editor/history |
| `/demo/chat`, `/preview/*` | Existing simulator and separate readonly fixtures retained |
| `/api/*`, `/internal/*`, `/health`, `/static/*`, `/documents/assets/*` | Existing server contracts, never assigned to React Router |

Vite has `base: '/app/'`; BrowserRouter consumes `import.meta.env.BASE_URL` as
basename. Client links use paths relative to this basename. Vite dev/preview support
direct nested navigations, but this does not establish production deep-link serving.
Unknown views are client-side 404 presentations, not a claim of an HTTP 404 response.

Loopback dev: http://127.0.0.1:5173/app/; preview: http://127.0.0.1:4173/app/.
No Vite API proxy is configured. To reach independently running local FastAPI,
set `VITE_DEV_BACKEND_ORIGIN=http://127.0.0.1:8000` in ignored
`frontend/.env.local`, then restart Vite. Only development anchors change;
production legacy links always remain `/hub`, `/planner`, `/documents/demo`.
No deployed hostname is hardcoded and no security headers are bypassed.
See [startup/configuration](../../frontend/README.md).

## FRONT-001B hosting contract (deferred)

Implement exact `/app` plus bounded `/app/` HTML navigation fallback in local and
cloud_demo only, under existing guards. Reserve `/app/assets/` for compiled output;
missing assets/chunks return 404, never index.html. Unknown APIs/internal/legacy paths
keep their original status/body semantics. No root catch-all or default-route cutover.

Preserve local_only and global IAP Host/Origin boundaries. Keep readonly_demo
allowlists and the Caddy public allowlist unchanged. Validate CSP, MIME/cache headers,
session failures, nested refreshes and protected chunks in the compiled image and
authorized hosted browser checks. Add the read-only `/health` PoC in that stage.
Source/build provenance, image packaging and fallback acceptance must move together.

This explicitly splits the [combined FRONT-001 roadmap](../architecture/migration-roadmap.md).
Real Planner, Studio, Marketing, Automations and Assistant workflows remain later work;
client placeholders do not reserve or modify FastAPI routes or permission contracts.
Legacy links use ordinary anchors; client navigation stays under the app basename.
