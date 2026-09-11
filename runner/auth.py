"""X-Runner-Secret fail-closed auth. LOCAL_DEV=1 is localhost-only and documented."""

from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, Request
from typing import Annotated

from settings import Settings


def check_auth(header: str | None, settings: Settings) -> None:
    """Missing/wrong/empty secret → 403 unless LOCAL_DEV=1.

    Empty RUNNER_SECRET with LOCAL_DEV off is not "open to the world".
    """
    if settings.local_dev:
        return
    expected = settings.runner_secret or ""
    if expected == "":
        raise HTTPException(status_code=403, detail="forbidden")
    if not header:
        raise HTTPException(status_code=403, detail="forbidden")
    if not hmac.compare_digest(header, expected):
        raise HTTPException(status_code=403, detail="forbidden")


def require_secret(
    request: Request,
    x_runner_secret: Annotated[str | None, Header()] = None,
) -> None:
    check_auth(x_runner_secret, request.app.state.settings)
