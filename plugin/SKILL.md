# GrokBot Remote — skill

Use this when **this Grok Bot** already runs heavy or repeating work and the user wants that work offloaded to their remote CPU.

## Stay in this chat

- Stay in this chat. Add the GrokBot Remote connector here (plugin catalog, add-by-URL, or local command wrapper).
- Do **not** create a second bot. Do not tell the user to "go create GrokBotRemote and talk there."
- After add, this same bot dispatches `job_run` / `job_get` / `job_cancel`. Results come back into this transcript.

## Offload status (no sidebar badge)

Grok Bot has no per-agent sidebar badge. Do not invent one.

When offload is enabled, update **this** agent's title and description (per-agent settings / info pane), for example:

- title: `QA · remote` (or the bot's name plus remote)
- description: nightly/repeat work is offloaded to the user's runner (hostname is enough)

When a job starts, say so in this chat (`job_id`, `run_id`). When it finishes, post the summary (and counts if any).

If the user says stop offloading, stop dispatching `job_run` for that workload and clear the title/description so they do not lie.

## Connector config

Install fields (stored in the user's Cursor account, never in git):

- `runner_url` — base URL of **their** runner. There is **no** default. Never embed the repo owner's host, Hetzner, or any other user's VM.
- `runner_token` — secret; sent as `X-Runner-Secret`. Same value as `RUNNER_SECRET` on the VM.

How to add: confirm with the user first (InstallPlugin / AddMcpServer). Do not install in the same turn as the question.

## Secrets

- Never paste `RUNNER_SECRET` / `runner_token` into an MCP URL, into logs, or back into the chat.
- Never echo the token after the user pastes it.
- GitHub, Gmail, and other Cursor connectors stay on this Grok Bot. They do not travel to the VM. A job only gets the env secrets it declared.
- For Agent86helperQA: do not read or send the assigned reporting Gmail from this bot or from the worker. Scheduled QA mail still goes through Agent86mail.

## Tools

- `runner_status` — is the remote runner up? Do not dump secrets.
- `job_list` — known job ids (at least `smoke`; nested samples under `jobs/examples/` appear by yaml `id`).
- `job_run` — dispatch (`job_id`, optional `env`, `git_sha`, `inputs`).
- `job_get` — status + result for a `run_id` (backfill if the webhook missed).
- `job_cancel` — best-effort cancel.

If the runner returns 403, explain a token mismatch. Do not claim the job ran. Do not fall back to doing the heavy work inline unless the user explicitly says to.

Job 0 (`smoke`) proves the pipe: no Agent86 passwords, no Grok API, no mail.

Optional sample `agent86-qa-dev` (under `jobs/examples/`) is the Agent86 DEV UI suite (UI_TEST_SPEC v0.8.24, `https://dev.agent86portal.com` only). Dispatch it only after smoke is green. Never paste QA passwords into chat. For the user's own jobs, see `docs/user/ADDING_A_JOB.md`.

## Reachability

The runner publishes HTTP on the owner's Docker host (recommended host port **8787**, container 8080 — do not publish on a host port already used by another service; avoid host 8080 when something else owns it). `runner_url` is **their** URL (e.g. `http://127.0.0.1:8787` or `http://YOUR_RUNNER_HOST:8787`). There is still no product-default URL. Do not publish the runner on a house public IP.
