import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  AlertCircle,
  CalendarDays,
  Hash,
  MapPin,
  Phone,
  Search,
} from "lucide-react";

import api from "../api/backend";

const STATUS_STYLES = {
  BOOKED: { background: "#dcfce7", color: "#15803d", label: "Booked" },
  COMPLETED: { background: "#dbeafe", color: "#1d4ed8", label: "Completed" },
  CANCELLED: { background: "#fee2e2", color: "#b91c1c", label: "Cancelled" },
};

function money(amount) {
  return Number(amount || 0).toLocaleString("en-IN");
}

function TrackBooking() {
  const [searchParams] = useSearchParams();

  const [bookingId, setBookingId] = useState(searchParams.get("bookingId") || "");
  const [phone, setPhone] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [found, setFound] = useState(null);

  async function handleLookup(e) {
    e.preventDefault();
    setError("");
    setFound(null);
    setLoading(true);

    try {
      const [bookingsRes, customersRes, machinesRes, invoicesRes] = await Promise.all([
        api.get("/bookings"),
        api.get("/customers"),
        api.get("/machines"),
        api.get("/billing/invoices"),
      ]);

      const booking = bookingsRes.data.find((b) => String(b.id) === bookingId.trim());

      if (!booking) {
        setError("No booking found with that ID. Please check the number and try again.");
        return;
      }

      const customer = customersRes.data.find((c) => c.id === booking.customer_id);

      if (!customer || (customer.phone || "").trim() !== phone.trim()) {
        setError("The phone number doesn't match our records for this booking.");
        return;
      }

      const machine = machinesRes.data.find((m) => m.id === booking.machine_id);
      const invoice = invoicesRes.data.find((i) => i.booking_id === booking.id);

      setFound({ booking, customer, machine, invoice });
    } catch (err) {
      setError("Could not reach the backend. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  const status = found && (STATUS_STYLES[found.booking.status] || { background: "#f3f4f6", color: "#374151", label: found.booking.status });

  return (
    <div className="page">
      <div className="booking-header">
        <span className="eyebrow">TRACK YOUR RENTAL</span>
        <h1>My booking</h1>
        <p>Enter your booking ID and phone number to check your rental status and billing.</p>
      </div>

      <form className="form-card" onSubmit={handleLookup}>
        <div className="form-card-header">
          <div className="step-number">
            <Search size={15} />
          </div>
          <div>
            <h2>Find your booking</h2>
            <p>Both fields must match the details you provided when booking.</p>
          </div>
        </div>

        <div className="customer-fields">
          <label className="customer-field">
            <span>Booking ID</span>
            <div className="input-with-icon">
              <Hash size={16} />
              <input
                required
                value={bookingId}
                onChange={(e) => setBookingId(e.target.value)}
                placeholder="e.g. 12"
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
                onChange={(e) => setPhone(e.target.value)}
                placeholder="The number you booked with"
              />
            </div>
          </label>
        </div>

        <button className="primary-button" style={{ marginTop: 18 }} disabled={loading}>
          {loading ? "Searching…" : "Find my booking"}
        </button>
      </form>

      {error && (
        <div className="error-message">
          <AlertCircle size={16} style={{ marginRight: 8 }} />
          {error}
        </div>
      )}

      {found && (
        <div className="summary-card" style={{ marginTop: 20 }}>
          <h2>Booking #{found.booking.id}</h2>

          <div className="summary-row">
            <span>Status</span>
            <strong>
              <span
                className="status-badge"
                style={{ background: status.background, color: status.color }}
              >
                {status.label}
              </span>
            </strong>
          </div>

          <div className="summary-row">
            <span>Machine</span>
            <strong>
              {found.machine ? `${found.machine.machine_code} — ${found.machine.name}` : `Machine ${found.booking.machine_id}`}
            </strong>
          </div>

          {found.machine && (
            <div className="summary-row">
              <span>
                <MapPin size={13} style={{ marginRight: 4, verticalAlign: "-2px" }} />
                Location
              </span>
              <strong>{found.machine.district}</strong>
            </div>
          )}

          <div className="summary-row">
            <span>
              <CalendarDays size={13} style={{ marginRight: 4, verticalAlign: "-2px" }} />
              Rental dates
            </span>
            <strong>{found.booking.start_date} — {found.booking.end_date}</strong>
          </div>

          {found.invoice ? (
            <>
              <div className="summary-total">
                <span>Amount so far</span>
                <strong>₹{money(found.invoice.total_invoice_amount)}</strong>
              </div>

              <div className="invoice-details">
                <div className="invoice-detail">
                  <span>Billing type</span>
                  <strong>{found.invoice.billing_type}</strong>
                </div>
                <div className="invoice-detail">
                  <span>Running hours</span>
                  <strong>{found.invoice.total_running_hours} hrs</strong>
                </div>
                <div className="invoice-detail">
                  <span>Chargeable days</span>
                  <strong>{found.invoice.chargeable_days}</strong>
                </div>
                <div className="invoice-detail">
                  <span>Breakdown days</span>
                  <strong>{found.invoice.breakdown_days}</strong>
                </div>
              </div>

              <p style={{ marginTop: 14, fontSize: 12, color: "var(--muted)" }}>
                This amount reflects rental usage recorded so far and updates automatically as usage
                is logged during your rental.
              </p>
            </>
          ) : (
            <p style={{ marginTop: 14, fontSize: 13, color: "var(--muted)" }}>
              Your contract is still being finalised — billing details will appear here shortly.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default TrackBooking;