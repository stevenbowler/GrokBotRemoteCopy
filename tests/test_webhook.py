"""R-WH — webhook deliver / retry / backfill."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app import create_app
from settings import Settings

from tests.conftest import GIT_SHA, ROOT, SECRET, wait_terminal
from tests.fakes import FakeDocker


def test_r_wh_01_delivered(tmp_path):
    posts: list[dict] = []

    def post(url, headers, body, timeout):
        assert headers.get("X-Webhook-Key") == "sender-key"
        posts.append(body)
        return 200, "ok"

    fake = FakeDocker()
    settings = Settings(
        runner_secret=SECRET,
        local_dev=False,
        runner_env="dev",
        jobs_dir=ROOT / "jobs",
        artifacts_dir=tmp_path / "artifacts",
        repo_dir=ROOT,
        git_sha=GIT_SHA,
        webhook_url="http://webhook.test/hook",
        webhook_key="sender-key",
        webhook_retries=2,
        webhook_backoff=0.0,
    )
    app = create_app(settings, docker_client=fake, webhook_post=post)
    client = TestClient(app)
    auth = {"X-Runner-Secret": SECRET}
    r = client.post("/v1/jobs", json={"job_id": "smoke", "env": "dev"}, headers=auth)
    result = wait_terminal(client, r.json()["run_id"], auth)
    assert result["status"] == "passed"
    assert posts and posts[0]["run_id"] == result["run_id"]
    assert SECRET not in str(posts[0])


def test_r_wh_02_retry(tmp_path):
    attempts = {"n": 0}

    def post(url, headers, body, timeout):
        attempts["n"] += 1
        if attempts["n"] <= 2:
            return 500, "nope"
        return 200, "ok"

    settings = Settings(
        runner_secret=SECRET,
        local_dev=False,
        runner_env="dev",
        jobs_dir=ROOT / "jobs",
        artifacts_dir=tmp_path / "artifacts",
        repo_dir=ROOT,
        git_sha=GIT_SHA,
        webhook_url="http://webhook.test/hook",
        webhook_key="k",
        webhook_retries=4,
        webhook_backoff=0.0,
    )
    app = create_app(settings, docker_client=FakeDocker(), webhook_post=post)
    client = TestClient(app)
    auth = {"X-Runner-Secret": SECRET}
    r = client.post("/v1/jobs", json={"job_id": "smoke", "env": "dev"}, headers=auth)
    result = wait_terminal(client, r.json()["run_id"], auth)
    assert result["status"] == "passed"
    assert attempts["n"] == 3


def test_r_wh_03_backfill_when_webhook_down(tmp_path):
    def post(url, headers, body, timeout):
        raise OSError("down")

    settings = Settings(
        runner_secret=SECRET,
        local_dev=False,
        runner_env="dev",
        jobs_dir=ROOT / "jobs",
        artifacts_dir=tmp_path / "artifacts",
        repo_dir=ROOT,
        git_sha=GIT_SHA,
        webhook_url="http://webhook.test/hook",
        webhook_key="k",
        webhook_retries=2,
        webhook_backoff=0.0,
    )
    app = create_app(settings, docker_client=FakeDocker(), webhook_post=post)
    client = TestClient(app)
    auth = {"X-Runner-Secret": SECRET}
    r = client.post("/v1/jobs", json={"job_id": "smoke", "env": "dev"}, headers=auth)
    run_id = r.json()["run_id"]
    result = wait_terminal(client, run_id, auth)
    assert result["status"] == "passed"
    got = client.get(f"/v1/jobs/{run_id}", headers=auth)
    assert got.status_code == 200
    assert got.json()["summary"]
