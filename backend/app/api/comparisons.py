"""Bounded read-only access to explicitly prepared exploratory comparisons."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import JSONResponse

from ..schemas.comparison_api import (
    ComparisonCatalogue,
    ComparisonMetadata,
    ComparisonPage,
)
from ..schemas.product_api import ErrorResponse
from ..storage.comparisons import ComparisonStore
from .products import json_result

router = APIRouter(
    prefix="/api/v1/comparisons",
    tags=["prepared comparisons"],
    responses={
        code: {"model": ErrorResponse} for code in (404, 409, 413, 422, 500, 503)
    },
)
ComparisonId = Annotated[str, Path(pattern=r"^c_[a-f0-9]{24}$", max_length=26)]


def get_store(request: Request) -> ComparisonStore:
    return request.app.state.comparison_store


Store = Annotated[ComparisonStore, Depends(get_store)]


@router.get("", response_model=ComparisonCatalogue)
def comparisons(store: Store) -> JSONResponse:
    """Inventory of prepared snapshots, not source freshness/scientific readiness."""
    return json_result(store.catalogue(), ComparisonCatalogue)


@router.get("/{comparison_id}", response_model=ComparisonMetadata)
def comparison_metadata(comparison_id: ComparisonId, store: Store) -> JSONResponse:
    return json_result(store.metadata(comparison_id), ComparisonMetadata)


@router.get("/{comparison_id}/samples", response_model=ComparisonPage)
def comparison_samples(
    comparison_id: ComparisonId,
    store: Store,
    offset: Annotated[int, Query(ge=0, le=5000)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    matched: Annotated[bool | None, Query()] = None,
) -> JSONResponse:
    """Filter before pagination; unmatched samples retain null residuals/reasons."""
    return json_result(
        store.samples(comparison_id, offset=offset, limit=limit, matched=matched),
        ComparisonPage,
    )
