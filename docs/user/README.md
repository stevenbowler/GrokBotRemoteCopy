# GrokBotRemote — user guide

**Status:** Core product (runner + compose + plugin + `smoke`) is on branch `dev`. Optional sample: `agent86-qa-dev` under `jobs/examples/`. Follow Step 3 to compose up on your **Linux Docker host**. Actions runner: [ACTIONS_RUNNER.md](ACTIONS_RUNNER.md). Add your own job: [ADDING_A_JOB.md](ADDING_A_JOB.md).
**Companion:** `docs/specs/ARCHITECTURE.md`
**Audience:** a Grok Bot user who already has a bot doing heavy or repeating work, and wants that work offloaded to a remote CPU.

---

## What it is

GrokBotRemote is not a second chatbot you live in.

You keep talking to the Grok Bot that already does the work. You add GrokBotRemote *there*. Nightly and other heavy jobs then run in a portable container on a host you control. First host is any Linux Docker host you own. Later you move that same container to any Docker host (another VPS, Hetzner, Amazon, Google, …). Results come back into that same chat.

Your Cursor connectors, plugins, and API keys stay on the Grok Bot side. The VM only gets an explicit list of secrets for that job. It does not inherit Gmail, GitHub, or the rest of your Grok Bot session.

---

## Typical path (do this)

You already have a proven Grok Bot (for the repo owner: Agent86helperQA). In **that** chat, say something like:

- *"Add GrokBotRemote so nightly QA runs on the remote box"*
- *"Install the GrokBot Remote connector"*
- *"Use the GrokBotRemote git repo and offload the repeat load"*

That bot should **not** tell you to create another agent. Two add paths, either is enough:

1. **Connector / plugin** — once it exists in the catalog, the bot asks you to confirm install, then you paste your `runner_url` and `runner_token`.
2. **Git repo** — stand the runner up from `stevenbowler/GrokBotRemote` on your VM, then do (1) so this bot can talk to it.

Until the repo is public, only people the owner has given private-repo access can use the git path. Until the marketplace listing exists, the bot can still add the connector as a **local command** MCP (`plugin/server.py`) with `RUNNER_URL` + `RUNNER_TOKEN`. Same outcome.

---

## What you need

- A Grok Bot that already runs the job you want to offload (chat + a routine, if it is scheduled).
- A Linux host with Docker and SSH. Do **not** colocate this on an Agent86 app server.
- SSH access to that host (or a private network / tunnel to it).
- Docker on that host (the runner starts jobs in containers).
- Optional Agent86 sample: QA scripts mapped to UI_TEST_SPEC v0.8.24 on `agent86homeBot` `dev` (see `docs/specs/JOB1_AGENT86_QA_DEV.md`). Your own jobs: [ADDING_A_JOB.md](ADDING_A_JOB.md).

You do **not** need a new Grok Bot named GrokBotRemote. The maintainer agent is optional: it owns the spec and the repo.

---

## Step 1 — Start on your Linux Docker host

You do not need a cloud VPS to begin. The runner is a portable container. Compose defaults to loopback publish:

`${RUNNER_HOST:-127.0.0.1}:${RUNNER_PORT:-8787}:8080`

Do **not** publish on a host port already used by another service; avoid host **8080** when something else owns it. Prefer host port **8787**.

On that host:

1. SSH in as a non-root user (preferably in the `docker` group).
2. Install Docker and enable it on boot (skip if already present).
3. Firewall: SSH from your IPs or private network only. Do **not** publish the runner on a house public IP. SSH tunnel, VPN, or private/tailnet address for inbound `job_run`. Webhook outbound is fine behind NAT.

Prove from the host:

```bash
curl -sS http://127.0.0.1:8787/v1/status
```

For other machines that can reach the host, use `http://YOUR_RUNNER_HOST:8787` and set `RUNNER_HOST` accordingly. Do **not** publish the runner on a house public IP.

Never the Agent86 MaxChat servers. A QA browser can starve the app.

