import logging

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, schemas


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


DUE_SOON_THRESHOLD_HOURS = 50.0


# =========================================================
# HELPERS
# =========================================================

def _f(value) -> float:
    """Numeric/Decimal -> float, with None treated as 0."""
    return float(value or 0)


def _service_status_label(hours_remaining: float) -> str:
    if hours_remaining <= 0:
        return "OVERDUE"
    if hours_remaining <= DUE_SOON_THRESHOLD_HOURS:
        return "DUE_SOON"
    return "OK"


def _get_machine_or_404(db: Session, machine_id: int) -> models.Machine:
    machine = (
        db.query(models.Machine)
        .filter(models.Machine.id == machine_id)
        .first()
    )

    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    return machine


def _get_booking_or_404(db: Session, booking_id: int) -> models.Booking:
    booking = (
        db.query(models.Booking)
        .filter(models.Booking.id == booking_id)
        .first()
    )

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    return booking


# =========================================================
# MACHINES
# =========================================================

def get_machines(db: Session):
    return db.query(models.Machine).order_by(models.Machine.id).all()


def get_machine(db: Session, machine_id: int):
    return _get_machine_or_404(db, machine_id)


# =========================================================
# CUSTOMERS
# =========================================================

def get_customers(db: Session):
    return db.query(models.Customer).order_by(models.Customer.id).all()


def create_customer(db: Session, customer: schemas.CustomerCreate):
    new_customer = models.Customer(
        name=customer.name,
        phone=customer.phone,
        email=customer.email
    )

    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)

    return new_customer


# =========================================================
# SERVICE STATUS / MAINTENANCE
# =========================================================

def check_service_status(db: Session, machine_id: int):
    machine = _get_machine_or_404(db, machine_id)

    total_hours = _f(machine.total_running_hours)
    last_service_hours = _f(machine.last_service_hours)
    service_interval = _f(machine.service_interval_hours)

    hours_since_service = total_hours - last_service_hours
    hours_until_service = service_interval - hours_since_service

    return {
        "machine_id": machine.id,
        "machine_code": machine.machine_code,
        "status": machine.status,
        "total_running_hours": total_hours,
        "last_service_hours": last_service_hours,
        "hours_since_last_service": hours_since_service,
        "service_interval_hours": service_interval,
        "hours_until_service": hours_until_service,
        "is_service_due": hours_since_service >= service_interval,
        "service_status": _service_status_label(hours_until_service),
    }


def get_maintenance_alerts(db: Session, only_due: bool = False):
    machines = db.query(models.Machine).order_by(models.Machine.id).all()

    alerts = []

    for machine in machines:
        total_hours = _f(machine.total_running_hours)
        last_service_hours = _f(machine.last_service_hours)
        interval = _f(machine.service_interval_hours)

        next_service_at = last_service_hours + interval
        hours_remaining = next_service_at - total_hours
        label = _service_status_label(hours_remaining)

        if only_due and label == "OK":
            continue

        alerts.append({
            "machine_id": machine.id,
            "machine_code": machine.machine_code,
            "name": machine.name,
            "district": machine.district,
            "total_running_hours": total_hours,
            "next_service_at": next_service_at,
            "hours_remaining": hours_remaining,
            "service_status": label,
        })

    # Most urgent first
    alerts.sort(key=lambda a: a["hours_remaining"])

    return alerts


# =========================================================
# BOOKINGS
# =========================================================

def get_bookings(db: Session):
    return db.query(models.Booking).order_by(models.Booking.id).all()


def create_booking(db: Session, booking: schemas.BookingCreate):
    if booking.start_date > booking.end_date:
        raise HTTPException(
            status_code=400,
            detail="Start date cannot be after end date"
        )

    machine = _get_machine_or_404(db, booking.machine_id)

    customer = (
        db.query(models.Customer)
        .filter(models.Customer.id == booking.customer_id)
        .first()
    )

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    if machine.status == "UNDER_MAINTENANCE":
        raise HTTPException(
            status_code=409,
            detail="Machine is under maintenance and cannot be booked"
        )

    if machine.status == "RETIRED":
        raise HTTPException(
            status_code=409,
            detail="Machine is retired and cannot be booked"
        )

    # Layer 1: friendly application-level overlap check.
    # Two ranges overlap when each starts on or before the other one ends.
    overlapping_booking = (
        db.query(models.Booking)
        .filter(
            models.Booking.machine_id == booking.machine_id,
            models.Booking.status == "BOOKED",
            models.Booking.start_date <= booking.end_date,
            models.Booking.end_date >= booking.start_date,
        )
        .first()
    )

    if overlapping_booking:
        logger.warning(
            "Double booking prevented (app layer) for machine %s",
            booking.machine_id
        )
        raise HTTPException(
            status_code=409,
            detail=(
                "Machine is already booked for the selected dates "
                f"(conflicting booking id {overlapping_booking.id})"
            )
        )

    new_booking = models.Booking(
        machine_id=booking.machine_id,
        customer_id=booking.customer_id,
        start_date=booking.start_date,
        end_date=booking.end_date,
        status="BOOKED"
    )

    db.add(new_booking)

    # Layer 2: the Postgres EXCLUDE constraint is the real guarantee.
    # It catches the race where two requests pass the check above
    # at the same instant.
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.warning(
            "Double booking prevented (database layer) for machine %s",
            booking.machine_id
        )
        raise HTTPException(
            status_code=409,
            detail="Machine is already booked for the selected dates"
        )

    db.refresh(new_booking)

    logger.info("Booking created: %s", new_booking.id)

    return new_booking


