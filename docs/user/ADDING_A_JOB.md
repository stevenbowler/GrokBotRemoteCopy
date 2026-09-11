# Adding your own job

Wire **your** functionality on the remote. The core product is the **runner + compose + plugin + `smoke`**. Everything under `jobs/examples/*` is an optional sample (Agent86 QA is one sample). You do not need Agent86 QA to use GrokBotRemote.

## 1. Copy smoke as a starting point

```bash
cp -R jobs/smoke jobs/my-job
# edit jobs/my-job/job.yaml — set id, image, command, timeout, secrets (names only)
```

Or keep a sample layout under `jobs/examples/my-job/` if you want it clearly marked optional. Prefer `jobs/<id>/` for jobs you own and run regularly.

## 2. `job.yaml` fields

| Field | Meaning |
|---|---|
| `id` | Stable slug used by `job_run` / catalog (e.g. `my-job`). Keep this stable even if the folder moves. |
| `image` | Container image, or build one from a Dockerfile in the job folder |
| `command` | Entrypoint inside the container (string or list) |
| `timeout` | Hard kill after N seconds |
| `secrets` | **Names** of required env vars (values never in git) |
| `inputs` | Non-secret parameters (URLs, suite ids, etc.) |
| `result` | Path of the result JSON the container must write (optional) |
| `callback` | `webhook` for v1 |
| `cpu` / `memory` | Hints |

The runner recursively finds every `job.yaml` under `jobs/`. Catalog ids come from the yaml `id` field (fallback: folder name). Directories without `job.yaml` (including `jobs/examples/` itself) are not listed as jobs.

`load_job` resolves:

- `jobs/<id>/job.yaml`
- `jobs/examples/<id>/job.yaml`
- relative path under `jobs/` equal to the requested id
- yaml `id` field equal to the requested id

So a sample at `jobs/examples/agent86-qa-dev/` still runs as `job_id=agent86-qa-dev`.

## 3. Secrets (names only)

1. Add names to `job.yaml` → `secrets:`.
2. Add the same names (empty values) to `compose/runner.env.example` as documentation.
3. Put real values only in the host's gitignored `compose/runner.env` (or `~/.grokbotremote/runner.env` for Actions deploy).

Never commit passwords, tokens, or personal emails.

## 4. Compose (custom image)

If the job needs its own image, add a build service next to the runner in `compose/docker-compose.yml`, for example:

```yaml
  my-job-image:
    image: grokbotremote-my-job:dev
    build:
      context: ../jobs/my-job
      dockerfile: Dockerfile
    profiles: ["my-job-image"]
    restart: "no"
    command: ["true"]
```

Build with the profile on deploy or locally:

```bash
docker compose -p grokbotremote -f compose/docker-compose.yml --profile my-job-image build
docker compose -p grokbotremote -f compose/docker-compose.yml up -d --build
```

Jobs that use a public image (like `smoke` → `alpine`) need no compose service.

## 5. Connector: `job_run`

In the Grok Bot that already does the work (after the GrokBot Remote connector is configured):

1. Prove the pipe: `job_run` with `job_id=smoke`.
2. Dispatch your job: `job_run` with `job_id=<your yaml id>` (and optional `env`, `inputs`).
3. Poll with `job_get` if the webhook is down.

Example for the Agent86 sample only: `job_run agent86-qa-dev` after smoke is green. That sample is optional.

## Checklist

- [ ] `job.yaml` has a stable `id` and an `image`
- [ ] Secret **names** in yaml + `runner.env.example`; values only on the host
- [ ] Custom Dockerfile + compose build context if you need a private image
- [ ] Smoke still passes on the same runner
- [ ] No personal IPs, hostnames, or emails in git
