"""Read-only pages of prepared scientific samples, never raw NetCDF downloads."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import JSONResponse

from ..schemas.observation_api import (
    ObservationCatalogueResponse,
    ObservationMetadataResponse,
    ObservationPageResponse,
)
from ..schemas.product_api import ErrorResponse
from ..storage.observations import ObservationStore
from .products import json_result

router = APIRouter(
    prefix="/api/v1/observations",
    tags=["prepared observations"],
    responses={
        code: {"model": ErrorResponse} for code in (404, 409, 413, 422, 500, 503)
    },
)
CollectionId = Annotated[str, Path(pattern=r"^o_[a-f0-9]{24}$", max_length=26)]


def get_observation_store(request: Request) -> ObservationStore:
    return request.app.state.observation_store


Store = Annotated[ObservationStore, Depends(get_observation_store)]


@router.get("", response_model=ObservationCatalogueResponse)
def observations(store: Store) -> JSONResponse:
    """List local scientific collections, not live provider access or overlap."""
    return json_result(store.catalogue(), ObservationCatalogueResponse)


@router.get("/{collection_id}", response_model=ObservationMetadataResponse)
def observation_metadata(collection_id: CollectionId, store: Store) -> JSONResponse:
    return json_result(store.metadata(collection_id), ObservationMetadataResponse)


@router.get("/{collection_id}/samples", response_model=ObservationPageResponse)
def observation_samples(
    collection_id: CollectionId,
    store: Store,
    offset: Annotated[int, Query(ge=0, le=5000)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    profile_id: Annotated[
        str | None, Query(pattern=r"^r_[a-f0-9]{24}$", max_length=26)
    ] = None,
) -> JSONResponse:
    """Read finite/null native samples with QC and stable profile/sample identity."""
    return json_result(
        store.samples(collection_id, offset=offset, limit=limit, profile_id=profile_id),
        ObservationPageResponse,
    )
