# Changelog

All notable changes to GrokBotRemote live here.

The owner designates a release. A release is everything since the last designated release. Catch notes up before production.

## Unreleased

### Changed — 2026-09-10

- Nested jobs catalog: `list_jobs` recursively finds `job.yaml`; stable ids from yaml `id`. `load_job` resolves top-level, `examples/<id>`, relative path, or yaml id (keeps `job_id=agent86-qa-dev` working).
- Moved optional sample `jobs/agent86-qa-dev/` → `jobs/examples/agent86-qa-dev/`. Compose build context updated. Added `docs/user/ADDING_A_JOB.md` and `jobs/examples/README.md` (core product = runner + compose + plugin + smoke; examples are optional).

### Added — 2026-09-10

- Job 1 contract doc `docs/specs/JOB1_AGENT86_QA_DEV.md` (UI_TEST_SPEC v0.8.24 on agent86homeBot `dev`; run vs skip; honest skips; secret names; result counts; first live-run notes).
- Public-ready scrub of tracked docs/compose: no home Tailscale IPs or house hostnames; compose default `${RUNNER_HOST:-127.0.0.1}:${RUNNER_PORT:-8787}:8080`; curl examples `http://127.0.0.1:8787` / `http://YOUR_RUNNER_HOST:8787`.
- AUTH-03 Playwright fix: `page.evaluate` uses a function parameter instead of browser `arguments`.
- Actions runner notes for a generic Linux Docker host (`./run.sh` + `@reboot` without sudo).

### Added

- Optional sample (`agent86-qa-dev`, now under `jobs/examples/`) Playwright suite for UI_TEST_SPEC v0.8.24 (DEV `https://dev.agent86portal.com` only). Result JSON with §6 counts. Secrets `QA_USER` / `QA_PASSWORD` / `QA_USER_ALT` / `QA_PASSWORD_ALT` (names only).
- Deploy workflow on push to `dev` (`pytest` on `ubuntu-latest`; `deploy-dev` on `[self-hosted, example-runner]`). Compose project name `grokbotremote`. Does not `docker compose down`.
- One-time Actions runner install notes (`docs/user/ACTIONS_RUNNER.md`). Label `example-runner` only. Do not reuse labels from other projects.

- Job 0 runner / compose / smoke / plugin / tests on `dev`.
  - Portable runner container (`compose/docker-compose.yml`) published at `${RUNNER_HOST:-127.0.0.1}:${RUNNER_PORT:-8787}:8080` (container 8080 internal). Docker socket + mounted `jobs/` + artifacts volume. `env_file: runner.env` (gitignored).
  - FastAPI runner: `POST /v1/jobs`, `GET /v1/jobs/{run_id}`, `POST /v1/jobs/{run_id}/cancel`, `GET /v1/status`. `X-Runner-Secret` fail-closed (LOCAL_DEV=1 documented; refused on test/prod). One job at a time (409). Result JSON per architecture §6. Webhook retry + GET backfill. `env=prod` rejected unless `RUNNER_ENV=prod`.
  - `jobs/smoke` (hostname, UTC time, git SHA, exit 0, no secrets) and test-only `jobs/timeout-stub`.
  - Thin MCP stdio wrapper (`plugin/`) exposing `runner_status`, `job_list`, `job_run`, `job_get`, `job_cancel`. Config from `RUNNER_URL` + `RUNNER_TOKEN`. No default `runner_url`. Skill: stay in the existing Grok Bot chat; do not create a second bot; title/description as offload status; never paste secrets into an MCP URL.
  - pytest covering R-AUTH-01/02/03, R-SMOKE-01/02/03, R-TIME-01, R-SEC-01/02/03, R-ONE-01, R-NET-01, R-ENV-01 (plus webhook, cancel, plugin static). CI on push to `dev`/`test`/`main` and PRs.
- Architecture spec v0.1.1 (`docs/specs/ARCHITECTURE.md`) — accepted 2026-08-27. Control plane is the user's existing Grok Bot; execution plane is a portable runner container (first host: owner's Linux Docker host; later any Docker host). Typical user adds GrokBotRemote in that same chat via plugin and/or git. Offload status is title/description + connector + chat, not a sidebar badge.
- User guide (`docs/user/README.md`).
- Runner test spec (`docs/specs/RUNNER_TEST_SPEC.md`).
- Plugin test spec (`docs/specs/PLUGIN_TEST_SPEC.md`).
- Specs index (`docs/specs/SPECS_INDEX.md`).

### Changed

- Bind defaults scrubbed for public-ready docs: runner publishes **127.0.0.1:8787** by default; do not publish on a host port already used by another service; avoid host 8080 when something else owns it. User-guide curls use `http://127.0.0.1:8787` or `http://YOUR_RUNNER_HOST:8787`. House public IP stays unpublished.
- Architecture spec v0.1.2 — §5.3 host publish guidance; Job 1 note.
- Runner is a portable container, independent of Hetzner / Amazon / Google. Relocate = same compose on any later Docker host. Never Agent86 app servers.

### Notes

- Private GitHub repo `stevenbowler/GrokBotRemote`. Public only with a later explicit allow. Optional sample `agent86-qa-dev` lives under `jobs/examples/` on `dev`.
