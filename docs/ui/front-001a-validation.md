# FRONT-001A — local verification record

2026-10-31 (Europe/Warsaw). Branch: `feature/front-001a-react-foundation`, created
from fetched `origin/dev` at `86481ac` (ARCH-001 and CI-007 included). Initial working
tree was clean. No existing package.json, Node lockfile, TypeScript or Vite setup
was present. Architecture/UI/API guidance, legacy Hub/Studio markup, proposed brand
tokens and CI security tests were inspected before adding the standalone frontend.
Legacy route inventory confirms `/hub`, `/planner`, `/documents/demo`.

## Results

| Check | Observed result |
| --- | --- |
| `cd frontend; npm ci` | PASS, 280 packages installed from lockfile |
| `npm run typecheck` | PASS, strict TypeScript including config and tests |
| `npm run lint` | PASS, typed ESLint, React Hooks and refresh rules, zero warnings |
| `npm run test` | PASS, 22 component/configuration tests in 2 files |
| `npm run build` | PASS, Vite 8.3.5; JS 341.66 kB / gzip 109.80 kB; CSS 17.24 kB / gzip 4.78 kB |
| `npm audit` / clean install audit | PASS, zero reported vulnerabilities with documented minimatch override |
| `.venv/Scripts/python.exe -m pytest -q` | PASS, 1146 tests, one existing Starlette/AnyIO deprecation warning |
| Focused CI/cache/integration/GCP deployment tests | PASS, 144 tests, same deprecation warning |
| `.venv/Scripts/python.exe -m scripts.gcp.ci offline` | PASS, source and preview contracts; no cloud access/deployment |
| `git diff --check` | PASS |
| Vite dev startup | PASS, loopback URL http://127.0.0.1:5173/app/ |
| Vite preview HTTP smoke | PASS, `/app`, `/app/`, all five modules and unknown nested URL return shell; hashed JS/CSS return correct MIME types |
| Production bundle inspection | PASS, `/app/assets/` prefix; development-origin canary absent; no credential patterns, matching process secret values or source maps found |
| Protected source diff | No changes to `app/`, Dockerfile, Docker/GCP source ignores, `infra/` or `delivery.yml` |

The HTTP smoke verifies serving only; it does not execute JavaScript or establish
visual usability. The browser connector reported `The browser access host is
unavailable`. Native Chrome fallback then stopped because Computer Use could not
determine the current browser URL with enough confidence to enforce policy. UI
automation stopped at that point. **No browser screenshot, desktop/mobile visual QA,
hosted acceptance or IAP/deep-link browser pass is claimed.** Actionlint was not
available and was not run. Existing browser/PDF/container scripts were not rerun;
their unchanged CI steps remain in place. No hosted CI run or PR was created.

## Failures corrected during implementation

- HTTP smoke found Vite's bare `/app` entry returned a base-path 404. A narrowly
  scoped dev/preview middleware redirects that entry to `/app/` and preserves query
  strings. Nested routing and future FastAPI integration remain separate.

- Typed lint initially rejected unused arguments in a no-op error hook; the unused
  hook was removed without weakening rules.
- Initial frontend assertions needed the test Vite base to match `/app/` and less
  brittle accessible-name matching for legacy anchors. All 22 now pass.
- First Python run: 1144 passed, one failed because an existing CI test enumerated
  the old command list. It now explicitly requires the five frontend commands;
  a new test checks unconditional execution and frontend working directory. Original
  permissions, single-job, credential and SHA-pin assertions remain intact. Full
  rerun: 1146 passed.
- Clean install initially encountered Windows EPERM because the task's running Vite
  server held the Lightning CSS native binary open. The owned server was stopped;
  `npm ci` and all frontend checks then passed. Stop dev/preview before reinstalling
  dependencies on Windows.
- Dependency review found a minimatch advisory in lint tooling. An exact 11.0.3
  override clears it; clean install and typed lint verify current compatibility.

## Scope and remaining acceptance

See [frontend README](../../frontend/README.md) for implemented structure, components,
routes, commands and the exact FRONT-001B scope. The UI is an informative shell;
planned modules have no data/API operations, fake statistics or authenticated user.
The proposed brand tokens are locally adapted, not newly approved branding.

Remaining risks: visual/mobile/browser acceptance still requires a working browser
automation session; dependency patch/override maintenance; temporary dual interfaces;
production fallback/security/asset/provenance behavior is entirely FRONT-001B.
No additional public loading/data primitives are needed until API reads are added.
API-001 owns generated clients/Query; later stages own actual business workflows.
FRONT-001B must finish the combined roadmap's `/health` PoC and hosted checks before
claiming the combined FRONT-001 accepted. No deployment or merge is performed here.
