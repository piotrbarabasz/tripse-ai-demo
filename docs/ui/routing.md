# UI routing and coexistence

FRONT-001A/B, 2026-10-31: React routing and private compiled FastAPI serving are
implemented. Existing static mounts, Caddy, authentication and legacy interfaces remain unchanged.
The [existing server route inventory](../ROUTING.md) is still authoritative.

| URL | Behavior in this stage |
| --- | --- |
| `/app`, `/app/` | Compiled entry on the existing FastAPI origin in local/cloud_demo |
| `/app/planner` | Operational React request/status flow; full-page existing token viewer and legacy fallback |
| `/app/documents` | Planned React view with full-page link to legacy Studio |
| `/app/marketing`, `/app/automations`, `/app/assistant` | Explicitly planned modules; no business workflows |
| Unknown extensionless `/app/*` document navigation | Entry HTML with client not-found view |
| `/app/assets/*` | Private compiled assets; absent assets return HTTP 404 |
| `/`, `/hub`, `/planner`, `/trip/{token}` | Existing FastAPI redirect/Hub/Planner/viewer retained |
| `/documents/demo` and hashes | Existing Studio retained, including library/editor/history |
| `/demo/chat`, `/preview/*` | Existing simulator and separate readonly fixtures retained |
| `/api/*`, `/internal/*`, `/health`, `/static/*`, `/documents/assets/*` | Existing server contracts, never assigned to React Router |

Vite has `base: '/app/'`; BrowserRouter consumes its value with the trailing slash
trimmed as basename, accepting both `/app` and `/app/`. Client links remain under
that prefix. FastAPI now serves direct nested document navigations and refreshes.
Unknown views are client-side 404 presentations, not a claim of an HTTP 404 response.

Loopback dev: http://127.0.0.1:5173/app/; preview: http://127.0.0.1:4173/app/.
No Vite API proxy is configured. To reach independently running local FastAPI,
set `VITE_DEV_BACKEND_ORIGIN=http://127.0.0.1:8000` in ignored
`frontend/.env.local`, then restart Vite. Only development anchors change;
production legacy links always remain `/hub`, `/planner`, `/documents/demo`.
No deployed hostname is hardcoded and no security headers are bypassed.
See [startup/configuration](../../frontend/README.md).

## FRONT-001B hosting behavior

Exact `/app` plus bounded `/app/` HTML navigation fallback run in local and
cloud_demo only, under existing guards. `/app/assets/` is reserved for compiled output;
missing assets/chunks return 404, never index.html. Unknown APIs/internal/legacy paths
keep their original status/body semantics. No root catch-all or default-route cutover.

HTML and assets both use local_only locally and verified global IAP plus the existing
authenticated policy in cloud_demo. readonly_demo registers no SPA route or asset tree;
the Caddy public allowlist is unchanged. Fallback requires `Accept: text/html` and
document destination (or no destination header), with extensionless path segments.
Missing resources, asset directory requests, traversal attempts and non-document
fetches return HTTP 404. Entry HTML is private/no-store with a unique style nonce;
local hashed JS/CSS is private/immutable, while cloud middleware retains no-store.
The `/health` PoC keeps its existing special access policy and proves only connectivity.
See [CSP/source contracts, evidence limits and rollback](front-001b-integration.md).
Compiled-image and authorized hosted IAP/chunk acceptance remain outstanding.

This explicitly splits the [combined FRONT-001 roadmap](../architecture/migration-roadmap.md).
FRONT-002 implements the [Planner request/status/viewer flow](front-002-planner.md).
Studio, Marketing, Automations and Assistant React workflows remain later work;
client placeholders do not reserve or modify FastAPI routes or permission contracts.
Legacy links use ordinary anchors; client navigation stays under the app basename.
