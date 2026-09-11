"""R-ONE — one job at a time (v1: 409)."""

from __future__ import annotations

import threading
import time

from tests.conftest import wait_terminal


def test_r_one_01_second_dispatch(client, auth, fake_docker):
    """R-ONE-01: while a job is running, another POST → 409; first is not killed."""
    gate = threading.Event()
    fake_docker.hold = gate
    r1 = client.post("/v1/jobs", json={"job_id": "smoke", "env": "dev"}, headers=auth)
    assert r1.status_code == 202, r1.text
    run_id = r1.json()["run_id"]
    deadline = time.time() + 3
    while time.time() < deadline and not fake_docker.containers_started:
        time.sleep(0.02)
    assert fake_docker.containers_started, "first container should start"
    first = fake_docker.containers_started[0]
    running = False
    deadline = time.time() + 3
    while time.time() < deadline:
        g = client.get(f"/v1/jobs/{run_id}", headers=auth).json()
        if g["status"] == "running":
            running = True
            break
        if g["status"] not in ("queued", "running"):
            break
        time.sleep(0.02)
    assert running or client.get(f"/v1/jobs/{run_id}", headers=auth).json()["status"] == "running"

    r2 = client.post("/v1/jobs", json={"job_id": "smoke", "env": "dev"}, headers=auth)
    assert r2.status_code == 409, r2.text
    assert not first.killed
    assert len(fake_docker.containers_started) == 1

    gate.set()
    result = wait_terminal(client, run_id, auth)
    assert result["status"] == "passed"
