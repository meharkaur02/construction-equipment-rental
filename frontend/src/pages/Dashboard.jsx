import { useEffect, useState } from "react";
import { MapPin, Clock3, Wrench, ArrowRight } from "lucide-react";
import { useNavigate } from "react-router-dom";

import api from "../api/backend";

function Dashboard() {
  const [machines, setMachines] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const navigate = useNavigate();

  useEffect(() => {
    loadMachines();
  }, []);

  async function loadMachines() {
    try {
      const response = await api.get("/machines");

      setMachines(response.data);
    } catch (err) {
      console.error(err);

      setError(
        "Could not connect to the backend. Please make sure FastAPI is running."
      );
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="page">
        <div className="loading-card">
          Loading equipment...
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <section className="hero">
        <div>
          <span className="eyebrow">
            EQUIPMENT RENTAL PLATFORM
          </span>

          <h1>
            Reliable equipment.
            <br />
            Ready for your next project.
          </h1>

          <p>
            Browse our construction equipment fleet,
            check availability and book the machine
            you need for your project.
          </p>

          <button
            className="primary-button"
            onClick={() => navigate("/book")}
          >
            Book a machine
            <ArrowRight size={18} />
          </button>
        </div>

        <div className="hero-stat">
          <span>Machines available</span>
          <strong>{machines.length}</strong>
          <small>Across multiple districts</small>
        </div>
      </section>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      <section className="section">
        <div className="section-heading">
          <div>
            <span className="eyebrow">
              OUR FLEET
            </span>

            <h2>Construction equipment</h2>

            <p>
              Choose from excavators, cranes and
              concrete pumps.
            </p>
          </div>

          <span className="machine-count">
            {machines.length} machines
          </span>
        </div>

        <div className="machine-grid">
          {machines.map((machine) => {
            const available =
              String(machine.status).toUpperCase() ===
              "AVAILABLE";

            return (
              <div
                className="machine-card"
                key={machine.id}
              >
                <div className="machine-card-top">
                  <span className="machine-type">
                    {machine.equipment_type}
                  </span>

                  <span
                    className={
                      available
                        ? "status available"
                        : "status unavailable"
                    }
                  >
                    {machine.status}
                  </span>
                </div>

                <div className="machine-icon">
                  <Wrench size={30} />
                </div>

                <span className="machine-code">
                  {machine.machine_code}
                </span>

                <h3>{machine.name}</h3>

                <div className="machine-location">
                  <MapPin size={15} />
                  {machine.district}
                </div>

                <div className="machine-hours">
                  <Clock3 size={15} />

                  <span>
                    {Number(
                      machine.total_running_hours || 0
                    ).toLocaleString()}
                    {" "}running hours
                  </span>
                </div>

                <button
                  className="outline-button"
                  disabled={!available}
                  onClick={() =>
                    navigate(
                      `/book?machine=${machine.id}`
                    )
                  }
                >
                  {available
                    ? "Book this machine"
                    : "Currently unavailable"}

                  {available && (
                    <ArrowRight size={16} />
                  )}
                </button>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}

export default Dashboard;