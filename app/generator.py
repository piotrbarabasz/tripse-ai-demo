from app.demo_data import generate_demo


def generate_mock_trip(trip_id: str, request_text: str) -> dict:
    return generate_demo(trip_id, request_text)
