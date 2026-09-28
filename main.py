from typing import List

from fastapi import Depends, FastAPI, Query
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db


app = FastAPI(
    title="Construction Equipment Rental API",
    description=(
        "Manages the machine catalogue, prevents double-booking, "
        "tracks running hours and service due dates, and computes invoices."
    ),
    version="1.0.0",
)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}


# =========================================================
# MACHINES
# =========================================================

@app.get(
    "/machines",
    response_model=List[schemas.MachineResponse],
    tags=["Machines"],
)
def list_machines(db: Session = Depends(get_db)):
    return crud.get_machines(db)


@app.get(
    "/machines/maintenance-alerts",
    response_model=List[schemas.MaintenanceAlertResponse],
    tags=["Maintenance"],
)
def maintenance_alerts(
    only_due: bool = Query(
        default=False,
        description="Return only machines that are DUE_SOON or OVERDUE",
    ),
    db: Session = Depends(get_db),
):
    return crud.get_maintenance_alerts(db, only_due=only_due)


@app.get(
    "/machines/{machine_id}",
    response_model=schemas.MachineResponse,
    tags=["Machines"],
)
def get_machine(machine_id: int, db: Session = Depends(get_db)):
    return crud.get_machine(db, machine_id)


@app.get(
    "/machines/{machine_id}/service-status",
    response_model=schemas.ServiceStatusResponse,
    tags=["Maintenance"],
)
def service_status(machine_id: int, db: Session = Depends(get_db)):
    return crud.check_service_status(db, machine_id)


# =========================================================
# CUSTOMERS
# =========================================================

@app.get(
    "/customers",
    response_model=List[schemas.CustomerResponse],
    tags=["Customers"],
)
def list_customers(db: Session = Depends(get_db)):
    return crud.get_customers(db)


@app.post(
    "/customers",
    response_model=schemas.CustomerResponse,
    tags=["Customers"],
)
def create_customer(
    customer: schemas.CustomerCreate,
    db: Session = Depends(get_db),
):
    return crud.create_customer(db, customer)


# =========================================================
# BOOKINGS
# =========================================================

@app.get(
    "/bookings",
    response_model=List[schemas.BookingResponse],
    tags=["Bookings"],
)
def list_bookings(db: Session = Depends(get_db)):
    return crud.get_bookings(db)


@app.post(
    "/bookings",
    response_model=schemas.BookingResponse,
    tags=["Bookings"],
    responses={409: {"description": "Machine already booked for those dates"}},
)
def create_booking(
    booking: schemas.BookingCreate,
    db: Session = Depends(get_db),
):
    return crud.create_booking(db, booking)


# =========================================================
# USAGE
# =========================================================

@app.post(
    "/usage",
    response_model=schemas.UsageResponse,
    tags=["Usage"],
)
def create_usage(
    usage: schemas.UsageCreate,
    db: Session = Depends(get_db),
):
    return crud.create_usage_log(db, usage)


# =========================================================
# CONTRACTS
# =========================================================

@app.post(
    "/contracts",
    response_model=schemas.ContractResponse,
    tags=["Contracts"],
)
def create_contract(
    contract: schemas.ContractCreate,
    db: Session = Depends(get_db),
):
    return crud.create_contract(db, contract)


# =========================================================
# SERVICES
# =========================================================

@app.post(
    "/services",
    response_model=schemas.ServiceResponse,
    tags=["Maintenance"],
)
def create_service(
    service: schemas.ServiceCreate,
    db: Session = Depends(get_db),
):
    return crud.create_service(db, service)


# =========================================================
# BILLING
# =========================================================

@app.get(
    "/billing/invoices",
    response_model=List[schemas.BillingResponse],
    tags=["Billing"],
)
def billing_preview(db: Session = Depends(get_db)):
    """Computed (not yet persisted) invoice amounts for every booking."""
    return crud.calculate_invoices(db)


@app.get(
    "/billing/invoices/{booking_id}",
    response_model=schemas.BillingResponse,
    tags=["Billing"],
)
def billing_preview_for_booking(
    booking_id: int,
    db: Session = Depends(get_db),
):
    return crud.calculate_invoice_for_booking(db, booking_id)


@app.post(
    "/invoices/{booking_id}",
    response_model=schemas.InvoiceResponse,
    tags=["Billing"],
)
def generate_invoice(booking_id: int, db: Session = Depends(get_db)):
    """Compute and persist the invoice for a booking."""
    return crud.generate_invoice(db, booking_id)


@app.get(
    "/invoices",
    response_model=List[schemas.InvoiceResponse],
    tags=["Billing"],
)
def list_invoices(db: Session = Depends(get_db)):
    return crud.get_invoices(db)


# =========================================================
# UTILISATION
# =========================================================

@app.get(
    "/utilisation",
    response_model=List[schemas.UtilisationResponse],
    tags=["Utilisation"],
)
def utilisation(db: Session = Depends(get_db)):
    return crud.get_utilisation(db)