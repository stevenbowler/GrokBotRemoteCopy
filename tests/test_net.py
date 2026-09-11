"""R-NET — isolation."""

from __future__ import annotations

import yaml
from fastapi.testclient import TestClient

from app import create_app
from settings import Settings

from tests.conftest import GIT_SHA, ROOT, SECRET, wait_terminal
from tests.fakes import FakeDocker


def test_r_net_01_no_host_network(client, auth, fake_docker):
    """R-NET-01: smoke is not network=host."""
    r = client.post("/v1/jobs", json={"job_id": "smoke", "env": "dev"}, headers=auth)
    wait_terminal(client, r.json()["run_id"], auth)
    kwargs = fake_docker.last_kwargs
    nm = (kwargs.get("network_mode") or "").lower()
    assert nm != "host"
    assert nm in {"bridge", ""} or nm == "bridge"


def test_r_net_01_host_network_job_rejected(tmp_path):
    """R-NET-01: job spec with host network is rejected unless owner-accepted."""
    jobs = tmp_path / "jobs"
    d = jobs / "needshost"
    d.mkdir(parents=True)
    (d / "job.yaml").write_text(
        yaml.safe_dump(
            {
                "id": "needshost",
                "image": "alpine:3.20",
                "command": ["true"],
                "timeout": 5,
                "network_mode": "host",
            }
        )
    )
    fake = FakeDocker()
    settings = Settings(
        runner_secret=SECRET,
        local_dev=False,
        runner_env="dev",
        jobs_dir=jobs,
        artifacts_dir=tmp_path / "artifacts",
        repo_dir=ROOT,
        git_sha=GIT_SHA,
    )
    app = create_app(settings, docker_client=fake)
    client = TestClient(app)
    r = client.post(
        "/v1/jobs",
        json={"job_id": "needshost", "env": "dev"},
        headers={"X-Runner-Secret": SECRET},
    )
    assert r.status_code == 400
    assert fake.calls == []
