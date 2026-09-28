"""FastAPI entry point with independent liveness and prepared-product access."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from . import __version__
from .api.acquisitions import router as acquisitions_router
from .api.comparisons import router as comparisons_router
from .api.health import router as health_router
from .api.observations import router as observations_router
from .api.products import router as products_router
from .config import Settings
from .storage.comparisons import ComparisonStore
from .storage.observations import ObservationStore
from .storage.product_common import ProductError
from .storage.products import ProductStore


async def product_error_handler(request: Request, error: ProductError) -> JSONResponse:
    """Expose only the service's deliberate public error code and message."""
    return JSONResponse(
        {"schema_version": 1, "error": {"code": error.code, "message": error.message}},
        status_code=error.http_status,
        headers={"Cache-Control": "no-store"},
    )


async def invalid_request_handler(
    request: Request, error: RequestValidationError
) -> JSONResponse:
    """Do not echo invalid inputs, paths, or validator exception details."""
    return JSONResponse(
        {
            "schema_version": 1,
            "error": {
                "code": "invalid_request",
                "message": "Request parameters are invalid.",
            },
        },
        status_code=422,
        headers={"Cache-Control": "no-store"},
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Construct the API without ingesting data or requiring provider services."""
    if settings is None:
        settings = Settings()

    application = FastAPI(
        title="Project Ocean Backend",
        version=__version__,
        description=(
            "Independent liveness plus bounded local prepared surface products, "
            "frames, and grid-cell time series. Inspection and preparation are "
            "explicit operator commands; readiness checks configured local products. "
            "Prepared exploratory comparisons are read-only snapshots; matching, "
            "live acquisition and frontend remain separate."
        ),
        debug=False,
        docs_url="/docs" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
        redoc_url=None,
    )
    application.state.settings = settings
    application.state.product_store = ProductStore(settings.project_root)
    application.state.observation_store = ObservationStore(settings.project_root)
    application.state.comparison_store = ComparisonStore(settings.project_root)
    application.add_exception_handler(ProductError, product_error_handler)
    application.add_exception_handler(RequestValidationError, invalid_request_handler)
    application.include_router(health_router)
    application.include_router(products_router)
    application.include_router(observations_router)
    application.include_router(acquisitions_router)
    application.include_router(comparisons_router)
    return application


app = create_app()
