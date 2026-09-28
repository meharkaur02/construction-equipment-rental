import { Link, useLocation } from "react-router-dom";
import { CalendarDays, Search, Truck } from "lucide-react";

const links = [
  {
    to: "/",
    label: "Machines",
    icon: Truck,
  },
  {
    to: "/book",
    label: "Book a Machine",
    icon: CalendarDays,
  },
  {
    to: "/track",
    label: "Track Booking",
    icon: Search,
  },
];

function Navbar() {
  const location = useLocation();

  return (
    <nav className="navbar">
      <Link to="/" className="navbar-brand">
        <span className="brand-icon">
          <Truck size={20} />
        </span>

        <span>
          <strong>Equipment Rental</strong>
          <small>Construction Equipment</small>
        </span>
      </Link>

      <div className="navbar-links">
        {links.map((link) => {
          const Icon = link.icon;

          const active =
            location.pathname === link.to;

          return (
            <Link
              key={link.to}
              to={link.to}
              className={`navbar-link ${
                active ? "active" : ""
              }`}
            >
              <Icon size={17} />
              {link.label}
            </Link>
          );
        })}
      </div>

      <Link to="/book" className="navbar-button">
        Book now
      </Link>
    </nav>
  );
}

export default Navbar;