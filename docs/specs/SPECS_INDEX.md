# Specs index

Developer-facing architecture and test specifications. Update this file when any spec is added, renamed, or removed.

| File | Covers |
|---|---|
| `ARCHITECTURE.md` | Control vs execute, typical user journey (same chat), offload status, job contract, secrets, portable container (any Linux Docker host; relocate anywhere), plugin phases, sibling agents, Job 0 smoke / optional sample Agent86 DEV QA under `jobs/examples/` |
| `JOB1_AGENT86_QA_DEV.md` | Optional sample contract: UI_TEST_SPEC v0.8.24 mapping, run vs skip groups, honest skips, secret names, result counts, first live-run notes (`jobs/examples/agent86-qa-dev/`) |
| `RUNNER_TEST_SPEC.md` | Runner HTTP API tests: auth fail-closed, smoke, timeout, secrets redaction, webhook retry, cancel, one-job-at-a-time, relocate to a second host |
| `PLUGIN_TEST_SPEC.md` | Add-from-existing-chat (plugin or git), must not create a second bot, tool calls, wrong token, skill wording, title/description status |
