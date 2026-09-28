from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    Date,
    DateTime,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Machine(Base):
    __tablename__ = "machines"

    __table_args__ = (
        CheckConstraint(
            "status IN ('AVAILABLE', 'BOOKED', 'UNDER_MAINTENANCE', 'RETIRED')",
            name="valid_machine_status"
        ),
        CheckConstraint(
            "total_running_hours >= 0",
            name="valid_total_running_hours"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    machine_code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    equipment_type = Column(String(50), nullable=False)
    district = Column(String(50), nullable=False)

    status = Column(String(20), nullable=False, default="AVAILABLE")

    total_running_hours = Column(Numeric(10, 2), nullable=False, default=0.0)
    service_interval_hours = Column(Numeric(10, 2), nullable=False, default=500.0)
    last_service_hours = Column(Numeric(10, 2), nullable=False, default=0.0)

    bookings = relationship("Booking", back_populates="machine")
    services = relationship("Service", back_populates="machine")
    usage_logs = relationship("MachineUsage", back_populates="machine")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20))
    email = Column(String(100))

    bookings = relationship("Booking", back_populates="customer")


class Booking(Base):
    __tablename__ = "bookings"

    __table_args__ = (
        CheckConstraint(
            "end_date >= start_date",
            name="valid_booking_dates"
        ),
        CheckConstraint(
            "status IN ('BOOKED', 'COMPLETED', 'CANCELLED')",
            name="valid_booking_status"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    status = Column(String(20), nullable=False, default="BOOKED")

    machine = relationship("Machine", back_populates="bookings")
    customer = relationship("Customer", back_populates="bookings")

    contract = relationship("Contract", back_populates="booking", uselist=False)
    usage_logs = relationship("MachineUsage", back_populates="booking")


class MachineUsage(Base):
    __tablename__ = "machine_usage"

    __table_args__ = (
        UniqueConstraint(
            "machine_id", "usage_date",
            name="unique_machine_usage_date"
        ),
        CheckConstraint(
            "status IN ('RUNNING', 'IDLE', 'BREAKDOWN')",
            name="valid_usage_status"
        ),
        CheckConstraint(
            "running_hours >= 0",
            name="valid_running_hours"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=False)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)

    usage_date = Column(Date, nullable=False)
    status = Column(String(20), nullable=False)
    running_hours = Column(Numeric(10, 2), nullable=False, default=0.0)

    machine = relationship("Machine", back_populates="usage_logs")
    booking = relationship("Booking", back_populates="usage_logs")


class Contract(Base):
    __tablename__ = "contracts"

    __table_args__ = (
        UniqueConstraint("booking_id", name="unique_contract_per_booking"),
        CheckConstraint(
            "billing_type IN ('DAILY', 'HOURLY', 'MONTHLY')",
            name="valid_billing_type"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    billing_type = Column(String(20), nullable=False)

    daily_rate = Column(Numeric(12, 2))

    hourly_rate = Column(Numeric(12, 2))
    daily_minimum_hours = Column(Numeric(10, 2))

    monthly_rate = Column(Numeric(12, 2))
    monthly_hour_cap = Column(Numeric(10, 2))
    overage_rate = Column(Numeric(12, 2))

    booking = relationship("Booking", back_populates="contract")


class Service(Base):
    __tablename__ = "services"

    __table_args__ = (
        CheckConstraint("service_hours >= 0", name="valid_service_hours"),
    )

    id = Column(Integer, primary_key=True, index=True)

    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=False)

    # Odometer reading (total running hours) at the moment of servicing.
    service_hours = Column(Numeric(10, 2), nullable=False)

    serviced_at = Column(Date, nullable=False, server_default=func.current_date())
    description = Column(String(255))

    machine = relationship("Machine", back_populates="services")


class Invoice(Base):
    __tablename__ = "invoices"

    __table_args__ = (
        CheckConstraint("amount >= 0", name="valid_invoice_amount"),
    )

    id = Column(Integer, primary_key=True, index=True)

    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)

    amount = Column(Numeric(12, 2), nullable=False)
    running_hours = Column(Numeric(10, 2), default=0)
    idle_days = Column(Integer, default=0)
    breakdown_days = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())