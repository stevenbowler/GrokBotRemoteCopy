"""GrokBotRemote runner HTTP API (FastAPI). Bind to 127.0.0.1 in compose."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from auth import require_secret
from engine import BusyError, JobRunner, RejectedError, UnknownJobError
from settings import Settings

log = logging.getLogger("gbr")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


class JobRequest(BaseModel):
    job_id: str
    git_sha: str | None = None
    env: str = "dev"
    inputs: dict[str, Any] | None = None


def create_app(
    settings: Settings | None = None,
    docker_client: Any | None = None,
    *,
    webhook_post=None,
) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.validate()
    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="GrokBotRemote runner", version="0.1.0")
    runner = JobRunner(settings, docker_client=docker_client, webhook_post=webhook_post)
    app.state.settings = settings
    app.state.runner = runner

    @app.get("/v1/status")
    def status() -> dict[str, Any]:
        # Health. No secrets. Auth not required so compose healthcheck is simple.
        return {
            "ok": True,
            "version": "0.1.0",
            "env": settings.runner_env,
            "busy": runner.is_busy(),
            "local_dev": bool(settings.local_dev),
        }

    @app.get("/v1/catalog", dependencies=[Depends(require_secret)])
    def catalog() -> dict[str, Any]:
        return {"jobs": runner.catalog()}

    @app.post("/v1/jobs", dependencies=[Depends(require_secret)])
    def post_job(body: JobRequest):
        try:
            run = runner.dispatch(
                body.job_id,
                env=body.env,
                git_sha=body.git_sha,
                inputs=body.inputs,
            )
        except UnknownJobError:
            raise HTTPException(status_code=404, detail="unknown job") from None
        except BusyError:
            raise HTTPException(status_code=409, detail="runner busy") from None
        except RejectedError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
        return JSONResponse(status_code=202, content=run)

    @app.get("/v1/jobs/{run_id}", dependencies=[Depends(require_secret)])
    def get_job(run_id: str):
        run = runner.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="unknown run")
        return run

    @app.post("/v1/jobs/{run_id}/cancel", dependencies=[Depends(require_secret)])
    def cancel_job(run_id: str):
        run = runner.cancel(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="unknown run")
        return run

    return app


app = create_app()
