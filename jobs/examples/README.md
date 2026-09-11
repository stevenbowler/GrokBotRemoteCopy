# Example jobs

Files under `jobs/examples/` are **optional samples** only (Agent86 DEV QA is one sample). They are not required to run the core product (runner + compose + plugin + `smoke`). Put your own jobs in `jobs/<id>/` with a `job.yaml`, or keep samples here under `jobs/examples/<id>/`. The runner catalogs any nested `job.yaml` and loads by the yaml `id` (so `job_run agent86-qa-dev` still works for the sample under `examples/`).
