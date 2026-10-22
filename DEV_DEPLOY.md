# Tripse AI Demo v0.1 — DEV deployment and end-to-end runbook

## Verified status (2026-10-22)

The **local** four-service stack runs at **https://localhost:8443**. It is explicitly
in **MOCK** mode because no OpenAI/Google credentials or paired WhatsApp session
are configured. This is not a verified real-map or WhatsApp demonstration and is
not a public DEV deployment. No external integration is substituted silently.

| Component | Automated / local status | Live external status |
|---|---|---|
| Webhook authentication and deduplication | PASS — HMAC, ignored senders, atomic duplicate handling | WAHA incoming delivery NOT VERIFIED |
| API, intent router, worker, SQLite | PASS — lifecycle, failure handling, persistence | Local processes verified |
| OpenAI brief and candidate generation | PASS — mocked HTTP contract | NOT VERIFIED — key absent |
| Google Places matches | PASS — mocked valid/invalid places | NOT VERIFIED — key absent |
| Google Routes and validator | PASS — mocked routes, failures and driving-limit warnings | NOT VERIFIED — key absent |
| Viewer desktop/mobile and directions URLs | PASS — browser, geometry contract and link construction | Live Google map / real directions NOT VERIFIED |
| WhatsApp acknowledgement and result | PASS — mocked WAHA HTTP adapter, retry and ordering | NOT VERIFIED — no paired session/test sender |
| Caddy HTTPS / admin isolation | PASS — local CA validation, redirect and private paths | Public DNS/ACME/mobile-network access NOT VERIFIED |

**83 unit/integration tests passed**, plus the headless browser smoke. One upstream
Starlette/AnyIO deprecation warning remains. See phase docs for schemas and limits.
The actual local HTTPS browser form also completed a mock job through the separate
worker and opened its viewer at desktop/mobile sizes. SQLite jobs, viewer tokens
and the local CA survived API/worker/Caddy container recreation. Public override
port isolation and URL-origin consistency were checked without starting a public
hostname. No paid API calls were made.

## 1. Local four-service demo

Requirements: Docker Engine/Desktop with Linux containers, Compose **2.24.4+**,
Python 3.11+ (commands below use Windows PowerShell and Python 3.12).

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
```

Preserve existing secrets. For the no-cost local run set these values in `.env`:

```dotenv
PLANNING_MODE=mock
CADDY_SITE=localhost
HTTP_PORT=8080
HTTPS_PORT=8443
PUBLIC_BASE_URL=https://localhost:8443
```

Set `WAHA_API_KEY` and `WAHA_WEBHOOK_HMAC_KEY` to different random secrets before
pairing WAHA. Generate each with Python's `secrets.token_hex(32)`. Leave
`WAHA_ALLOWED_SENDERS` empty until you know the exact test sender ID; empty means
deny all. No actual WhatsApp messages are sent by the mock/API smoke command.

```powershell
docker compose --profile dev --profile whatsapp up --build -d
docker compose --profile dev --profile whatsapp ps
docker compose --profile dev cp caddy:/data/caddy/pki/authorities/local/root.crt .venv/caddy-root.crt
.\.venv\Scripts\python -m app.smoke --base-url https://localhost:8443 --expect-mode mock --ca-cert .venv/caddy-root.crt
```

Caddy uses its **local CA** for localhost. The smoke verifies TLS with that exported
CA, without disabling certificate checks. To open it without a browser certificate
warning, install this stack's local CA in your current Windows user trust store:

```powershell
certutil -user -addstore Root .venv/caddy-root.crt
Start-Process https://localhost:8443
```

The API/browser fallback is the root page. Submit the prefilled target request,
wait for `completed`, then open the plan. In mock mode both days are placeholders;
all map values stay unverified and no routes, pins or Maps directions are invented.
`http://localhost:8080` redirects to the correct HTTPS port. No system trust-store
changes were made automatically during implementation.

If WAHA will not start/pair, the same fallback works with only three services:

```powershell
docker compose --profile dev up --build -d api worker caddy
```

API-only entry remains `POST /api/trips` with `{"text":"Zaplanuj 2 dni…"}`; poll
`GET /api/trips/{trip_id}` and use `result.viewer_url`. There is no WhatsApp-specific
planning path. Native Python startup remains documented in README.md.

## 2. Enable real planning

Add actual server secrets in `.env` and restart API/worker:

```dotenv
PLANNING_MODE=live
OPENAI_API_KEY=<server-key>
OPENAI_MODEL=gpt-4o-mini
GOOGLE_MAPS_API_KEY=<server-key-for-Places-New-and-Routes>
GOOGLE_MAPS_BROWSER_KEY=<different-browser-key-for-Maps-JavaScript>
GOOGLE_MAPS_MAP_ID=DEMO_MAP_ID
```

Separate `GOOGLE_PLACES_API_KEY` and `GOOGLE_ROUTES_API_KEY` override the shared
server key if provided. Enable the respective APIs and billing/limits. Restrict
the browser key to Maps JavaScript API and the local/DEV HTTP referrers you use.
Never reuse the server key as a browser key. Server credentials go only to the
worker in Compose. Use your own Google map ID for hosted DEV.

```powershell
docker compose --profile dev --profile whatsapp up -d api worker
.\.venv\Scripts\python -m app.live_maps_smoke
.\.venv\Scripts\python -m app.smoke --base-url https://localhost:8443 --expect-mode live --ca-cert .venv/caddy-root.crt
```

The first smoke makes at most two real Places lookups and one Routes call when
keys exist. The second creates **one normal trip job**, so live provider usage is
billable. It fails if the result is partial, lacks two calculated routes, fewer
than four matched places, geometry, or daily directions links. It never changes
mode or calls a mock provider to make a live test pass. Full model/provider limits
and estimation caveats are in [docs/PLANNING.md](docs/PLANNING.md).

