"""Official toolbox access; authentication is explicit and server-only."""

import os
from pathlib import Path
from typing import Any

from pydantic import SecretStr

from ..schemas.acquisition import AcquisitionRequest
from ..schemas.datasets import DatasetDefinition
from .base import fail, model_subset, save_dataset


def credentials() -> tuple[SecretStr, SecretStr]:
    username = os.environ.get("COPERNICUSMARINE_SERVICE_USERNAME", "")
    password = os.environ.get("COPERNICUSMARINE_SERVICE_PASSWORD", "")
    if not username.strip() or not password:
        raise fail("credentials_missing")
    if (
        os.environ.get("COPERNICUSMARINE_DISABLE_SSL_CONTEXT", "False").lower()
        == "true"
    ):
        raise fail("unsafe_transport")
    return SecretStr(username), SecretStr(password)


def _open(client: Any, **kwargs: Any) -> Any:
    try:
        return client.open_dataset(**kwargs)
    except client.CoordinatesOutOfDatasetBounds:
        # Strict-inside also rejects partially overlapping requests. This is
        # not evidence that the selection contains no model samples.
        raise fail("provider_request_rejected") from None
    except client.VariableDoesNotExistInTheDataset:
        raise fail("unsupported_source") from None
    except client.InvalidUsernameOrPassword:
        raise fail("provider_auth_failed") from None
    except client.CredentialsCannotBeNone:
        raise fail("credentials_missing") from None
    except client.CouldNotConnectToAuthenticationSystem:
        raise fail("provider_unavailable") from None


def fetch(
    request: AcquisitionRequest, definition: DatasetDefinition, destination: Path
) -> dict[str, Any]:
    username, password = credentials()
    # Set before importing the provider client: no implicit credential search,
    # prompt, inherited TLS bypass, long retry cascade, or parallel processing.
    os.environ["COPERNICUSMARINE_HTTPS_TIMEOUT"] = "15"
    os.environ["COPERNICUSMARINE_HTTPS_RETRIES"] = "0"
    os.environ["COPERNICUSMARINE_DISABLE_SSL_CONTEXT"] = "False"
    os.environ["COPERNICUSMARINE_USE_THREADS"] = "False"
    os.environ["COPERNICUSMARINE_CREDENTIALS_DIRECTORY"] = str(destination.parent)
    import copernicusmarine

    selected = request.selection
    assert selected is not None
    region = selected.region
    dataset = _open(
        copernicusmarine,
        dataset_id=request.provider_dataset_id,
        dataset_version=request.provider_version,
        username=username.get_secret_value(),
        password=password.get_secret_value(),
        variables=request.variables,
        minimum_longitude=region.west,
        maximum_longitude=region.east,
        minimum_latitude=region.south,
        maximum_latitude=region.north,
        minimum_depth=selected.vertical_min,
        maximum_depth=selected.vertical_max,
        vertical_axis="depth",
        start_datetime=selected.start_time,
        end_datetime=selected.end_time,
        coordinates_selection_method="strict-inside",
        raise_if_updating=True,
        chunk_size_limit=8,
    )
    try:
        subset = model_subset(dataset, request)
        save_dataset(subset, destination, request)
    finally:
        dataset.close()
    return {
        "client": "copernicusmarine",
        "client_version": copernicusmarine.__version__,
        "client_processing": (
            "Explicit selected dataset/version through official toolbox; "
            "strict-inside source centres; vertical_axis=depth requests SDK "
            "elevation-to-depth sign/order/name conversion when needed; "
            "CF mask/scale/time decoding and NetCDF re-encoding; "
            "no quantity harmonization or QC filtering."
        ),
        "transport": "https",
        "original_filename": None,
    }
