from tests.conftest import (
    DAILY_BOOKING_ID,
    EXPECTED_DAILY_AMOUNT,
    EXPECTED_HOURLY_AMOUNT,
    EXPECTED_MONTHLY_AMOUNT,
    HOURLY_BOOKING_ID,
    MONTHLY_BOOKING_ID,
    client,
)


def _invoice_for(booking_id: int) -> dict:
    response = client.get("/billing/invoices")
    assert response.status_code == 200

    data = response.json()

    return next(
        item for item in data
        if item["booking_id"] == booking_id
    )


def test_billing_endpoint_returns_all_contracted_bookings():
    response = client.get("/billing/invoices")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 3

    booking_ids = {item["booking_id"] for item in data}

    assert {
        DAILY_BOOKING_ID,
        HOURLY_BOOKING_ID,
        MONTHLY_BOOKING_ID,
    }.issubset(booking_ids)


def test_billing_contains_required_fields():
    invoice = _invoice_for(DAILY_BOOKING_ID)

    for field in (
        "booking_id",
        "machine_id",
        "billing_type",
        "running_days",
        "idle_days",
        "breakdown_days",
        "chargeable_days",
        "total_running_hours",
        "total_invoice_amount",
    ):
        assert field in invoice


def test_daily_billing_charges_idle_days_but_not_breakdown_days():
    invoice = _invoice_for(DAILY_BOOKING_ID)

    assert invoice["billing_type"] == "DAILY"
    assert invoice["running_days"] == 2
    assert invoice["idle_days"] == 1
    assert invoice["breakdown_days"] == 1

    # Running + idle are chargeable, the breakdown day is free.
    assert invoice["chargeable_days"] == 3
    assert invoice["total_invoice_amount"] == EXPECTED_DAILY_AMOUNT


def test_hourly_billing_applies_the_daily_minimum():
    invoice = _invoice_for(HOURLY_BOOKING_ID)

    assert invoice["billing_type"] == "HOURLY"

    # 6 h billed as 8 (minimum), 9 h billed as 9,
    # idle day billed as 8, breakdown day billed as 0.
    assert invoice["total_running_hours"] == 15.0
    assert invoice["total_invoice_amount"] == EXPECTED_HOURLY_AMOUNT


def test_hourly_billing_excludes_breakdown_days():
    invoice = _invoice_for(HOURLY_BOOKING_ID)

    assert invoice["breakdown_days"] == 1

    # Without the exclusion the breakdown day would add
    # the 8 h minimum, i.e. another 12,000.
    assert invoice["total_invoice_amount"] < EXPECTED_HOURLY_AMOUNT + 12000


def test_monthly_billing_adds_overage_above_the_hour_cap():
    invoice = _invoice_for(MONTHLY_BOOKING_ID)

    assert invoice["billing_type"] == "MONTHLY"
    assert invoice["total_running_hours"] == 230.0

    # 200,000 flat + 30 h over the 200 h cap at 1,000/h.
    assert invoice["total_invoice_amount"] == EXPECTED_MONTHLY_AMOUNT


def test_single_booking_billing_matches_the_list_endpoint():
    response = client.get(f"/billing/invoices/{HOURLY_BOOKING_ID}")

    assert response.status_code == 200
    assert response.json()["total_invoice_amount"] == EXPECTED_HOURLY_AMOUNT


def test_invoice_can_be_generated_and_persisted():
    response = client.post(f"/invoices/{DAILY_BOOKING_ID}")

    assert response.status_code == 200

    invoice = response.json()

    assert invoice["booking_id"] == DAILY_BOOKING_ID
    assert invoice["amount"] == EXPECTED_DAILY_AMOUNT
    assert invoice["breakdown_days"] == 1
    assert "created_at" in invoice


def test_duplicate_invoice_is_rejected():
    first = client.post(f"/invoices/{MONTHLY_BOOKING_ID}")
    assert first.status_code == 200

    second = client.post(f"/invoices/{MONTHLY_BOOKING_ID}")
    assert second.status_code == 409


def test_booking_without_contract_cannot_be_invoiced():
    # Booking 1 has no contract.
    response = client.post("/invoices/1")

    assert response.status_code == 400