## Step 1b — Move the container later

When you want it on any other box:

1. Copy the same `compose/docker-compose.yml` and `compose/runner.env` to the new Docker host, plus this git checkout (jobs are mounted from it).
2. Copy the artifacts volume if you still need old logs; otherwise start clean.
3. `docker compose -f compose/docker-compose.yml up -d --build` on the new host.
4. Point the connector `runner_url` at the new place (tunnel/private network as needed).
5. `docker compose -f compose/docker-compose.yml down` on the old host.
6. In the original chat: *Run smoke*. Same job, new host.

There is no Hetzner path vs Amazon path vs Google path. Same image, new parking spot.

---

## Step 2 — Secrets (names only in git)

On the host, copy the example and fill values. The file is gitignored (`runner.env`). Values never go in the repo, the plugin, or a chat paste except the one-time connector setup fields.

```bash
cp compose/runner.env.example compose/runner.env
# edit compose/runner.env — set RUNNER_SECRET to a long random string
```

| Name | Who uses it |
|---|---|
| `RUNNER_SECRET` | Runner API. Same value you paste as the connector token. |
| `GROKBOT_WEBHOOK_URL` | Runner callback into the original bot's webhook routine |
| `GROKBOT_WEBHOOK_KEY` | Sender key from that routine panel (`X-Webhook-Key`) |
| `GIT_SHA` | Optional. If empty, the runner stamps `git rev-parse HEAD` from the mounted checkout. |
| `LOCAL_DEV` | Must stay `0` on any real host. `1` allows missing `X-Runner-Secret` for plugin-author localhost only. **Never set `LOCAL_DEV=1` on test or prod** — the runner refuses to start if `RUNNER_ENV` is `test` or `prod` and this flag is on. |
| `RUNNER_HOST` / `RUNNER_PORT` | Compose publish. Defaults `127.0.0.1` / `8787`. Also put them in `compose/.env`. |
| `QA_USER` / `QA_PASSWORD` | Optional sample `agent86-qa-dev` primary login (email + bypass code). Names only in git. |
| `QA_USER_ALT` / `QA_PASSWORD_ALT` | Optional sample fallback login if primary is missing. AUTH-01 fails; suite continues. |

Job 0 does **not** need a GitHub deploy key. v1 jobs come from this git checkout mounted into the runner. A deploy key is only needed later if the runner should pull a SHA itself.

Copy the webhook URL and sender key from the **original bot's** routine panel (the bot that will keep the chat). Create a webhook routine there if it does not exist yet. Webhook is optional for smoke: the result stays on the runner for `GET /v1/jobs/{run_id}` / `job_get` backfill.

Rotate `RUNNER_SECRET` by changing `runner.env` and the connector token together, then `docker compose up -d`. The old token must 403 immediately.

---

## Step 3 — Install the runner

On your Linux Docker host, from a checkout of this repo on branch `dev`:

```bash
cd /path/to/GrokBotRemote
git checkout dev
cp compose/runner.env.example compose/runner.env
# set RUNNER_SECRET (required). Optional: GROKBOT_WEBHOOK_URL, GROKBOT_WEBHOOK_KEY, GIT_SHA.
# leave LOCAL_DEV=0
nano compose/runner.env

# project name grokbotremote (also set in compose/docker-compose.yml)
docker compose -p grokbotremote -f compose/docker-compose.yml --profile qa-image build
docker compose -p grokbotremote -f compose/docker-compose.yml up -d --build
docker compose -p grokbotremote -f compose/docker-compose.yml ps
# do not docker compose down the whole daemon
```

The API defaults to `http://127.0.0.1:8787`. Prove Job 0:

```bash
# load the secret without printing it
set -a && . compose/runner.env && set +a

curl -sS http://127.0.0.1:8787/v1/status

curl -sS -X POST http://127.0.0.1:8787/v1/jobs \
  -H "Content-Type: application/json" \
  -H "X-Runner-Secret: ${RUNNER_SECRET}" \
  -d '{"job_id":"smoke","env":"dev"}'
```

