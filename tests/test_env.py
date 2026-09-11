"""R-ENV — environments."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app import create_app
from settings import Settings

from tests.conftest import GIT_SHA, ROOT, SECRET, wait_terminal
from tests.fakes import FakeDocker


def test_r_env_01_env_field(client, auth):
    """R-ENV-01: dispatch env=dev → result env=dev."""
    r = client.post("/v1/jobs", json={"job_id": "smoke", "env": "dev"}, headers=auth)
    result = wait_terminal(client, r.json()["run_id"], auth)
    assert result["env"] == "dev"


def test_r_env_01_prod_rejected_on_dev_runner(client, auth, fake_docker):
    """R-ENV-01: env=prod on a non-prod runner is rejected."""
    r = client.post("/v1/jobs", json={"job_id": "smoke", "env": "prod"}, headers=auth)
    assert r.status_code == 400
    assert fake_docker.calls == []


def test_r_env_01_prod_allowed_on_prod_runner(tmp_path):
    fake = FakeDocker()
    settings = Settings(
        runner_secret=SECRET,
        local_dev=False,
        runner_env="prod",
        jobs_dir=ROOT / "jobs",
        artifacts_dir=tmp_path / "artifacts",
        repo_dir=ROOT,
        git_sha=GIT_SHA,
    )
    app = create_app(settings, docker_client=fake)
    client = TestClient(app)
    auth = {"X-Runner-Secret": SECRET}
    r = client.post("/v1/jobs", json={"job_id": "smoke", "env": "prod"}, headers=auth)
    assert r.status_code == 202, r.text
    result = wait_terminal(client, r.json()["run_id"], auth)
    assert result["env"] == "prod"
