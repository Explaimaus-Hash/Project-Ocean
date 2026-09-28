"""Read private manifest/stat inventory only; HTTP never acquires source data."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..schemas.acquisition_api import AcquisitionCatalogueResponse
from ..schemas.product_api import ErrorResponse
from ..storage.product_common import ProductError
from .products import json_result

router = APIRouter(
    tags=["source acquisitions"],
    responses={code: {"model": ErrorResponse} for code in (409, 413, 500, 503)},
)


@router.get("/api/v1/acquisitions", response_model=AcquisitionCatalogueResponse)
def acquisitions(request: Request) -> JSONResponse:
    """List available acquired inputs, not prepared products or live-source health."""
    from ..ingestion.acquisition import list_acquisitions

    try:
        manifests = list_acquisitions(request.app.state.settings.project_root)
    except OSError:
        raise ProductError(
            "acquisitions_unavailable", "Acquisition inventory is unavailable.", 503
        ) from None
    items = []
    for manifest in manifests:
        item = manifest.model_dump(
            mode="json",
            include={
                "acquisition_id",
                "dataset_id",
                "source_id",
                "origin_url",
                "source_version",
                "retrieved_at",
                "data_mode",
                "status",
                "client",
                "client_version",
                "client_processing",
                "transport",
                "comparison_ready",
            },
        )
        item.update(
            {
                "provider": manifest.request.provider,
                "provider_dataset_id": manifest.request.provider_dataset_id,
                "selection": manifest.request.selection.model_dump(mode="json")
                if manifest.request.selection
                else None,
                "variables": manifest.request.variables,
                "input_sha256": manifest.input_file.sha256,
                "size_bytes": manifest.input_file.size_bytes,
            }
        )
        items.append(item)
    return json_result(
        {
            "scope": "locally_available_acquisitions_not_live_access",
            "acquisitions": items,
        },
        AcquisitionCatalogueResponse,
    )