The POST returns `202` with a `run_id`. Poll until `status` is `passed`:

```bash
RUN_ID='<paste-run_id>'
curl -sS "http://127.0.0.1:8787/v1/jobs/${RUN_ID}" \
  -H "X-Runner-Secret: ${RUNNER_SECRET}"
```

From another machine that can reach the host: replace with `http://YOUR_RUNNER_HOST:8787`. Do not default to publishing host 8080.

v1 artifacts stay on disk in the compose volume (`/artifacts/<run_id>/result.json` and `logs.txt` inside the runner). Fetch with SSH. No object storage yet.

One job at a time. A second `POST /v1/jobs` while one is running returns **409**. Missing or wrong `X-Runner-Secret` returns **403**. `env=prod` is rejected unless the runner's `RUNNER_ENV` is `prod`.

---

## Step 4 — Add the connector in the original chat

In the proven bot (not a new one):

1. Ask it to add GrokBotRemote / the GrokBot Remote connector.
2. Confirm the install card. The bot must not install without that.
3. Set `runner_url` to `http://127.0.0.1:8787` (or `http://YOUR_RUNNER_HOST:8787`) and `runner_token` (`RUNNER_SECRET`). There is **no** product default `runner_url` for other users. Never paste the token into the MCP URL.
4. On the next message, that bot can `job_run` / `job_get`.

v1 local command wrapper (until a catalog listing exists). Env only, no default URL:

```bash
# from a checkout of this repo
pip install -r plugin/requirements.txt
export RUNNER_URL=http://127.0.0.1:8787
export RUNNER_TOKEN='<same as RUNNER_SECRET>'
python plugin/server.py
```

Point Cursor at that command (stdio MCP). Cursor connectors are account-wide: other Grok Bots on the same Cursor account will also see the tools. The original bot is still where you talk.

---

## Step 5 — Offload status on that bot

Grok Bot has no sidebar badge for "running remote." Use what exists:

1. Open that bot's info pane (click its name in the chat header, or Cmd+Shift+I). Gear opens per-agent settings.
2. Set **title** to something like `QA · remote` (or your bot's name plus remote).
3. Set **description** to say nightly/repeat work is offloaded to your runner (hostname is enough; no secrets).
4. Keep the existing routine on **that** bot. It should `job_run` instead of doing the heavy work inline.
5. That chat should say when a run starts (`job_id`, `run_id`) and when it finishes (summary, counts).

If you turn offload off, clear the title/description so it does not lie.

---

## Step 6 — Prove the pipe (`smoke`)

In the original chat: *"Run smoke on the remote runner."*

You should get a pass line and a `run_id`. No Agent86 passwords, no Grok API, no mail.

Only after smoke is green, point a real job at it.

---

## GitHub Actions (dev)

Push to `dev` runs `.github/workflows/deploy.yml`: job `pytest` on `ubuntu-latest`, then `deploy-dev` on `[self-hosted, example-runner]`. One-time runner install: [ACTIONS_RUNNER.md](ACTIONS_RUNNER.md).

## Optional sample — Agent86 nightly QA (`agent86-qa-dev`)

This is an **optional example** under `jobs/examples/agent86-qa-dev/` (not required for the core product). Playwright, UI_TEST_SPEC v0.8.24. Target `https://dev.agent86portal.com` only. Secrets: `QA_USER` / `QA_PASSWORD` then `QA_USER_ALT` / `QA_PASSWORD_ALT`. Do not sign up. Full contract: [`docs/specs/JOB1_AGENT86_QA_DEV.md`](../specs/JOB1_AGENT86_QA_DEV.md). To wire your own job instead: [ADDING_A_JOB.md](ADDING_A_JOB.md).

Today Agent86helperQA still owns the cron (Mon/Wed/Fri 11:00pm America/Chicago). After smoke is green:

- Same chat: Agent86helperQA.
- Same cron: keep it on that bot.
- The routine calls `job_run agent86-qa-dev` instead of driving the browser.
- Email still goes through Agent86mail (has an assigned Gmail account and manages reporting; From has no personal display name; scheduled To is the configured recipient). The worker never sends mail and never reads that inbox.
- Do not open test or prod unless a later job id says so.

---

## Useful things to say in the original chat

- *"Add GrokBotRemote and offload the nightly job"*
- *"Run smoke"*
- *"What's on the remote runner?"*
- *"Cancel run &lt;run_id&gt;"*
- *"Stop offloading; run the suite here again"* (clear title/description)

---

## If something goes wrong

**The bot tells you to create a new GrokBotRemote agent.** Wrong. Stay in this chat and add the connector. That is a product bug (see PLUGIN_TEST_SPEC P-ADD-03).

**403 from the runner.** Missing or wrong `RUNNER_SECRET`. Check the connector token matches the VM env. Empty secret is allowed only on a documented local-dev flag (`LOCAL_DEV=1`), never on test/prod.

**Timeout.** The job hit its `timeout`. The container must be killed; status `timeout`. Raise the job timeout in git if the work is legitimately longer; do not wait forever.

**Webhook miss.** Result is still on the runner. In the original chat: *"Get run &lt;run_id&gt;"*. Check `GROKBOT_WEBHOOK_URL` and the sender key. The runner retries; the chat can backfill.

**Secrets in logs or in the result JSON.** Fail. Rotate those secrets. Do not ship.

**409 runner busy.** v1 runs one job at a time. Wait for the current run to finish, or cancel it.

**Connector connected but this bot still drives the browser.** The routine on that bot was not switched to `job_run`. Fix the routine; do not add a second bot.

**Gmail / GitHub "doesn't work on the worker."** Expected. Those connectors stay here. Either do that part in the Grok Bot chat, or give the job a *narrow* token it declared.

**I want this on Hetzner / Amazon / Google.** Same container. Copy compose + env to that host, point `runner_url` at it, run smoke. Do not wait on a cloud adapter.

**Runner not ready / cannot reach `runner_url`.**

1. On the Docker host: `docker compose -p grokbotremote -f compose/docker-compose.yml ps` — is `runner` Up and healthy?
2. `curl -sS http://127.0.0.1:8787/v1/status` on the host. If that fails, check logs: `docker compose -p grokbotremote -f compose/docker-compose.yml logs --tail=100 runner`.
3. If localhost works but your connector does not: confirm `RUNNER_URL` / `runner_url` matches how you publish (`127.0.0.1` vs `YOUR_RUNNER_HOST`), and that nothing else owns the host port you chose (prefer **8787**; avoid host **8080** when another service owns it).
4. Self-hosted Actions: is the `example-runner` runner Idle in GitHub? If deploy never ran, compose may be stale — see [ACTIONS_RUNNER.md](ACTIONS_RUNNER.md) (`./run.sh` + `@reboot`).

---

## Public-ready checklist (before any public allow)

- [ ] `rg` for house Tailscale IPs, house hostnames, personal emails, and personal display names returns **zero** hits in tracked content
- [ ] Compose default bind is loopback (`127.0.0.1:8787`); examples use `YOUR_RUNNER_HOST` where needed
- [ ] No house public IP in docs
- [ ] Secrets remain names-only in git (`runner.env` / `.env` gitignored)
- [ ] Repo stays **private** until the owner explicitly allows making it public
- [ ] Do **not** touch `main` for scrub-only work; ship on `dev`

---

## What this guide will not tell you to do

- Put secrets in git or in the public plugin.
- Point other people's connectors at the repo owner's VM.
- Run the runner on Grok Bot's own computer as the real worker (localhost is plugin-author dev only).
- Set `LOCAL_DEV=1` on test or prod.
- Make the GitHub repo public, or create it, without the owner's explicit allow for that action.