# =========================================================
# USAGE
# =========================================================

def create_usage_log(db: Session, usage: schemas.UsageCreate):
    machine = _get_machine_or_404(db, usage.machine_id)
    booking = _get_booking_or_404(db, usage.booking_id)

    if booking.machine_id != usage.machine_id:
        raise HTTPException(
            status_code=400,
            detail="Usage machine does not match booking machine"
        )

    if booking.status == "CANCELLED":
        raise HTTPException(
            status_code=400,
            detail="Cannot log usage against a cancelled booking"
        )

    if (
        usage.usage_date < booking.start_date
        or usage.usage_date > booking.end_date
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Usage date must be within the booking date range "
                f"({booking.start_date} to {booking.end_date})"
            )
        )

    existing_usage = (
        db.query(models.MachineUsage)
        .filter(
            models.MachineUsage.machine_id == usage.machine_id,
            models.MachineUsage.usage_date == usage.usage_date,
        )
        .first()
    )

    if existing_usage:
        raise HTTPException(
            status_code=409,
            detail="Usage already recorded for this machine on this date"
        )

    usage_record = models.MachineUsage(
        machine_id=usage.machine_id,
        booking_id=usage.booking_id,
        usage_date=usage.usage_date,
        status=usage.status,
        running_hours=usage.running_hours
    )

    db.add(usage_record)

    # The application owns the running-hours counter.
    # The old database trigger did this too, which double-counted.
    machine.total_running_hours = (
        _f(machine.total_running_hours) + usage.running_hours
    )

    if usage.status == "BREAKDOWN":
        machine.status = "UNDER_MAINTENANCE"

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Usage already recorded for this machine on this date"
        )

    db.refresh(usage_record)

    logger.info(
        "Usage recorded: machine %s on %s (%s, %s h)",
        usage.machine_id, usage.usage_date, usage.status, usage.running_hours
    )

    return usage_record


# =========================================================
# CONTRACTS
# =========================================================

def create_contract(db: Session, contract: schemas.ContractCreate):
    _get_booking_or_404(db, contract.booking_id)

    existing_contract = (
        db.query(models.Contract)
        .filter(models.Contract.booking_id == contract.booking_id)
        .first()
    )

    if existing_contract:
        raise HTTPException(
            status_code=409,
            detail="Contract already exists for this booking"
        )

    new_contract = models.Contract(
        booking_id=contract.booking_id,
        billing_type=contract.billing_type,

        daily_rate=contract.daily_rate,

        hourly_rate=contract.hourly_rate,
        daily_minimum_hours=contract.daily_minimum_hours,

        monthly_rate=contract.monthly_rate,
        monthly_hour_cap=contract.monthly_hour_cap,
        overage_rate=contract.overage_rate
    )

    db.add(new_contract)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Contract already exists for this booking"
        )

    db.refresh(new_contract)

    return new_contract


# =========================================================
# SERVICES
# =========================================================

def create_service(db: Session, service: schemas.ServiceCreate):
    machine = _get_machine_or_404(db, service.machine_id)

    current_hours = _f(machine.total_running_hours)

    # Default: the service happened at the machine's current odometer reading.
    service_hours = (
        current_hours
        if service.service_hours is None
        else service.service_hours
    )

    if service_hours > current_hours:
        raise HTTPException(
            status_code=400,
            detail=(
                "Service hours cannot exceed the machine's current "
                f"running hours ({current_hours})"
            )
        )

    new_service = models.Service(
        machine_id=service.machine_id,
        service_hours=service_hours,
        serviced_at=service.serviced_at,
        description=service.description
    )

    db.add(new_service)

    # Reset the maintenance counter and bring the machine back into service.
    machine.last_service_hours = service_hours

    if machine.status == "UNDER_MAINTENANCE":
        machine.status = "AVAILABLE"

    db.commit()
    db.refresh(new_service)

    logger.info(
        "Service recorded for machine %s at %s hours",
        service.machine_id, service_hours
    )

    return new_service


# =========================================================
# BILLING
# =========================================================

