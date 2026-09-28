from tests.conftest import client


def test_get_utilisation():
    response = client.get("/utilisation")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)


def test_utilisation_contains_required_fields():
    response = client.get("/utilisation")

    assert response.status_code == 200

    data = response.json()

    assert len(data) >= 1

    machine = data[0]

    for field in (
        "machine_id",
        "machine_code",
        "machine_name",
        "district",
        "equipment_type",
        "running_days",
        "idle_days",
        "breakdown_days",
        "tracked_days",
        "total_running_hours",
        "utilisation_rate",
    ):
        assert field in machine


def test_utilisation_counts_day_statuses_correctly():
    data = client.get("/utilisation").json()

    # Machine 2 is the DAILY fixture: 2 running, 1 idle, 1 breakdown.
    machine = next(m for m in data if m["machine_id"] == 2)

    assert machine["running_days"] == 2
    assert machine["idle_days"] == 1
    assert machine["breakdown_days"] == 1
    assert machine["tracked_days"] == 4
    assert machine["total_running_hours"] == 15.0
    assert machine["utilisation_rate"] == 50.0


def test_idle_machine_shows_zero_utilisation():
    data = client.get("/utilisation").json()

    # Machine 5 has never been logged: the "sitting in the yard" case.
    machine = next(m for m in data if m["machine_id"] == 5)

    assert machine["tracked_days"] == 0
    assert machine["utilisation_rate"] == 0.0


def test_every_machine_appears_in_the_report():
    machines = client.get("/machines").json()
    utilisation = client.get("/utilisation").json()

    assert len(utilisation) == len(machines)