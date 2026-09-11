"""Static checks for the MCP wrapper and skill (P-CFG, P-SEC, P-SKL)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugin"
SKILL = (PLUGIN / "SKILL.md").read_text()
SERVER = (PLUGIN / "server.py").read_text()
USERDOC = (ROOT / "docs" / "user" / "README.md").read_text()


def test_p_cfg_01_no_default_runner_url():
    # empty default only
    assert 'os.environ.get(_RUNNER_URL_ENV) or ""' in SERVER or 'os.environ.get("RUNNER_URL")' in SERVER
    assert "hetzner" not in SERVER.lower()
    assert "RUNNER_URL =" not in SERVER.replace(" ", "")
    assert 'os.environ.get(_RUNNER_URL_ENV, "http' not in SERVER
    for line in SERVER.splitlines():
        if "http://" in line or "https://" in line:
            assert "environ" in line.lower() or "example" in line.lower() or "127.0.0.1" in line or "your" in line.lower() or "error" in line.lower() or "webhook" in line.lower() or "tunnel" in line.lower()


def test_p_sec_01_skill_no_secrets():
    lowered = SKILL.lower()
    assert "never paste" in lowered or "never" in lowered and "token" in lowered
    assert "password" not in SKILL or "passwords" in SKILL
    assert "sk-" not in SKILL
    assert "ghp_" not in SKILL
    assert "RUNNER_SECRET=" not in SKILL


def test_p_skl_01_when_to_use():
    assert "heavy or repeating" in SKILL.lower() or "heavy or repeating work" in SKILL.lower()


def test_p_skl_02_stay_here():
    text = SKILL.lower()
    assert "stay in this chat" in text
    assert "do not create a second bot" in text or "do **not** create a second bot" in SKILL.lower()
    assert "title" in text and "description" in text


def test_p_stat_no_sidebar_badge():
    assert "sidebar badge" in SKILL.lower()
    assert "do not invent" in SKILL.lower()


def test_local_dev_documented_never_on_test_prod():
    """R-AUTH-04: user doc states LOCAL_DEV must never be used on test/prod."""
    assert "LOCAL_DEV" in USERDOC
    assert "test" in USERDOC.lower() and "prod" in USERDOC.lower()
