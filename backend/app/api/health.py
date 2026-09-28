"""Constant-time API liveness without network or scientific-file access."""

from fastapi import APIRouter, Response, status

from ..schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Check API liveness",
    description=(
        "Confirms only that the API responds. Does not inspect datasets, contact "
        "providers, or report scientific-data readiness."
    ),
)
async def get_health(response: Response) -> HealthResponse:
    """Return liveness without triggering data access or processing."""
    response.headers["Cache-Control"] = "no-store"
    return HealthResponse()
