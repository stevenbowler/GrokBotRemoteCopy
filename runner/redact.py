"""Redact secret values from logs and result JSON. Never print secret values."""

from __future__ import annotations

import json
from typing import Any, Iterable

PLACEHOLDER = "***"


def secret_values(values: Iterable[str | None]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for v in values:
        if not v:
            continue
        if len(v) < 4:
            continue
        if v not in seen:
            seen.add(v)
            out.append(v)
    # Longer first so overlapping values redact fully.
    out.sort(key=len, reverse=True)
    return out


def redact_text(text: str, secrets: Iterable[str | None]) -> str:
    if not text:
        return text
    out = text
    for v in secret_values(secrets):
        out = out.replace(v, PLACEHOLDER)
    return out


def redact_obj(obj: Any, secrets: Iterable[str | None]) -> Any:
    blob = json.dumps(obj, default=str)
    blob = redact_text(blob, secrets)
    return json.loads(blob)
