"""Fake Docker client for unit tests. Captures run() kwargs; no real daemon."""

from __future__ import annotations

import threading
from typing import Any


class FakeContainer:
    def __init__(
        self,
        *,
        logs: bytes | None = None,
        exit_code: int = 0,
        hold: threading.Event | None = None,
        never_finish: bool = False,
        leak_env: bool = False,
        kwargs: dict[str, Any] | None = None,
    ):
        self.status = "running"
        self.killed = False
        self.removed = False
        self.exit_code = exit_code
        self._hold = hold
        self._never_finish = never_finish
        self._leak_env = leak_env
        self.kwargs = kwargs or {}
        self._logs = logs

    def reload(self) -> None:
        if self.killed:
            self.status = "exited"
            return
        if self._never_finish:
            self.status = "running"
            return
        if self._hold is not None and not self._hold.is_set():
            self.status = "running"
            return
        self.status = "exited"

    def wait(self, timeout: float | None = None) -> dict[str, int]:
        return {"StatusCode": 137 if self.killed and self.exit_code == 0 else self.exit_code}

    def kill(self) -> None:
        self.killed = True
        self.status = "exited"
        if self._hold is not None:
            self._hold.set()

    def logs(self, stdout: bool = True, stderr: bool = True) -> bytes:
        if self._logs is not None:
            return self._logs
        env = self.kwargs.get("environment") or {}
        if self._leak_env:
            # Simulate a job that prints env (R-SEC-01). Runner must redact.
            lines = [f"{k}={v}" for k, v in env.items()]
            return ("\n".join(lines) + "\n").encode()
        sha = env.get("GIT_SHA", "unknown")
        return (
            f"hostname=testhost\n"
            f"time=2026-08-27T16:35:00Z\n"
            f"git_sha={sha}\n"
        ).encode()

    def remove(self, force: bool = False) -> None:
        self.removed = True
        self.status = "removed"


class FakeContainers:
    def __init__(self, client: "FakeDocker"):
        self._client = client

    def run(self, image: str, command=None, **kwargs: Any) -> FakeContainer:
        kwargs = dict(kwargs)
        kwargs["image"] = image
        kwargs["command"] = command
        self._client.calls.append(kwargs)
        self._client.last_kwargs = kwargs
        c = FakeContainer(
            logs=self._client.forced_logs,
            exit_code=self._client.exit_code,
            hold=self._client.hold,
            never_finish=self._client.never_finish,
            leak_env=self._client.leak_env,
            kwargs=kwargs,
        )
        self._client.containers_started.append(c)
        return c


class FakeDocker:
    def __init__(self) -> None:
        self.containers = FakeContainers(self)
        self.calls: list[dict[str, Any]] = []
        self.last_kwargs: dict[str, Any] = {}
        self.containers_started: list[FakeContainer] = []
        self.hold: threading.Event | None = None
        self.never_finish = False
        self.exit_code = 0
        self.forced_logs: bytes | None = None
        self.leak_env = False

    def ping(self) -> bool:
        return True
