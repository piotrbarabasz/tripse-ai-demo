# Task 04 — minimal trip viewer

## Run and configure

The existing worker generates `/trip/{token}` links when a job completes. Those
URLs now serve a responsive HTML viewer directly from FastAPI. The page fetches
`/api/viewer/{token}` for its plan. Both endpoints validate the 43-character
URL-safe token, its SHA-256 hash, 24-hour expiry and completed job status.
Invalid/expired tokens return 404 without trip data. Tokens are not renewed by
visiting the viewer. There are no editing endpoints or accounts.

Keep existing server credentials in the worker. Add these **different browser
settings** to `.env` for Compose (or export them in the native API terminal):

```dotenv
GOOGLE_MAPS_BROWSER_KEY=<separate-browser-key>
GOOGLE_MAPS_MAP_ID=DEMO_MAP_ID
```

Enable Maps JavaScript API for the browser key. Restrict its APIs to Maps
JavaScript API and its application usage to the HTTP referrers you use, such as
`http://localhost:8000/*`, `http://127.0.0.1:8000/*` and your DEV HTTPS origin.
Use origin-wide restrictions because the Maps loader uses
`auth_referrer_policy=origin`. Use your own map ID for hosted DEV; `DEMO_MAP_ID`
is the documented development value for advanced markers.

The browser key is intentionally visible to users and must be restricted. The
server keys `GOOGLE_MAPS_API_KEY`, `GOOGLE_PLACES_API_KEY` and
`GOOGLE_ROUTES_API_KEY` are not passed to the API service by Compose and are never
used as a viewer fallback. Native configuration also refuses to publish a browser
key if it equals a configured server key. Never assign the same key to both roles.

```powershell
docker compose up --build -d
```

Open a newly generated viewer URL from `GET /api/trips/{id}`. Without a browser
key the daily itinerary and Google Maps links remain usable; the map explicitly
says it is not configured. Missing server keys still require explicit
`PLANNING_MODE=mock` for a no-cost sample. A mock plan shows no map geometry or pins
and labels all route data unverified. A valid live result needs the Task 03 keys.

## Behavior

- Desktop: itinerary on the left, sticky map on the right. Below 760px: itinerary
  followed by the map, with no horizontal scrolling at the tested 390px viewport.
- Each day has ordered stops, calculation status, driving time/distance, warnings
  and a directions link when one is available. Missing values remain visibly
  unverified. Display rounding never turns a null metric into zero.
- Only places with verified status, Google Places provenance, a Place ID and valid
  coordinates become markers. Mock/unresolved places never become map pins.
- Only verified Google Routes geometry is decoded and drawn. No straight-line or
  guessed fallback route is drawn when geometry is missing, invalid or failed.
- Clicking a day card/button emphasizes its colored polyline and fits its bounds;
  clicking a route also selects that day. “Show all days” restores the itinerary
  bounds. Google Maps links open in a separate tab and Maps may recompute routes.
- Loading, data-fetch retry, missing key, map-load timeout and authorization
  failures are handled separately. A map failure does not hide the itinerary.
- Provider strings use DOM `textContent`; no raw plan HTML is inserted. Directions
  URLs allow only HTTPS `www.google.com/maps/dir/?api=1` links. Server-rendered HTML
  contains no inline plan payload or credentials.
- The page is `no-store`, not indexed, not frameable, and uses a Content Security
  Policy for local assets and Google Maps. Page referrers send **only the origin**
  so browser-key restrictions work without exposing token paths to Google. JSON
  uses `no-referrer`. The public plan excludes original request text and sender data.

The viewer requests no Places or Routes calculations. It renders the facts already
stored by the worker. Google Maps JavaScript loading can incur normal Google usage.

## Verification — 2026-10-22

```powershell
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m playwright install chromium
.\.venv\Scripts\python tests/browser_smoke.py
```

- **78 unit/API tests passed**, including token expiry, read-only methods, private
  data filtering, secret isolation and HTML/static asset serving.
- Headless Chromium smoke passed at **1440×1000** and **390×844**. It covers both
  days, directions URLs, marker/polyline selection, fitting bounds, missing routes,
  unverified points, safe text/URLs, loading/retry, missing configuration, map load
  and authorization failures, and invalid/expired token pages.
- Screenshots were visually reviewed; the browser smoke saves them under
  `local-data/viewer-qa/` in the current worktree. Its map is an explicit test double, not a real map.
- Unit tests block paid provider HTTP calls. Browser tests use synthetic persisted
  data and intercept external requests; **no live Maps API calls are made**.
- Docker build/start and HTTP smoke passed: healthy API, served JS/CSS assets,
  invalid HTML token rejection and invalid JSON token rejection. JavaScript syntax,
  Compose configuration and dependency consistency checks also passed.

**Live Google map rendering remains NOT VERIFIED** without a configured restricted
browser key and a plan produced by live Places/Routes. The automated map contract
checks do not establish live Google authorization or real route accuracy.

Official references: [Maps loader](https://developers.google.com/maps/documentation/javascript/load-maps-js-api),
[advanced markers](https://developers.google.com/maps/documentation/javascript/advanced-markers/start),
[polyline decoding](https://developers.google.com/maps/documentation/javascript/geometry),
[key restrictions](https://developers.google.com/maps/api-security-best-practices).
