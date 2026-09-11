"""R-CAN — cancel."""

from __future__ import annotations

import threading
import time
from uuid import uuid4

from tests.conftest import wait_terminal


def test_r_can_01_cancel_running(client, auth, fake_docker):
    gate = threading.Event()
    fake_docker.hold = gate
    r = client.post("/v1/jobs", json={"job_id": "smoke", "env": "dev"}, headers=auth)
    run_id = r.json()["run_id"]
    deadline = time.time() + 3
    while time.time() < deadline and not fake_docker.containers_started:
        time.sleep(0.02)
    assert fake_docker.containers_started
    c = client.post(f"/v1/jobs/{run_id}/cancel", headers=auth)
    assert c.status_code == 200, c.text
    result = wait_terminal(client, run_id, auth)
    assert result["status"] == "cancelled"
    assert fake_docker.containers_started[0].killed or fake_docker.containers_started[0].status != "running"


def test_r_can_02_cancel_unknown(client, auth):
    r = client.post(f"/v1/jobs/{uuid4()}/cancel", headers=auth)
    assert r.status_code == 404
