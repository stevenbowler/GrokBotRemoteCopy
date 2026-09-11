# Plugin / connector — test spec

**Status:** Draft. No plugin implementation yet. Cases are for a human or a test bot once `plugin/` exists.
**Audience:** human / QA bot in a real Grok Bot chat; automated tests for the MCP wrapper where possible.
**Date:** 2026-08-27
**Companion:** `ARCHITECTURE.md` §1.1, §1.2, §5.4, §11; `docs/user/README.md`

IDs are stable. Do not reuse an ID for a different assert.

---

## Setup

- A **proven existing** Grok Bot chat (for the repo owner: Agent86helperQA, or a throwaway bot that already has a dummy routine). Call this bot **Origin**.
- A runner that already passes R-SMOKE-01, or a mock runner with the same HTTP contract.
- Catalog plugin **or** add-by-URL / local command wrapper (v1).
- Origin does **not** start with the connector installed (P-ADD-* need a clean add).

---

## P-ADD — stay in the original chat

### P-ADD-01 plugin path
**Given** Origin chat
**When** user says "add GrokBotRemote" or "install the GrokBot Remote connector"
**Then** Origin offers to add the connector in this chat (confirm card)
**Then** Origin does not create a new agent
**Then** after confirm + `runner_url` / `runner_token`, Origin can call runner tools on the next message

### P-ADD-02 git path
**Given** Origin chat, repo available to that user
**When** user says "use the GrokBotRemote git repo to offload nightly work"
**Then** Origin treats this as: stand up / point at the runner from that repo, then add the connector in this chat
**Then** Origin does not create a new agent

### P-ADD-03 must not spawn a second bot
**Given** P-ADD-01 or P-ADD-02
**Then** no new Grok Bot is created
**Then** Origin never instructs the user to "go create GrokBotRemote and talk there"
**Then** this case fails the skill if that sentence appears

### P-ADD-04 confirm before install
**When** add would change the user's Cursor account (InstallPlugin / AddMcpServer)
**Then** Origin asks with a confirm first and waits
**Then** it does not install in the same turn as the question

---

## P-CFG — install fields

### P-CFG-01 required fields
**Then** setup fields are `runner_url` (not secret) and `runner_token` (secret)
**Then** the plugin ships **no** default `runner_url` pointing at the repo owner's VM

### P-CFG-02 token not echoed
**When** user pastes `runner_token`
**Then** later chat messages from Origin do not reprint the token
**Then** skill text and tool logs do not contain the token

---

## P-RUN — tools

### P-RUN-01 job_run smoke
**Given** connector configured toward a healthy runner
**When** user says "run smoke" in Origin
**Then** Origin calls `job_run` (or equivalent) with `job_id=smoke`
**Then** Origin replies in **this** chat with `run_id` and that work is on the remote runner

### P-GET-01 job_get
**Given** P-RUN-01
**When** user says "what's the status of that run" or "get run &lt;id&gt;"
**Then** Origin calls `job_get` and reports `status` / `summary`

### P-RUN-02 job_list
**When** user says "what jobs can you offload"
**Then** Origin lists job ids from `job_list` (at least `smoke`)

### P-RUN-03 job_cancel
**Given** a running job
**When** user says cancel
**Then** Origin calls `job_cancel`
**Then** follow-up `job_get` is `cancelled` or already terminal

### P-RUN-04 runner_status
**When** user asks if the remote runner is up
**Then** Origin calls `runner_status` and says up/down without dumping secrets

---

## P-AUTH — bad token

### P-AUTH-01 wrong token
**Given** connector token does not match the runner
**When** `job_run smoke`
**Then** Origin reports a 403 / token mismatch in Origin chat
**Then** it does not claim the job ran
**Then** it does not fall back to running the heavy work inline unless the user explicitly says to

---

## P-SEC — skill and connectors

### P-SEC-01 skill does not leak secrets
**Then** the skill file contains no real tokens, QA passwords, or owner webhook keys
**Then** it tells the bot never to paste `RUNNER_SECRET` into a URL or into logs

### P-SEC-02 connectors do not travel
**Given** Origin has GitHub and Gmail connectors
**When** a job runs on the VM
**Then** those Cursor connectors are not invoked *on the VM*
**Then** skill says GitHub/Gmail stay on Origin; the job only gets declared env secrets

### P-SEC-03 Gmail ownership (Agent86)
**Given** Agent86helperQA is Origin
**Then** offload does not cause Origin or the worker to read/send the assigned reporting Gmail
**Then** scheduled report still goes through Agent86mail

---

## P-STAT — offload status

### P-STAT-01 title or description
**Given** offload is enabled on Origin
**Then** Origin's **title** or **description** (per-agent settings) states that repeat/nightly work is remote
**Then** there is no requirement for a sidebar badge (that UI does not exist)

### P-STAT-02 chat lines
**When** a job starts and finishes
**Then** Origin posts start (`job_id`, `run_id`) and finish (summary, counts if any) in this chat

### P-STAT-03 disable
**When** user says stop offloading
**Then** Origin stops dispatching `job_run` for that workload
**Then** title/description no longer claim remote offload

---

## P-ACC — account scope

### P-ACC-01 other bots see tools
**Given** connector installed on the Cursor account
**Then** another Grok Bot on the same account can see the runner tools
**Then** the human still uses Origin for that workload unless they choose otherwise

### P-ACC-02 not the repo owner's box
**Given** a stranger's install
**Then** their `runner_url` is whatever they typed
**Then** no bundled default reaches `stevenbowler` Hetzner

---

## P-SKL — skill wording

### P-SKL-01 when to use
**Then** skill description is "use this when this Grok Bot already runs heavy or repeating work and the user wants that offloaded to their remote CPU"

### P-SKL-02 stay here
**Then** skill says stay in this chat; add connector; update title/description; do not create a second bot

---

## UI (human / Agent86helperQA)

### UI-P1 In Agent86helperQA (or Origin), "add GrokBotRemote" never opens a "create agent" path
### UI-P2 After add, "run smoke" in that same chat is enough
### UI-P3 Info pane shows title/description reflecting remote offload
### UI-P4 Routines list still on Origin; nightly trigger is not moved to the maintainer agent

---

## Definition of done (plugin)

- P-ADD-01, P-ADD-03, P-ADD-04 pass
- P-CFG-01, P-CFG-02, P-RUN-01, P-GET-01, P-AUTH-01 pass
- P-SEC-01, P-SEC-02, P-STAT-01, P-STAT-02, P-SKL-02 pass
- UI-P1 and UI-P2 executed once by a human or QA bot
- Marketplace listing is **not** required for this DoD (git + add-by-URL is enough for v1)
