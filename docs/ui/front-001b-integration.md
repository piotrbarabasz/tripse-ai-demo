# FRONT-001B — FastAPI SPA integration and provenance

2026-10-31, Europe/Warsaw. Branch `feature/front-001b-fastapi-integration` starts
from fetched `origin/dev` at `3f923d864c59296b17a2ccaf9db85081e62bdc53`, after the
FRONT-001A merge. Initial tree was clean. This implements source and local acceptance;
it does not deploy, merge, change cloud resources or establish hosted acceptance.

## Serving and security boundaries

`app/spa.py` registers only `/app`, `/app/` and a prefix-scoped `/app/{path:path}`
router after local/cloud composition. Local compiled output is `frontend/dist`;
the image uses `app/spa_dist`. Missing/incompatible index returns a generic 503;
legacy routes remain available without installing Node or building the SPA.
`create_app(frontend_dist=...)` is an injection seam for isolated tests, not an
HTTP/environment-controlled filesystem selector.

Both entry forms return HTML. Extensionless document navigations under the prefix
require `Accept: text/html` and absent/document Sec-Fetch-Dest. Unknown app views
load the client not-found page; static paths with extensions, absent chunks,
non-document fetches and asset-directory requests return real 404. Paths reject
traversal/backslash/Windows drive syntax and resolve asset containment before access.
There is no root catch-all. Existing `/`, Hub, Planner, token viewer, Studio,
simulator, API/internal/static routes and Caddy allowlists remain unchanged.

| Mode | HTML, navigation and assets |
| --- | --- |
| local | Existing `local_only`: loopback/explicit Docker-local peer, local Host, exact Origin when supplied, forwarded-header and cross-site denial |
| cloud_demo | Existing global Host + verified IAP/membership boundary, then `authenticated_demo`; reader/editor/task and write-Origin policies unchanged |
| readonly_demo | Separate app returned before SPA registration; no SPA route or asset tree |

All SPA responses, including denials, have nosniff, DENY framing, no-referrer and a
restricted CSP. Entry HTML is private/no-store. Local hashed JS/CSS gets
`private, max-age=31536000, immutable`, ETag and Last-Modified; cloud middleware
continues to override every response with private/no-store. No public caching or
authenticated cache policy is relaxed. Other assets remain private/no-store.

