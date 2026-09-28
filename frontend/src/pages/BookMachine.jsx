import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  CalendarDays,
  CheckCircle2,
  Clock3,
  Mail,
  MapPin,
  Phone,
  ShieldCheck,
  User,
} from "lucide-react";

import api from "../api/backend";
import { billingPlans } from "../api/mockData";

function money(amount) {
  return Number(amount || 0).toLocaleString("en-IN");
}

function BookMachine() {
  const [searchParams] = useSearchParams();

  const [machines, setMachines] = useState([]);
  const [loadingMachines, setLoadingMachines] = useState(true);

  const [machineId, setMachineId] = useState(searchParams.get("machine") || "");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [billingType, setBillingType] = useState("DAILY");

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    api
      .get("/machines")
      .then((response) => setMachines(response.data))
      .catch(() =>
        setResult({ success: false, message: "Could not load machines from the backend." })
      )
      .finally(() => setLoadingMachines(false));
  }, []);

  const selectedMachine = machines.find(
    (machine) => String(machine.id) === String(machineId)
  );

  const selectedPlan = billingPlans.find((plan) => plan.type === billingType);

  const rentalDays = useMemo(() => {
    if (!startDate || !endDate) return 0;

    const start = new Date(`${startDate}T00:00:00`);
    const end = new Date(`${endDate}T00:00:00`);

    if (end < start) return 0;

    return Math.floor((end - start) / (1000 * 60 * 60 * 24)) + 1;
  }, [startDate, endDate]);

  const estimatedAmount = useMemo(() => {
    if (!selectedPlan || rentalDays === 0) return 0;

    if (billingType === "DAILY") {
      return rentalDays * selectedPlan.rate;
    }

    if (billingType === "HOURLY") {
      return rentalDays * selectedPlan.minimumHours * selectedPlan.rate;
    }

    if (billingType === "MONTHLY") {
      return selectedPlan.rate;
    }

    return 0;
  }, [selectedPlan, rentalDays, billingType]);

  async function handleSubmit(event) {
    event.preventDefault();
    setResult(null);

    if (!machineId) {
      setResult({ success: false, message: "Please select a machine." });
      return;
    }

    if (!startDate || !endDate) {
      setResult({ success: false, message: "Please select both rental dates." });
      return;
    }

    if (new Date(endDate) < new Date(startDate)) {
      setResult({ success: false, message: "End date cannot be before start date." });
      return;
    }

    if (
      selectedMachine &&
      String(selectedMachine.status).toUpperCase() !== "AVAILABLE"
    ) {
      setResult({ success: false, message: "This machine is currently unavailable." });
      return;
    }

    if (!name.trim() || !phone.trim() || !email.trim()) {
      setResult({ success: false, message: "Please fill in your name, phone and email." });
      return;
    }

    setSubmitting(true);

    try {
      // Step 1 — create the customer.
      const customerResponse = await api.post("/customers", {
        name: name.trim(),
        phone: phone.trim(),
        email: email.trim(),
      });

      const customerId = customerResponse.data.id;

      // Step 2 — create the booking for that customer.
      const bookingResponse = await api.post("/bookings", {
        machine_id: Number(machineId),
        customer_id: customerId,
        start_date: startDate,
        end_date: endDate,
      });

      const booking = bookingResponse.data;

      // Step 3 — create the contract with the chosen billing plan.
      const contractPayload = {
        booking_id: booking.id,
        billing_type: billingType,
        daily_rate: billingType === "DAILY" ? selectedPlan.rate : null,
        hourly_rate: billingType === "HOURLY" ? selectedPlan.rate : null,
        daily_minimum_hours: billingType === "HOURLY" ? selectedPlan.minimumHours : null,
        monthly_rate: billingType === "MONTHLY" ? selectedPlan.rate : null,
        monthly_hour_cap: billingType === "MONTHLY" ? selectedPlan.hourCap : null,
        overage_rate: billingType === "MONTHLY" ? selectedPlan.overageRate : null,
      };

      await api.post("/contracts", contractPayload);

      setResult({
        success: true,
        message: `Booking confirmed for ${name}! Booking ID: ${booking.id}.`,
        bookingId: booking.id,
      });

      setName("");
      setPhone("");
      setEmail("");
      setMachineId("");
      setStartDate("");
      setEndDate("");
      setBillingType("DAILY");
    } catch (error) {
      const status = error.response?.status;
      const detail = error.response?.data?.detail;

      if (status === 409) {
        setResult({
          success: false,
          message:
            "This machine is already booked for the selected dates. Please choose different dates.",
        });
      } else if (status === 400) {
        setResult({ success: false, message: detail || "The booking request is invalid." });
      } else if (status === 404) {
        setResult({
          success: false,
          message: "The selected machine or customer could not be found.",
        });
      } else if (status === 422) {
        setResult({ success: false, message: "Please check the booking details." });
      } else {
        setResult({
          success: false,
          message: "Something went wrong while creating the booking.",
        });
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (loadingMachines) {
    return (
      <div className="page">
        <div className="loading-card">Loading machines...</div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="booking-header">
        <span className="eyebrow">NEW RENTAL</span>
        <h1>Book your equipment</h1>
        <p>Enter your details, select a machine, choose your dates and billing plan.</p>
      </div>

      <form className="booking-layout" onSubmit={handleSubmit}>
        <div className="booking-main">
          {/* STEP 1 — Customer details */}
          <section className="form-card">
            <div className="form-card-header">
              <div className="step-number">01</div>
              <div>
                <h2>Your details</h2>
                <p>So we can confirm your booking and let you track it later.</p>
              </div>
            </div>

            <div className="customer-fields">
              <label className="customer-field">
                <span>Full name</span>
                <div className="input-with-icon">
                  <User size={16} />
                  <input
                    required
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    placeholder="Your name"
                  />
                </div>
              </label>

              <label className="customer-field">
                <span>Phone number</span>
                <div className="input-with-icon">
                  <Phone size={16} />
                  <input
                    required
                    value={phone}
                    onChange={(event) => setPhone(event.target.value)}
                    placeholder="Your mobile number"
                  />
                </div>
              </label>

              <label className="customer-field">
                <span>Email address</span>
                <div className="input-with-icon">
                  <Mail size={16} />
                  <input
                    required
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder="you@example.com"
                  />
                </div>
              </label>
            </div>
          </section>

          {/* STEP 2 — Select equipment */}
          <section className="form-card">
            <div className="form-card-header">
              <div className="step-number">02</div>
              <div>
                <h2>Select equipment</h2>
                <p>Choose the machine you need for your project.</p>
              </div>
            </div>

            <div className="machine-select-grid">
              {machines.map((machine) => {
                const available = String(machine.status).toUpperCase() === "AVAILABLE";
                const selected = String(machine.id) === String(machineId);

                return (
                  <button
                    type="button"
                    key={machine.id}
                    disabled={!available}
                    className={`select-machine ${selected ? "selected" : ""}`}
                    onClick={() => setMachineId(String(machine.id))}
                  >
                    <h3>{machine.machine_code}</h3>
                    <p>{machine.name}</p>
                    <p>
                      {machine.equipment_type} · {machine.district}
                    </p>

                    {selected && <CheckCircle2 className="machine-check" size={18} />}
                  </button>
                );
              })}
            </div>
          </section>

          {/* STEP 3 — Rental period */}
          <section className="form-card">
            <div className="form-card-header">
              <div className="step-number">03</div>
              <div>
                <h2>Rental period</h2>
                <p>Tell us when you need the equipment.</p>
              </div>
            </div>

            <div className="date-grid">
              <label className="customer-field">
                <span>Start date</span>
                <div className="input-with-icon">
                  <CalendarDays size={16} />
                  <input
                    type="date"
                    required
                    value={startDate}
                    onChange={(event) => setStartDate(event.target.value)}
                  />
                </div>
              </label>

              <label className="customer-field">
                <span>End date</span>
                <div className="input-with-icon">
                  <CalendarDays size={16} />
                  <input
                    type="date"
                    required
                    min={startDate || undefined}
                    value={endDate}
                    onChange={(event) => setEndDate(event.target.value)}
                  />
                </div>
              </label>
            </div>

            {rentalDays > 0 && (
              <div className="duration-info">
                <Clock3 size={15} style={{ marginRight: 6, verticalAlign: "-2px" }} />
                {rentalDays} rental day{rentalDays !== 1 ? "s" : ""}
              </div>
            )}
          </section>

          {/* STEP 4 — Billing plan */}
          <section className="form-card">
            <div className="form-card-header">
              <div className="step-number">04</div>
              <div>
                <h2>Billing plan</h2>
                <p>Select how your rental will be billed.</p>
              </div>
            </div>

            <div className="billing-grid">
              {billingPlans.map((plan) => {
                const selected = billingType === plan.type;

                return (
                  <button
                    type="button"
                    key={plan.type}
                    className={`billing-option ${selected ? "selected" : ""}`}
                    onClick={() => setBillingType(plan.type)}
                  >
                    <h3>{plan.name}</h3>
                    <p>{plan.description}</p>
                    <div>
                      <span className="billing-price">₹{money(plan.rate)}</span>{" "}
                      <span className="billing-unit">/ {plan.unit}</span>
                    </div>
                    <div className="billing-minimum">{plan.minimumText}</div>
                  </button>
                );
              })}
            </div>
          </section>
        </div>

        {/* SUMMARY SIDEBAR */}
        <aside className="booking-summary">
          <div className="summary-card">
            <h2>Booking summary</h2>

            <div className="summary-row">
              <span>Customer</span>
              <strong>{name || "Not entered"}</strong>
            </div>

            <div className="summary-row">
              <span>Machine</span>
              <strong>{selectedMachine ? selectedMachine.machine_code : "Not selected"}</strong>
            </div>

            {selectedMachine && (
              <div className="summary-row">
                <span>
                  <MapPin size={13} style={{ marginRight: 4, verticalAlign: "-2px" }} />
                  Location
                </span>
                <strong>{selectedMachine.district}</strong>
              </div>
            )}

            <div className="summary-row">
              <span>Billing plan</span>
              <strong>{selectedPlan?.name || "Not selected"}</strong>
            </div>

            <div className="summary-row">
              <span>Rental period</span>
              <strong>
                {rentalDays ? `${rentalDays} day${rentalDays !== 1 ? "s" : ""}` : "Not selected"}
              </strong>
            </div>

            <div className="summary-row">
              <span>Rate</span>
              <strong>
                {selectedPlan ? `₹${money(selectedPlan.rate)} / ${selectedPlan.unit}` : "-"}
              </strong>
            </div>

            <div className="summary-total">
              <span>Estimated amount</span>
              <strong>₹{money(estimatedAmount)}</strong>
            </div>

            <button type="submit" className="primary-button" style={{ width: "100%" }} disabled={submitting}>
              {submitting ? "Creating booking..." : "Check availability & book"}
            </button>

            <div className="secure-note">
              <ShieldCheck size={15} />
              <span>Your booking is validated by the backend before confirmation.</span>
            </div>
          </div>
        </aside>
      </form>

      {result && (
        <div className={result.success ? "success-message" : "error-message"} style={{ marginTop: 18 }}>
          {result.message}

          {result.success && (
            <div style={{ marginTop: 8 }}>
              <Link
                to={`/track?bookingId=${result.bookingId}`}
                style={{ color: "var(--brand)", fontWeight: 700 }}
              >
                Track this booking →
              </Link>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default BookMachine;