from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "runner"
if str(RUNNER) not in sys.path:
    sys.path.insert(0, str(RUNNER))

from app import create_app  # noqa: E402
from settings import Settings  # noqa: E402

from tests.fakes import FakeDocker  # noqa: E402

SECRET = "test-runner-secret"
GIT_SHA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


@pytest.fixture
def artifacts(tmp_path: Path) -> Path:
    d = tmp_path / "artifacts"
    d.mkdir()
    return d


@pytest.fixture
def fake_docker() -> FakeDocker:
    return FakeDocker()


@pytest.fixture
def settings(artifacts: Path) -> Settings:
    s = Settings(
        runner_secret=SECRET,
        local_dev=False,
        runner_env="dev",
        jobs_dir=ROOT / "jobs",
        artifacts_dir=artifacts,
        repo_dir=ROOT,
        git_sha=GIT_SHA,
        webhook_url="",
        webhook_key="webhook-test-key",
        webhook_retries=3,
        webhook_backoff=0.01,
        secrets={},
    )
    s.validate()
    return s


@pytest.fixture
def client(settings: Settings, fake_docker: FakeDocker) -> TestClient:
    app = create_app(settings, docker_client=fake_docker)
    return TestClient(app)


@pytest.fixture
def auth() -> dict[str, str]:
    return {"X-Runner-Secret": SECRET}


def wait_terminal(client: TestClient, run_id: str, auth: dict[str, str], timeout: float = 8.0) -> dict:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        r = client.get(f"/v1/jobs/{run_id}", headers=auth)
        assert r.status_code == 200, r.text
        last = r.json()
        if last["status"] not in ("queued", "running"):
            return last
        time.sleep(0.03)
    raise AssertionError(f"run {run_id} still {last}")
