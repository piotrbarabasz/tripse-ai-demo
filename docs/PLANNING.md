# Task 03 — AI trip planning pipeline

## Configuration

Native Python reads exported environment variables. Docker Compose loads `.env`.
Do not overwrite the existing WAHA secrets when adding these settings:

```dotenv
PLANNING_MODE=live
OPENAI_API_KEY=<server-secret>
OPENAI_MODEL=gpt-4o-mini
GOOGLE_MAPS_API_KEY=<server-secret>
PUBLIC_BASE_URL=http://localhost:8000
```

Enable **Places API (New)** and **Routes API** for the Google key's project and
configure billing/limits. Alternatively use separate `GOOGLE_PLACES_API_KEY` and
`GOOGLE_ROUTES_API_KEY`; these take precedence over the shared key. Keys are only
passed to the worker, never the viewer or model. `OPENAI_MODEL` must support the
Responses API and strict structured output. The default is a small compatible
model; this is not an automatic choice of the newest model.

```powershell
docker compose up --build -d
# Add --profile whatsapp before up when using the paired gateway.
```

API startup and `/health` work without paid keys. In live mode a queued job fails
with a readable configuration error if keys are missing. For the fixed no-cost
sample from Task 01, explicitly set `PLANNING_MODE=mock`. There is no silent mock
fallback. `/health` reports the selected mode, not provider readiness.

## Pipeline and bounds

1. One OpenAI Responses request uses `text.format` with a strict JSON schema.
   Pydantic validates the returned brief and named candidates. The schema contains
   only start/end names, days, required places, preferences, the user's driving
   limit, candidate queries and proposed days. It has **no fields for provider map
   facts**, and extra fields are rejected. Refusal, truncation, invalid output and
   OpenAI errors fail the job explicitly. Missing start/end/days are not guessed.
2. This demo supports **one or two days**. Other durations fail explicitly. Required
   places retain their relative order and are spread across days; candidates are
   placed in their suggested day. This is a draft grouping, not an optimizer.
3. There are at most **eight unique search queries including endpoints and required
   places**. Required places take priority; extra optional candidates are omitted
   with a warning. Repeated queries are cached within the job. No follow-up research
   or pagination is performed.
4. Places Text Search (New) requests only `id`, `displayName`, and `location`, with
   one top match per query. Only returned, valid Google IDs/coordinates become
   `Place` records. The match confirms the returned place's geography, not that the
   top result necessarily matches the user's intended attraction; review relevance.
   Empty or failed lookups are stored as `unresolved_places`, never map pins with
   placeholder coordinates. Locations do not prove safe driving/parking access.
5. Day 1 starts at the requested origin; later days continue from the previous
   day's final stop. The final day ends at the requested destination. Missing
   required points/endpoints prevent a full-route claim for that day. Optional
   unresolved candidates are omitted and warned about. No hotels are inferred.
6. Each routable day gets one `computeRoutes` request using verified Place IDs,
   `DRIVE`, and `TRAFFIC_UNAWARE`. Only the returned `distanceMeters`, protobuf
   duration and encoded polyline are saved. Seconds/meters are preserved and
   deterministically converted to minutes/kilometers without early rounding.
7. Warnings are deterministic: `daily_drive_limit_exceeded` compares seconds with
   the requested minute limit; `unresolved_place` identifies failed matches;
   `route_calculation_failed` identifies Routes failures. Missing required points
   yield `routing_status: unverified`. Provider calculation failures yield
   `routing_status: routing_failed`. All missing route metrics and geometry are
   **null**, never zero or LLM estimates. Partial plans complete with warnings.
8. Pydantic `TripPlan` is serialized to SQLite. Job status, viewer access and pending
   WhatsApp result are committed atomically. Fatal errors produce `failed` and a
   readable error, plus a failure reply for WhatsApp-origin jobs.

