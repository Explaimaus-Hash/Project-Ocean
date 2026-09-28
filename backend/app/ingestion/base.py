"""Bounded provider helpers, called only inside explicit acquisition workers."""

import math
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from ..schemas.acquisition import AcquisitionRequest
from ..storage.product_common import ProductError, stat_file

SOCKET_TIMEOUT = 15
MAX_AXIS_VALUES = 10000
MAX_SOURCE_CHUNK_BYTES = 33_554_432


def fail(code: str = "provider_unavailable") -> ProductError:
    messages = {
        "provider_unavailable": "The provider did not complete this bounded request.",
        "acquisition_limit": "The source selection exceeds acquisition limits.",
        "unsupported_source": "The source layout or coordinates are unsupported.",
        "no_data": "The selected source request contains no samples.",
        "credentials_missing": "Server-side Copernicus credentials are not configured.",
        "unsafe_transport": "Verified HTTPS transport is required for this provider.",
        "input_changed": "The source changed during acquisition.",
        "provider_request_rejected": "The provider rejected this source request.",
        "provider_auth_failed": "The provider did not accept source authentication.",
    }
    return ProductError(code, messages.get(code, "Acquisition did not complete."))


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        raise fail("unsafe_transport")


def bounded_http(url: str, destination: Path, max_bytes: int) -> int:
    """Stream one public ERDDAP response, with TLS and a hard saved-byte ceiling."""
    parts = urlsplit(url)
    if (
        parts.scheme != "https"
        or parts.hostname != "erddap.ifremer.fr"
        or parts.port not in {None, 443}
        or parts.username
        or parts.password
        or not parts.path.startswith("/erddap/tabledap/ArgoFloats.")
        or parts.fragment
    ):
        raise fail("unsafe_transport")
    import ssl

    import certifi

    # Explicit public CA roots make Windows trust behavior reproducible without
    # disabling certificate validation or hostname checking.
    context = ssl.create_default_context(cafile=certifi.where())
    opener = build_opener(NoRedirect(), HTTPSHandler(context=context))
    # Argopy URIs retain ERDDAP operators/quoted orderBy expressions. urllib does
    # not quote these automatically, unlike the client's normal aiohttp store;
    # Tomcat rejects raw '<', '>' and double quotes in the HTTP request target.
    transport_url = parts._replace(
        query=quote(parts.query, safe="=&,()!:%.+-_")
    ).geturl()
    request = Request(transport_url, headers={"Accept-Encoding": "identity"})
    total = 0
    try:
        response = opener.open(request, timeout=SOCKET_TIMEOUT)
    except HTTPError as error:
        body = error.read(4096)
        error.close()
        if error.code == 404 and b"Your query produced no matching results" in body:
            raise fail("no_data") from None
        if error.code in {401, 403}:
            raise fail("provider_auth_failed") from None
        if 400 <= error.code < 500:
            raise fail("provider_request_rejected") from None
        raise fail() from None
    with response:
        declared = response.headers.get("Content-Length")
        if declared is not None and int(declared) > max_bytes:
            raise fail("acquisition_limit")
        if response.headers.get("Content-Encoding", "identity") != "identity":
            raise fail("unsupported_source")
        with destination.open("xb") as stream:
            while block := response.read(min(65_536, max_bytes - total + 1)):
                total += len(block)
                if total > max_bytes:
                    raise fail("acquisition_limit")
                stream.write(block)
    if total == 0:
        raise fail("no_data")
    if declared is not None and total != int(declared):
        raise fail("input_changed")
    return total


def validate_raw(path: Path, request: AcquisitionRequest) -> None:
    """Bound file/header metadata without loading observation/model value arrays."""
    from .netcdf_metadata import MetadataInspectionError, inspect_netcdf_metadata

    stat_file(path, request.max_bytes)
    try:
        inspect_netcdf_metadata(path)
    except MetadataInspectionError:
        raise fail("unsupported_source") from None


def bound_dataset(
    dataset: Any,
    request: AcquisitionRequest,
    *,
    fixed_text_widths: dict[str, int] | None = None,
) -> None:
    """Inspect lazy shapes/types/chunks before field materialization."""
    if len(dataset.variables) > 128 or len(dataset.sizes) > 16:
        raise fail("acquisition_limit")
    count = 0
    decoded_bytes = 0
    fixed_text_widths = fixed_text_widths or {}
    for name, variable in dataset.variables.items():
        bounded_object_text = variable.dtype.kind == "O" and name in fixed_text_widths
        if variable.dtype.kind not in "biufmMSU" and not bounded_object_text:
            raise fail("unsupported_source")
        if variable.dtype.kind in "SU":
            width = variable.dtype.itemsize // (4 if variable.dtype.kind == "U" else 1)
            if width > 128:
                raise fail("acquisition_limit")
        count += variable.size
        # Fixed-byte text may become NumPy Unicode in the provider client.
        text_expansion = 4 if variable.dtype.kind == "S" else 1
        decoded_width = (
            fixed_text_widths[name] * 4
            if bounded_object_text
            else variable.dtype.itemsize * text_expansion
        )
        decoded_bytes += variable.size * max(8, decoded_width)
        chunks = variable.encoding.get("chunksizes")
        if (
            chunks
            and math.prod(chunks) * variable.dtype.itemsize > MAX_SOURCE_CHUNK_BYTES
        ):
            raise fail("acquisition_limit")
        preferred = variable.encoding.get("preferred_chunks")
        if (
            preferred
            and math.prod(preferred.values()) * variable.dtype.itemsize
            > MAX_SOURCE_CHUNK_BYTES
        ):
            raise fail("acquisition_limit")
        if variable.chunks:
            chunk_bytes = (
                math.prod(max(axis) for axis in variable.chunks)
                * variable.dtype.itemsize
            )
            if chunk_bytes > MAX_SOURCE_CHUNK_BYTES:
                raise fail("acquisition_limit")
    if count > request.max_values or decoded_bytes > request.max_bytes:
        raise fail("acquisition_limit")


