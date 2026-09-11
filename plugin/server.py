#!/usr/bin/env python3
"""GrokBot Remote — local stdio MCP wrapper around the runner REST API.

Config from the environment (required, no defaults that point at anyone's VM):

  RUNNER_URL    Base URL of *your* runner, e.g. http://127.0.0.1:8080
  RUNNER_TOKEN  Shared secret; sent as X-Runner-Secret

There is NO default runner_url. Do not paste the token into an MCP URL.
"""

from __future__ import annotations

import os
import sys
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

# Intentionally empty default — never ship a URL that points at the repo owner's host.
_RUNNER_URL_ENV = "RUNNER_URL"
_RUNNER_TOKEN_ENV = "RUNNER_TOKEN"


def _base_url() -> str:
    url = (os.environ.get(_RUNNER_URL_ENV) or "").strip()
    if not url:
        raise RuntimeError(
            "RUNNER_URL is required. There is no default. "
            "Point it at YOUR runner (SSH tunnel or tailnet), not someone else's."
        )
    return url.rstrip("/")


def _headers() -> dict[str, str]:
    token = os.environ.get(_RUNNER_TOKEN_ENV) or ""
    return {"X-Runner-Secret": token, "Content-Type": "application/json"}


def _request(method: str, path: str, json_body: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{_base_url()}{path}"
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.request(method, url, headers=_headers(), json=json_body)
    except httpx.RequestError as exc:
        return {"ok": False, "error": f"runner unreachable: {type(exc).__name__}"}
    if r.status_code == 403:
        return {
            "ok": False,
            "status": 403,
            "error": "token mismatch (403). Check runner_token vs RUNNER_SECRET. Job did not run.",
        }
    if r.status_code == 409:
        return {"ok": False, "status": 409, "error": "runner busy (one job at a time)", "body": _safe_json(r)}
    if r.status_code >= 400:
        return {"ok": False, "status": r.status_code, "error": "runner error", "body": _safe_json(r)}
    body = _safe_json(r)
    if isinstance(body, dict):
        body.setdefault("ok", True)
        return body
    return {"ok": True, "body": body}


def _safe_json(r: httpx.Response) -> Any:
    try:
        return r.json()
    except Exception:  # noqa: BLE001
        return {"text": r.text[:500]}


mcp = FastMCP("GrokBot Remote")


@mcp.tool()
def runner_status() -> dict[str, Any]:
    """Health of the remote runner (up/down, env, busy). Does not dump secrets."""
    return _request("GET", "/v1/status")


@mcp.tool()
def job_list() -> dict[str, Any]:
    """Known job ids from the mounted git checkout on the runner."""
    return _request("GET", "/v1/catalog")


@mcp.tool()
def job_run(
    job_id: str,
    env: str = "dev",
    git_sha: str | None = None,
    inputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Dispatch a job to the remote runner. Stay in this chat with the run_id."""
    body: dict[str, Any] = {"job_id": job_id, "env": env}
    if git_sha:
        body["git_sha"] = git_sha
    if inputs:
        body["inputs"] = inputs
    return _request("POST", "/v1/jobs", json_body=body)


@mcp.tool()
def job_get(run_id: str) -> dict[str, Any]:
    """Status + result for a run_id (backfill if the webhook missed)."""
    return _request("GET", f"/v1/jobs/{run_id}")


@mcp.tool()
def job_cancel(run_id: str) -> dict[str, Any]:
    """Best-effort cancel of a running job."""
    return _request("POST", f"/v1/jobs/{run_id}/cancel")


def main() -> None:
    if not (os.environ.get(_RUNNER_URL_ENV) or "").strip():
        print(
            "GrokBot Remote MCP: RUNNER_URL is not set. Tools will error until it is. "
            "There is no default URL.",
            file=sys.stderr,
        )
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
