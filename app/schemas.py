from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


# -------------------------
# Machine
# -------------------------

class MachineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    machine_code: str
    name: str
    equipment_type: str
    district: str
    status: str
    total_running_hours: float
    service_interval_hours: float
    last_service_hours: float


class ServiceStatusResponse(BaseModel):
    machine_id: int
    machine_code: str
    status: str
    total_running_hours: float
    last_service_hours: float
    hours_since_last_service: float
    service_interval_hours: float
    hours_until_service: float
    is_service_due: bool
    service_status: Literal["OK", "DUE_SOON", "OVERDUE"]


class MaintenanceAlertResponse(BaseModel):
    machine_id: int
    machine_code: str
    name: str
    district: str
    total_running_hours: float
    next_service_at: float
    hours_remaining: float
    service_status: Literal["OK", "DUE_SOON", "OVERDUE"]


# -------------------------
# Customer
# -------------------------

class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=100)


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str | None = None
    email: str | None = None


# -------------------------
# Booking
# -------------------------

class BookingCreate(BaseModel):
    machine_id: int
    customer_id: int
    start_date: date
    end_date: date


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    machine_id: int
    customer_id: int
    start_date: date
    end_date: date
    status: str


# -------------------------
# Usage
# -------------------------

class UsageCreate(BaseModel):
    machine_id: int
    booking_id: int
    usage_date: date
    status: Literal["RUNNING", "IDLE", "BREAKDOWN"]
    running_hours: float = Field(ge=0)

    @model_validator(mode="after")
    def check_hours_match_status(self):
        if self.status in ("IDLE", "BREAKDOWN") and self.running_hours > 0:
            raise ValueError(
                f"{self.status} days cannot have running hours greater than 0"
            )
        return self


class UsageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    machine_id: int
    booking_id: int
    usage_date: date
    status: str
    running_hours: float


# -------------------------
# Contract
# -------------------------

REQUIRED_CONTRACT_FIELDS: dict[str, list[str]] = {
    "DAILY": ["daily_rate"],
    "HOURLY": ["hourly_rate", "daily_minimum_hours"],
    "MONTHLY": ["monthly_rate", "monthly_hour_cap", "overage_rate"],
}


class ContractCreate(BaseModel):
    booking_id: int
    billing_type: Literal["DAILY", "HOURLY", "MONTHLY"]

    daily_rate: float | None = Field(default=None, ge=0)

    hourly_rate: float | None = Field(default=None, ge=0)
    daily_minimum_hours: float | None = Field(default=None, ge=0)

    monthly_rate: float | None = Field(default=None, ge=0)
    monthly_hour_cap: float | None = Field(default=None, ge=0)
    overage_rate: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def check_required_rates(self):
        required = REQUIRED_CONTRACT_FIELDS[self.billing_type]

        missing = [
            field
            for field in required
            if getattr(self, field) is None
        ]

        if missing:
            raise ValueError(
                f"A {self.billing_type} contract requires: "
                f"{', '.join(missing)}"
            )

        return self


class ContractResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    booking_id: int
    billing_type: str
    daily_rate: float | None = None
    hourly_rate: float | None = None
    daily_minimum_hours: float | None = None
    monthly_rate: float | None = None
    monthly_hour_cap: float | None = None
    overage_rate: float | None = None


# -------------------------
# Service
# -------------------------

class ServiceCreate(BaseModel):
    machine_id: int

    # Odometer reading at the time of service.
    # Leave null to use the machine's current total running hours.
    service_hours: float | None = Field(default=None, ge=0)

    serviced_at: date
    description: str | None = None


class ServiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    machine_id: int
    service_hours: float
    serviced_at: date
    description: str | None = None


# -------------------------
# Billing / Invoice
# -------------------------

class BillingResponse(BaseModel):
    booking_id: int
    machine_id: int
    billing_type: str

    running_days: int
    idle_days: int
    breakdown_days: int
    chargeable_days: int

    total_running_hours: float
    total_invoice_amount: float


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    booking_id: int
    amount: float
    running_hours: float
    idle_days: int
    breakdown_days: int
    created_at: datetime


# -------------------------
# Utilisation
# -------------------------

class UtilisationResponse(BaseModel):
    machine_id: int
    machine_code: str
    machine_name: str
    district: str
    equipment_type: str

    running_days: int
    idle_days: int
    breakdown_days: int
    tracked_days: int

    total_running_hours: float
    utilisation_rate: float