from tests.conftest import MAINTENANCE_MACHINE_ID, client


def test_service_status_is_returned():
    response = client.get("/machines/1/service-status")

    assert response.status_code == 200

    data = response.json()

    assert data["machine_id"] == 1

    for field in (
        "total_running_hours",
        "last_service_hours",
        "hours_since_last_service",
        "service_interval_hours",
        "hours_until_service",
        "is_service_due",
        "service_status",
    ):
        assert field in data


def test_service_is_not_due_before_the_interval():
    data = client.get("/machines/1/service-status").json()

    assert data["hours_since_last_service"] < data["service_interval_hours"]
    assert data["is_service_due"] is False


def test_service_is_overdue_past_the_interval():
    # Machine 5 has run 600 h on a 500 h interval.
    data = client.get(
        f"/machines/{MAINTENANCE_MACHINE_ID}/service-status"
    ).json()

    assert data["is_service_due"] is True
    assert data["service_status"] == "OVERDUE"


def test_service_is_recorded():
    service = {
        "machine_id": 1,
        "service_hours": 100,
        "serviced_at": "2026-12-01",
        "description": "Regular maintenance",
    }

    response = client.post("/services", json=service)

    assert response.status_code == 200

    data = response.json()

    assert data["machine_id"] == 1
    assert data["service_hours"] == 100
    assert data["serviced_at"] == "2026-12-01"
    assert data["description"] == "Regular maintenance"


def test_service_hours_cannot_exceed_running_hours():
    service = {
        "machine_id": 1,
        "service_hours": 999999,
        "serviced_at": "2026-12-01",
        "description": "Impossible service",
    }

    response = client.post("/services", json=service)

    assert response.status_code == 400


def test_service_resets_the_counter_and_clears_maintenance():
    before = client.get(
        f"/machines/{MAINTENANCE_MACHINE_ID}/service-status"
    ).json()

    total = before["total_running_hours"]

    service = {
        "machine_id": MAINTENANCE_MACHINE_ID,
        "serviced_at": "2026-12-01",
        "description": "Scheduled engine and hydraulic service",
    }

    response = client.post("/services", json=service)
    assert response.status_code == 200

    # service_hours defaults to the machine's current odometer reading.
    assert response.json()["service_hours"] == total

    after = client.get(
        f"/machines/{MAINTENANCE_MACHINE_ID}/service-status"
    ).json()

    assert after["last_service_hours"] == total
    assert after["hours_since_last_service"] == 0.0
    assert after["is_service_due"] is False
    assert after["service_status"] == "OK"

    # The machine is back in the fleet.
    assert after["status"] == "AVAILABLE"


def test_maintenance_alerts_endpoint():
    response = client.get("/machines/maintenance-alerts")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 1

    alert = data[0]

    for field in (
        "machine_id",
        "machine_code",
        "next_service_at",
        "hours_remaining",
        "service_status",
    ):
        assert field in alert

    # Most urgent machine first.
    assert data[0]["hours_remaining"] <= data[-1]["hours_remaining"]


def test_maintenance_alerts_can_filter_to_due_machines_only():
    response = client.get(
        "/machines/maintenance-alerts",
        params={"only_due": "true"},
    )

    assert response.status_code == 200

    for alert in response.json():
        assert alert["service_status"] in ("DUE_SOON", "OVERDUE")