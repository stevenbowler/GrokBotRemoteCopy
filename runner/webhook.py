"""POST result JSON to the control-plane webhook with retry/backoff."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

import httpx

from redact import redact_obj, redact_text

log = logging.getLogger("gbr.webhook")

PostFn = Callable[[str, dict, dict, float], tuple[int, str]]


def _default_post(url: str, headers: dict, body: dict, timeout: float) -> tuple[int, str]:
    with httpx.Client(timeout=timeout) as client:
        r = client.post(url, headers=headers, json=body)
        return r.status_code, r.text[:500]


def send_result(
    url: str,
    key: str,
    result: dict[str, Any],
    *,
    secrets: list[str] | None = None,
    retries: int = 4,
    backoff: float = 0.5,
    post: PostFn | None = None,
    sleeper: Callable[[float], None] = time.sleep,
) -> bool:
    """POST redacted result. Returns True if a 2xx was received.

    Sender key is a header only; it is never added to the JSON body.
    """
    if not url:
        return False
    post = post or _default_post
    payload = redact_obj(result, secrets or [])
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Key": key or "",
    }
    last_status = 0
    attempts = max(1, retries)
    for i in range(attempts):
        try:
            status, _text = post(url, headers, payload, 15.0)
            last_status = status
            if 200 <= status < 300:
                log.info("webhook delivered run_id=%s status=%s", result.get("run_id"), status)
                return True
            log.warning(
                "webhook attempt %s/%s HTTP %s run_id=%s",
                i + 1,
                attempts,
                status,
                result.get("run_id"),
            )
        except Exception as exc:  # noqa: BLE001 — keep going; result is on disk
            log.warning(
                "webhook attempt %s/%s error run_id=%s err=%s",
                i + 1,
                attempts,
                result.get("run_id"),
                redact_text(type(exc).__name__, secrets or []),
            )
        if i + 1 < attempts:
            sleeper(backoff * (2**i))
    log.warning(
        "webhook exhausted retries run_id=%s last_http=%s (result kept for GET backfill)",
        result.get("run_id"),
        last_status,
    )
    return False
