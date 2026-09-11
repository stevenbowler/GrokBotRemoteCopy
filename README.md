# GrokBotRemote

Private repo. Offload heavy or repeating Grok Bot work to a portable runner container.

First host is any Linux Docker host you control (compose defaults to `127.0.0.1:8787`). Later the same compose stack can move to any Docker host. You stay in the Grok Bot chat that already does the work and add GrokBotRemote there. You do not create a second bot.

**Core product** on branch `dev`: runner daemon, compose, plugin wrapper, tests, and Job 0 (`smoke`). **Optional sample:** `agent86-qa-dev` under `jobs/examples/`.

| Path | What |
|---|---|
| [compose/](compose/) | Portable runner stack (`docker compose up`) |
| [runner/](runner/) | FastAPI daemon |
| [jobs/smoke/](jobs/smoke/) | Job 0 — hostname, UTC time, git SHA |
| [jobs/examples/](jobs/examples/) | Optional samples only |
| [jobs/examples/agent86-qa-dev/](jobs/examples/agent86-qa-dev/) | Sample — Playwright UI_TEST_SPEC v0.8.24 on DEV |
| [plugin/](plugin/) | Local stdio MCP wrapper + [SKILL.md](plugin/SKILL.md) |
| [Architecture](docs/specs/ARCHITECTURE.md) | Accepted spec (v0.1.3) |
| [Add a job](docs/user/ADDING_A_JOB.md) | Wire your own functionality on the remote |
| [Sample QA contract](docs/specs/JOB1_AGENT86_QA_DEV.md) | Run/skip groups, secrets names, live-run notes |
| [User guide](docs/user/README.md) | Install, bind, secrets, troubleshooting |
| [Runner tests](docs/specs/RUNNER_TEST_SPEC.md) | Auth, smoke, timeout, webhook |
| [Plugin tests](docs/specs/PLUGIN_TEST_SPEC.md) | Add-in-existing-chat, no second bot |
| [Changelog](CHANGELOG.md) | Unreleased |

Bring-up: see **Step 3** in the [user guide](docs/user/README.md). Default publish is `127.0.0.1:8787` (container 8080). Prefer host port **8787**. Do not publish on a host port already used by another service; avoid host 8080 when something else owns it. Do not publish a house public IP. Actions runner: [docs/user/ACTIONS_RUNNER.md](docs/user/ACTIONS_RUNNER.md). Label `example-runner`.

Branches: `dev` (dev), `test` (test), `main` (prod). Most work happens on `dev`.

Do not make this repository public without the owner's explicit allow for that action. Do not commit secrets. `.env` / `runner.env` are gitignored; keep `!.env.example`.
