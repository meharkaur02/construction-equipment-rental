import os
import sys
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.models import Booking, Contract, Customer, Machine, MachineUsage
from main import app


# =========================================================
# TEST DATABASE
# =========================================================

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://postgres:Mehar%40123"
    "@localhost:5432/construction_equipment_test",
)

engine = create_engine(TEST_DATABASE_URL)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# =========================================================
# EXPECTED BILLING RESULTS
# =========================================================
#
# DAILY   (booking 2): 2 RUNNING + 1 IDLE + 1 BREAKDOWN
#                      -> 3 chargeable days x 10,000 = 30,000
#
# HOURLY  (booking 3): rate 1,500/h, daily minimum 8 h
#                      6 h -> billed 8, 9 h -> billed 9, IDLE -> billed 8,
#                      BREAKDOWN -> billed 0
#                      -> 25 h x 1,500 = 37,500
#
# MONTHLY (booking 4): 200,000 flat, cap 200 h, overage 1,000/h
#                      230 h run -> 30 h over cap
#                      -> 200,000 + 30,000 = 230,000

EXPECTED_DAILY_AMOUNT = 30000.0
EXPECTED_HOURLY_AMOUNT = 37500.0
EXPECTED_MONTHLY_AMOUNT = 230000.0

DAILY_BOOKING_ID = 2
HOURLY_BOOKING_ID = 3
MONTHLY_BOOKING_ID = 4

MAINTENANCE_MACHINE_ID = 5


# =========================================================
# SEED
# =========================================================

def setup_test_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()

    db.add_all([
        Machine(
            id=1,
            machine_code="TEST-MACHINE-001",
            name="Test Excavator",
            equipment_type="Excavator",
            district="Test District",
            status="AVAILABLE",
            total_running_hours=100,
            service_interval_hours=500,
            last_service_hours=0,
        ),
        Machine(
            id=2,
            machine_code="TEST-DAILY-002",
            name="Daily Billed Crane",
            equipment_type="Crane",
            district="Test District",
            status="AVAILABLE",
            total_running_hours=15,
            service_interval_hours=500,
            last_service_hours=0,
        ),
        Machine(
            id=3,
            machine_code="TEST-HOURLY-003",
            name="Hourly Billed Excavator",
            equipment_type="Excavator",
            district="Test District",
            status="AVAILABLE",
            total_running_hours=15,
            service_interval_hours=500,
            last_service_hours=0,
        ),
        Machine(
            id=4,
            machine_code="TEST-MONTHLY-004",
            name="Monthly Billed Concrete Pump",
            equipment_type="Concrete Pump",
            district="Test District",
            status="AVAILABLE",
            total_running_hours=230,
            service_interval_hours=500,
            last_service_hours=0,
        ),
        Machine(
            id=MAINTENANCE_MACHINE_ID,
            machine_code="TEST-MAINT-005",
            name="Machine Under Maintenance",
            equipment_type="Crane",
            district="Test District",
            status="UNDER_MAINTENANCE",
            total_running_hours=600,
            service_interval_hours=500,
            last_service_hours=0,
        ),
    ])

    db.add(Customer(
        id=1,
        name="Test Customer",
        phone="9999999999",
        email="test@example.com",
    ))

    db.flush()

    # ---- Booking 1: used by the booking / usage / service tests ----
    db.add(Booking(
        id=1,
        machine_id=1,
        customer_id=1,
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 5),
        status="BOOKED",
    ))

    # ---- Booking 2: DAILY ----
    db.add(Booking(
        id=DAILY_BOOKING_ID,
        machine_id=2,
        customer_id=1,
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 4),
        status="BOOKED",
    ))

    # ---- Booking 3: HOURLY with daily minimum ----
    db.add(Booking(
        id=HOURLY_BOOKING_ID,
        machine_id=3,
        customer_id=1,
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 4),
        status="BOOKED",
    ))

    # ---- Booking 4: MONTHLY with hour cap and overage ----
    db.add(Booking(
        id=MONTHLY_BOOKING_ID,
        machine_id=4,
        customer_id=1,
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 31),
        status="BOOKED",
    ))

    db.flush()

    db.add_all([
        Contract(
            booking_id=DAILY_BOOKING_ID,
            billing_type="DAILY",
            daily_rate=10000,
        ),
        Contract(
            booking_id=HOURLY_BOOKING_ID,
            billing_type="HOURLY",
            hourly_rate=1500,
            daily_minimum_hours=8,
        ),
        Contract(
            booking_id=MONTHLY_BOOKING_ID,
            billing_type="MONTHLY",
            monthly_rate=200000,
            monthly_hour_cap=200,
            overage_rate=1000,
        ),
    ])

    usage_rows = [
        # DAILY booking
        (2, DAILY_BOOKING_ID, date(2026, 10, 1), "RUNNING", 7),
        (2, DAILY_BOOKING_ID, date(2026, 10, 2), "RUNNING", 8),
        (2, DAILY_BOOKING_ID, date(2026, 10, 3), "IDLE", 0),
        (2, DAILY_BOOKING_ID, date(2026, 10, 4), "BREAKDOWN", 0),

        # HOURLY booking
        (3, HOURLY_BOOKING_ID, date(2026, 11, 1), "RUNNING", 6),
        (3, HOURLY_BOOKING_ID, date(2026, 11, 2), "RUNNING", 9),
        (3, HOURLY_BOOKING_ID, date(2026, 11, 3), "IDLE", 0),
        (3, HOURLY_BOOKING_ID, date(2026, 11, 4), "BREAKDOWN", 0),

        # MONTHLY booking
        (4, MONTHLY_BOOKING_ID, date(2026, 12, 1), "RUNNING", 115),
        (4, MONTHLY_BOOKING_ID, date(2026, 12, 2), "RUNNING", 115),
    ]

    for machine_id, booking_id, usage_date, status, hours in usage_rows:
        db.add(MachineUsage(
            machine_id=machine_id,
            booking_id=booking_id,
            usage_date=usage_date,
            status=status,
            running_hours=hours,
        ))

    db.flush()

    # The rows above were seeded with explicit IDs, so Postgres's
    # auto-increment sequences don't yet know about them. Without this,
    # the next API-created row collides with a seeded row's ID and the
    # insert fails with an IntegrityError that gets mistaken for a
    # double-booking rejection.
    for table, column in (
        ("machines", "id"),
        ("customers", "id"),
        ("bookings", "id"),
        ("contracts", "id"),
        ("machine_usage", "id"),
    ):
        db.execute(text(
            f"SELECT setval("
            f"pg_get_serial_sequence('{table}', '{column}'), "
            f"COALESCE((SELECT MAX({column}) FROM {table}), 1), "
            f"(SELECT MAX({column}) FROM {table}) IS NOT NULL)"
        ))

    db.commit()
    db.close()


# =========================================================
# FASTAPI OVERRIDE
# =========================================================

def override_get_db():
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def initialize_test_database():
    setup_test_database()
    yield
    app.dependency_overrides.clear()