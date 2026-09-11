# One-time GitHub Actions runner (Linux Docker host)

Install this **once** on a **generic Linux Docker host** you control (Ubuntu or similar). The user running the Actions service must be in the `docker` group.

Do **not** publish the GrokBotRemote runner HTTP port on a host port already used by another service; avoid host **8080** when something else owns it. Prefer host port **8787**.

Labels must be `self-hosted,example-runner` only. Do **not** reuse labels from other projects.

The registration token is created in GitHub and expires in about an hour. Generate it immediately before `config.sh`.

## 1. Token

In the repo (Settings → Actions → Runners → New self-hosted runner):

1. **Settings → Actions → Runners → New self-hosted runner**
2. OS: Linux, Architecture: x64
3. Copy the token from that page (do not commit it)

## 2. Install (exact commands)

SSH into the Linux Docker host as a user in the `docker` group. Docker must already be running.

```bash
mkdir -p "$HOME/actions-runner-example"
cd "$HOME/actions-runner-example"

RUNNER_VERSION=$(curl -fsSL https://api.github.com/repos/actions/runner/releases/latest \
  | sed -n 's/.*"tag_name": "v\([^"]*\)".*/\1/p' | head -1)
echo "runner version ${RUNNER_VERSION}"

curl -fsSL -o "actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz" \
  "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"
tar xzf "actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"

# Paste the token from step 1. GitHub always adds the self-hosted label.
./config.sh --url https://github.com/stevenbowler/GrokBotRemoteCopy \
  --token '<PASTE_TOKEN_FROM_GITHUB_UI>' \
  --name example-runner-host \
  --labels example-runner \
  --work _work \
  --unattended

# Ensure Docker access for compose up --build (no sudo needed after logout/login)
sudo usermod -aG docker "$USER" || true
```

### Start without systemd sudo (`./run.sh` + `@reboot`)

If you do not want `sudo ./svc.sh install`, run the Actions listener in the user session and keep it across reboots with crontab:

```bash
cd "$HOME/actions-runner-example"
nohup ./run.sh > "$HOME/actions-runner-example/run.log" 2>&1 &

# Persist across reboot (no sudo):
(crontab -l 2>/dev/null | grep -v actions-runner-example; \
  echo "@reboot cd $HOME/actions-runner-example && ./run.sh >> $HOME/actions-runner-example/run.log 2>&1") | crontab -
```

Optional (needs sudo): `sudo ./svc.sh install && sudo ./svc.sh start` if you prefer a system service instead.

Confirm in GitHub **Settings → Actions → Runners** that the runner is Idle with labels `self-hosted`, `Linux`, `X64`, `example-runner`. If you see labels reused from other projects, remove this runner and re-register with only `example-runner`.

## 3. Persistent secrets (values never in git)

```bash
mkdir -p "$HOME/.grokbotremote"
chmod 700 "$HOME/.grokbotremote"

# From a checkout of GrokBotRemoteCopy branch dev:
cp compose/runner.env.example "$HOME/.grokbotremote/runner.env"
# Edit: RUNNER_SECRET, QA_USER, QA_PASSWORD, QA_USER_ALT, QA_PASSWORD_ALT,
# optional GROKBOT_WEBHOOK_URL / GROKBOT_WEBHOOK_KEY. Leave LOCAL_DEV=0.
chmod 600 "$HOME/.grokbotremote/runner.env"

printf '%s\n' 'RUNNER_HOST=127.0.0.1' 'RUNNER_PORT=8787' \
  > "$HOME/.grokbotremote/compose.env"
# For clients on a private network/tailnet, set RUNNER_HOST to that address instead.
```

`deploy-dev` copies these into the Actions checkout. It runs `docker compose -f compose/docker-compose.yml up -d --build` (project name `grokbotremote`). It does **not** `docker compose down`.

## 4. Prove bind after first deploy

From the host (or any client that can reach `YOUR_RUNNER_HOST`):

```bash
curl -sS http://127.0.0.1:8787/v1/status
# or: curl -sS http://YOUR_RUNNER_HOST:8787/v1/status
```

Expect JSON from the runner. Prefer port **8787**. Do not use host 8080 when another service already owns it. Do not publish on a house public IP.
