from tests.conftest import MAINTENANCE_MACHINE_ID, client


def test_get_machines():
    response = client.get("/machines")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 1


def test_double_booking_is_rejected():
    # Booking 1 already holds machine 1 for 2026-12-01 to 2026-12-05.
    booking = {
        "machine_id": 1,
        "customer_id": 1,
        "start_date": "2026-12-03",
        "end_date": "2026-12-07",
    }

    response = client.post("/bookings", json=booking)

    assert response.status_code == 409


def test_booking_that_ends_exactly_when_another_starts_is_rejected():
    # Inclusive date ranges: 2026-12-05 is the last day of booking 1.
    booking = {
        "machine_id": 1,
        "customer_id": 1,
        "start_date": "2026-11-28",
        "end_date": "2026-12-01",
    }

    response = client.post("/bookings", json=booking)

    assert response.status_code == 409


def test_valid_booking_is_created():
    booking = {
        "machine_id": 1,
        "customer_id": 1,
        "start_date": "2027-01-01",
        "end_date": "2027-01-05",
    }

    response = client.post("/bookings", json=booking)

    assert response.status_code == 200

    data = response.json()

    assert data["machine_id"] == 1
    assert data["customer_id"] == 1
    assert data["start_date"] == "2027-01-01"
    assert data["end_date"] == "2027-01-05"
    assert data["status"] == "BOOKED"


def test_adjacent_booking_is_allowed():
    # Starts the day after the booking created above ends.
    booking = {
        "machine_id": 1,
        "customer_id": 1,
        "start_date": "2027-01-06",
        "end_date": "2027-01-10",
    }

    response = client.post("/bookings", json=booking)

    assert response.status_code == 200


def test_end_date_before_start_date_is_rejected():
    booking = {
        "machine_id": 1,
        "customer_id": 1,
        "start_date": "2027-03-10",
        "end_date": "2027-03-01",
    }

    response = client.post("/bookings", json=booking)

    assert response.status_code == 400


def test_booking_unknown_machine_is_rejected():
    booking = {
        "machine_id": 9999,
        "customer_id": 1,
        "start_date": "2027-04-01",
        "end_date": "2027-04-02",
    }

    response = client.post("/bookings", json=booking)

    assert response.status_code == 404


def test_booking_unknown_customer_is_rejected():
    booking = {
        "machine_id": 1,
        "customer_id": 9999,
        "start_date": "2027-04-01",
        "end_date": "2027-04-02",
    }

    response = client.post("/bookings", json=booking)

    assert response.status_code == 404


def test_machine_under_maintenance_cannot_be_booked():
    booking = {
        "machine_id": MAINTENANCE_MACHINE_ID,
        "customer_id": 1,
        "start_date": "2027-05-01",
        "end_date": "2027-05-03",
    }

    response = client.post("/bookings", json=booking)

    assert response.status_code == 409