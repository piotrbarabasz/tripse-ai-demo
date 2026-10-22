def generate_mock_trip(trip_id: str, request_text: str) -> dict:
    """Fixed sample structure only: no parsing, external calls or verified map data."""
    warning = "MOCK sample only. No places or routes have been verified."
    return {
        "trip_id": trip_id,
        "status": "completed",
        "is_mock": True,
        "generation_mode": "mock",
        "verification_status": "unverified",
        "title": "MOCK trip draft (fixed two-day sample)",
        "request_text": request_text,
        "requirements": {"days": None, "max_daily_drive_min": None},
        "days": [
            {
                "number": number,
                "summary": "Mock placeholder day; itinerary generation is not connected yet.",
                "stops": [],
                "routing_status": "unverified",
                "drive_minutes": None,
                "distance_km": None,
                "encoded_polyline": None,
                "google_maps_url": None,
                "warnings": [warning],
            }
            for number in (1, 2)
        ],
        "warnings": [warning, "The request is stored but has not been interpreted."],
    }
