"""R-SMOKE — Job 0."""

from __future__ import annotations

import re
from uuid import UUID

from tests.conftest import wait_terminal


def test_r_smoke_01_pass(client, auth):
    """R-SMOKE-01: POST smoke → run_id, exit 0, status passed, summary has host or sha."""
    r = client.post("/v1/jobs", json={"job_id": "smoke", "env": "dev"}, headers=auth)
    assert r.status_code in (200, 202), r.text
    body = r.json()
    run_id = body["run_id"]
    UUID(run_id)
    result = wait_terminal(client, run_id, auth)
    assert result["status"] == "passed"
    assert result["exit_code"] == 0
    summary = result["summary"] or ""
    assert "testhost" in summary or "sha=" in summary or "aaaaaaaa" in summary


def test_r_smoke_02_result_contract(client, auth):
    """R-SMOKE-02: GET result has required fields, ISO-8601 UTC, no secrets."""
    r = client.post("/v1/jobs", json={"job_id": "smoke", "env": "dev"}, headers=auth)
    run_id = r.json()["run_id"]
    result = wait_terminal(client, run_id, auth)
    for key in (
        "run_id",
        "job_id",
        "git_sha",
        "env",
        "status",
        "started_at",
        "finished_at",
        "exit_code",
        "summary",
    ):
        assert key in result, key
        assert result[key] is not None, key
    assert result["job_id"] == "smoke"
    assert result["run_id"] == run_id
    iso = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
    assert iso.match(result["started_at"]), result["started_at"]
    assert iso.match(result["finished_at"]), result["finished_at"]
    blob = str(result)
    assert "test-runner-secret" not in blob
    assert "webhook-test-key" not in blob


def test_r_smoke_03_unknown_job(client, auth):
    """R-SMOKE-03: unknown job_id → 4xx, no container."""
    r = client.post(
        "/v1/jobs",
        json={"job_id": "does-not-exist", "env": "dev"},
        headers=auth,
    )
    assert 400 <= r.status_code < 500
    fake = client.app.state.runner.docker()
    assert fake.calls == []


def test_r_git_01_requested_sha(client, auth):
    """R-GIT-01: dispatch git_sha is stamped on the result."""
    sha = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    r = client.post(
        "/v1/jobs",
        json={"job_id": "smoke", "env": "dev", "git_sha": sha},
        headers=auth,
    )
    result = wait_terminal(client, r.json()["run_id"], auth)
    assert result["git_sha"] == sha
