"""R-TIME — timeout kill."""

from __future__ import annotations

import yaml
from fastapi.testclient import TestClient

from app import create_app
from settings import Settings

from tests.conftest import GIT_SHA, ROOT, SECRET, wait_terminal
from tests.fakes import FakeDocker


def test_r_time_01_kill_past_timeout(tmp_path):
    """R-TIME-01: job timeout 1s that never exits → status timeout, container killed."""
    jobs = tmp_path / "jobs"
    job_dir = jobs / "timeout-stub"
    job_dir.mkdir(parents=True)
    (job_dir / "job.yaml").write_text(
        yaml.safe_dump(
            {
                "id": "timeout-stub",
                "image": "alpine:3.20",
                "command": ["sleep", "60"],
                "timeout": 1,
                "secrets": [],
                "test_only": True,
            }
        )
    )
    fake = FakeDocker()
    fake.never_finish = True
    settings = Settings(
        runner_secret=SECRET,
        local_dev=False,
        runner_env="dev",
        jobs_dir=jobs,
        artifacts_dir=tmp_path / "artifacts",
        repo_dir=ROOT,
        git_sha=GIT_SHA,
        webhook_url="http://webhook.test/hook",
        webhook_key="k",
        webhook_retries=1,
        webhook_backoff=0.0,
    )
    posts: list[dict] = []

    def post(url, headers, body, timeout):
        posts.append(body)
        return 200, "ok"

    app = create_app(settings, docker_client=fake, webhook_post=post)
    client = TestClient(app)
    auth = {"X-Runner-Secret": SECRET}
    r = client.post("/v1/jobs", json={"job_id": "timeout-stub", "env": "dev"}, headers=auth)
    assert r.status_code == 202, r.text
    result = wait_terminal(client, r.json()["run_id"], auth, timeout=5)
    assert result["status"] == "timeout"
    assert fake.containers_started, "container should have started"
    assert fake.containers_started[0].killed, "container must be killed after timeout"
    assert fake.containers_started[0].status != "running"
    assert posts, "webhook should fire"
    assert posts[0]["status"] == "timeout"
