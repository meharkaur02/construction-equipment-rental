from tests.conftest import client


def test_usage_date_must_be_inside_booking():
    usage = {
        "machine_id": 1,
        "booking_id": 1,
        "usage_date": "2026-12-10",
        "status": "RUNNING",
        "running_hours": 5,
    }

    response = client.post("/usage", json=usage)

    assert response.status_code == 400


def test_usage_machine_must_exist():
    usage = {
        "machine_id": 999,
        "booking_id": 1,
        "usage_date": "2026-12-02",
        "status": "RUNNING",
        "running_hours": 5,
    }

    response = client.post("/usage", json=usage)

    assert response.status_code == 404


def test_negative_running_hours_are_rejected():
    usage = {
        "machine_id": 1,
        "booking_id": 1,
        "usage_date": "2026-12-02",
        "status": "RUNNING",
        "running_hours": -5,
    }

    response = client.post("/usage", json=usage)

    assert response.status_code == 422


def test_idle_day_cannot_have_running_hours():
    usage = {
        "machine_id": 1,
        "booking_id": 1,
        "usage_date": "2026-12-02",
        "status": "IDLE",
        "running_hours": 4,
    }

    response = client.post("/usage", json=usage)

    assert response.status_code == 422


def test_valid_usage_is_created_and_updates_running_hours():
    before = client.get("/machines/1").json()["total_running_hours"]

    usage = {
        "machine_id": 1,
        "booking_id": 1,
        "usage_date": "2026-12-02",
        "status": "RUNNING",
        "running_hours": 5,
    }

    response = client.post("/usage", json=usage)

    assert response.status_code == 200

    data = response.json()

    assert data["machine_id"] == 1
    assert data["booking_id"] == 1
    assert data["usage_date"] == "2026-12-02"
    assert data["status"] == "RUNNING"
    assert data["running_hours"] == 5

    after = client.get("/machines/1").json()["total_running_hours"]

    # Counted exactly once, not twice.
    assert after == before + 5


def test_duplicate_usage_is_rejected():
    usage = {
        "machine_id": 1,
        "booking_id": 1,
        "usage_date": "2026-12-03",
        "status": "RUNNING",
        "running_hours": 6,
    }

    first_response = client.post("/usage", json=usage)
    assert first_response.status_code == 200

    second_response = client.post("/usage", json=usage)
    assert second_response.status_code == 409


def test_breakdown_puts_machine_under_maintenance():
    usage = {
        "machine_id": 1,
        "booking_id": 1,
        "usage_date": "2026-12-04",
        "status": "BREAKDOWN",
        "running_hours": 0,
    }

    response = client.post("/usage", json=usage)

    assert response.status_code == 200
    assert client.get("/machines/1").json()["status"] == "UNDER_MAINTENANCE"