"""Liveness response; deliberately carries no scientific-data readiness."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """Fixed, non-sensitive response for the lightweight health endpoint."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["ok"] = "ok"
    service: Literal["Project Ocean Backend"] = "Project Ocean Backend"
