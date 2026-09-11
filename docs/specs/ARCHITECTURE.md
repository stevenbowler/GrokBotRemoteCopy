# GrokBotRemote Architecture Specification

**Status:** Accepted 2026-08-27 (America/Chicago) — notes folded (typical-user journey, offload status, portable container / first Docker host)
**Accepted defaults (§15):** runner is a portable container; first host = a Docker host the owner controls; then the same container can move to any Docker host (Hetzner / Amazon / Google / other are parking spots, not product forks); never Agent86 app servers; public git before marketplace; schedules triggered from this chat; v1 artifacts on disk + SSH; private repo `stevenbowler/GrokBotRemote`
**Version:** 0.1.3
**Date:** 2026-09-10
**Owner:** the repo owner (GitHub: `stevenbowler`)
**User docs:** `docs/user/README.md` (draft 2026-08-27, pending owner acceptance)
**Test specs:** `docs/specs/RUNNER_TEST_SPEC.md`, `docs/specs/PLUGIN_TEST_SPEC.md` (drafts 2026-08-27, pending owner acceptance)

This is the architecture spec for **GrokBotRemote**: a control-plane / execution-plane split so a Grok Bot chat stays the UI, while long or scheduled work runs in a **portable runner container** on a host the owner controls (first: a Docker host the owner controls; later: any Docker host). **Typical user:** they already have a proven Grok Bot doing heavy/repeat work. In *that same chat* they add GrokBotRemote (plugin and/or this git repo) and offload nightly/repeat load. They do not create a second bot. The GrokBotRemote *agent* in the repo owner's account is the product owner (spec, repo, runner), not the typical end-user control plane.

---

## 1. Overview

Grok Bot is a good control plane and a poor place to burn hours of CPU. Nightly UI suites, future batch jobs, and anything that should keep running while this chat sleeps belong on a dedicated worker.

