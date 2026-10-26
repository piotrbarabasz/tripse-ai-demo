"use strict";
(() => {
  const $ = (id) => document.getElementById(id);
  let tripId = null;
  let checking = false;
  let submissionKey = null, submissionText = null;
  const delay = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

  fetch("/health", {cache: "no-store", signal: AbortSignal.timeout(10000)})
    .then((response) => response.json())
    .then((health) => { $("mode").textContent = health.generation_mode === "mock"
      ? "DEMO — przykładowe miejsca, czasy i schemat mapy. Bez AI i Google."
      : "Live demo · A draft with Google place matches and driving estimates; review all warnings."; })
    .catch(() => { $("mode").textContent = "Demo status unavailable. You can still try submitting your request."; });

  fetch('/api/demo/scenarios').then(r => r.ok ? r.json() : null).then(data => {
    if (!data) return;
    $('demo-link').hidden = false;
    data.scenarios.forEach(s => {const b=document.createElement('button'); b.type='button'; b.className='secondary-button'; b.textContent=s.name; b.onclick=()=>{$('request-text').value=s.text;}; $('examples').append(b);});
  }).catch(()=>{});
  async function checkStatus() {
    if (checking || !tripId) return;
    checking = true;
    $("retry-status").hidden = true;
    try {
      for (let attempt = 0; attempt < 180; attempt++) {
        const response = await fetch(`/api/trips/${encodeURIComponent(tripId)}`, {
          cache: "no-store", signal: AbortSignal.timeout(10000),
        });
        if (!response.ok) throw new Error("Status is temporarily unavailable. Your job may still be processing.");
        const job = await response.json();
        $("job-status").textContent = `Status: ${{queued:"W kolejce",running:"Przygotowanie planu",completed:"Plan gotowy",failed:"Błąd"}[job.status]}`;
        if (job.status === "failed") {
          $("job-warning").textContent = job.error || "Nie udało się przygotować planu.";
          $("submit-trip").disabled = false;
          return;
        }
        if (job.status === "completed") {
          const result = job.result;
          const url = new URL(result.viewer_url, location.origin);
          if (!/^\/trip\/[A-Za-z0-9_-]{43}$/.test(url.pathname)) throw new Error("The viewer link is unavailable.");
          // Keep the browser fallback on its current HTTPS origin.
          $("open-trip").href = url.pathname;
          $("open-trip").hidden = false;
          $("job-warning").textContent = result.is_mock
            ? "Plan DEMO gotowy — wszystkie dane są przykładowe."
            : result.verification_status === "verified"
              ? "The draft is ready. Review daily driving limits and all plan notes."
              : "The draft is ready with unverified places or routes. Review its warnings.";
          $("submit-trip").disabled = false;
          return;
        }
        await delay(1000);
      }
      throw new Error("The job is still processing. Check again shortly.");
    } catch (error) {
      $("job-status").textContent = error.name === "TimeoutError" ? "Status check timed out. Your job may still be processing." : error.message;
      $("retry-status").hidden = false;
    } finally { checking = false; }
  }

  $("trip-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = $("request-text").value.trim();
    if (!text) { $("request-text").focus(); return; }
    $("submit-trip").disabled = true;
    $("job-panel").hidden = false;
    $("open-trip").hidden = true;
    $("retry-status").hidden = true;
    $("job-warning").textContent = "";
    $("job-id").textContent = "";
    $("job-status").textContent = "Submitting your request…";
    try {
      if (!submissionKey || submissionText !== text) {
        submissionKey = crypto.randomUUID(); submissionText = text;
      }
      const response = await fetch("/api/trips", {method: "POST", headers: {"Content-Type": "application/json", "Idempotency-Key": submissionKey},
        body: JSON.stringify({text}), signal: AbortSignal.timeout(10000)});
      if (response.status !== 202) throw new Error("The request could not be accepted. Check your description and try again.");
      const job = await response.json();
      submissionKey = null;
      tripId = job.trip_id;
      $("job-id").textContent = `Trip ID: ${tripId}`;
      await checkStatus();
    } catch (_) {
      $("job-status").textContent = "Could not confirm submission. A request may have been accepted; avoid resubmitting until you have checked connectivity.";
      $("submit-trip").disabled = false;
    }
  });
  $("retry-status").addEventListener("click", checkStatus);
})();