# Billing rules from the problem statement:
#   DAILY    -> chargeable days = RUNNING + IDLE (breakdown days are free)
#   HOURLY   -> per chargeable day, bill GREATEST(running_hours, daily_minimum)
#   MONTHLY  -> flat monthly rate + (hours above the cap) * overage rate
_BILLING_SQL = """
    SELECT
        b.id                AS booking_id,
        b.machine_id        AS machine_id,
        c.billing_type      AS billing_type,

        COUNT(*) FILTER (WHERE mu.status = 'RUNNING')   AS running_days,
        COUNT(*) FILTER (WHERE mu.status = 'IDLE')      AS idle_days,
        COUNT(*) FILTER (WHERE mu.status = 'BREAKDOWN') AS breakdown_days,

        COUNT(*) FILTER (
            WHERE mu.status IN ('RUNNING', 'IDLE')
        ) AS chargeable_days,

        COALESCE(SUM(mu.running_hours), 0) AS total_running_hours,

        COALESCE(
            CASE
                WHEN c.billing_type = 'DAILY' THEN
                    COUNT(*) FILTER (
                        WHERE mu.status IN ('RUNNING', 'IDLE')
                    ) * c.daily_rate

                WHEN c.billing_type = 'HOURLY' THEN
                    COALESCE(
                        SUM(
                            CASE
                                WHEN mu.status IN ('RUNNING', 'IDLE')
                                THEN GREATEST(
                                    mu.running_hours,
                                    c.daily_minimum_hours
                                ) * c.hourly_rate
                                ELSE 0
                            END
                        ),
                        0
                    )

                WHEN c.billing_type = 'MONTHLY' THEN
                    c.monthly_rate
                    + GREATEST(
                        COALESCE(SUM(mu.running_hours), 0)
                            - c.monthly_hour_cap,
                        0
                    ) * c.overage_rate

                ELSE 0
            END,
            0
        ) AS total_invoice_amount

    FROM bookings b

    JOIN contracts c
        ON c.booking_id = b.id

    LEFT JOIN machine_usage mu
        ON mu.booking_id = b.id

    {where_clause}

    GROUP BY
        b.id,
        b.machine_id,
        c.billing_type,
        c.daily_rate,
        c.hourly_rate,
        c.daily_minimum_hours,
        c.monthly_rate,
        c.monthly_hour_cap,
        c.overage_rate

    ORDER BY b.id
"""


def _billing_rows(db: Session, booking_id: int | None = None):
    where_clause = "WHERE b.id = :booking_id" if booking_id else ""

    query = text(_BILLING_SQL.format(where_clause=where_clause))

    params = {"booking_id": booking_id} if booking_id else {}

    result = db.execute(query, params)

    rows = []

    for row in result:
        rows.append({
            "booking_id": row.booking_id,
            "machine_id": row.machine_id,
            "billing_type": row.billing_type,
            "running_days": int(row.running_days or 0),
            "idle_days": int(row.idle_days or 0),
            "breakdown_days": int(row.breakdown_days or 0),
            "chargeable_days": int(row.chargeable_days or 0),
            "total_running_hours": _f(row.total_running_hours),
            "total_invoice_amount": _f(row.total_invoice_amount),
        })

    return rows


def calculate_invoices(db: Session):
    return _billing_rows(db)


def calculate_invoice_for_booking(db: Session, booking_id: int):
    _get_booking_or_404(db, booking_id)

    rows = _billing_rows(db, booking_id=booking_id)

    if not rows:
        raise HTTPException(
            status_code=400,
            detail="Booking has no contract, so it cannot be invoiced"
        )

    return rows[0]


def generate_invoice(db: Session, booking_id: int):
    """Compute the invoice for a booking and persist it."""
    summary = calculate_invoice_for_booking(db, booking_id)

    existing = (
        db.query(models.Invoice)
        .filter(models.Invoice.booking_id == booking_id)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Invoice already generated for booking {booking_id}"
        )

    invoice = models.Invoice(
        booking_id=booking_id,
        amount=summary["total_invoice_amount"],
        running_hours=summary["total_running_hours"],
        idle_days=summary["idle_days"],
        breakdown_days=summary["breakdown_days"],
    )

    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    logger.info(
        "Invoice %s generated for booking %s: %s",
        invoice.id, booking_id, summary["total_invoice_amount"]
    )

    return invoice


def get_invoices(db: Session):
    return db.query(models.Invoice).order_by(models.Invoice.id).all()


# =========================================================
# UTILISATION
# =========================================================

def get_utilisation(db: Session):
    machines = db.query(models.Machine).order_by(models.Machine.id).all()

    result = []

    for machine in machines:
        usage_logs = (
            db.query(models.MachineUsage)
            .filter(models.MachineUsage.machine_id == machine.id)
            .all()
        )

        running_days = sum(1 for u in usage_logs if u.status == "RUNNING")
        idle_days = sum(1 for u in usage_logs if u.status == "IDLE")
        breakdown_days = sum(1 for u in usage_logs if u.status == "BREAKDOWN")

        tracked_days = len(usage_logs)

        total_running_hours = sum(_f(u.running_hours) for u in usage_logs)

        utilisation_rate = (
            round(running_days / tracked_days * 100, 2)
            if tracked_days
            else 0.0
        )

        result.append({
            "machine_id": machine.id,
            "machine_code": machine.machine_code,
            "machine_name": machine.name,
            "district": machine.district,
            "equipment_type": machine.equipment_type,
            "running_days": running_days,
            "idle_days": idle_days,
            "breakdown_days": breakdown_days,
            "tracked_days": tracked_days,
            "total_running_hours": total_running_hours,
            "utilisation_rate": utilisation_rate,
        })

    return result