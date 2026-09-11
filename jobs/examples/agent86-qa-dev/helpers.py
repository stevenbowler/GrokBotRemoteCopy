"""Playwright helpers for MaxChat DEV. Never log secret values."""

from __future__ import annotations

import os
import re
from typing import Any

from playwright.sync_api import Page, TimeoutError as PWTimeout

ACCOUNT_MISSING = re.compile(
    r"sign up instead|no active account|account not found",
    re.I,
)


def env_name(name: str) -> str:
    val = (os.environ.get(name) or "").strip()
    if not val:
        raise RuntimeError(f"missing declared secret {name}")
    return val


def base_url() -> str:
    return (os.environ.get("BASE_URL") or "https://dev.agent86portal.com").rstrip("/")


def redact(text: str, secrets: list[str]) -> str:
    out = text or ""
    for s in secrets:
        if s:
            out = out.replace(s, "[redacted]")
    return out


def page_error_text(page: Page) -> str:
    loc = page.locator(".error, #error-msg, [class*='error']").first
    try:
        if loc.count() and loc.is_visible(timeout=500):
            return loc.inner_text(timeout=500)
    except Exception:
        pass
    return page.locator("body").inner_text()[:800]


def goto_login(page: Page) -> None:
    page.goto(f"{base_url()}/login", wait_until="domcontentloaded")
    page.wait_for_selector("#email", timeout=30000)


def send_code(page: Page, email: str) -> None:
    page.fill("#email", email)
    page.click("#submit-btn")


def account_missing(page: Page) -> bool:
    try:
        page.wait_for_timeout(800)
        body = page.locator("body").inner_text()
        if ACCOUNT_MISSING.search(body):
            return True
        if page.locator("#code").count() == 0 and "/login" in (page.url or ""):
            if ACCOUNT_MISSING.search(body):
                return True
    except Exception:
        return False
    return False


def verify_code(page: Page, code: str) -> None:
    page.wait_for_selector("#code", timeout=30000)
    page.fill("#code", code)
    page.click("#submit-btn")


def wait_authenticated(page: Page, timeout_ms: int = 45000) -> bool:
    try:
        page.wait_for_url(re.compile(r"/maxchat|/chat|/app"), timeout=timeout_ms)
        return True
    except PWTimeout:
        pass
    for sel in (
        "textarea[placeholder*='Message Max']",
        "text=My MaxChat",
        ".badge-label",
    ):
        try:
            page.wait_for_selector(sel, timeout=5000)
            return True
        except PWTimeout:
            continue
    if "/signup" in (page.url or ""):
        return False
    return "login" not in (page.url or "").lower()


def login(page: Page, email: str, code: str) -> dict[str, Any]:
    """UI login. Never clicks Sign up. Returns ok / missing / error."""
    goto_login(page)
    send_code(page, email)
    page.wait_for_timeout(1200)
    if account_missing(page):
        return {"ok": False, "missing": True, "error": "account missing (did not sign up)"}
    try:
        verify_code(page, code)
    except PWTimeout:
        if account_missing(page):
            return {"ok": False, "missing": True, "error": "account missing (did not sign up)"}
        return {"ok": False, "missing": False, "error": "code field never appeared"}
    if wait_authenticated(page):
        return {"ok": True, "missing": False, "error": ""}
    err = page_error_text(page)
    if ACCOUNT_MISSING.search(err):
        return {"ok": False, "missing": True, "error": "account missing (did not sign up)"}
    return {"ok": False, "missing": False, "error": redact(err, [email, code])[:400]}


def composer(page: Page):
    loc = page.locator("textarea[placeholder*='Message Max'], textarea[placeholder*='Add a message']")
    loc.first.wait_for(timeout=30000)
    return loc.first


def open_my_maxchat(page: Page) -> None:
    for label in ("My MaxChat", "MaxChat"):
        loc = page.get_by_text(label, exact=True)
        if loc.count():
            try:
                loc.first.click(timeout=5000)
                break
            except Exception:
                pass
    composer(page)


def send_chat(page: Page, text: str) -> None:
    box = composer(page)
    box.click()
    box.fill(text)
    box.press("Enter")


def wait_reply_contains(page: Page, needle: str, timeout_ms: int = 90000) -> str:
    deadline_sel = page.locator("body")
    page.wait_for_function(
        """(n) => document.body && document.body.innerText.toLowerCase().includes(String(n).toLowerCase())""",
        arg=needle,
        timeout=timeout_ms,
    )
    return deadline_sel.inner_text()


def last_thread_text(page: Page) -> str:
    return page.locator("body").inner_text()


def click_text(page: Page, label: str, timeout_ms: int = 8000) -> bool:
    loc = page.get_by_text(label, exact=False)
    try:
        loc.first.click(timeout=timeout_ms)
        return True
    except Exception:
        return False


def open_badge(page: Page, label: str) -> bool:
    btn = page.locator(".status-dot-btn, button").filter(has_text=label)
    try:
        btn.first.click(timeout=8000)
        return True
    except Exception:
        return click_text(page, label)


def attach_via_file_input(page: Page, paths: list[str]) -> bool:
    file_inputs = page.locator("input[type=file]")
    try:
        if file_inputs.count() == 0:
            plus = page.locator("button").filter(has_text=re.compile(r"^\+|Attach|Upload"))
            if plus.count():
                plus.first.click(timeout=5000)
        file_inputs = page.locator("input[type=file]")
        if file_inputs.count() == 0:
            return False
        file_inputs.first.set_input_files(paths)
        return True
    except Exception:
        return False


def has_master_menu(page: Page) -> bool:
    # Open account menu if needed
    body = page.locator("body").inner_text()
    if re.search(r"\bMaster\b", body):
        return True
    for label in ("Demo User", "QA Tester", "Profile", "Log out", "Logout"):
        loc = page.get_by_text(label, exact=False)
        if loc.count():
            try:
                loc.first.click(timeout=2000)
            except Exception:
                pass
    body = page.locator("body").inner_text()
    return bool(re.search(r"\bMaster\b", body))


def logout(page: Page) -> bool:
    for label in ("Log out", "Logout", "Sign out"):
        if click_text(page, label, 4000):
            page.wait_for_timeout(1500)
            return "login" in (page.url or "").lower() or page.locator("#email").count() > 0
    # try avatar / account name
    for label in ("Demo User", "QA Tester", "Profile"):
        click_text(page, label, 2000)
    for label in ("Log out", "Logout"):
        if click_text(page, label, 4000):
            page.wait_for_timeout(1500)
            return "login" in (page.url or "").lower() or page.locator("#email").count() > 0
    return False
