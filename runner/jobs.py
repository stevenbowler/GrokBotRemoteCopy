"""Load job definitions from the mounted git checkout (jobs/**/job.yaml)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class JobDef:
    id: str
    image: str
    command: list[str]
    timeout: int = 300
    secrets: list[str] = field(default_factory=list)
    inputs: dict[str, Any] = field(default_factory=dict)
    result: str | None = None
    callback: str = "webhook"
    cpu: str | None = None
    memory: str | None = None
    network_mode: str | None = None
    allow_host_network: bool = False
    test_only: bool = False
    path: Path | None = None


def _as_command(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return ["/bin/sh", "-c", raw]
    if isinstance(raw, list):
        return [str(x) for x in raw]
    raise ValueError("command must be a string or list")


def _iter_job_yaml_paths(jobs_dir: Path) -> list[Path]:
    """Recursively find job.yaml files. Skip dirs that have no job.yaml."""
    if not jobs_dir.is_dir():
        return []
    return sorted(p for p in jobs_dir.rglob("job.yaml") if p.is_file())


def _rel_job_path(yaml_path: Path, jobs_dir: Path) -> str:
    return yaml_path.parent.relative_to(jobs_dir).as_posix()


def _stable_job_id(data: dict[str, Any], yaml_path: Path) -> str:
    """Prefer yaml `id`; fall back to the job folder name (not nested path)."""
    if data.get("id"):
        return str(data["id"])
    return yaml_path.parent.name


def _parse_job(yaml_path: Path, data: dict[str, Any], fallback_id: str) -> JobDef:
    image = data.get("image")
    if not image:
        raise ValueError(f"job {fallback_id} is missing image")
    jid = _stable_job_id(data, yaml_path)
    timeout = int(data.get("timeout") or 300)
    secrets = [str(s) for s in (data.get("secrets") or [])]
    inputs = dict(data.get("inputs") or {})
    network_mode = data.get("network_mode") or data.get("network")
    job_dir = yaml_path.parent
    return JobDef(
        id=jid,
        image=str(image),
        command=_as_command(data.get("command")),
        timeout=timeout,
        secrets=secrets,
        inputs=inputs,
        result=data.get("result"),
        callback=str(data.get("callback") or "webhook"),
        cpu=str(data["cpu"]) if data.get("cpu") is not None else None,
        memory=str(data["memory"]) if data.get("memory") is not None else None,
        network_mode=str(network_mode) if network_mode else None,
        allow_host_network=bool(data.get("allow_host_network", False)),
        test_only=bool(data.get("test_only", False)),
        path=job_dir,
    )


def _load_yaml_dict(yaml_path: Path) -> dict[str, Any] | None:
    raw = yaml.safe_load(yaml_path.read_text()) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"invalid job.yaml at {yaml_path}")
    return raw


def load_job(jobs_dir: Path, job_id: str) -> JobDef | None:
    """Find a job by id or path.

    Match order:
    1. jobs_dir/job_id/job.yaml
    2. jobs_dir/examples/job_id/job.yaml
    3. Any job.yaml whose relative path under jobs_dir equals job_id
       (e.g. examples/agent86-qa-dev)
    4. Any job.yaml whose yaml `id` equals job_id

    Keeps job_id=agent86-qa-dev working after the sample moves under examples/.
    """
    if not jobs_dir.is_dir() or not job_id:
        return None

    direct_candidates = [
        jobs_dir / job_id / "job.yaml",
        jobs_dir / "examples" / job_id / "job.yaml",
    ]
    for yaml_path in direct_candidates:
        if yaml_path.is_file():
            data = _load_yaml_dict(yaml_path)
            assert data is not None
            return _parse_job(yaml_path, data, job_id)

    for yaml_path in _iter_job_yaml_paths(jobs_dir):
        rel = _rel_job_path(yaml_path, jobs_dir)
        data = _load_yaml_dict(yaml_path)
        assert data is not None
        if rel == job_id or _stable_job_id(data, yaml_path) == job_id:
            return _parse_job(yaml_path, data, job_id)
    return None


def list_jobs(jobs_dir: Path) -> list[str]:
    """Recursively catalog jobs that have a job.yaml.

    Returns stable ids from the yaml `id` field (fallback: folder name).
    Does not list container dirs such as `examples` itself (no job.yaml there).
    """
    if not jobs_dir.is_dir():
        return []
    ids: list[str] = []
    seen: set[str] = set()
    for yaml_path in _iter_job_yaml_paths(jobs_dir):
        data = _load_yaml_dict(yaml_path)
        assert data is not None
        jid = _stable_job_id(data, yaml_path)
        if jid in seen:
            continue
        seen.add(jid)
        ids.append(jid)
    return ids


def host_network_requested(job: JobDef) -> bool:
    nm = (job.network_mode or "").strip().lower()
    return nm in {"host", "network=host"}
