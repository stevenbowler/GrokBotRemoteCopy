"""Runner configuration. Secrets come from env / env_file, never from git."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _truthy(value: str | None) -> bool:
    if not value:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    runner_secret: str = ""
    local_dev: bool = False
    runner_env: str = "dev"
    jobs_dir: Path = Path("jobs")
    artifacts_dir: Path = Path("artifacts")
    repo_dir: Path = Path(".")
    git_sha: str = ""
    webhook_url: str = ""
    webhook_key: str = ""
    webhook_retries: int = 4
    webhook_backoff: float = 0.5
    # Extra secret values for tests (job-declared names only at inject time).
    secrets: dict[str, str] = field(default_factory=dict)
    listen_port: int = 8080

    def validate(self) -> None:
        env = (self.runner_env or "dev").strip().lower()
        if env not in {"dev", "test", "prod"}:
            raise RuntimeError(f"invalid RUNNER_ENV: {self.runner_env!r}")
        self.runner_env = env
        # R-AUTH-04: LOCAL_DEV must never be used on test/prod.
        if self.local_dev and self.runner_env in {"test", "prod"}:
            raise RuntimeError(
                "LOCAL_DEV is forbidden when RUNNER_ENV is test or prod"
            )

    @classmethod
    def from_env(cls) -> "Settings":
        jobs = os.environ.get("JOBS_DIR", "jobs")
        artifacts = os.environ.get("ARTIFACTS_DIR", "artifacts")
        repo = os.environ.get("REPO_DIR", ".")
        s = cls(
            runner_secret=os.environ.get("RUNNER_SECRET", ""),
            local_dev=_truthy(os.environ.get("LOCAL_DEV", "0")),
            runner_env=os.environ.get("RUNNER_ENV", "dev"),
            jobs_dir=Path(jobs),
            artifacts_dir=Path(artifacts),
            repo_dir=Path(repo),
            git_sha=os.environ.get("GIT_SHA", "").strip(),
            webhook_url=os.environ.get("GROKBOT_WEBHOOK_URL", "").strip(),
            webhook_key=os.environ.get("GROKBOT_WEBHOOK_KEY", ""),
            webhook_retries=int(os.environ.get("WEBHOOK_RETRIES", "4")),
            webhook_backoff=float(os.environ.get("WEBHOOK_BACKOFF", "0.5")),
            listen_port=int(os.environ.get("PORT", "8080")),
        )
        s.validate()
        return s


def resolve_git_sha(settings: Settings, requested: str | None = None) -> str:
    """Stamp git_sha from the request, GIT_SHA env, or the mounted tree.

    v1 does not git-fetch a SHA (no deploy key). The mounted checkout is what runs.
    """
    if requested and requested.strip():
        return requested.strip()
    if settings.git_sha:
        return settings.git_sha
    repo = settings.repo_dir
    git_dir = repo / ".git"
    if repo.is_dir() and git_dir.exists():
        import subprocess

        try:
            out = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=str(repo),
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
            sha = out.strip()
            if sha:
                return sha
        except (OSError, subprocess.SubprocessError):
            pass
    return "unknown"
