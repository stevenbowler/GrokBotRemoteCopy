# Example — `agent86-qa-dev`

**Optional sample** under `jobs/examples/`. Not part of the core product (runner + compose + plugin + `smoke`).

Playwright suite for `docs/specs/UI_TEST_SPEC.md` (Active v0.8.24) on
`stevenbowler/agent86homeBot` branch `dev`.

Contract detail: [`docs/specs/JOB1_AGENT86_QA_DEV.md`](../../../docs/specs/JOB1_AGENT86_QA_DEV.md).

How to add your own job: [`docs/user/ADDING_A_JOB.md`](../../../docs/user/ADDING_A_JOB.md).

- Job id: `agent86-qa-dev` (stable; `job_run agent86-qa-dev` still works from this nested path)
- Path: `jobs/examples/agent86-qa-dev/`
- URL: `https://dev.agent86portal.com` only
- Secrets (names only): `QA_USER`, `QA_PASSWORD`, `QA_USER_ALT`, `QA_PASSWORD_ALT`
- Login primary first; if the account is missing, Fail AUTH-01 and continue on the alt account
- Do not sign up
- Skip: CHAT-05, BILLING-01–04, WhatsApp/Telegram/SMS, inbound email, mobile
- Skip MASTER-01–06 when the Master menu is absent
- Result JSON: `/out/result.json` plus `GROKBOT_RESULT=` on stdout (ARCHITECTURE §6 counts)

Image: `grokbotremote-agent86-qa-dev:dev` (compose profile `qa-image`, build context `../jobs/examples/agent86-qa-dev`).
