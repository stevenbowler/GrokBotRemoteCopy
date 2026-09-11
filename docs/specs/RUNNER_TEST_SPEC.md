# Runner — test spec

**Status:** Draft. No runner implementation yet. Cases are written so a human or a test bot can execute them once `runner/` exists.
**Audience:** pytest (CI on `dev` when present) and human / QA bot on the worker (first: a Docker host the owner controls; later any Docker host).
**Date:** 2026-08-27
**Companion:** `ARCHITECTURE.md` §5.2, §6, §7, §13; Job 0 `smoke`

IDs are stable. Do not reuse an ID for a different assert.

---

## Setup

- Runner in `dev` with `RUNNER_SECRET` set to a non-empty test value.
- Docker available.
- Job `smoke` defined in git.
- Optional: a tiny `jobs/timeout-stub` that sleeps past its timeout (test-only; not a production job).
- Webhook test sink (httptest or the Grok Bot webhook routine on a throwaway routine).

Unless noted, calls include `X-Runner-Secret: $RUNNER_SECRET`.

---

## R-AUTH — fail closed

### R-AUTH-01 missing secret
**Given** runner in test or prod mode (local-dev flag off)
**When** `POST /v1/jobs` with no `X-Runner-Secret`
**Then** 403
**Then** no container starts

### R-AUTH-02 wrong secret
**When** `POST /v1/jobs` with `X-Runner-Secret: not-the-token`
**Then** 403
**Then** no container starts

### R-AUTH-03 empty secret rejected outside local-dev
**Given** `RUNNER_SECRET` is empty and local-dev flag is off
**When** any `POST /v1/jobs`
**Then** 403 (fail closed). Empty secret is not "open to the world"

### R-AUTH-04 local-dev flag documented
**Given** documented local-dev flag on
**Then** the user doc states this must never be used on test/prod
**Then** a test or lint fails the flag on `test`/`main` deploy

---

## R-SMOKE — Job 0

### R-SMOKE-01 pass
**When** `POST /v1/jobs` `{ "job_id": "smoke" }`
**Then** 202 or 200 with a `run_id` (UUID)
**Then** container exits 0
**Then** status becomes `passed`
**Then** result `summary` is a short human line including hostname or git SHA

### R-SMOKE-02 result contract
**Given** R-SMOKE-01
**When** `GET /v1/jobs/{run_id}`
**Then** JSON includes `run_id`, `job_id=smoke`, `git_sha`, `env`, `status`, `started_at`, `finished_at`, `exit_code`, `summary`
**Then** timestamps are ISO-8601 UTC
**Then** no secret values appear anywhere in the body

### R-SMOKE-03 unknown job
**When** `POST /v1/jobs` `{ "job_id": "does-not-exist" }`
**Then** 4xx, no container

---

## R-TIME — timeout

### R-TIME-01 kill past timeout
**Given** a job whose `timeout` is 5s and whose command sleeps 60s
**When** dispatched
**Then** status `timeout`
**Then** the container is not still running 10s after timeout
**Then** webhook (if configured) still fires with `status=timeout`

---

## R-SEC — secrets stay off the record

### R-SEC-01 not in logs
**Given** a job with a secret env `QA_PASSWORD=super-secret-test-value`
**When** it runs (even if it prints env by mistake)
**Then** runner-captured logs either omit that value or redact it
**Then** CI grep for `super-secret-test-value` in runner log files fails the test if found unredacted

### R-SEC-02 not in result JSON
**Given** R-SEC-01
**Then** `GET /v1/jobs/{run_id}` body does not contain `super-secret-test-value`

### R-SEC-03 declared secrets only
**Given** extra env in the host environment `LEAK_ME=1`
**When** `smoke` runs (smoke does not declare `LEAK_ME`)
**Then** the container does not see `LEAK_ME`

---

## R-WH — webhook

### R-WH-01 delivered
**Given** webhook URL and key configured
**When** smoke completes
**Then** sink received POST with the result JSON
**Then** `run_id` matches
**Then** unauthenticated or wrong-key POST from a fake client is rejected by the Grok Bot routine (sender key)

### R-WH-02 retry
**Given** webhook sink returns 500 for the first two attempts
**When** smoke completes
**Then** runner retries with backoff
**Then** a later 200 stops retries
**Then** the same `run_id` is not treated as a new job

### R-WH-03 backfill
**Given** webhook is down for the whole run
**When** `GET /v1/jobs/{run_id}` after completion
**Then** full result is still available
**Then** a later "get run" from the original Grok Bot chat can summarize it

---

## R-CAN — cancel

### R-CAN-01 cancel running
**Given** a long-running job
**When** cancel endpoint or `job_cancel` for that `run_id`
**Then** status `cancelled`
**Then** container stops
**Then** webhook fires with `cancelled` if configured

### R-CAN-02 cancel unknown
**When** cancel a random UUID
**Then** 404, no side effects

---

## R-ONE — one job at a time (v1)

### R-ONE-01 second dispatch
**Given** a job is `running`
**When** another `POST /v1/jobs`
**Then** either 409 or `queued` behind the first
**Then** the running container is not killed to start the second
**Then** v1 docs match whichever behavior is implemented (pick one; default **409**)

---

## R-GIT — pin SHA

### R-GIT-01 requested sha
**When** dispatch includes `git_sha`
**Then** the executed tree is that SHA
**Then** result `git_sha` equals the request

---

## R-NET — isolation

### R-NET-01 no host network by default
**When** smoke runs
**Then** the container is not `network=host`
**Then** a job spec that needs host network is rejected unless that job spec was owner-accepted with that flag

---

## R-ENV — environments

### R-ENV-01 env field
**When** dispatch `env=dev`
**Then** result `env=dev`
**When** `env=prod` on a runner that is not the prod runner
**Then** rejected (do not run prod jobs on the dev VM)

---

## R-MOVE — relocate the container

### R-MOVE-01 same image, new host
**Given** smoke passed on host A (first Docker host)
**When** the same compose file and `runner.env` are started on host B (any Docker host; not Agent86)
**And** the connector `runner_url` points at host B
**Then** R-SMOKE-01 still passes
**Then** no Hetzner / Amazon / Google-specific code path was required

### R-MOVE-02 old host stopped
**Given** R-MOVE-01
**When** compose is down on host A
**Then** `job_run` via the old URL fails (connection error or 403)
**Then** `job_run` via the new URL still works

---

## UI / chat (human or Agent86helperQA)

### UI-R1 From the original bot chat, "run smoke" yields a pass line and `run_id`
### UI-R2 A 403 is explained as a token mismatch, not a generic failure
### UI-R3 After a webhook miss, "get run &lt;id&gt;" still shows the result

---

## Definition of done (runner)

- R-AUTH-01, R-AUTH-02, R-AUTH-03 pass on `dev`
- R-SMOKE-01, R-SMOKE-02 pass on `dev`
- R-TIME-01, R-SEC-01, R-SEC-02, R-WH-01, R-WH-02, R-CAN-01 pass on `dev`
- UI-R1 executed once on the first Docker host `dev` worker
- R-MOVE-01 executed once when relocating (not required for first smoke)
- Automated tests run as part of deploy to `dev` / `test` / `prod` when the stack allows it
