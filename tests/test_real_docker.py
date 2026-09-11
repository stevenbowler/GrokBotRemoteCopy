"""Optional real-docker path. Skipped when no daemon (this box, most laptops)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import create_app
from settings import Settings

from tests.conftest import GIT_SHA, ROOT, SECRET, wait_terminal


def _docker_or_skip():
    try:
        import docker
    except ImportError:
        pytest.skip("docker SDK not importable")
    try:
        client = docker.from_env()
        client.ping()
        return client
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"docker daemon not available: {exc}")


def test_real_docker_smoke(tmp_path):
    dclient = _docker_or_skip()
    settings = Settings(
        runner_secret=SECRET,
        local_dev=False,
        runner_env="dev",
        jobs_dir=ROOT / "jobs",
        artifacts_dir=tmp_path / "artifacts",
        repo_dir=ROOT,
        git_sha=GIT_SHA,
    )
    app = create_app(settings, docker_client=dclient)
    client = TestClient(app)
    auth = {"X-Runner-Secret": SECRET}
    r = client.post("/v1/jobs", json={"job_id": "smoke", "env": "dev"}, headers=auth)
    assert r.status_code == 202, r.text
    result = wait_terminal(client, r.json()["run_id"], auth, timeout=60)
    assert result["status"] == "passed"
    assert result["exit_code"] == 0
    assert result["summary"]
