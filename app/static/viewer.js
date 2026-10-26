"use strict";

(() => {
  const $ = (id) => document.getElementById(id);
  const colors = ["#28745d", "#4667af"];
  let plan, map, selectedDay = null;
  const overlays = new Map();
  const markers = [];
  let allBounds;
  let mapAuthFailed = false;

  function element(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  const numeric = (value) => typeof value === "number" && Number.isFinite(value) && value >= 0;
  const verifiedStop = (stop) => stop.verification_status === "verified" && stop.source === "google_places"
    && typeof stop.place_id === "string" && stop.place_id.length > 0
    && typeof stop.lat === "number" && Number.isFinite(stop.lat) && Math.abs(stop.lat) <= 90
    && typeof stop.lng === "number" && Number.isFinite(stop.lng) && Math.abs(stop.lng) <= 180;
  const verifiedRoute = (day) => !plan.is_mock && day.routing_status === "verified"
    && numeric(day.drive_minutes) && numeric(day.distance_km)
    && typeof day.encoded_polyline === "string" && day.encoded_polyline.length > 0;

  function duration(minutes) {
    const rounded = Math.ceil(minutes);
    const hours = Math.floor(rounded / 60);
    return hours ? `${hours}h${rounded % 60 ? ` ${rounded % 60}min` : ""}` : `${rounded}min`;
  }
  function warningText(text) {
    if (text === "daily_drive_limit_exceeded") return "Przekroczony limit jazdy. Sprawdź plan tego dnia.";
    if (text === "route_calculation_failed") return "Nie udało się przygotować trasy. Brak czasu, odległości i przebiegu.";
    if (text.startsWith("unresolved_place:")) return `Place not verified: ${text.slice(17).trim()}`;
    if (text.startsWith("route_unverified:")) return "Route unverified: a required place or route endpoint is missing.";
    if (text.startsWith("candidate_limit:")) return "Some suggested stops were omitted to keep the itinerary short.";
    return text;
  }
  function safeDirectionsLink(value) {
    try {
      const url = new URL(value);
      return url.protocol === "https:" && url.hostname === "www.google.com"
        && url.pathname === "/maps/dir/" && url.searchParams.get("api") === "1"
        && !url.username && !url.password && !url.port ? url.href : null;
    } catch (_) { return null; }
  }
  function selectDay(number) {
    selectedDay = number;
    if (plan.is_mock && window.selectDemoDay) window.selectDemoDay(number);
    document.querySelectorAll(".day-card").forEach((card) => {
      const selected = Number(card.dataset.day) === number;
      card.classList.toggle("selected", selected);
      card.querySelector("button").setAttribute("aria-pressed", String(selected));
    });
    overlays.forEach(({line}, day) => line.setOptions({
      strokeOpacity: number === null || day === number ? .95 : .25,
      strokeWeight: day === number ? 7 : 4, zIndex: day === number ? 10 : 1,
    }));
    markers.forEach(({marker, days}) => { marker.zIndex = number !== null && days.has(number) ? 20 : 1; });
    if (!plan.is_mock) $("map-caption").textContent = number === null
      ? "All days · Only verified places and calculated routes appear on this map."
      : `Day ${number} highlighted · Missing routes are never drawn as straight lines.`;
    if (map) {
      const bounds = number === null ? allBounds : overlays.get(number)?.bounds;
      if (bounds && !bounds.isEmpty()) map.fitBounds(bounds, 45);
    }
  }
  function renderItinerary() {
    $("trip-title").textContent = plan.title || "Your trip plan";
    document.title = `${plan.title || "Trip plan"} · Tripse`;
    const brief = plan.requirements || {};
    const summary = [`${plan.days.length} ${plan.days.length === 1 ? "dzień" : "dni"}`];
    if (Array.isArray(brief.preferences) && brief.preferences.length) summary.push(brief.preferences.join(", "));
    if (numeric(brief.max_daily_drive_min)) summary.push(`Limit jazdy: ${duration(brief.max_daily_drive_min)}/dzień`);
    $("trip-summary").textContent = summary.join(" · ");
    const complete = !plan.is_mock && plan.verification_status === "verified" && plan.days.every(verifiedRoute);
    $("plan-status").textContent = plan.is_mock ? "DEMO — przykładowe miejsca, czasy i schemat mapy. Bez weryfikacji Google."
      : complete ? "Draft itinerary · Map data checked with Google; review all plan notes."
        : "Draft itinerary · Some places or routes are unverified. Review the warnings.";
    $("plan-status").classList.toggle("caution", !complete);
    $("plan-status").hidden = false;
    $("day-cards").replaceChildren();
    plan.days.forEach((day, index) => {
      const card = element("article", undefined, "day-card");
      card.dataset.day = String(day.number);
      card.style.setProperty("--day-color", colors[index % colors.length]);
      const heading = element("div", undefined, "day-heading");
      const button = element("button", undefined, "day-button");
      button.setAttribute("aria-pressed", "false");
      button.setAttribute("aria-label", `Highlight Day ${day.number} on map`);
      button.append(element("span", "", "day-swatch"), element("span", `Dzień ${day.number}`));
      const verified = verifiedRoute(day);
      const demo = plan.is_mock && day.routing_status === "demo";
      heading.append(button, element("span", demo ? "Trasa DEMO" : verified ? "Route calculated" : "Brak trasy",
        `route-badge${verified ? "" : " unverified"}`));
      card.append(heading);
      card.append(element("p", (verified || demo) ? `${duration(day.drive_minutes)} jazdy · ${day.distance_km.toLocaleString(undefined, {maximumFractionDigits: 1})} km`
        : "Czas i odległość niedostępne", "drive-stats"));
      card.append(element("p", demo ? "Dane przykładowe — bez obliczeń Google Routes" : verified ? "Google Routes · Estimate without live traffic" : "Brak obliczonej trasy", "source-note"));
      const stops = element("ol", undefined, "stops");
      (day.stops || []).forEach((stop) => {
        const item = element("li", stop.name || stop.query || "Unnamed stop");
        if (stop.description) item.append(element("span", stop.description, "hint"));
        if (!plan.is_mock && !verifiedStop(stop)) item.append(element("span", "Location unverified · Not shown on map", "stop-unverified"));
        stops.append(item);
      });
      card.append(stops.children.length ? stops : element("p", "No verified stops available for this day.", "empty-stops"));
      const warnings = [...(day.warnings || [])];
      if (!verified && warnings.length === 0) warnings.push("Route data is unavailable or unverified.");
      if (warnings.length) {
        const list = element("ul", undefined, "day-warnings");
        warnings.forEach((warning) => list.append(element("li", warningText(warning))));
        card.append(list);
      }
      const href = plan.is_mock ? null : safeDirectionsLink(day.google_maps_url);
      if (href) {
        const link = element("a", "Open in Google Maps ↗", "maps-link");
        link.href = href; link.target = "_blank"; link.rel = "noopener noreferrer";
        link.setAttribute("aria-label", `Open Day ${day.number} in Google Maps`);
        card.append(link);
      } else card.append(element("p", "Mapa DEMO pokazuje schemat. Brak obliczonej trasy Google Maps.", "maps-link unavailable"));
      card.addEventListener("click", (event) => { if (!event.target.closest("a")) selectDay(day.number); });
      $("day-cards").append(card);
    });
    const missing = (plan.unresolved_places || []).map(p => `Nieznalezione miejsce: ${p.query}. ${p.reason}`);
    const warnings = [...(plan.warnings || []), ...missing].filter((text) => !/^day_\d+:/.test(text));
    $("warning-list").replaceChildren();
    warnings.forEach((text) => $("warning-list").append(element("li", warningText(text))));
    $("notes-heading").textContent = `Uwagi do planu (${warnings.length})`;
    $("plan-notes").hidden = warnings.length === 0;
    $("viewer").hidden = false;
    $("page-status").hidden = true;
  }
  function mapMessage(message) {
    $("map-status").replaceChildren(element("p", message));
    $("map-status").hidden = false;
  }
  function loadMaps(key) {
    return new Promise((resolve, reject) => {
      const timer = window.setTimeout(() => reject(new Error("Map loading timed out. Use the daily Google Maps links.")), 15000);
      window.tripseMapsReady = () => { window.clearTimeout(timer); resolve(); };
      window.gm_authFailure = () => {
        mapAuthFailed = true;
        window.clearTimeout(timer);
        $("map").hidden = true;
        mapMessage("The interactive map could not be authorized. Use the daily Google Maps links.");
        reject(new Error("The interactive map could not be authorized. Use the daily Google Maps links."));
      };
      const script = document.createElement("script");
      const params = new URLSearchParams({key, v: "quarterly", loading: "async", callback: "tripseMapsReady",
        libraries: "geometry,marker", auth_referrer_policy: "origin"});
      script.src = `https://maps.googleapis.com/maps/api/js?${params}`;
      script.async = true;
      script.onerror = () => { window.clearTimeout(timer); reject(new Error("The map could not load. Check your connection or use the daily Google Maps links.")); };
      document.head.append(script);
    });
  }
  async function renderMap(config) {
    if (plan.is_mock && !config.browser_key) { window.renderDemoMap(plan, selectDay); return; }
    const visibleStop = plan.is_mock ? (stop) =>
      Number.isFinite(stop.lat) && Math.abs(stop.lat) <= 90 && Number.isFinite(stop.lng) && Math.abs(stop.lng) <= 180
      : verifiedStop;
    const places = new Map();
    plan.days.forEach((day) => (day.stops || []).filter(visibleStop).forEach((stop) => {
      if (!places.has(stop.place_id)) places.set(stop.place_id, {stop, days: new Set()});
      places.get(stop.place_id).days.add(day.number);
    }));
    if (places.size === 0) { mapMessage("No verified places are available to show on the map."); return; }
    if (!config.browser_key) { mapMessage("The interactive map is not configured for this demo. Use the daily Google Maps links."); return; }
    await loadMaps(config.browser_key);
    if (mapAuthFailed) throw new Error("The interactive map could not be authorized. Use the daily Google Maps links.");
    const maps = window.google.maps;
    map = new maps.Map($("map"), {mapId: config.map_id || "DEMO_MAP_ID", zoom: 7,
      center: {lat: places.values().next().value.stop.lat, lng: places.values().next().value.stop.lng},
      mapTypeControl: false, streetViewControl: false, fullscreenControl: true});
    allBounds = new maps.LatLngBounds();
    places.forEach(({stop, days}) => {
      const position = {lat: stop.lat, lng: stop.lng};
      const marker = new maps.marker.AdvancedMarkerElement({map, position,
        title: `${stop.name} · Day ${[...days].join(", ")}`});
      markers.push({marker, days}); allBounds.extend(position);
    });
    let invalidGeometry = false;
    plan.days.forEach((day, index) => {
      const bounds = new maps.LatLngBounds();
        (day.stops || []).filter(visibleStop).forEach((stop) => bounds.extend({lat: stop.lat, lng: stop.lng}));
      if (plan.is_mock ? day.routing_status !== "demo" || !day.demo_geometry
        : !verifiedRoute(day) || !day.encoded_polyline || !(day.stops || []).every(verifiedStop)) return;
      try {
        const path = plan.is_mock
          ? (day.demo_geometry || []).map(([lng, lat]) => new maps.LatLng(lat, lng))
          : maps.geometry.encoding.decodePath(day.encoded_polyline);
        if (path.length < 2 || path.some((point) => !Number.isFinite(point.lat()) || !Number.isFinite(point.lng())
          || Math.abs(point.lat()) > 90 || Math.abs(point.lng()) > 180)) throw new Error("Invalid geometry");
        path.forEach((point) => { bounds.extend(point); allBounds.extend(point); });
        const line = new maps.Polyline({map, path, strokeColor: colors[index % colors.length],
          strokeOpacity: .95, strokeWeight: 4, zIndex: 1});
        line.addListener("click", () => selectDay(day.number));
        overlays.set(day.number, {line, bounds});
      } catch (_) { invalidGeometry = true; }
    });
    $("map-status").hidden = true;
    map.fitBounds(allBounds, 45);
    maps.event.addListenerOnce(map, "idle", () => { if (map.getZoom() > 15) map.setZoom(15); });
    if (selectedDay !== null) selectDay(selectedDay);
    if (plan.is_mock) $("map-caption").textContent = "Mapa Google · linie DEMO są schematem, nie przebiegiem drogi. Czasy i dystanse są przykładowe.";
    if (invalidGeometry) $("map-caption").textContent = "Some route geometry could not be displayed. No replacement routes have been drawn.";
  }
  async function start() {
    $("page-status").hidden = false;
    $("retry-plan").hidden = true;
    $("page-message").textContent = "Loading your itinerary…";
    try {
      const token = window.location.pathname.split("/").filter(Boolean).pop();
      const response = await fetch(`/api/viewer/${encodeURIComponent(token)}`, {cache: "no-store",
        signal: AbortSignal.timeout(10000)});
      if (!response.ok) throw new Error(response.status === 404
        ? "This plan link is invalid or has expired. Ask for a current link."
        : "Your plan could not be loaded. Please try again.");
      const data = await response.json();
      plan = data.plan;
      if (!plan || !Array.isArray(plan.days) || !plan.days.length) throw new Error("This plan has no itinerary available.");
      renderItinerary();
      try { await renderMap(data.maps || {}); }
      catch (error) { mapMessage(error.message || "The interactive map is unavailable. Use the daily Google Maps links."); }
    } catch (error) {
      $("viewer").hidden = true;
      $("page-message").textContent = error.name === "TimeoutError"
        ? "Loading took too long. Please check your connection and try again." : error.message;
      $("retry-plan").hidden = false;
    }
  }
  $("show-all").addEventListener("click", () => selectDay(null));
  $("retry-plan").addEventListener("click", start);
  start();
})();
