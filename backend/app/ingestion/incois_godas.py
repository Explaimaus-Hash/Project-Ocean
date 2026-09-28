"""Explicit OPeNDAP acquisition with inspected GODAS coordinates/variable names."""

from pathlib import Path
from typing import Any

from ..schemas.acquisition import AcquisitionRequest
from ..schemas.datasets import DatasetDefinition
from .base import model_subset, save_dataset


def fetch(
    request: AcquisitionRequest, definition: DatasetDefinition, destination: Path
) -> dict[str, Any]:
    import xarray as xr

    # The registry, not user-supplied arbitrary URLs, selects the endpoint.
    # The enclosing worker has a process deadline even if libnetcdf blocks.
    with xr.open_dataset(
        definition.origin_url,
        engine="netcdf4",
        chunks=None,
        cache=False,
        create_default_indexes=False,
    ) as dataset:
        subset = model_subset(dataset, request)
        save_dataset(subset, destination, request)
    return {
        "client": "xarray/netCDF4 OPeNDAP",
        "client_version": xr.__version__,
        "client_processing": (
            "Exact selected rectilinear source centres; xarray CF "
            "decoding/re-encoding; no quantity conversion or QC filtering."
        ),
        "transport": "https",
        "original_filename": None,
    }
