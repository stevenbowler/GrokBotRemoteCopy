# Job 1 — Agent86 DEV QA contract

**Status:** Active on branch `dev`  
**Job id:** `agent86-qa-dev`  
**Spec map:** UI_TEST_SPEC **v0.8.24** on `stevenbowler/agent86homeBot` branch `dev`  
**Target URL:** `https://dev.agent86portal.com` only (do not open test/prod unless a later job says so)  
**Date:** 2026-09-10

This is the execution contract for the **optional sample** Playwright suite in `jobs/examples/agent86-qa-dev/`. Job id remains `agent86-qa-dev`. It **reads** the Agent86 UI spec; it does not author Agent86 product specs. Core product = runner + compose + plugin + `smoke`.

## Secrets (names only)

Values never in git. Declared in `jobs/examples/agent86-qa-dev/job.yaml` and `compose/runner.env.example`:

| Name | Role |
|---|---|
| `QA_USER` | Primary login email |
| `QA_PASSWORD` | Primary bypass OTP code |
| `QA_USER_ALT` | Fallback login if primary account is missing |
| `QA_PASSWORD_ALT` | Fallback bypass OTP code |

Rules: try primary first. If the account is missing, **Fail AUTH-01** and continue on alt. **Do not sign up.**

## Run vs skip groups

### Run (automate honestly)

- AUTH-01–04  
- CHAT-01–04  
- FILE-01–06  
- PROJ-01–07  
- SKILL-01–06  
- TRIG-01–02  
- TODO-01–03  
- CHART-01  
- MEM-01–02  
- NAV-01–03  
- MASTER-01–06 (**skip** the MASTER group when the Master menu is absent)

### Skip (requested / out of scope)

- CHAT-05  
- BILLING-01–04  
- WhatsApp / Telegram / SMS  
- Inbound email  
- Mobile  

If a case cannot be automated yet, mark **skip** with the spec id — **never fake a pass**.

## Result counts

Suite writes `/out/result.json` and prints `GROKBOT_RESULT=` on stdout. Counts follow ARCHITECTURE §6:

`{ "pass", "fail", "skip", "n/a" }`

Runner merges those counts into the job result JSON.

## First live run notes (2026-09-10)

Observed totals: **31 pass / 6 fail / 12 skip**.

Notable outcomes from that run:

| Case | Note |
|---|---|
| AUTH-01 | Primary account missing (fail as designed; suite continued on alt) |
| AUTH-03 | Failed with Page.evaluate `arguments is not defined` — fixed in tree (Playwright-safe evaluate with a function parameter) |
| CHAT-02 | History assertion failed |
| TRIG-01 | Failed |
| AUTH-04 | Logout failed |
| MEM-02 | Blocked by AUTH-04 (depends on logout path) |
| FILE-02 | **Passed** via drag/drop path in that run |

Re-run after the AUTH-03 fix before treating remaining fails as product bugs.
