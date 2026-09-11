#!/usr/bin/env python3
"""Job 1 entrypoint. Writes ARCHITECTURE §6 result JSON with counts. Never prints secret values."""

from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

from cases import SUITE
from fixtures import prepare
from helpers import base_url, env_name, redact

OUT = Path(os.environ.get("JOB_RESULT_PATH") or "/out/result.json")


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    secrets = {
        "QA_USER": env_name("QA_USER"),
        "QA_PASSWORD": env_name("QA_PASSWORD"),
        "QA_USER_ALT": env_name("QA_USER_ALT"),
        "QA_PASSWORD_ALT": env_name("QA_PASSWORD_ALT"),
    }
    secret_vals = list(secrets.values())
    files = prepare(Path("/job/generated"))
    ctx = {
        "qa_user": secrets["QA_USER"],
        "qa_password": secrets["QA_PASSWORD"],
        "qa_user_alt": secrets["QA_USER_ALT"],
        "qa_password_alt": secrets["QA_PASSWORD_ALT"],
        "files": files,
        "logged_in": False,
        "auth01_missing": False,
        "has_master": False,
    }
    cases: list[dict] = []
    started = utcnow()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage", "--no-sandbox"],
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            ignore_https_errors=False,
        )
        context.grant_permissions(["clipboard-read", "clipboard-write"])
        page = context.new_page()
        page.set_default_timeout(30000)
        for spec_id, fn in SUITE:
            status = "fail"
            note = ""
            try:
                status, note = fn(page, ctx)
            except Exception as exc:  # noqa: BLE001
                status = "fail"
                note = f"{type(exc).__name__}: {exc}"
                traceback.print_exc()
            note = redact(note, secret_vals)
            cases.append({"id": spec_id, "status": status, "note": note})
            print(f"{spec_id} {status} {note}", flush=True)
        context.close()
        browser.close()

    counts = {"pass": 0, "fail": 0, "skip": 0, "n/a": 0}
    for c in cases:
        key = c["status"] if c["status"] in counts else "fail"
        counts[key] += 1
    failed = counts["fail"]
    summary = (
        f"agent86-qa-dev {base_url()} pass={counts['pass']} fail={counts['fail']} "
        f"skip={counts['skip']} n/a={counts['n/a']}"
    )
    payload = {
        "job_id": "agent86-qa-dev",
        "spec": "UI_TEST_SPEC.md v0.8.24",
        "env": os.environ.get("ENV") or "dev",
        "base_url": base_url(),
        "started_at": started,
        "finished_at": utcnow(),
        "status": "failed" if failed else "passed",
        "summary": summary,
        "counts": counts,
        "cases": cases,
        "run_id": os.environ.get("RUN_ID") or "",
        "git_sha": os.environ.get("GIT_SHA") or "",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    # Also cwd copy for get_archive fallback
    Path("/tmp/result.json").write_text(json.dumps(payload, indent=2) + "\n")
    line = "GROKBOT_RESULT=" + json.dumps(
        {"summary": summary, "counts": counts, "status": payload["status"]},
        separators=(",", ":"),
    )
    print(line, flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
