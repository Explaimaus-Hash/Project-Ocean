"""Read-only HTTP access to already prepared, bounded surface products."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import JSONResponse
from pydantic import FiniteFloat, ValidationError

from ..schemas.product_api import (
    CatalogueResponse,
    ErrorResponse,
    FrameResponse,
    MetadataResponse,
    ReadinessResponse,
    TimeseriesResponse,
    VersionedResponse,
)
from ..schemas.products import Region
from ..storage.product_common import ProductError
from ..storage.products import ProductStore

router = APIRouter(
    tags=["prepared products"],
    responses={
        code: {"model": ErrorResponse} for code in (404, 409, 413, 422, 500, 503)
    },
)

ProductId = Annotated[
    str, Path(pattern=r"^[a-z][a-z0-9_]{0,95}$", min_length=1, max_length=96)
]
Variable = Annotated[
    str, Query(pattern=r"^[A-Za-z][A-Za-z0-9_]{0,63}$", min_length=1, max_length=64)
]
Longitude = Annotated[FiniteFloat, Query(ge=-180, lt=180)]
Latitude = Annotated[FiniteFloat, Query(ge=-90, le=90)]


def get_product_store(request: Request) -> ProductStore:
    """Use the factory's lightweight service without loading raw datasets."""
    return request.app.state.product_store


Store = Annotated[ProductStore, Depends(get_product_store)]


def json_result(
    payload: dict, model: type[VersionedResponse], *, status_code: int = 200
) -> JSONResponse:
    """Validate the public wire contract before serializing a bounded response."""
    try:
        result = model.model_validate({"schema_version": 1, **payload})
    except ValidationError:
        raise ProductError(
            "invalid_response", "Prepared response failed contract validation.", 500
        ) from None
    response = JSONResponse(
        result.model_dump(mode="json", exclude_unset=True),
        status_code=status_code,
        headers={"Cache-Control": "no-store"},
    )
    if len(response.body) > 2097152:
        raise ProductError(
            "response_limit", "Prepared response exceeds byte limits.", 413
        )
    return response


@router.get("/api/v1/datasets", response_model=CatalogueResponse)
def datasets(store: Store) -> JSONResponse:
    """List configured sources and their local prepared products, not live access."""
    return json_result(store.catalogue(), CatalogueResponse)


@router.get("/api/v1/products/{product_id}", response_model=MetadataResponse)
def product_metadata(product_id: ProductId, store: Store) -> JSONResponse:
    """Return public selection, units, timestamps, and supported capabilities."""
    return json_result(store.metadata(product_id), MetadataResponse)


@router.get("/api/v1/products/{product_id}/frame", response_model=FrameResponse)
def product_frame(
    product_id: ProductId,
    store: Store,
    variable: Variable,
    time_index: Annotated[int, Query(ge=0)],
    quality: Literal["preview", "scientific"] = "preview",
    west: Annotated[FiniteFloat | None, Query(ge=-180, lt=180)] = None,
    east: Annotated[FiniteFloat | None, Query(gt=-180, le=180)] = None,
    south: Annotated[FiniteFloat | None, Query(ge=-90, le=90)] = None,
    north: Annotated[FiniteFloat | None, Query(ge=-90, le=90)] = None,
) -> JSONResponse:
    """Read one bounded frame; region bounds must be complete and increasing."""
    bounds = (west, east, south, north)
    region = None
    if any(value is not None for value in bounds):
        if any(value is None for value in bounds):
            raise ProductError(
                "invalid_request", "Provide all four geographic bounds.", 422
            )
        try:
            region = Region(west=west, east=east, south=south, north=north)
        except ValidationError:
            raise ProductError(
                "invalid_request",
                "Geographic bounds must increase without wrapping.",
                422,
            ) from None
    return json_result(
        store.frame(product_id, variable, time_index, quality=quality, region=region),
        FrameResponse,
    )


@router.get(
    "/api/v1/products/{product_id}/timeseries", response_model=TimeseriesResponse
)
def product_timeseries(
    product_id: ProductId,
    store: Store,
    variable: Variable,
    longitude: Longitude,
    latitude: Latitude,
) -> JSONResponse:
    """Inspect a scientific grid-cell series, not an observation comparison."""
    return json_result(
        store.timeseries(product_id, variable, longitude, latitude), TimeseriesResponse
    )


@router.get(
    "/ready",
    tags=["readiness"],
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse}},
)
def readiness(request: Request, store: Store) -> JSONResponse:
    """Check explicitly required local prepared products without raw-data work."""
    result = store.readiness(request.app.state.settings.required_product_ids)
    return json_result(
        result,
        ReadinessResponse,
        status_code=200 if result.get("status") == "ready" else 503,
    )
