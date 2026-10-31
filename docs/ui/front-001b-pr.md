# Proposed PR: Integrate private React SPA with FastAPI and release provenance

Base: `dev`. Head: `feature/front-001b-fastapi-integration`.

## Behavior

Serve the compiled React shell at `/app` and `/app/` on the existing FastAPI origin.
Document deep links work; missing resources/chunks stay HTTP 404. Both HTML and assets
retain local-only/verified-IAP protection, with no registration in readonly_demo.
Legacy routes and business functionality remain unchanged. Normalize the Router
basename so the previously masked bare `/app` case renders correctly.

Add a bounded same-origin health read with validation, error/timeout/cancellation
states and explicit connectivity-only semantics. Use a per-response style nonce
for Radix scroll-lock CSS while preserving strict script/style CSP.

Build frontend via a digest-pinned Node stage, copy only dist into the unchanged
pinned Python runtime, and version the committed frontend input allowlist. Exact
source/manifest proof includes lock/config/source bytes, while pre-integration
contexts retain historical promotion/rollback compatibility. The outer Cloud Build
recipe and delivery security/artifact contracts remain unchanged.

## Validation

- Frontend clean install, typecheck, lint, 38 tests and production build pass.
- Full Python suite: 1218 pass; one pre-existing Starlette/AnyIO deprecation warning.
- Focused SPA/provenance/Docker-contract/Make/CI/history/benchmark suite: 235 pass.
- Compiled local and mocked-cloud SPA browser smoke plus existing Hub, cloud preview
  and authenticated cloud UI browser regressions pass.
- Offline source/runtime contracts and diff checks pass. The new SPA browser smoke
  is added to existing unprivileged CI via the existing browser runner.

Docker CLI is installed but the Linux daemon pipe is unavailable: image build,
startup and runtime-content checks have not run. No hosted Cloud Run/IAP acceptance,
deployment or cloud change is claimed. Those remain explicit evidence gates.

## Review and rollback

See [integration guide](front-001b-integration.md) for screenshots, source boundaries,
remaining gates and rollback. Revert serving/build/source-contract changes together
without changing business data, or use an actual previously accepted legacy-only
image through the existing accepted-release rollback flow. Merging to dev retains
the repository's existing DEV delivery trigger; this task does not merge or deploy.
