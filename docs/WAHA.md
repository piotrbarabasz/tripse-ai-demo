# Task 02 — WhatsApp test gateway

## Version and authentication

Compose pins the free WAHA image `devlikeapro/waha:latest-2026.9.2` and digest
`sha256:280bdc8f860267a2488a45d00ec88529646f7468c0bf0283c595d6efdd1b5e3b`.
The official release and Docker Hub tag were checked during implementation.
The engine is WEBJS; the single session is `default`.

The receiver implements the documented **raw-body HMAC-SHA512, hex digest**:
`X-Webhook-Hmac` and `X-Webhook-Hmac-Algorithm: sha512`. It uses constant-time
comparison before parsing JSON. This is not WAHA's outbound API key; the two
secrets must differ. No configured webhook key means 503 (disabled), invalid or
missing authentication means 401. WAHA's global `WHATSAPP_HOOK_HMAC_KEY` signs
requests to `http://api:8000/api/webhooks/waha` with these exact headers.

Official references:

- [Webhook authentication, global configuration and retries](https://waha.devlike.pro/docs/how-to/events/#hmac-authentication)
- [Versioned sender implementation](https://github.com/devlikeapro/waha/blob/2026.9.2/src/modules/waha-webhook/WebhookPlugin.sender.ts)
- [Versioned global webhook configuration](https://github.com/devlikeapro/waha/blob/2026.9.2/src/modules/waha-webhook/webhook.config.ts)
- [WAHA release](https://github.com/devlikeapro/waha/releases/tag/2026.9.2)
- [API key and dashboard security](https://waha.devlike.pro/docs/how-to/security/)
- [Send text API](https://waha.devlike.pro/docs/how-to/send-messages/#send-text)
- [Session and QR API](https://waha.devlike.pro/docs/how-to/sessions/)

## Configuration and startup

Use a **dedicated test number** for the bot. WAHA is unofficial; do not pair a
personal or production account. The gateway itself makes no paid API calls;
Task 03 live planning uses OpenAI and Google APIs (see [PLANNING.md](PLANNING.md)).

Copy `.env.example` to `.env` if it does not already exist. Generate two different
secrets with Python's `secrets.token_hex(32)` and set:

```dotenv
WAHA_API_KEY=<first-random-secret>
WAHA_WEBHOOK_HMAC_KEY=<second-random-secret>
WAHA_ALLOWED_SENDERS=48123456789@c.us
```

Replace the example sender with the actual test sender's full ID. The allowlist
is comma-separated, exact IDs only, and defaults to **deny all**. `@lid` IDs are
also accepted only when explicitly listed; the gateway never infers an ID or
looks up phone numbers. With WEBJS, use the actual inbound ID if WhatsApp uses a
LID for that contact. Never add group IDs. The paired bot number is distinct from
allowed testers. Keep `.env` and QR/session data private (ignored by Git).

```powershell
docker compose --profile whatsapp up --build -d
```

WAHA has **no published port** by default; dashboard and Swagger are disabled.
`waha_sessions:/app/.sessions` persists authentication and session configuration.
`docker compose down` preserves it; `down -v` deletes sessions and trip data.
API and worker have no startup dependency on WAHA. Without WhatsApp, the original
`docker compose up --build` still runs API and worker with no keys required.

## Pair locally

Temporarily enable authenticated API access on **127.0.0.1 only**:

```powershell
docker compose -f compose.yaml -f compose.waha-local.yaml --profile whatsapp up -d
# Enter the WAHA_API_KEY value from your local .env; do not commit it.
$headers = @{ 'X-Api-Key' = '<your-local-WAHA_API_KEY>' }
Invoke-RestMethod http://localhost:3000/api/version -Headers $headers
Invoke-RestMethod http://localhost:3000/api/sessions -Headers $headers
# Create only if default does not exist. Global webhook config is already applied.
Invoke-RestMethod http://localhost:3000/api/sessions -Headers $headers -Method Post -ContentType 'application/json' -Body '{"name":"default","start":true}'
# For an existing stopped session instead:
# Invoke-RestMethod http://localhost:3000/api/sessions/default/start -Headers $headers -Method Post
New-Item -ItemType Directory -Force data | Out-Null
$qrHeaders = $headers.Clone()
$qrHeaders['Accept'] = 'image/png'
Invoke-WebRequest http://localhost:3000/api/default/auth/qr -Headers $qrHeaders -OutFile data/waha-qr.png
```

Open the PNG and scan it using WhatsApp → Linked devices on the **test number**.
Wait for session status `WORKING`. Remove the temporary pairing port afterwards:

```powershell
docker compose --profile whatsapp up -d --force-recreate waha
```

Do not publish WAHA via a tunnel, reverse proxy or public interface. Only the
FastAPI webhook is an integration endpoint. For native Python, set
`WAHA_WEBHOOK_HMAC_KEY`, `WAHA_ALLOWED_SENDERS` in the API terminal, and
`WAHA_BASE_URL` / `WAHA_API_KEY` in the worker terminal; `.env` is not auto-loaded.
Use the local pairing override if a native worker needs to reach WAHA.

## Behavior and boundaries

- Only `message` events in `default` are accepted. Bot messages (`fromMe`), groups,
  broadcasts, other sessions, media, known non-text types and unlisted senders
  return 200 `ignored`. Missing safety fields are ignored as well.
- Supported commands: `trip.create <request>`, `Zaplanuj wycieczkę…`,
  `Zaplanuj 2 dni…`, `Plan a trip…`. A small deterministic rule maps these to
  `trip.create`; other messages return `intent: unsupported` and create no job.
  This is a command router, not a language understanding model.
- A valid event returns 200 `accepted` plus `trip_id`. A repeated message returns
  200 `duplicate` and the original ID. The deduplication key is
  `(session, payload.id)`, not the webhook envelope ID, and survives restarts.
  SQLite commits the deduplication row, trip and pending acknowledgement atomically.
- The existing worker sends acknowledgements through the reusable
  `MessagingProvider` interface and `WahaMessagingProvider` adapter. The outbound
  API uses `POST /api/sendText` with `X-Api-Key`. Acknowledgements include the
  `trip_id` and a mode-appropriate disclaimer. Planning still runs independently.
- Failed sends remain pending, retry after 30 seconds, and use a five-second HTTP
  timeout per attempt. Worker startup recovers interrupted sends. Exactly one
  worker is supported. Delivery is at least once: a crash or timeout after WAHA
  accepts a send but before its receipt is saved can repeat an acknowledgement;
  it **cannot create another trip**. No exactly-once outbound guarantee is claimed.
- Task 03 adds durable completion/failure replies after acknowledgement delivery,
  with a short summary, warnings and a 24-hour read-only viewer URL. Completion
  sends retry independently of planning, so WAHA outages do not rerun the pipeline.
  Conversational memory and advanced intent routing remain outside scope.

## Verification

Run `.\.venv\Scripts\python -m pytest -q`. Automated tests cover valid signed
messages, durable and concurrent deduplication, authentication failures, ignored
messages, exact outbound API payloads, offline WAHA, retry, and interrupted sends.

For a real smoke test, send `Zaplanuj 2 dni w Karpaczu` from an allowlisted tester
to the paired test number. Confirm the acknowledgement includes a trip ID, then
poll `/api/trips/{id}` to completion. Replay the same captured signed event and
confirm there is still one job. Inspect `docker compose logs worker` on send errors.

**Real WhatsApp smoke test: NOT VERIFIED until a dedicated test number is paired
and an allowed tester sends a message.** Container startup, synthetic webhooks and
mocked outbound tests do not prove real WhatsApp delivery.

### Implementation test report — 2026-10-22

- Automated suite: **53 passed**; one upstream Starlette/AnyIO deprecation warning.
- `pip check`: no broken requirements.
- Default and WhatsApp-profile Compose configuration checks passed.
- `docker compose --profile whatsapp up --build -d` completed successfully.
- Running `/api/version`: **2026.9.2**, **WEBJS**, **CORE**; session list: `[]`.
- WAHA administration has no host port mapping; API remains bound to localhost.
- Container HTTP smoke: unsigned webhook → 401; correctly signed webhook from
  an unlisted sender → 200 `ignored`.
- With WAHA stopped: health → 200; direct trip creation → 202; worker → `completed`
  with the labeled mock result. WAHA was restarted afterwards.
- Real WhatsApp receive/acknowledgement: **NOT VERIFIED**. No paired session or
  allowlisted tester was configured. Local `.env` has generated secrets and an
  empty sender allowlist. Pair and configure a dedicated test number before use.
