"""Run one job at a time in Docker. Capture logs, write result JSON, webhook."""

from __future__ import annotations

import json
import logging
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from jobs import JobDef, host_network_requested, list_jobs, load_job
from redact import redact_obj, redact_text
from settings import Settings, resolve_git_sha
from webhook import send_result

log = logging.getLogger("gbr.engine")

STATUSES = ("queued", "running", "passed", "failed", "error", "timeout", "cancelled")
TERMINAL = frozenset({"passed", "failed", "error", "timeout", "cancelled"})
VALID_ENVS = frozenset({"dev", "test", "prod"})


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class BusyError(Exception):
    pass


class UnknownJobError(Exception):
    pass


class RejectedError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def _parse_field(logs: str, name: str) -> str | None:
    m = re.search(rf"^{name}=(.+)$", logs, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return None


def _normalize_counts(raw: Any) -> dict[str, int] | None:
    if not isinstance(raw, dict):
        return None
    def _i(*keys: str) -> int:
        for k in keys:
            if k in raw and raw[k] is not None:
                try:
                    return int(raw[k])
                except (TypeError, ValueError):
                    return 0
        return 0
    return {
        "pass": _i("pass", "passed"),
        "fail": _i("fail", "failed"),
        "skip": _i("skip", "skipped"),
        "n/a": _i("n/a", "na", "not_applicable"),
    }


def _extract_job_payload(logs: str) -> dict[str, Any] | None:
    """Last GROKBOT_RESULT=<json> line in container logs (ARCHITECTURE §6 extras)."""
    found = None
    for m in re.finditer(r"^GROKBOT_RESULT=(.+)$", logs or "", re.MULTILINE):
        found = m.group(1).strip()
    if not found:
        return None
    try:
        data = json.loads(found)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _read_container_json(container: Any, inner_path: str) -> dict[str, Any] | None:
    getter = getattr(container, "get_archive", None)
    if getter is None:
        return None
    try:
        bits, _stat = getter(inner_path)
    except Exception:  # noqa: BLE001
        return None
    import io
    import tarfile

    buf = io.BytesIO()
    try:
        for chunk in bits:
            buf.write(chunk)
    except Exception:  # noqa: BLE001
        return None
    buf.seek(0)
    try:
        with tarfile.open(fileobj=buf) as tar:
            for member in tar.getmembers():
                if not member.isfile():
                    continue
                name = member.name.rsplit("/", 1)[-1]
                if name != "result.json" and not member.name.endswith("result.json"):
                    # also accept the basename of inner_path
                    if name != Path(inner_path).name:
                        continue
                f = tar.extractfile(member)
                if f is None:
                    continue
                data = json.loads(f.read().decode("utf-8", errors="replace"))
                return data if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001
        return None
    return None


def _summary(job_id: str, status: str, logs: str, git_sha: str, error: str | None) -> str:
    host = _parse_field(logs, "hostname") or "unknown-host"
    short = git_sha[:12] if git_sha and git_sha != "unknown" else git_sha or "?"
    if status == "passed":
        return f"{job_id} passed on {host} sha={short}"
    if status == "timeout":
        return f"{job_id} timed out on {host} sha={short}"
    if status == "cancelled":
        return f"{job_id} cancelled sha={short}"
    if status == "failed":
        return f"{job_id} failed on {host} sha={short}"
    if error:
        return f"{job_id} error: {error}"
    return f"{job_id} {status} sha={short}"


class JobRunner:
    def __init__(
        self,
        settings: Settings,
        docker_client: Any | None = None,
        *,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        webhook_post: Any | None = None,
    ):
        self.settings = settings
        self._docker = docker_client
        self._sleep = sleep
        self._monotonic = monotonic
        self._webhook_post = webhook_post
        self._lock = threading.Lock()
        self._current_id: str | None = None
        self._runs: dict[str, dict[str, Any]] = {}
        self._cancel: dict[str, threading.Event] = {}
        self._containers: dict[str, Any] = {}
        self._docker_kwargs: dict[str, Any] = {}  # last run() kwargs (tests)
        self.settings.artifacts_dir.mkdir(parents=True, exist_ok=True)

    # ----- docker -----
    def docker(self) -> Any:
        if self._docker is not None:
            return self._docker
        import docker  # type: ignore

        self._docker = docker.from_env()
        return self._docker

    def last_docker_kwargs(self) -> dict[str, Any]:
        return dict(self._docker_kwargs)

    # ----- queries -----
    def get(self, run_id: str) -> dict[str, Any] | None:
        run = self._runs.get(run_id)
        if run is None:
            # disk backfill (process restart)
            path = self.settings.artifacts_dir / run_id / "result.json"
            if path.is_file():
                try:
                    run = json.loads(path.read_text())
                    self._runs[run_id] = run
                except json.JSONDecodeError:
                    return None
        if not run:
            return None
        return redact_obj(run, self._secret_values_for(run))

    def catalog(self) -> list[str]:
        return list_jobs(self.settings.jobs_dir)

    def is_busy(self) -> bool:
        with self._lock:
            return self._is_busy_unlocked()

    def _is_busy_unlocked(self) -> bool:
        if not self._current_id:
            return False
        run = self._runs.get(self._current_id)
        if not run:
            return False
        return run.get("status") in {"queued", "running"}

    def _secret_values_for(self, run: dict[str, Any] | None = None) -> list[str]:
        vals = [
            self.settings.runner_secret,
            self.settings.webhook_key,
            *self.settings.secrets.values(),
        ]
        if run:
            vals.extend((run.get("_secret_values") or []))
        return [v for v in vals if v]

    # ----- dispatch -----
    def dispatch(
        self,
        job_id: str,
        *,
        env: str = "dev",
        git_sha: str | None = None,
        inputs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        env = (env or "dev").strip().lower()
        if env not in VALID_ENVS:
            raise RejectedError(f"invalid env: {env}")
        if env == "prod" and self.settings.runner_env != "prod":
            raise RejectedError("prod jobs are not allowed on this runner")

        try:
            job = load_job(self.settings.jobs_dir, job_id)
        except ValueError as exc:
            raise RejectedError(str(exc)) from exc
        if job is None:
            raise UnknownJobError(job_id)

        if host_network_requested(job) and not job.allow_host_network:
            raise RejectedError(
                "host network is not allowed unless the job spec is owner-accepted "
                "with allow_host_network: true"
            )

        sha = resolve_git_sha(self.settings, git_sha)

        with self._lock:
            if self._is_busy_unlocked():
                raise BusyError()
            run_id = str(uuid.uuid4())
            secret_env, secret_vals = self._collect_secrets(job)
            run: dict[str, Any] = {
                "run_id": run_id,
                "job_id": job.id,
                "git_sha": sha,
                "env": env,
                "status": "queued",
                "started_at": None,
                "finished_at": None,
                "exit_code": None,
                "summary": f"{job.id} queued",
                "counts": None,
                "artifact_urls": None,
                "error": None,
                "_secret_values": secret_vals,
                "_secret_env": secret_env,
                "_inputs": dict(job.inputs) | dict(inputs or {}),
            }
            self._runs[run_id] = run
            self._cancel[run_id] = threading.Event()
            self._current_id = run_id
            self._persist(run)

        thread = threading.Thread(
            target=self._execute, args=(run_id, job), daemon=True, name=f"job-{job.id}"
        )
        thread.start()
        return self.get(run_id)  # type: ignore[return-value]

    def cancel(self, run_id: str) -> dict[str, Any] | None:
        run = self._runs.get(run_id)
        if run is None and self.get(run_id) is None:
            return None
        run = self._runs[run_id]
        if run["status"] in TERMINAL:
            return self.get(run_id)
        ev = self._cancel.get(run_id)
        if ev:
            ev.set()
        container = self._containers.get(run_id)
        if container is not None:
            try:
                container.kill()
            except Exception:  # noqa: BLE001
                log.info("cancel kill failed run_id=%s", run_id)
        self._finish(run, status="cancelled", exit_code=None, logs="", error=None)
        return self.get(run_id)

    def _collect_secrets(self, job: JobDef) -> tuple[dict[str, str], list[str]]:
        """Only declared secret *names* are injected. Values from settings/env."""
        import os

        env: dict[str, str] = {}
        vals: list[str] = []
        for name in job.secrets:
            val = self.settings.secrets.get(name)
            if val is None:
                val = os.environ.get(name)
            if val is None:
                raise RejectedError(f"missing declared secret {name}")
            env[name] = val
            vals.append(val)
        for extra in (self.settings.runner_secret, self.settings.webhook_key):
            if extra:
                vals.append(extra)
        return env, vals

    def _execute(self, run_id: str, job: JobDef) -> None:
        run = self._runs[run_id]
        try:
            self._execute_inner(run_id, job, run)
        except Exception as exc:  # noqa: BLE001 — convert to status=error
            log.exception("runner error run_id=%s", run_id)
            self._finish(
                run,
                status="error",
                exit_code=None,
                logs="",
                error=type(exc).__name__,
            )
        finally:
            with self._lock:
                if self._current_id == run_id:
                    self._current_id = None
            self._containers.pop(run_id, None)

    def _execute_inner(self, run_id: str, job: JobDef, run: dict[str, Any]) -> None:
        if self._cancel[run_id].is_set():
            self._finish(run, status="cancelled", exit_code=None, logs="", error=None)
            return

        run["status"] = "running"
        run["started_at"] = utcnow_iso()
        self._persist(run)

        container_env = {
            "GIT_SHA": run["git_sha"],
            "JOB_ID": job.id,
            "RUN_ID": run_id,
            "ENV": run["env"],
        }
        # Non-secret inputs as env (stringified). Do not dump host os.environ.
        for k, v in (run.get("_inputs") or {}).items():
            key = str(k)
            if not key.isidentifier():
                continue
            if key in container_env:
                continue
            container_env[key] = str(v)
        container_env.update(run.get("_secret_env") or {})

        network_mode = "bridge"
        if host_network_requested(job) and job.allow_host_network:
            network_mode = "host"

        kwargs: dict[str, Any] = {
            "image": job.image,
            "command": job.command or None,
            "environment": container_env,
            "network_mode": network_mode,
            "detach": True,
            "stdout": True,
            "stderr": True,
            "name": f"gbr-{run_id[:8]}",
        }
        if job.memory:
            kwargs["mem_limit"] = job.memory
        if job.cpu:
            try:
                kwargs["nano_cpus"] = int(float(job.cpu) * 1_000_000_000)
            except ValueError:
                pass

        self._docker_kwargs = dict(kwargs)

        client = self.docker()
        try:
            container = client.containers.run(**kwargs)
        except Exception as exc:  # noqa: BLE001
            self._finish(
                run,
                status="error",
                exit_code=None,
                logs="",
                error=f"docker: {type(exc).__name__}",
            )
            return

        self._containers[run_id] = container
        status, exit_code, logs = self._wait(run_id, job, container)
        inner_result = job.result or "/out/result.json"
        job_payload = _read_container_json(container, inner_result)
        if job_payload:
            run["_job_payload"] = job_payload
        try:
            raw_logs = container.logs(stdout=True, stderr=True)
            if isinstance(raw_logs, bytes):
                logs = raw_logs.decode("utf-8", errors="replace")
            elif raw_logs:
                logs = str(raw_logs)
        except Exception:  # noqa: BLE001
            pass
        try:
            container.remove(force=True)
        except Exception:  # noqa: BLE001
            pass

        secrets = run.get("_secret_values") or []
        logs = redact_text(logs, secrets)
        self._write_logs(run_id, logs)
        error = None
        if status == "error" and not logs:
            error = "container error"
        self._finish(run, status=status, exit_code=exit_code, logs=logs, error=error)

    def _wait(self, run_id: str, job: JobDef, container: Any) -> tuple[str, int | None, str]:
        deadline = self._monotonic() + max(1, int(job.timeout))
        while True:
            if self._cancel.get(run_id) and self._cancel[run_id].is_set():
                try:
                    container.kill()
                except Exception:  # noqa: BLE001
                    pass
                return "cancelled", None, ""
            try:
                container.reload()
            except Exception:  # noqa: BLE001
                return "error", None, ""
            status = getattr(container, "status", "running")
            if status in {"exited", "dead", "removing", "removed"}:
                try:
                    result = container.wait()
                    code = int(result.get("StatusCode", 1)) if isinstance(result, dict) else 1
                except Exception:  # noqa: BLE001
                    code = 1
                return ("passed" if code == 0 else "failed"), code, ""
            if self._monotonic() >= deadline:
                try:
                    container.kill()
                except Exception:  # noqa: BLE001
                    pass
                return "timeout", None, ""
            self._sleep(0.05)

    def _write_logs(self, run_id: str, logs: str) -> None:
        d = self.settings.artifacts_dir / run_id
        d.mkdir(parents=True, exist_ok=True)
        (d / "logs.txt").write_text(logs)

    def _persist(self, run: dict[str, Any]) -> None:
        d = self.settings.artifacts_dir / run["run_id"]
        d.mkdir(parents=True, exist_ok=True)
        public = self._public(run)
        (d / "result.json").write_text(json.dumps(public, indent=2) + "\n")
        rel = f"artifacts/{run['run_id']}/result.json"
        run["artifact_urls"] = [rel]

    def _public(self, run: dict[str, Any]) -> dict[str, Any]:
        keys = [
            "run_id",
            "job_id",
            "git_sha",
            "env",
            "status",
            "started_at",
            "finished_at",
            "exit_code",
            "summary",
            "counts",
            "artifact_urls",
            "error",
        ]
        obj = {k: run.get(k) for k in keys}
        return redact_obj(obj, self._secret_values_for(run))

    def _finish(
        self,
        run: dict[str, Any],
        *,
        status: str,
        exit_code: int | None,
        logs: str,
        error: str | None,
    ) -> None:
        if run.get("status") in TERMINAL:
            return
        ev = self._cancel.get(run["run_id"])
        if ev and ev.is_set() and status != "cancelled":
            status = "cancelled"
            exit_code = None
        run["status"] = status
        run["exit_code"] = exit_code
        run["finished_at"] = utcnow_iso()
        if not run.get("started_at"):
            run["started_at"] = run["finished_at"]
        err = redact_text(error or "", run.get("_secret_values") or []) or None
        run["error"] = err
        payload = run.get("_job_payload") or _extract_job_payload(logs)
        counts = _normalize_counts((payload or {}).get("counts")) if payload else None
        if counts is not None:
            run["counts"] = counts
        summary = _summary(
            run["job_id"], status, logs, run.get("git_sha") or "", err
        )
        if payload and payload.get("summary"):
            summary = redact_text(str(payload["summary"]), run.get("_secret_values") or []) or summary
        elif counts is not None:
            summary = (
                f"{summary} pass={counts['pass']} fail={counts['fail']} "
                f"skip={counts['skip']} n/a={counts['n/a']}"
            )
        run["summary"] = summary
        if payload:
            try:
                d = self.settings.artifacts_dir / run["run_id"]
                d.mkdir(parents=True, exist_ok=True)
                public_payload = redact_obj(payload, self._secret_values_for(run))
                (d / "job-result.json").write_text(json.dumps(public_payload, indent=2) + "\n")
            except Exception:  # noqa: BLE001
                pass
        self._persist(run)
        # webhook (best-effort; result stays for GET backfill)
        try:
            send_result(
                self.settings.webhook_url,
                self.settings.webhook_key,
                self._public(run),
                secrets=self._secret_values_for(run),
                retries=self.settings.webhook_retries,
                backoff=self.settings.webhook_backoff,
                post=self._webhook_post,
                sleeper=self._sleep,
            )
        except Exception:  # noqa: BLE001
            log.warning("webhook send failed run_id=%s", run.get("run_id"))