CSP uses default-src none; script/style/connect/img/font sources self; object,
base, form-action and frame-ancestor sources none. No unsafe-inline or unsafe-eval.
Radix scroll lock inserts runtime style elements, so each entry response substitutes
a random 24-byte nonce into a fixed meta marker and its style-src nonce directive.
The bootstrap passes that nonce to the exact shared `get-nonce` dependency before
React renders. No inline script is added. Browser QA verifies the open drawer's
style nonces and captures no CSP violations. Reference mechanisms:
[CSP style sources](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/style-src),
[get-nonce](https://github.com/theKashey/get-nonce).

## Bounded read-only health PoC

Hub requests same-origin GET `/health`, JSON Accept, same-origin credentials,
no-store and redirect:error. There are no retries or credential/token storage.
It validates the actual common response projection `{status: 'ok', generation_mode:
'mock' | 'live'}` and discards service, version, storage and other metadata.
Loading, success, generic HTTP/network/schema errors and a 5-second timeout are
explicit. AbortController cancels on timeout and unmount; late responses cannot
update an unmounted/timed-out view. Raw errors/bodies are never displayed.

Cloud `/health` retains its existing middleware exception. Success proves service
connectivity only, not authentication, IAP session validity or permissions. UI copy
states this explicitly. Standalone Vite does not host `/health`; its PoC displays an
error until using the compiled FastAPI origin. No proxy or alternate API origin is
introduced. Generated OpenAPI/Query remain API-001.

## Image and source proof

The Dockerfile has two stages: the official Node `24.18.0-bookworm-slim` index
`sha256:6f7b03f7c2c8e2e784dcf9295400527b9b1270fd37b7e9a7285cf83b6951452d`
and the unchanged Python 3.12-slim index
`sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159`.
The Node index digest/platforms were retrieved over TLS from Docker's official
registry token/manifest endpoints on 2026-10-31. Builder version is checked against
`.nvmrc`; install is `npm ci` and build is `npm run build`. Only dist is copied from
the builder to the Python runtime. Runtime pip install, API command, worker command,
storage volumes, port and Python pin remain unchanged. No Node tooling is copied.

The reviewed `TRIPSE_FRONTEND_BUILD_V1` marker opts a **selected committed Dockerfile**
into the frontend source contract in `scripts/gcp/frontend_build.py`. Exact inputs:

- `frontend/package.json`, `package-lock.json`, `.nvmrc`, `index.html`,
  `tsconfig.json`, `vite.config.ts`.
- `.ts`, `.tsx`, `.css` under `frontend/src/`, including tests required by the
  existing strict build; no speculative public assets or arbitrary frontend files.

Existing reviewed app/fixture/requirements/ignore inputs remain. node_modules,
dist (including `app/spa_dist`), coverage, caches, tsbuildinfo, dotenv, credentials,
private data and symlinks are excluded/rejected. Docker/GCP ignores match these
boundaries. A recipe/pin change, missing config, Node mismatch or lockfile root
dependency drift fails closed. Tests cover altered/missing source/lock/config bytes,
unexpected generated files, symlinks, secret scanning and exact manifest drift.

**Historical compatibility:** pre-marker Python-only Dockerfiles do not acquire
frontend files merely because those files exist at that historical SHA. Existing
historical trust anchors, immutable digest checks and accepted artifact rules are
unchanged. The outer Cloud Build operation is still the reviewed single Docker
command; only its committed multi-stage Dockerfile changes. Exact generation-pinned
archive comparison and context SHA256 manifests include new frontend inputs.
There is no working-tree source fallback or weakening of source verification.
The manual buildx benchmark accepts the reviewed multi-stage recipe without
rewriting either pin; unreviewed recipes still fail closed. It remains non-release QA.

## Verification and outstanding gates

| Check | Observed result |
| --- | --- |
| Frontend npm ci/typecheck/lint/test/build | PASS; 38 tests across 3 files; zero audit findings |
| Full Python suite | PASS; 1218 tests; existing Starlette/AnyIO deprecation warning |
| Focused SPA/provenance/Docker/Make/CI/history/benchmark suite | PASS; 235 tests; same warning |
| Compiled SPA browser smoke | PASS; actual local FastAPI plus offline cloud reader/IAP double; entries, all deep-link reloads, health, active links, not-found recovery, desktop/mobile focus, scroll-lock CSP and no external requests |
| Existing Hub browser smoke | PASS; legacy destinations/returns, real mock worker Planner/chat flows and responsive/keyboard checks |
| Existing cloud preview browser smoke | PASS; four viewports, fixture links, two PDF variants, no external requests |
| Existing authenticated cloud UI browser smoke | PASS; offline doubles; Hub, Studio save/reload/edit/preview, Planner/viewer and chat |
| Offline GCP source/runtime contracts | PASS; no cloud operations |
| Docker runtime | NOT RUN: CLI exists but Linux daemon pipe is absent; no image build/startup/content pass claimed |
| Hosted Cloud Run/IAP | NOT RUN; no deployment or hosted acceptance claimed |

Screenshots (ignored local QA artifacts, not customer data):
[local desktop](../../local-data/spa-qa/local-desktop.png),
[local mobile](../../local-data/spa-qa/local-mobile.png),
[cloud-double desktop](../../local-data/spa-qa/cloud-desktop.png),
[cloud-double mobile](../../local-data/spa-qa/cloud-mobile.png).
The new script is included in existing `make test-browser`, so the unchanged
unprivileged CI workflow runs it after the frontend production build. Existing
browser gates stay in place. `delivery.yml` and cloud/security resources are unchanged.
`make test-container` is extended to build frontend inputs, check Python-only runtime
contents, private local serving and readonly exclusion when Docker is available.

Initial checks caught and corrected: bare `/app` rendered no React content with a
slash-terminated Router basename; test/compiler lint expectations needed adjustment;
the manual benchmark's synthetic new Dockerfile needed matching frontend fixtures.
The exact Node version shell check also strips CRLF/newlines from `.nvmrc` so a
Windows working context does not falsely fail the same pin check.
The final checks described above passed after those corrections. No error was fixed
by weakening type/lint/source/security assertions.

Required before claiming complete image/hosted acceptance: run `make test-container`
with a Linux daemon; then, only in a separately authorized release, verify exact
Cloud Build source/digest evidence, compiled image/worker startup, IAP denials,
protected chunks, session expiry, CSP/cache/MIME behavior and deep-link refresh on
Cloud Run. Local mocks and passing source tests do not prove those outcomes.

## Exact rollback without changing business data

For immediate user continuity, use unchanged `/hub`, `/planner`, `/documents/demo`;
no default-route cutover or data migration was performed.

For a source rollback to legacy-only hosting:

1. Create a rollback branch from the then-current dev. Identify this integration
   commit (or its eventual squash/merge commit) with `git log --oneline -- Dockerfile
   app/spa.py scripts/gcp/frontend_build.py` and review `git show <commit>`.
2. Revert that integration commit with `git revert <commit>` (for a merge use its
   reviewed first parent). Revert the serving registration/module, nonce/health
   additions, Docker/ignore/input-contract changes and their tests together. Do not
   reset dev/master or edit document/database contents. Resolve later code conflicts
   against the reviewed diff; never restore old business data.
3. Run Python/legacy browser/offline source checks, frontend checks if retained,
   and container startup. Verify `/app*` is absent on FastAPI and legacy routes work.
   Publish through the normal dev PR/review process; no direct protected-branch edit.

For an already deployed release, use the **existing accepted-release rollback**
workflow with the target environment, an actual previously accepted legacy-only
image SHA and its unexpired accepted run/artifact IDs. Confirm its exact immutable
digest and proof first; do not assume the source baseline above was deployed or
accepted. This path reuses the prior image, does not rebuild a tag, and preserves
current data/storage. Missing historical proof requires existing operator recovery,
not a provenance bypass. No rollback/deployment operation is executed in this task.