## 3. Public single-host DEV preparation

No hostname/server was supplied; this deployment was **prepared, not executed**.
On an always-on Docker host, copy this project including `Caddyfile`, create its
private `.env`, and point a real DNS A/AAAA record at that host. TCP ports 80 and
443 must reach Caddy. Configure the keys above and:

```dotenv
DEV_DOMAIN=tripse-dev.your-domain.example
PUBLIC_BASE_URL=https://tripse-dev.your-domain.example
PLANNING_MODE=live
WAHA_ALLOWED_SENDERS=<exact-test-sender>@c.us
```

Use a bare real hostname for `DEV_DOMAIN`, without a scheme/path/port. The public
override derives both Caddy's site and worker URLs from that same hostname.

```powershell
docker compose -f compose.yaml -f compose.dev.yaml config --quiet
docker compose -f compose.yaml -f compose.dev.yaml up --build -d
docker compose -f compose.yaml -f compose.dev.yaml ps
```

This starts exactly `api`, `worker`, `waha`, `caddy`. Only Caddy publishes ports
80/443; API port 8000 is removed by the override. WAHA publishes no port, and its
dashboard/Swagger are disabled. Caddy proxies only application routes; WAHA
session/send endpoints, Caddy administration, `/docs` and `/openapi.json` are not
public. WAHA sends its signed webhook internally to `http://api:8000`.

Caddy obtains and renews a publicly trusted certificate automatically when DNS
and reachability are correct. The `localhost` local CA configuration is not used
for a real public DNS hostname. There is no third-party hosting/tunnel dependency.
This is a limited DEV demo: the browser/API create endpoint is intentionally
available to the demo audience, so restrict host access to that audience.

Verify the actual URL from a second network, including a phone on mobile data:

```powershell
.\.venv\Scripts\python -m app.smoke --base-url https://tripse-dev.your-domain.example --expect-mode live
```

Do not pass the localhost CA or disable TLS verification for a public host. Public
certificate issuance and mobile-network access must be reported NOT VERIFIED
until these checks have actually passed.

## 4. Pair only the dedicated WhatsApp test number

Follow [docs/WAHA.md](docs/WAHA.md) for session creation and QR pairing. Confirm the
session is `WORKING`; an empty session list is not evidence of WhatsApp delivery.
Configure exact allowed tester IDs. Groups, bot messages and other senders remain
ignored. Pairing administration stays private.

For local pairing, temporarily add `compose.waha-local.yaml` as documented there.
For a remote DEV host, add that file **on the host** and use SSH port forwarding
to its loopback port; never publish WAHA on the internet:

```powershell
# On the DEV host:
docker compose -f compose.yaml -f compose.dev.yaml -f compose.waha-local.yaml up -d waha
# On your computer, while pairing:
ssh -L 3000:127.0.0.1:3000 user@your-dev-host
# After pairing, remove the loopback binding on the host:
docker compose -f compose.yaml -f compose.dev.yaml up -d --force-recreate waha
```

Send from an allowed **tester phone** to the bot's dedicated test number:

> Zaplanuj 2 dni: Wrocław → Karpacz → Szklarska Poręba → Wrocław. Natura, maksymalnie 3 godziny jazdy dziennie.

Confirm, in order: acknowledgement with `trip_id`; completed job; result message
with a reachable HTTPS URL; two readable days on the phone; calculated polylines
and driving estimates; relevant warnings; both daily Maps links open the intended
stops. Driving-limit warnings appear only when actual duration exceeds the limit.
No warning or route is manufactured for the demonstration.

Check that existing job without generating a second paid trip:

```powershell
.\.venv\Scripts\python -m app.smoke --base-url https://tripse-dev.your-domain.example --expect-mode live --trip-id <trip_id-from-ack>
```

This checks persisted status/result/viewer. It still reports phone delivery and
live browser-map rendering as NOT VERIFIED until a person confirms them. The
automated suite separately replays the same signed message ID to prove one job
and one stored result notification. Message delivery is at least once; a crash
after WAHA accepts an outbound request can repeat the message, not the trip job.

## 5. Persistence, checks and troubleshooting

- `tripse_data`: SQLite shared by API and the single worker.
- `waha_sessions`: WhatsApp authentication/session storage.
- `caddy_data`, `caddy_config`: certificates/CA, renewal state and Caddy config.

`docker compose down` preserves volumes. **`down -v` deletes jobs, sessions and
certificate state.** Do not scale the worker. Recovery can repeat paid provider
calls for a job interrupted by a process crash; failed WhatsApp sends retry without
rerunning completed planning. Docker API access logging is disabled so viewer
tokens are not written to Uvicorn access logs; Caddy access logging is not enabled.

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m playwright install chromium
.\.venv\Scripts\python tests/browser_smoke.py
docker compose --profile dev exec caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
docker compose logs --tail 50 worker
```

The repeatable API smoke checks the selected mode, browser fallback, authentication
rejection, private paths, terminal job state, viewer/data access and direction
links in live mode. It returns nonzero on failed assertions/timeouts. Browser smoke
uses intercepted Google calls and synthetic data; unit tests forbid paid HTTP.

Current blockers for the **live P0 demonstration**: OpenAI key, Places/Routes server
key(s), restricted browser key, dedicated number paired to WAHA, allowed tester,
and (for remote/mobile-network access) a public DEV host/DNS. The public Caddy stack
is ready to configure; these missing inputs have not been presented as successful
integrations. Visual polish was not added in this phase.
