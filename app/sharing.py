import hashlib
import os
import secrets
import time
from urllib.parse import urlsplit

from app.planning_providers import PlanningError


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def viewer_link():
    base = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
    url = urlsplit(base)
    if (url.scheme not in ("http", "https") or not url.netloc or url.username
            or url.password or url.query or url.fragment or url.path not in ("", "/")):
        raise PlanningError("PUBLIC_BASE_URL must be an HTTP(S) origin without credentials, path or query.")
    token = secrets.token_urlsafe(32)
    expires = time.time() + 24 * 60 * 60
    return token, f"{base}/trip/{token}", expires


def result_summary(result):
    if result.get("is_mock"):
        days = result['days']
        summary = '; '.join(f"Dzień {d['number']}: przykładowo {d['distance_km']} km / {d['drive_minutes']} min" if d['routing_status'] == 'demo' else f"Dzień {d['number']}: brak trasy" for d in days)
        alerts = ' Uwaga: przekroczony limit jazdy.' if any('daily_drive_limit_exceeded' in d['warnings'] for d in days) else ''
        return f"Tripse DEMO — MOCK, dane przykładowe. {result['title']}. {summary}.{alerts} Plan i ostrzeżenia: {result['viewer_url']}"
    days = result["days"]
    parts = []
    for day in days:
        if day["routing_status"] == "verified":
            parts.append(f"Day {day['number']}: {day['distance_km']:.1f} km, {day['drive_minutes']:.0f} min")
        else:
            parts.append(f"Day {day['number']}: route unverified")
    alerts = []
    if any("daily_drive_limit_exceeded" in day["warnings"] for day in days):
        alerts.append("driving limit exceeded")
    if result["unresolved_places"]:
        alerts.append("unresolved places")
    if any(day["routing_status"] != "verified" for day in days):
        alerts.append("routing incomplete")
    return (f"Tripse draft ({result['verification_status']}): " + "; ".join(parts)
            + (". Warnings: " + ", ".join(alerts) if alerts else "")
            + f". Review the draft and warnings: {result['viewer_url']}")
