"""Job containers may emit GROKBOT_RESULT JSON; runner merges counts (ARCHITECTURE §6)."""

from __future__ import annotations

import json

from tests.conftest import wait_terminal


def test_job_result_counts_from_logs(client, auth, fake_docker):
    fake_docker.forced_logs = (
        "hostname=testhost\n"
        "GROKBOT_RESULT="
        + json.dumps(
            {
                "summary": "agent86-qa-dev pass=2 fail=1 skip=3 n/a=0",
                "counts": {"pass": 2, "fail": 1, "skip": 3, "n/a": 0},
            }
        )
        + "\n"
    ).encode()
    r = client.post("/v1/jobs", json={"job_id": "smoke", "env": "dev"}, headers=auth)
    result = wait_terminal(client, r.json()["run_id"], auth)
    assert result["counts"]["pass"] == 2
    assert result["counts"]["fail"] == 1
    assert result["counts"]["skip"] == 3
    assert result["counts"]["n/a"] == 0
    assert "pass=2" in (result["summary"] or "")


def test_job1_secret_names_only():
    from tests.conftest import ROOT

    text = (ROOT / "jobs" / "examples" / "agent86-qa-dev" / "job.yaml").read_text()
    assert "QA_USER" in text
    assert "QA_PASSWORD" in text
    assert "QA_USER_ALT" in text
    assert "QA_PASSWORD_ALT" in text
    lowered = text.lower()
    assert "902100" not in text
    assert "qademo@" not in lowered
    assert "googledemo@" not in lowered
    assert "appledemo@" not in lowered


def test_compose_publishes_8787_not_host_8080():
    from tests.conftest import ROOT

    text = (ROOT / "compose" / "docker-compose.yml").read_text()
    assert "name: grokbotremote" in text
    assert "${RUNNER_HOST:-127.0.0.1}:${RUNNER_PORT:-8787}:8080" in text
    assert "127.0.0.1:8080:8080" not in text
    assert "8787" in text
    assert "context: ../jobs/examples/agent86-qa-dev" in text
    lowered = text.lower()
    assert "already used" in lowered or "avoid host 8080" in lowered


def test_deploy_yml_example_runner_label_only():
    from tests.conftest import ROOT

    text = (ROOT / ".github" / "workflows" / "deploy.yml").read_text()
    assert "runs-on: [self-hosted, example-runner]" in text
    runs = [ln for ln in text.splitlines() if "runs-on:" in ln]
    joined = "\n".join(runs)
    assert "example-runner" in joined
    assert "home-server" not in joined
    assert "test-server" not in joined
    assert "prod-server" not in joined
    assert "ubuntu-latest" in joined
    assert not any(
        ln.strip().startswith("docker compose down") for ln in text.splitlines()
    )
    assert "Do not reuse compose stacks from other projects" in text
    assert "branches: [dev]" in text
    assert "needs: pytest" in text
