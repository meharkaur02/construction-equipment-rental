from tests.conftest import DAILY_BOOKING_ID, client


def test_daily_contract_without_a_rate_is_rejected():
    contract = {
        "booking_id": 1,
        "billing_type": "DAILY",
    }

    response = client.post("/contracts", json=contract)

    assert response.status_code == 422


def test_hourly_contract_without_a_daily_minimum_is_rejected():
    contract = {
        "booking_id": 1,
        "billing_type": "HOURLY",
        "hourly_rate": 1500,
    }

    response = client.post("/contracts", json=contract)

    assert response.status_code == 422


def test_monthly_contract_without_an_overage_rate_is_rejected():
    contract = {
        "booking_id": 1,
        "billing_type": "MONTHLY",
        "monthly_rate": 200000,
        "monthly_hour_cap": 200,
    }

    response = client.post("/contracts", json=contract)

    assert response.status_code == 422


def test_unknown_billing_type_is_rejected():
    contract = {
        "booking_id": 1,
        "billing_type": "WEEKLY",
        "daily_rate": 1000,
    }

    response = client.post("/contracts", json=contract)

    assert response.status_code == 422


def test_negative_rate_is_rejected():
    contract = {
        "booking_id": 1,
        "billing_type": "DAILY",
        "daily_rate": -500,
    }

    response = client.post("/contracts", json=contract)

    assert response.status_code == 422


def test_contract_for_unknown_booking_is_rejected():
    contract = {
        "booking_id": 9999,
        "billing_type": "DAILY",
        "daily_rate": 10000,
    }

    response = client.post("/contracts", json=contract)

    assert response.status_code == 404


def test_valid_contract_is_created():
    # Own booking, so this test cannot disturb the billing fixtures.
    booking = client.post("/bookings", json={
        "machine_id": 2,
        "customer_id": 1,
        "start_date": "2028-01-01",
        "end_date": "2028-01-05",
    })

    assert booking.status_code == 200

    booking_id = booking.json()["id"]

    contract = {
        "booking_id": booking_id,
        "billing_type": "DAILY",
        "daily_rate": 12500,
    }

    response = client.post("/contracts", json=contract)

    assert response.status_code == 200

    data = response.json()

    assert data["booking_id"] == booking_id
    assert data["billing_type"] == "DAILY"
    assert data["daily_rate"] == 12500


def test_second_contract_on_the_same_booking_is_rejected():
    contract = {
        "booking_id": DAILY_BOOKING_ID,
        "billing_type": "DAILY",
        "daily_rate": 10000,
    }

    response = client.post("/contracts", json=contract)

    assert response.status_code == 409