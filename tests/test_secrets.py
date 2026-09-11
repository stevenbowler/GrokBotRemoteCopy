"""R-SEC — secrets stay off the record."""

from __future__ import annotations

import yaml
from fastapi.testclient import TestClient

from app import create_app
from settings import Settings

from tests.conftest import GIT_SHA, ROOT, SECRET, wait_terminal
from tests.fakes import FakeDocker

LEAK = "super-secret-test-value"


def _leaky_app(tmp_path, extra_host_env=None):
    jobs = tmp_path / "jobs"
    job_dir = jobs / "leaky"
    job_dir.mkdir(parents=True)
    (job_dir / "job.yaml").write_text(
        yaml.safe_dump(
            {
                "id": "leaky",
                "image": "alpine:3.20",
                "command": ["printenv"],
                "timeout": 10,
                "secrets": ["QA_PASSWORD"],
            }
        )
    )
    fake = FakeDocker()
    fake.leak_env = True
    settings = Settings(
        runner_secret=SECRET,
        local_dev=False,
        runner_env="dev",
        jobs_dir=jobs,
        artifacts_dir=tmp_path / "artifacts",
        repo_dir=ROOT,
        git_sha=GIT_SHA,
        secrets={"QA_PASSWORD": LEAK},
    )
    app = create_app(settings, docker_client=fake)
    return app, fake, TestClient(app), {"X-Runner-Secret": SECRET}


def test_r_sec_01_not_in_logs(tmp_path):
    """R-SEC-01: secret value redacted from captured logs."""
    app, fake, client, auth = _leaky_app(tmp_path)
    r = client.post("/v1/jobs", json={"job_id": "leaky", "env": "dev"}, headers=auth)
    result = wait_terminal(client, r.json()["run_id"], auth)
    logs_path = app.state.settings.artifacts_dir / result["run_id"] / "logs.txt"
    text = logs_path.read_text()
    assert LEAK not in text
    for p in app.state.settings.artifacts_dir.rglob("*"):
        if p.is_file():
            assert LEAK not in p.read_text(errors="replace")


def test_r_sec_02_not_in_result_json(tmp_path):
    """R-SEC-02: GET body does not contain the secret value."""
    _app, _fake, client, auth = _leaky_app(tmp_path)
    r = client.post("/v1/jobs", json={"job_id": "leaky", "env": "dev"}, headers=auth)
    result = wait_terminal(client, r.json()["run_id"], auth)
    assert LEAK not in str(result)
    assert LEAK not in client.get(f"/v1/jobs/{result['run_id']}", headers=auth).text


def test_r_sec_03_declared_secrets_only(client, auth, fake_docker, monkeypatch):
    """R-SEC-03: host env LEAK_ME is not injected into smoke (undeclared)."""
    monkeypatch.setenv("LEAK_ME", "1")
    r = client.post("/v1/jobs", json={"job_id": "smoke", "env": "dev"}, headers=auth)
    wait_terminal(client, r.json()["run_id"], auth)
    env = fake_docker.last_kwargs.get("environment") or {}
    assert "LEAK_ME" not in env
    assert "GIT_SHA" in env