def save_dataset(dataset: Any, destination: Path, request: AcquisitionRequest) -> None:
    bound_dataset(dataset, request)
    # Provider raw output may already be decoded/renamed by its official client.
    # xarray re-encoding semantics are retained; normalization is a later step.
    # NC_STRING/VLEN lacks a header-only maximum decoded-string size. Use fixed
    # char arrays for bounded client strings so normalization can preflight them.
    encoding = {
        name: {"dtype": "S1"}
        for name, variable in dataset.variables.items()
        if variable.dtype.kind in "SU"
    }
    dataset.to_netcdf(destination, engine="netcdf4", encoding=encoding)
    validate_raw(destination, request)


def model_subset(dataset: Any, request: AcquisitionRequest) -> Any:
    """Select exact rectilinear cell centres, rejecting guesses and extrapolation."""
    import numpy as np

    selection = request.selection
    coordinates = request.coordinates
    assert selection is not None and coordinates is not None
    names = coordinates.model_dump()
    if any(
        name not in dataset.variables for name in [*names.values(), *request.variables]
    ):
        raise fail("unsupported_source")
    indexers: dict[str, slice] = {}
    region = selection.region
    bounds = {
        "longitude": (region.west, region.east),
        "latitude": (region.south, region.north),
        "depth": (selection.vertical_min, selection.vertical_max),
    }
    for role, name in names.items():
        axis = dataset[name]
        if axis.dims != (name,) or not 0 < axis.size <= MAX_AXIS_VALUES:
            raise fail("unsupported_source")
        # Bounded coordinate arrays may be read before selected data variables.
        if role == "time":
            values = axis.values
            if values.dtype.kind != "M" or np.isnat(values).any():
                raise fail("unsupported_source")
            lower = np.datetime64(selection.start_time.replace(tzinfo=None), "ns")
            upper = np.datetime64(selection.end_time.replace(tzinfo=None), "ns")
        else:
            if axis.dtype.kind not in "iuf":
                raise fail("unsupported_source")
            values = axis.values.astype("float64")
            if not np.isfinite(values).all():
                raise fail("unsupported_source")
            units = axis.attrs.get("units")
            accepted = {
                "longitude": {"degrees_east", "degree_east"},
                "latitude": {"degrees_north", "degree_north"},
                "depth": {"m", "metres", "meters"},
            }
            if units not in accepted[role]:
                raise fail("unsupported_source")
            if role == "depth" and axis.attrs.get("positive") != "down":
                raise fail("unsupported_source")
            if role == "longitude" and (values.min() < -180 or values.max() >= 180):
                raise fail("unsupported_source")
            if role == "latitude" and (values.min() < -90 or values.max() > 90):
                raise fail("unsupported_source")
            if role == "depth" and values.min() < 0:
                raise fail("unsupported_source")
            lower, upper = bounds[role]
        differences = np.diff(values)
        if values.dtype.kind == "M":
            increasing = (differences > np.timedelta64(0, "ns")).all()
            decreasing = (differences < np.timedelta64(0, "ns")).all()
        else:
            increasing, decreasing = (differences > 0).all(), (differences < 0).all()
        if not increasing and not decreasing:
            raise fail("unsupported_source")
        selected = np.flatnonzero((values >= lower) & (values <= upper))
        if not selected.size:
            raise fail("no_data")
        if role == "time" and selected.size > 32:
            raise fail("acquisition_limit")
        indexers[name] = slice(int(selected[0]), int(selected[-1]) + 1)
    keep = set(names.values()) | set(request.variables)
    # Retain explicit ancillary QC and bounds arrays rather than silently dropping.
    for name in tuple(keep):
        for attr in ("ancillary_variables", "bounds", "climatology", "grid_mapping"):
            references = dataset[name].attrs.get(attr, "").split()
            if any(value not in dataset.variables for value in references):
                raise fail("unsupported_source")
            keep.update(references)
    if len(keep) > 64:
        raise fail("acquisition_limit")
    for name in request.variables:
        variable = dataset[name]
        if set(variable.dims) != set(names.values()) or len(variable.dims) != 4:
            raise fail("unsupported_source")
        if not variable.attrs.get("units"):
            raise fail("unsupported_source")
    subset = dataset[sorted(keep)].isel(indexers)
    bound_dataset(subset, request)
    return subset