Maximum provider workload per job: **one OpenAI request, eight Places requests and
two Routes requests**. Connect/read/write timeouts are 60, 10 and 15 seconds per
request respectively; no automatic HTTP retries. One worker processes jobs. On
restart interrupted jobs are requeued, so a crash can repeat provider calls and
charges; this is a demo, not an exactly-once paid-task system.

## Plan links and messaging

Every successfully completed new job receives a random 256-bit URL token valid
for 24 hours. SQLite stores the token hash/expiry; Task 04 serves the HTML viewer
at `GET /trip/{token}` and the read-only **JSON payload** at `GET /api/viewer/{token}`.
JSON uses `no-store` and `no-referrer` headers. Invalid or expired
tokens return 404. Raw request text and WhatsApp sender data are excluded. There
is no edit endpoint. Task 04 adds the HTML/map UI; public deployment is later work. Old completed
Task 01/02 jobs are not retroactively issued links.

Per-day Google Maps directions URLs use names plus verified origin/destination
and waypoint Place IDs, with URL encoding. They ask Maps to calculate directions
when opened; they do not prove a successful Routes calculation. A Routes failure
may still retain a directions URL for verified points. Missing required endpoints
leave it null. Maps may recalculate a different route/traffic estimate when opened;
mobile browsers may support fewer waypoints than desktop Maps.

For WhatsApp-origin jobs the worker first attempts acknowledgement, then runs
planning, then sends a short result summary and viewer URL after acknowledgement
has been delivered. It includes incomplete-routing and driving-limit warnings.
Completion delivery uses its own durable outbox and 30-second retries, independent
of planning. Duplicate webhook events create neither new jobs nor extra result
rows. A crash/timeout after WAHA accepts a message can still repeat that message.
API-origin jobs never send WhatsApp messages.

Use a reachable `PUBLIC_BASE_URL` origin for WhatsApp; localhost URLs are only
usable on this computer. Links may expire while WAHA is unavailable. The default
Compose deployment remains local and is not a public DEV deployment.

## Tests and controlled live maps smoke

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m app.live_maps_smoke
```

Unit tests use `httpx.MockTransport`, fake provider keys and temporary SQLite files.
An autouse fixture blocks real HTTP transport, even if keys are present. Synthetic
provider IDs, coordinates and routes exist only in test fixtures and are not
evidence of live verification.

The **separate, manually invoked** smoke command reads exported variables and local
`.env`. With Google keys it makes at most two Places lookups (Wrocław and Karpacz)
and one Routes call, with no retries and no OpenAI call. It prints safe place/route
facts and whether a polyline was returned; it never prints keys. Without keys it
prints **NOT VERIFIED** and makes no paid calls. This small smoke does not verify
all suggested attractions or the full target itinerary.

Official API contracts used:

- [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [Google Places Text Search (New)](https://developers.google.com/maps/documentation/places/web-service/text-search)
- [Google Routes computeRoutes](https://developers.google.com/maps/documentation/routes/compute_route_directions)
- [Google Maps directions URLs](https://developers.google.com/maps/documentation/urls/get-started)

Real map calculations: **NOT VERIFIED** during implementation because no Google
Places/Routes keys were configured. Full live OpenAI planning and WhatsApp result
delivery also remain unverified without credentials and a paired test session.

### Implementation test report — 2026-10-22

- **73 automated tests passed**; one upstream Starlette/AnyIO deprecation warning.
- Mocked target-scenario success, invalid places, missing required endpoints,
  Routes failures, unrounded driving-limit checks and the eight-query cap passed.
- Persistence, expiring viewer access, forbidden viewer writes, fatal worker
  failures and WhatsApp completion retry/recovery passed.
- Default Compose configuration validated; API and worker images built and started.
- Container HTTP smoke: health returned 200 in live mode; POST returned 202; worker
  recorded a readable `failed` job because keys were missing. Unknown viewer
  tokens returned 404.
- Controlled Google smoke command: **NOT VERIFIED — no configured keys; zero paid
  calls made**. No live OpenAI or WhatsApp completion test was performed.
