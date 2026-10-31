# UI routing and coexistence

Status: proposed. The [existing route inventory](../ROUTING.md) remains the current
contract. ARCH-001 adds no routes.

| URL | Current behavior | Proposed migration ownership |
| --- | --- | --- |
| `/`, `/hub` | 302 to Hub; legacy Hub | Retain; FRONT-002 adds a new Hub under `/app`, no default redirect cutover. |
| `/planner`, `/trip/{token}` | Planner form and token viewer | Retain, including public-proxy semantics; FRONT-002 adds `/app/planner`. Viewer stays legacy initially. |
| `/documents/demo` and its hashes | Studio catalog, creation, sources, library/edit/history | Retain deep links; FRONT-003 introduces separate `/app/documents/*` routes after workflow parity. |
| `/demo/chat` | Mock simulator | Retain; it is not the proposed general assistant. |
| `/preview/*` | readonly_demo fixture pages | Retain unchanged; no React shell in readonly_demo initially. |
| `/app`, `/app/*` | Not implemented | FRONT-001 shell; future `/app/planner`, `/app/documents/*`, `/app/assistant` belong to later stages. |
| `/api/*`, `/internal/*`, `/health`, `/static/*`, `/documents/assets/*` | Existing API/asset/probe routes | Never handled by React Router or SPA fallback. |

FRONT-001 must register exact `/app` plus a bounded HTML navigation fallback under
`/app/` in local/cloud_demo composition only. Reserve `/app/assets/` for build output;
missing chunks/files return 404 instead of index.html. Valid deep links refresh into
the shell, and unknown app paths display an app not-found state. Legacy/API unknown
paths keep existing status/body semantics. Do not register a root catch-all.

Apply local_only to private shell requests/assets locally and the existing global
IAP middleware in cloud_demo. Static JavaScript is not an identity capability.
Keep readonly_demo's separate route/asset allowlists intact. Caddy public allowlist
does not gain `/app`; private app access follows existing local/private cloud paths.

Vite development is loopback-only, with a reviewed same-origin API proxy that preserves
Host/Origin and does not introduce forbidden forwarded headers. If that cannot satisfy
the existing guard, test compiled assets through FastAPI instead of relaxing the guard.
Document the chosen development setup in FRONT-001. Do not expose the dev server to cloud.

Use real anchors for transitions to legacy modules. Preserve legacy hashes/query strings
and browser back/forward behavior; do not silently translate old links before parity.
Future cutover of `/` or existing module URLs requires separate owner acceptance and
rollback evidence. See [stage gates](../architecture/migration-roadmap.md).