**Control plane (the user's existing Grok Bot):** that same chat, Cursor connectors, plugins, routines, and sibling agents. The human keeps talking to the bot that already does the work. Jobs are prepared, dispatched, and reported *there*.

**Execution plane (there):** a small runner daemon on a host. It pulls a job definition, runs it in isolation (Docker), writes a result JSON, and posts it back. It does not own the conversation.

The first real workload is Agent86helperQA, once the test *scripts* exist. Today that bot still drives the suite itself (Mon/Wed/Fri 11:00pm America/Chicago, DEV only, `https://dev.agent86portal.com`). Offload means: the QA chat and the report stay in Agent86helperQA; the browser/script run moves to the worker.

### 1.1 Typical user journey (primary use case)

Confirmed owner intent 2026-08-27. This is what we are building toward.

1. User already has a regular Grok Bot (or sub-bot) that runs heavy or repeating jobs. That bot is proven.
2. In **that same chat**, they ask to offload nightly/repeat load. Phrasing examples: "add GrokBotRemote", "install the GrokBot Remote connector", "use the GrokBotRemote repo".
3. Two add paths, either is enough:
   - **Plugin / connector:** install from the catalog (once listed) or add the MCP by URL. User pastes `runner_url` + `runner_token` for *their* VM.
   - **Git repo:** clone/install the runner from `stevenbowler/GrokBotRemote` (private until the owner allows public), stand it up on their VM, then point the connector at it.
4. After add, the original bot keeps the conversation. Scheduled routines on that bot dispatch `job_run` instead of doing the heavy work inline. Results come back into that same chat (and whatever mail/report path that bot already uses).
5. They do **not** have to create a new agent named GrokBotRemote. A dedicated product-owner agent is optional (the repo owner's GrokBotRemote agent is that optional maintainer).

Cursor plugins are account-scoped: once installed, every Grok Bot on that Cursor account can see the connector tools. The *skill* tells the original bot when to offload. The human still lives in the original chat.

### 1.2 Offload status (what we can actually show)

There is **no** Grok Bot sidebar badge or traffic-light on an agent row today. Do not invent one. Per-agent UI that exists: name, title, description (info pane / per-agent settings), routines list, connected channels.

v1 status, all on the **original** bot:

| Signal | Where | What |
|---|---|---|
| Title or description | Per-agent settings | e.g. title `QA · remote`, description names the runner and that nightly work is offloaded |
| Connector | Account connectors | GrokBot Remote shows as connected (this is account-wide, not a per-agent badge) |
| Routine | That bot's routines list | Cron still fires *there*; webhook result routine can live there too |
| Chat | That same transcript | "Offloaded `agent86-qa-dev` to remote, `run_id` …" on start; summary on finish |

If Cursor later adds a real per-agent status pill, adopt it. Until then, title/description + chat + connector is the indicator. The skill must remind the original bot to keep title/description accurate when offload is enabled or disabled.

---

## 2. Goals

1. Offload long, scheduled, or CPU-heavy Grok Bot work to a remote host without losing this chat as the UI.
2. Keep Cursor connectors, plugins, and sibling-agent rules on the control plane. They do not "follow" the job onto the VM.
3. The runner is a portable container, independent of Hetzner, Amazon, Google, or any other cloud. First bring-up is a Docker host the owner controls. Moving it later is the same compose stack on a new Docker host, then point `runner_url` at the new place.
4. Ship as open source after private testing. Other Grok Bot users install a plugin and point it at their own runner.
5. Spec-first. No implementation until this spec is accepted. User docs, test specs, and a changelog exist before any deploy. Environments are `dev` / `test` / `prod` (`dev` / `test` / `main` branches).
6. GitHub: private `stevenbowler/GrokBotRemote` first. Public only when the owner explicitly allows that specific action. Grok Bots do not write, push, create, or change a GitHub repo without that permission.

---

## 3. Non-goals (v1)

- Hosting a shared public worker that other users' jobs run on. Each user (or you) runs their own VM.
- Moving Cursor MCP connectors, Grok Bot desktop/browser, or sibling-agent identity onto the VM.
- Replacing Agent86helperQA, Agent86mail, or Agent86 CodeBot. Those stay the QA chat, the mailbox, and the Agent86 spec bot.
- Cloud-specific runners. v1 does not ship a Hetzner runner, an AWS runner, and a GCP runner. One container. Optional later adapters only *provision* a VM; they do not change the runner.
- Kubernetes, autoscaling, or a job marketplace.
- Storing secrets in git, in the public plugin, or in chat transcripts.

---

## 4. Planes — what lives where

```
Owner  →  existing Grok Bot chat (e.g. Agent86helperQA)
              │
              │  GrokBotRemote added here: plugin and/or git repo
              │  Cursor connectors (GitHub, Gmail, …) still on this bot
              │  Grok Bot routines (schedule + webhook) still on this bot
              │  title/description: offload status
              │
              ├── prepare job (ids, env URL, git SHA, secret *names*)
              ├── dispatch via plugin / runner API
              └── receive result webhook → same chat (+ Agent86mail for QA)

Remote host (first: a Docker host the owner controls; later: any Docker host)
              │
              │  runner daemon + Docker
              │  job images / scripts from git
              │  explicit env secrets only
              │  optional xAI Grok API key for *that job*
              │
              └── POST result JSON back to control-plane webhook
```

### 4.1 What stays on the control plane

- The user's existing Grok Bot chat. All human conversation stays there.
- Cursor connectors and plugins already connected here (GitHub, Gmail, later others).
- Grok Bot routines (cron and webhook).
- Sibling agents and their rules. Example: Agent86mail is the exclusive operator of an assigned Gmail account used for reporting. The worker never touches that inbox. Scheduled QA reports still go to the recipient Agent86mail is configured to use. On-demand reports go to the requester, same as today.
- Decisions that need judgment (skip a flaky case, interpret a failure, decide whether to re-run).

### 4.2 What moves to the execution plane

- Deterministic or long-running work: test scripts, browsers, builds, batch transforms.
- Optional LLM calls *inside a job*, using a real xAI API key on the VM. That is not this chat session, not Cursor usage, and not "connectors applying on the server."

### 4.3 Invariant — connectors do not travel

Cursor MCP exists in this environment only. A job on the worker cannot call `user-Github` or `user-Gmail`. If a job needs GitHub or mail, either:

- the control plane does that part before/after the job, or
- the job gets a *narrow* token in its secret set (for example a GitHub Actions-style checkout token, never the owner's full connector).

The phrase "keys, connectors, and plugins still apply" means: **while you talk to GrokBotRemote here, they apply.** The worker is a separate process with an explicit allow-list of env vars.

---

## 5. Components

### 5.1 Job definition (in git)

Jobs are data, not ad-hoc shell. Each job is a directory with `job.yaml` under `jobs/` (top-level `jobs/<job-id>/` or optional samples under `jobs/examples/<job-id>/`). The runner catalogs nested `job.yaml` files by the yaml `id` field:

| Field | Meaning |
|---|---|
| `id` | Stable slug, e.g. `smoke`, `agent86-qa-dev` |
| `image` | Container image, or a Dockerfile in the job folder |
| `command` | Entrypoint inside the container |
| `timeout` | Hard kill after N seconds |
| `secrets` | *Names* of required env vars (values never in git) |
| `inputs` | Non-secret parameters (target URL, git SHA, suite id, env `dev`/`test`/`prod`) |
| `result` | Path of the result JSON the container must write |
| `callback` | `webhook` (required for v1) |
| `cpu` / `memory` | Hints for the provider |

v1 may keep definitions as YAML. The schema is the contract; the file format can change without changing the runner API.

### 5.2 Runner daemon (on the VM)

A small HTTP service on the worker, bound to localhost or a private interface, fronted by SSH tunnel or HTTPS with auth. Responsibilities:

- Accept `POST /v1/jobs` (dispatch) and `GET /v1/jobs/{run_id}` (status).
- Reject missing/wrong shared secret (`X-Runner-Secret`) with HTTP 403.
- Pull the requested git SHA of `stevenbowler/GrokBotRemote` (private: deploy key).
- Run one job in Docker, with only declared secrets injected.
- Enforce timeout, capture logs, write result JSON.
- POST the result to the control-plane webhook. Retry with backoff. Idempotent `run_id`.
- Never print secret values in logs.

One job at a time in v1. Queue later if needed.

### 5.3 Host (the runner is a portable container)

The product is **one runner container** (compose stack). It is not a Hetzner product, an AWS product, or a GCP product. Those names are only places you can park the same container later.

Jobs still run in their own Docker containers inside that stack. The host only needs Linux, Docker, and SSH (or equivalent).

**Gameplan (owner, 2026-08-27):**

1. **Start on the first Docker host** (Linux with Docker). This is Job 0 / bring-up.
2. **Move the same container anywhere** when you want it off the house or on a different box: copy compose + `runner.env` (+ artifact volume if you care), `compose up` on the new host, point the connector `runner_url` at the new place, `compose down` on the old host, run `smoke` again.
3. Never on Agent86 MaxChat app servers. Owner confirmed they do not want that. A runaway QA browser can starve the app.

Relocate is **workflow**, not a rewrite. No per-cloud runner. Optional later *provisioners* (`hcloud`, AWS, GCP) may create a VM for you; they do not change the image you run.

| How you reach the host | v1 | Later |
|---|---|---|
| `ssh` / tailnet / tunnel to an existing Docker host | Yes. This is how v1 actually runs, starting on a Docker host the owner controls. | — |
| `hetzner` / `aws` / `gcp` provisioner | Not required to run. | Optional: create a VM, then run the same compose on it. |

**Host publish guidance:**

Bind the runner on a Linux Docker host you control. Compose default:

`${RUNNER_HOST:-127.0.0.1}:${RUNNER_PORT:-8787}:8080`

Container stays 8080 internally. Prefer host port **8787**. Do **not** publish on a host port already used by another service; avoid host **8080** when something else owns it. For other machines, set `RUNNER_HOST` to a private/tailnet address and use `http://YOUR_RUNNER_HOST:8787`.

GitHub Actions: GrokBotRemote deploy uses self-hosted label `example-runner` only. Do not reuse labels from other projects.

**Reachability notes:**

- Webhook *out* to Grok Bot is fine behind NAT.
- `job_run` *in* must not be published on a house public IP. Default examples use `http://127.0.0.1:8787` or `http://YOUR_RUNNER_HOST:8787` (not host 8080 as the product default).
- Host uptime, power, and ISP are the owner's problem until they relocate.

**Agent86 app servers: no.**

### 5.4 Control-plane plugin (how Grok Bot talks to the runner)

This is both how *this* agent dispatches, and how **other Grok Bot users** get the product.

A Cursor **plugin** is a marketplace bundle of:

1. **Connector (MCP server)** — tools the bot can call:
   - `runner_status` — health, provider, version
   - `job_list` — known job ids from git
   - `job_run` — dispatch (job id, inputs, git SHA)
   - `job_get` — status + result for a `run_id`
   - `job_cancel` — best-effort cancel
2. **Skill** — when to use the runner vs doing the work in-chat; how to map a user ask ("run nightly QA") onto `job_run`; never to paste secrets into the MCP URL.

Install config (per user, stored in their Cursor account, not in git):

| Field | Secret? | Meaning |
|---|---|---|
| `runner_url` | no | Base URL of *their* runner, e.g. `https://runner.example:8443` |
| `runner_token` | yes | Shared secret; sent as `X-Runner-Secret` |

Each Grok Bot user points the plugin at **their** runner. They do not get access to the repo owner's VPS, keys, or Agent86 tenants.

v1 for the owner may use the same MCP as a **local or remote server added directly** (not yet in the public marketplace). Marketplace listing is a later release, after private testing, and only when the owner explicitly allows public distribution.

### 5.5 Result webhook (how the VM talks back)

Grok Bot routines support a webhook trigger. A dedicated GrokBotRemote routine:

- Wakes on `POST` from the runner.
- Verifies the sender key.
- Posts a short summary in this chat (totals, fail ids, log link).
- For Agent86 QA jobs: `SendToAgent` Agent86mail to send the existing email (From its assigned Gmail account, with no personal display name; scheduled To is the recipient Agent86mail is configured to use). The worker does not send mail.

If the webhook is down, the runner keeps the result. The control plane can `job_get` and backfill.

---

## 6. Job run contract

Every run produces one JSON object. Fields:

| Field | Meaning |
|---|---|
| `run_id` | UUID, created at dispatch |
| `job_id` | Job slug |
| `git_sha` | What was executed |
| `env` | `dev` / `test` / `prod` |
| `status` | `queued` / `running` / `passed` / `failed` / `error` / `timeout` / `cancelled` |
| `started_at` / `finished_at` | ISO-8601 UTC |
| `exit_code` | Container exit code |
| `summary` | Short human line for chat |
| `counts` | Optional `{pass, fail, skip, n/a}` |
| `artifact_urls` | Logs, screenshots, traces (object storage or a path the owner can SSH to in v1) |
| `error` | Runner-level error, if any |

Job containers **must not** write secrets into this JSON.

---

## 7. Secrets

| Secret | Where it lives | Who uses it |
|---|---|---|
| `RUNNER_SECRET` | VM env / systemd credential | Runner API + plugin token |
| Webhook sender key | Grok Bot routine panel (owner copies it once) | Runner callback |
| Deploy key or GitHub token (repo read) | VM | `git pull` of job definitions |
| `GROK_API_KEY` (xAI) | VM, only if a job declares it | Job container |
| QA account passwords, target URLs | VM env for that job, or injected at dispatch from control-plane secret store — never in git | QA job |
| Hetzner `hcloud` token | Owner machine / control plane for *provision*, not inside random jobs | Provider |
| Assigned reporting Gmail | Agent86mail only | Never on the worker |

Rules:

- `.env` files are gitignored. Templates list names only (`docs/user` explains how to set them).
- Public plugin ships **zero** credentials. Each user pastes `runner_url` + `runner_token` at install.
- Rotating `RUNNER_SECRET` is a documented ops step. Old token 403s immediately.

---

## 8. Grok / LLM on the worker

Two different Grok paths:

1. **This chat** — Cursor/Grok Bot session. Connectors and plugins apply. Used to plan, dispatch, and explain results.
2. **Job-time xAI API** — `GROK_API_KEY` in the container. Used only when a job truly needs a model on the box (for example classifying a screenshot). Cost, model, and rate limits are the job author's problem and must be in that job's spec.

Default: keep reasoning here; send the worker scripts and browsers.

---

## 9. First jobs

Implementation order after this spec is accepted, user docs + test specs exist, and the private repo is explicitly allowed:

### Job 0 — `smoke` (proves the pipe)

- Container prints hostname, time, and git SHA.
- Exits 0.
- Result webhook lands in this chat within the timeout.
- No Agent86 credentials. No Grok API. No mail.

Done when: the owner can say "run smoke" in the bot that has the connector (Agent86helperQA or this maintainer chat during bring-up) and see a pass line plus a `run_id`.

### Job 1 — `agent86-qa-dev` (optional sample offload)

**Optional sample** under `jobs/examples/agent86-qa-dev/`. Not required for the core product (runner + compose + plugin + `smoke`). Spec: `docs/specs/UI_TEST_SPEC.md` on `stevenbowler/agent86homeBot` branch `dev` (Active v0.8.24). This sample **reads** that spec; it does not author Agent86 product specs. Put your own jobs in `jobs/<id>/` (see `docs/user/ADDING_A_JOB.md`).

- Same target as Agent86helperQA: DEV only, `https://dev.agent86portal.com`. Do not open test or prod unless a later job says so.
- Run: AUTH-01–04, CHAT-01–04, FILE-01–06, PROJ-01–07, SKILL-01–06, TRIG-01–02, TODO-01–03, CHART-01, MEM-01–02, NAV-01–03, MASTER-01–06 (skip MASTER if no Master menu).
- Skip: CHAT-05, BILLING-01–04, WhatsApp/Telegram/SMS, inbound email, mobile. If a case cannot be automated yet, mark **skip** with the spec id — never fake a pass.
- Login: `QA_USER` / `QA_PASSWORD` first; if the account is missing, Fail AUTH-01 and continue with `QA_USER_ALT` / `QA_PASSWORD_ALT`. Do not sign up. Values never in git.
- Result JSON per §6 with `counts` `{pass, fail, skip, n/a}`. Timeout 45–90 minutes. Image includes browsers.
- Unique `run_id`. Artifacts on disk; summary in the original chat; email via Agent86mail, not the worker.

Schedule: keep the existing Agent86helperQA cron as the *trigger* (Mon/Wed/Fri 11:00pm America/Chicago). After the plugin is added in that chat, the routine calls `job_run agent86-qa-dev` itself instead of driving the browser. The owner still sees the wake in the QA chat. GrokBotRemote (this maintainer agent) is not in the nightly path.

TEST and PROD suites are later jobs, each with their own id and explicit owner allow.

---

## 10. Repo, environments, delivery

Repo: **private** [`stevenbowler/GrokBotRemote`](https://github.com/stevenbowler/GrokBotRemote). Created 2026-08-27 at owner request. Remain private until the owner explicitly allows making it public.

| Branch | Environment |
|---|---|
| `dev` | dev runner (or a dev namespace on the same VM) |
| `test` | test runner |
| `main` | production runner |

Most coding and testing happens on `dev`. Automated tests run on deploy to every environment when the stack allows it. Changelog always. Owner designates a release; write notes; promote to test (notes may be mandatory); then to prod. Iteration builds may land on test without notes; catch notes up before prod.

Layout (target, not created until implementation):

```
docs/specs/ARCHITECTURE.md     this file
docs/specs/RUNNER_TEST_SPEC.md
docs/specs/PLUGIN_TEST_SPEC.md
docs/specs/JOB1_AGENT86_QA_DEV.md
docs/user/                     install, secrets, troubleshooting, ADDING_A_JOB.md
jobs/smoke/                    Job 0 — core pipe proof
jobs/timeout-stub/             test-only
jobs/examples/                 optional samples only
jobs/examples/agent86-qa-dev/  sample Playwright suite (UI_TEST_SPEC v0.8.24)
runner/                        daemon
plugin/                        MCP server + skill bundle
compose/                       runner + jobs (portable; any Docker host)
providers/                      optional later VM provisioners (not required to run)
CHANGELOG.md
```

---

## 11. Plugin and git — how a typical user adds it

Primary path is §1.1: stay in the proven bot, add GrokBotRemote there. Marketplace listing is not a v1 blocker; git + add-connector is enough.

### 11.1 Two add paths (same chat)

In the original bot, the user can:

1. **Ask to add the plugin / connector** — catalog install once listed, or add MCP by URL. Confirm, then paste `runner_url` + `runner_token`.
2. **Reference this git repo** — use `stevenbowler/GrokBotRemote` to stand up the runner on their VM, then do (1) so the original bot can talk to it.

Either path ends the same: original bot gains `job_run` / `job_get` / … and starts offloading. Asking "add GrokBotRemote" in that chat should be treated as this flow, not as "create another agent."

### 11.2 What they install

A Cursor plugin named something like **GrokBot Remote** (final marketplace name is owner-designated before listing):

- Connector: the runner MCP in §5.4.
- Skill: "use this when this Grok Bot already runs heavy or repeating work and the user wants that work offloaded to their remote CPU. Stay in this chat. Install/configure the connector. Update this agent's title/description as the offload status. Do not tell the user to create a second bot."

To the user we say **connector**. "Plugin" / "MCP" stay plumbing except when they are installing from the catalog.

### 11.2 What they must already have

1. A VM they control (Hetzner, AWS, GCP, or any SSH box).
2. The open-source runner installed on it (from this repo, once public).
3. `runner_url` + `runner_token` from that install.

They never receive the repo owner's tokens, QA passwords, or Agent86 access.

### 11.3 Phased distribution

| Phase | Visibility | Condition |
|---|---|---|
| A | Private git + owner-only MCP | This spec accepted; owner allows private repo; smoke job green |
| B | Private repo, runner usable by owner's other Grok Bots (same Cursor account) | Plugin install config documented |
| C | Public git (open source) | Owner explicitly allows making the repo public; secrets audit clean |
| D | Cursor marketplace plugin | Owner explicitly allows listing; PLUGIN_TEST_SPEC passing; docs a stranger can follow |

Phase D is optional. Open-source git (C) is enough for a technical user to `AddMcpServer` with the runner URL. Marketplace is convenience.

### 11.4 What the plugin must not do

- Embed a default `runner_url` that points at the owner's VM.
- Proxy other users' jobs through the owner's Hetzner.
- Request the user's Cursor GitHub/Gmail connectors and forward those tokens to the VM.
- Run the runner "on Grok Bot's computer" as a substitute for a real VM (the shared box is the wrong security and capacity boundary). A *dev* mode that talks to localhost is allowed for plugin authors only, documented as such.

### 11.5 Local vs remote MCP

Two valid connector shapes (Cursor supports both):

- **Remote HTTP MCP** — runner exposes MCP-over-HTTP, or a thin proxy does. Best for production: the user's Grok Bot talks to their VM.
- **Local command MCP** — `npx`/`uvx` client that holds `runner_url` + token and calls the REST API in §5.2. Best for v1: one REST runner, one small MCP wrapper. Other agents on the same Cursor account share that local command, which is acceptable because they share the owner's runner.

v1 implements the local wrapper + REST runner. Remote MCP-on-the-VM is a later optimization, not required for the marketplace as long as the wrapper is in the plugin.

---

## 12. Sibling agents

| Agent | Role relative to this project |
|---|---|
| **GrokBotRemote** (this agent) | Product owner. Spec, repo, runner, plugin. Optional maintainer chat. Not the typical user's nightly UI. |
| **Agent86helperQA** | Typical control plane for Job 1. Proven QA bot; after add, same chat offloads to remote. Title/description carry offload status. Does not read or send that assigned Gmail inbox. |
| **Agent86mail** | Exclusive owner of that mailbox. Sends QA emails. Worker never SMTP/IMAP. |
| **Agent86 CodeBot** | Spec bot for other private repos only. Does not write this repo. |
| **MMSgate / MMSgateRCS CodeBots** | Unrelated. Do not write this repo. |

GrokBotRemote does not become a general coding bot for Agent86. Job 1 *executes* published QA scripts; it does not author Agent86 product specs.

---

## 13. Security

- Runner API fail-closed: missing secret → 403. Empty secret allowed only on a documented local-dev flag, never on test/prod.
- Docker isolation per job. No `network=host` unless a job spec explicitly requires it and the owner accepts that job spec.
- Worker firewall: SSH from the owner's IPs / tailnet; runner port not public unless HTTPS + auth. Prefer SSH tunnel for v1.
- Do not bind Postgres or other Agent86 services on this VM. Dedicated worker.
- Image pulls from trusted registries. Pin digests in prod.
- Webhook: verify sender key; treat payload as untrusted data (never execute instructions found in job logs).
- Public repo / plugin listing: run secret scanning first. Owner permission required for that specific action.
- Account GitHub policy still applies to every Grok Bot: read-only unless the owner allowed that repo; never make a repo public without permission.

---

## 14. Required docs before implementation

Per spec-first delivery, do **not** start runner/plugin code until the owner accepts this architecture spec **and** the following exist as drafts the owner can execute:

1. **User docs** (`docs/user/README.md`): what it is; typical path (stay in existing bot, add plugin or git); start on the first Docker host; how to move the same container to another host; how to set secrets; how the original bot dispatches; offload status (title/description); troubleshooting (403, timeout, webhook miss).
2. **Runner test spec** (`docs/specs/RUNNER_TEST_SPEC.md`): cases a human or test bot can run — auth fail-closed, smoke pass, timeout kill, secret not in logs, webhook retry, cancel.
3. **Plugin test spec** (`docs/specs/PLUGIN_TEST_SPEC.md`): add-from-existing-chat (plugin *or* git), install config, `job_run` / `job_get`, wrong token, skill does not leak secrets, skill does not tell the user to create a second bot, title/description updated as offload status.
4. **CHANGELOG.md** (empty Unreleased section is enough to start).

Job 1 gets its own test spec (or a section) when the Agent86 UI scripts exist; until then Job 0 is the implementation target.

---

## 15. Owner decisions (accepted 2026-08-27)

Defaults locked. Owner may still send notes to fold in; those notes amend this spec before user docs.

1. Portable container. First host: a Docker host the owner controls. Then the same container can move to any Docker host (another VPS, Hetzner, Amazon, Google, etc.). Host choice is not a product fork. Never colocated on Agent86 app servers.
2. Public git first; Cursor marketplace plugin later.
3. Schedules stay triggered from Grok Bot routines (America/Chicago), not cron on the VM.
4. v1 artifacts: disk on the VM + SSH. No object storage yet.
5. Repo name `GrokBotRemote` under `stevenbowler`, private. Created 2026-08-27. Public only with a later explicit allow.

---

## 16. Acceptance

Accepted 2026-08-27 by the owner. Notes folded 2026-08-27: typical user stays in the proven bot and adds GrokBotRemote there (plugin and/or git); offload status is title/description + connector + chat, not a sidebar badge. Runner is a portable container: start on the first Docker host, then move the same stack anywhere (Hetzner / Amazon / Google / other are parking spots). Never Agent86 app servers. More notes still welcome. User docs and test specs are drafted and on this repo for review. Product code waits until those drafts are accepted, then Job 0 (`smoke`) on `dev` only (first Docker host).

Next steps in order:

1. Owner reviews/accepts user docs + test specs on GitHub.
2. Implement Job 0 (`smoke`) on `dev` only, first Docker host.
3. Promote per §10. Job 1 waits on published Agent86 test scripts.

Implementation that starts before step 2 is out of spec.
