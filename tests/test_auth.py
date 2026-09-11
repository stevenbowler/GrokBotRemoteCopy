"""R-AUTH — fail closed."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import create_app
from settings import Settings

from tests.conftest import GIT_SHA, ROOT, SECRET
from tests.fakes import FakeDocker


def _settings(artifacts: Path, **kwargs) -> Settings:
    base = dict(
        runner_secret=SECRET,
        local_dev=False,
        runner_env="dev",
        jobs_dir=ROOT / "jobs",
        artifacts_dir=artifacts,
        repo_dir=ROOT,
        git_sha=GIT_SHA,
    )
    base.update(kwargs)
    s = Settings(**base)
    s.validate()
    return s


def test_r_auth_01_missing_secret(client):
    """R-AUTH-01: no X-Runner-Secret → 403, no container."""
    r = client.post("/v1/jobs", json={"job_id": "smoke", "env": "dev"})
    assert r.status_code == 403
    # docker never started
    fake = client.app.state.runner.docker()
    assert fake.calls == []


def test_r_auth_02_wrong_secret(client):
    """R-AUTH-02: wrong secret → 403, no container."""
    r = client.post(
        "/v1/jobs",
        json={"job_id": "smoke", "env": "dev"},
        headers={"X-Runner-Secret": "not-the-token"},
    )
    assert r.status_code == 403
    fake = client.app.state.runner.docker()
    assert fake.calls == []


def test_r_auth_03_empty_secret_rejected(artifacts):
    """R-AUTH-03: empty RUNNER_SECRET and LOCAL_DEV off → 403 (not open)."""
    s = _settings(artifacts, runner_secret="")
    app = create_app(s, docker_client=FakeDocker())
    c = TestClient(app)
    r = c.post("/v1/jobs", json={"job_id": "smoke", "env": "dev"})
    assert r.status_code == 403
    r2 = c.post(
        "/v1/jobs",
        json={"job_id": "smoke", "env": "dev"},
        headers={"X-Runner-Secret": ""},
    )
    assert r2.status_code == 403
    assert app.state.runner.docker().calls == []


def test_r_auth_04_local_dev_forbidden_on_prod(artifacts):
    """R-AUTH-04: LOCAL_DEV cannot be on when RUNNER_ENV is test/prod."""
    with pytest.raises(RuntimeError, match="LOCAL_DEV"):
        _settings(artifacts, local_dev=True, runner_env="prod")
    with pytest.raises(RuntimeError, match="LOCAL_DEV"):
        _settings(artifacts, local_dev=True, runner_env="test")


def test_local_dev_allows_missing_secret(artifacts):
    s = _settings(artifacts, local_dev=True, runner_secret="")
    app = create_app(s, docker_client=FakeDocker())
    c = TestClient(app)
    r = c.post("/v1/jobs", json={"job_id": "smoke", "env": "dev"})
    assert r.status_code == 202
