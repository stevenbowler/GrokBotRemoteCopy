"""Nested jobs catalog + load (examples/ and stable yaml id)."""

from __future__ import annotations

from pathlib import Path

from tests.conftest import ROOT


def test_list_jobs_includes_nested_examples_and_core():
    from jobs import list_jobs

    ids = list_jobs(ROOT / "jobs")
    assert "smoke" in ids
    assert "timeout-stub" in ids
    assert "agent86-qa-dev" in ids
    assert "examples" not in ids
    # Nested sample must not appear only as a path slug
    assert "examples/agent86-qa-dev" not in ids


def test_load_job_by_stable_id_agent86_qa_dev():
    from jobs import load_job

    job = load_job(ROOT / "jobs", "agent86-qa-dev")
    assert job is not None
    assert job.id == "agent86-qa-dev"
    assert job.path is not None
    assert job.path.name == "agent86-qa-dev"
    assert (job.path / "job.yaml").is_file()
    assert "examples" in job.path.parts


def test_load_job_by_examples_relative_path():
    from jobs import load_job

    job = load_job(ROOT / "jobs", "examples/agent86-qa-dev")
    assert job is not None
    assert job.id == "agent86-qa-dev"


def test_load_job_smoke_top_level():
    from jobs import load_job

    job = load_job(ROOT / "jobs", "smoke")
    assert job is not None
    assert job.id == "smoke"
    assert job.path == ROOT / "jobs" / "smoke"


def test_list_jobs_tmp_nested(tmp_path: Path):
    from jobs import list_jobs, load_job

    (tmp_path / "smoke").mkdir()
    (tmp_path / "smoke" / "job.yaml").write_text(
        "id: smoke\nimage: alpine:3.20\ncommand: [true]\n"
    )
    (tmp_path / "examples").mkdir()
    (tmp_path / "examples" / "nested-demo").mkdir()
    (tmp_path / "examples" / "nested-demo" / "job.yaml").write_text(
        "id: nested-demo\nimage: alpine:3.20\ncommand: [true]\n"
    )
    # empty examples dir and a dir without job.yaml must be skipped
    (tmp_path / "examples" / "empty").mkdir()
    (tmp_path / "not-a-job").mkdir()
    (tmp_path / "not-a-job" / "readme.txt").write_text("no yaml")

    ids = list_jobs(tmp_path)
    assert ids == ["nested-demo", "smoke"] or set(ids) == {"nested-demo", "smoke"}
    assert "examples" not in ids
    assert "empty" not in ids
    assert "not-a-job" not in ids

    j = load_job(tmp_path, "nested-demo")
    assert j is not None
    assert j.id == "nested-demo"
    assert j.path == tmp_path / "examples" / "nested-demo"

    # fallback folder name when yaml has no id
    (tmp_path / "fallback-only").mkdir()
    (tmp_path / "fallback-only" / "job.yaml").write_text(
        "image: alpine:3.20\ncommand: [true]\n"
    )
    ids2 = list_jobs(tmp_path)
    assert "fallback-only" in ids2
    assert load_job(tmp_path, "fallback-only") is not None
