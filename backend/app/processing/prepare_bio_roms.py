"""Prepare a verified local V2 selection without loading the complete source.

This first rectilinear surface adapter uses netCDF4 directly: every field read is
one selected frame, and source decompression chunks are checked first. xarray
remains a later adapter/analysis option, not an implicit whole-array operation.
Only source masks/packing and nonfinite values are handled; quantity definitions
are not harmonized and no profile, volume, current or comparison is implied.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from time import sleep
from typing import Any

from pydantic import ValidationError

from ..ingestion.incois_bio_roms import input_status
from ..ingestion.registry import RegistryError, find_dataset, load_registry
from ..schemas.datasets import MAX_REPORT_BYTES, DatasetDefinition, InspectionReport
from ..schemas.products import (
    PROCESSING_VERSION,
    PerformanceLimits,
    PreparationRequest,
    ProductManifest,
    VariableInfo,
)
from ..storage.product_common import (
    ProductError,
    contained,
    describe_file,
    load_limits,
    read_json,
)

SUPPORTED_UNITS = {
    "SST": "deg C",
    "SSS": "PSU",
    "MLD": "m",
    "DIC": "milimole/m3",
    "NO3": "milimole/m3",
    "CHL": "kg/m3",
    "pCO2_Int": "micro atm",
    "pCO2_Clim": "micro atm",
    "pCO2_Original": "micro atm",
    "Deviant_uncertainty": "micro atm",
}
AXES = ("TIME", "LAT", "LON")
CALENDARS = {"standard", "gregorian", "proleptic_gregorian"}
_ATTRIBUTE_COPY = ("units", "long_name", "standard_name", "cell_methods", "comment")


def _error(code: str, message: str) -> ProductError:
    return ProductError(code, message)


def _verified_input(
    request: PreparationRequest, root: Path
) -> tuple[DatasetDefinition, InspectionReport, Path]:
    try:
        definition = find_dataset(
            load_registry(root / "config" / "data_sources.yaml"), request.dataset_id
        )
    except RegistryError:
        raise _error(
            "configuration_unavailable", "Source registry is invalid."
        ) from None
    if (
        definition.dataset_id != "incois_bio_roms_v2"
        or definition.source_id != "incois_bio_roms"
        or definition.version != "v2"
        or definition.access_method != "local_netcdf"
        or not definition.expected_md5
        or not definition.local_path
    ):
        raise _error(
            "unsupported_source", "Only registered local BIO-ROMS V2 is supported."
        )
    try:
        report = InspectionReport.model_validate(
            read_json(
                contained(root, f"data/metadata/{request.dataset_id}.json"),
                MAX_REPORT_BYTES,
            )
        )
    except (ProductError, ValidationError):
        raise _error(
            "inspection_required", "Save a verified source inspection first."
        ) from None
    current = input_status(definition, root)
    if (
        report.status != "not_prepared"
        or report.reason_code != "metadata_inspected_only"
        or report.checksum_status != "verified"
        or report.expected_md5 != definition.expected_md5
        or report.observed_md5 != definition.expected_md5
        or report.source_id != definition.source_id
        or report.dataset_id != definition.dataset_id
        or report.source_version != definition.version
        or report.origin_url != definition.origin_url
        or report.local_path != definition.local_path
        or report.metadata is None
        or report.file_identity is None
        or current.status != "uninspected"
        or current.file_identity != report.file_identity
    ):
        raise _error("inspection_required", "Source inspection is unverified or stale.")
    return definition, report, contained(root, definition.local_path)


def _check_unchanged(
    definition: DatasetDefinition, report: InspectionReport, root: Path
) -> None:
    current = input_status(definition, root)
    if current.status != "uninspected" or current.file_identity != report.file_identity:
        raise _error(
            "source_changed", "Source changed; inspect it again before preparing."
        )


def _check_storage(variable: Any, limits: PerformanceLimits) -> None:
    if variable.dtype.kind not in "iuf" or variable.dtype.itemsize > 8:
        raise _error(
            "unsupported_dtype", "Only primitive numeric source values are supported."
        )
    chunking = variable.chunking()
    if isinstance(chunking, (list, tuple)):
        if (
            math.prod(chunking) * variable.dtype.itemsize
            > limits.max_source_chunk_bytes
        ):
            raise _error(
                "source_chunk_limit", "A decompressed source chunk exceeds limits."
            )
    variable.set_var_chunk_cache(
        size=limits.netcdf_cache_bytes, nelems=1009, preemption=0.75
    )
    variable.set_auto_maskandscale(True)


def _reject_qc(variable: Any) -> None:
    if any(
        name.startswith("flag_")
        or name in {"ancillary_variables", "bounds", "climatology"}
        for name in variable.ncattrs()
    ):
        raise _error(
            "unsupported_qc", "QC/ancillary or temporal bounds require another adapter."
        )


def _axes(
    source: Any, limits: PerformanceLimits, np: Any
) -> tuple[dict, list, str, str]:
    from netCDF4 import num2date

    axes = {}
    for name in AXES:
        if name not in source.variables:
            raise _error(
                "unsupported_grid", "TIME/LAT/LON coordinate variables are required."
            )
        variable = source.variables[name]
        if (
            variable.dimensions != (name,)
            or not 0 < variable.size <= limits.max_axis_values
        ):
            raise _error("axis_limit", "Coordinate shape or size is unsupported.")
        _check_storage(variable, limits)
        _reject_qc(variable)
        values = np.ma.asarray(variable[:], dtype="float64")
        if np.ma.getmaskarray(values).any():
            raise _error("invalid_coordinates", "Coordinate values cannot be missing.")
        values = np.asarray(values)
        if not np.isfinite(values).all() or not (np.diff(values) > 0).all():
            raise _error(
                "invalid_coordinates", "Coordinates must be finite and increasing."
            )
        axes[name] = values
    for name, unit, axis, minimum, maximum in (
        ("LAT", "degrees_north", "Y", -90, 90),
        ("LON", "degrees_east", "X", -180, 180),
    ):
        variable = source.variables[name]
        if (
            getattr(variable, "units", None) != unit
            or getattr(variable, "axis", axis) != axis
        ):
            raise _error("unsupported_units", "Coordinate units/axis are unsupported.")
        values = axes[name]
        if (
            values[0] < minimum
            or values[-1] > maximum
            or (name == "LON" and values[-1] >= 180)
        ):
            raise _error("invalid_coordinates", "Coordinates exceed geographic bounds.")
    time = source.variables["TIME"]
    units = getattr(time, "units", "")
    calendar = getattr(time, "calendar", "standard")
    if calendar not in CALENDARS:
        raise _error(
            "unsupported_calendar", "Only real-world Gregorian calendars are supported."
        )
    if (
        not isinstance(units, str)
        or len(units) > 256
        or getattr(time, "axis", "T") != "T"
    ):
        raise _error("unsupported_units", "Time units/axis are unsupported.")
    try:
        decoded = num2date(axes["TIME"], units=units, calendar=calendar)
        timestamps = [
            datetime(
                t.year,
                t.month,
                t.day,
                t.hour,
                t.minute,
                t.second,
                t.microsecond,
                tzinfo=UTC,
            )
            for t in decoded
        ]
    except (ValueError, TypeError, OverflowError):
        raise _error(
            "unsupported_time", "Time values cannot be decoded to supported UTC dates."
        ) from None
    if any(a >= b for a, b in zip(timestamps, timestamps[1:], strict=False)):
        raise _error("invalid_coordinates", "Decoded time must strictly increase.")
    return axes, timestamps, units, calendar


def _selection(
    request: PreparationRequest,
    axes: dict,
    timestamps: list,
    limits: PerformanceLimits,
    np: Any,
) -> tuple:
    time_indices = [
        i
        for i, t in enumerate(timestamps)
        if request.start_date <= t.date() <= request.end_date
    ]
    lat_indices = np.flatnonzero(
        (axes["LAT"] >= request.region.south) & (axes["LAT"] <= request.region.north)
    )
    lon_indices = np.flatnonzero(
        (axes["LON"] >= request.region.west) & (axes["LON"] <= request.region.east)
    )
    if not time_indices or not len(lat_indices) or not len(lon_indices):
        raise _error("no_overlap", "No source samples overlap the requested selection.")
    values = (
        len(time_indices) * len(lat_indices) * len(lon_indices) * len(request.variables)
    )
    if (
        len(time_indices) > limits.max_time_steps
        or values > limits.max_preparation_values
    ):
        raise _error(
            "preparation_limit", "Reduce the selected variables, region or dates."
        )
    if values * 8 > limits.max_product_file_bytes:
        raise _error(
            "product_size_limit", "Scientific output would exceed the file limit."
        )
    stride = max(
        1,
        math.ceil(
            math.sqrt(len(lat_indices) * len(lon_indices) / limits.max_preview_cells)
        ),
    )
    while (
        math.ceil(len(lat_indices) / stride) * math.ceil(len(lon_indices) / stride)
        > limits.max_preview_cells
    ):
        stride += 1
    return (
        time_indices,
        slice(int(lat_indices[0]), int(lat_indices[-1]) + 1),
        slice(int(lon_indices[0]), int(lon_indices[-1]) + 1),
        stride,
    )


def _variables(
    source: Any, request: PreparationRequest, limits: PerformanceLimits
) -> dict[str, VariableInfo]:
    info = {}
    for name in request.variables:
        if name not in SUPPORTED_UNITS or name not in source.variables:
            raise _error(
                "unsupported_variable", "Requested variable is unsupported or absent."
            )
        variable = source.variables[name]
        if variable.dimensions != AXES:
            raise _error(
                "unsupported_grid",
                "Only scalar TIME/LAT/LON surface fields are supported.",
            )
        if getattr(variable, "units", None) != SUPPORTED_UNITS[name]:
            raise _error(
                "unsupported_units",
                "Variable units differ from the inspected V2 contract.",
            )
        _check_storage(variable, limits)
        _reject_qc(variable)
        info[name] = VariableInfo(
            source_name=name,
            units=variable.units,
            long_name=getattr(variable, "long_name", name),
            standard_name=getattr(variable, "standard_name", ""),
            cell_methods=getattr(variable, "cell_methods", "not_declared"),
            source_dtype=str(variable.dtype),
        )
    return info


def _product_id(
    request: PreparationRequest,
    report: InspectionReport,
    limits: PerformanceLimits,
    data_mode: str,
) -> str:
    key = {
        "selection": request.model_dump(mode="json"),
        "md5": report.observed_md5,
        "processing_version": PROCESSING_VERSION,
        "limits": limits.model_dump(),
        "data_mode": data_mode,
    }
    return (
        "p_"
        + hashlib.sha256(
            json.dumps(key, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:24]
    )


def _existing(
    root: Path,
    product_id: str,
    request: PreparationRequest,
    report: InspectionReport,
    limits: PerformanceLimits,
    data_mode: str,
) -> ProductManifest | None:
    folder = contained(root, f"data/processed/{product_id}")
    cache = contained(root, f"data/cache/{product_id}")
    if not folder.exists() and not cache.exists():
        return None
    try:
        manifest = ProductManifest.model_validate(
            read_json(
                contained(root, f"data/processed/{product_id}/manifest.json"),
                limits.max_manifest_bytes,
            )
        )
        if (
            manifest.product_id != product_id
            or manifest.selection != request
            or manifest.input_md5 != report.observed_md5
            or manifest.input_size_bytes != report.file_identity.size_bytes
            or manifest.input_modified_ns != report.file_identity.modified_ns
            or manifest.data_mode != data_mode
            or manifest.source_id != report.source_id
            or manifest.source_version != report.source_version
            or manifest.origin_url != report.origin_url
            or describe_file(
                contained(root, f"data/processed/{product_id}/fields.nc"),
                limits.max_product_file_bytes,
            )
            != manifest.scientific_file
            or describe_file(
                contained(root, f"data/cache/{product_id}/preview.nc"),
                limits.max_product_file_bytes,
            )
            != manifest.preview_file
        ):
            raise ValueError("existing product identity differs")
        return manifest
    except (ProductError, ValueError, OSError):
        raise _error(
            "product_conflict",
            "Existing product is incomplete or changed; no files were overwritten.",
        ) from None


def _write_dataset(
    destination: Any,
    source: Any,
    axes: dict,
    time_indices: list,
    ys: slice,
    xs: slice,
    stride: int,
    request: PreparationRequest,
    report: InspectionReport,
    product_id: str,
    data_mode: str,
    limits: PerformanceLimits,
) -> None:
    for name, values in (
        ("TIME", axes["TIME"][time_indices]),
        ("LAT", axes["LAT"][ys][::stride]),
        ("LON", axes["LON"][xs][::stride]),
    ):
        destination.createDimension(name, len(values))
        output = destination.createVariable(name, "f8", (name,))
        original = source.variables[name]
        for attr in (*_ATTRIBUTE_COPY, "axis", "calendar"):
            if attr in original.ncattrs():
                output.setncattr(attr, original.getncattr(attr))
        if name == "TIME":
            output.calendar = getattr(original, "calendar", "standard")
        output[:] = values
    destination.setncattr("product_id", product_id)
    destination.setncattr("data_mode", data_mode)
    destination.setncattr("processing_version", PROCESSING_VERSION)
    destination.setncattr("origin_url", report.origin_url)
    destination.setncattr("input_md5", report.observed_md5)
    destination.setncattr("qc_policy", "source_mask_and_nonfinite_only")
    destination.setncattr("temporal_support", "source_timestamps_no_inferred_bounds")
    destination.setncattr("display_stride", stride)
    destination.setncattr(
        "source_global_attributes_json",
        json.dumps(report.metadata.get("global_attributes", {}), allow_nan=False),
    )
    for name in request.variables:
        original = source.variables[name]
        variable = destination.createVariable(
            name,
            "f8",
            AXES,
            fill_value=float("nan"),
            zlib=True,
            complevel=1,
            chunksizes=(
                1,
                min(128, len(destination.dimensions["LAT"])),
                min(128, len(destination.dimensions["LON"])),
            ),
        )
        variable.set_var_chunk_cache(
            size=limits.netcdf_cache_bytes, nelems=1009, preemption=0.75
        )
        for attr in _ATTRIBUTE_COPY:
            if attr in original.ncattrs():
                variable.setncattr(attr, original.getncattr(attr))
        # Packed valid ranges, unsigned flags and scale/offset remain provenance
        # only: output values are already decoded float64 and must not decode twice.
        attributes = (
            report.metadata.get("variables", {}).get(name, {}).get("attributes", {})
        )
        variable.setncattr(
            "source_attributes_json", json.dumps(attributes, allow_nan=False)
        )


def _cleanup_private(directory: Path | None, parent: Path) -> None:
    if directory is None or not directory.exists():
        return
    resolved = directory.resolve()
    if resolved.parent != parent.resolve() or not directory.name.startswith(
        ".prepare_"
    ):
        return
    for filename in ("fields.nc", "preview.nc", "manifest.json"):
        candidate = directory / filename
        if candidate.exists() and not candidate.is_symlink():
            candidate.unlink()
    directory.rmdir()


def _publish_directory(source: Path, destination: Path) -> None:
    """Retry transient Windows sharing/access locks, never replace an output."""
    for attempt in range(8):
        if destination.exists():
            raise _error("product_conflict", "Another operator published this product.")
        try:
            source.rename(destination)
            return
        except PermissionError as error:
            if getattr(error, "winerror", None) not in {5, 32} or attempt == 7:
                raise
            sleep(0.1 * (attempt + 1))


def prepare_product(
    request: PreparationRequest, root: Path, *, data_mode: str = "real"
) -> ProductManifest:
    """Create bounded scientific and preview files; original bytes are never written.

    A completed checksum-verified inspection is required. Normal concurrent source
    changes are detected with size/mtime; this is not an adversarial immutable-file
    snapshot. Products are trusted local files, not arbitrary uploaded content.
    """
    if data_mode not in {"real", "synthetic"}:
        raise _error("invalid_data_mode", "Data mode must be real or synthetic.")
    root = root.resolve()
    limits = load_limits(root)
    definition, report, raw = _verified_input(request, root)
    product_id = _product_id(request, report, limits, data_mode)
    existing = _existing(root, product_id, request, report, limits, data_mode)
    if existing is not None:
        _check_unchanged(definition, report, root)
        return existing
    processed_parent = contained(root, "data/processed")
    cache_parent = contained(root, "data/cache")
    for parent in (processed_parent, cache_parent):
        if parent.exists():
            for count, _child in enumerate(parent.iterdir(), start=1):
                # Count invalid/private leftovers as well: do not scan an
                # unbounded directory or let failed work bypass capacity limits.
                if count >= limits.max_products:
                    raise _error(
                        "product_count_limit", "Prepared-product capacity is reached."
                    )
    scientific_temp = preview_temp = None
    try:
        import numpy as np
        from netCDF4 import Dataset

        with Dataset(raw, "r") as source:
            if source.groups or source.cmptypes or source.vltypes or source.enumtypes:
                raise _error(
                    "unsupported_grid", "Grouped/custom-type sources are unsupported."
                )
            # Validate variables and source chunks before reading even the axes.
            variables = _variables(source, request, limits)
            axes, timestamps, time_units, calendar = _axes(source, limits, np)
            indices, ys, xs, stride = _selection(request, axes, timestamps, limits, np)
            _check_unchanged(definition, report, root)
            processed_parent.mkdir(parents=True, exist_ok=True)
            cache_parent.mkdir(parents=True, exist_ok=True)
            scientific_temp = Path(
                tempfile.mkdtemp(prefix=".prepare_", dir=processed_parent)
            )
            preview_temp = Path(tempfile.mkdtemp(prefix=".prepare_", dir=cache_parent))
            scientific_path = scientific_temp / "fields.nc"
            preview_path = preview_temp / "preview.nc"
            with (
                Dataset(scientific_path, "w", format="NETCDF4") as scientific,
                Dataset(preview_path, "w", format="NETCDF4") as preview,
            ):
                _write_dataset(
                    scientific,
                    source,
                    axes,
                    indices,
                    ys,
                    xs,
                    1,
                    request,
                    report,
                    product_id,
                    data_mode,
                    limits,
                )
                _write_dataset(
                    preview,
                    source,
                    axes,
                    indices,
                    ys,
                    xs,
                    stride,
                    request,
                    report,
                    product_id,
                    data_mode,
                    limits,
                )
                for name in request.variables:
                    original = source.variables[name]
                    chunks = original.chunking()
                    # Source chunks span many dates. Read each small spatial tile
                    # for this bounded batch once, avoiding repeated decompression.
                    # At most 12 * 256 * 256 float64 values (~6 MiB) per tile;
                    # source decompression/cache ceilings remain independently enforced.
                    tile_y = min(256, chunks[1]) if isinstance(chunks, list) else 128
                    tile_x = min(256, chunks[2]) if isinstance(chunks, list) else 128
                    height, width = ys.stop - ys.start, xs.stop - xs.start
                    for y in range(0, height, tile_y):
                        stop_y = min(height, y + tile_y)
                        for x in range(0, width, tile_x):
                            stop_x = min(width, x + tile_x)
                            values = np.ma.asarray(
                                original[
                                    indices,
                                    ys.start + y : ys.start + stop_y,
                                    xs.start + x : xs.start + stop_x,
                                ],
                                dtype="float64",
                            ).filled(np.nan)
                            values[~np.isfinite(values)] = np.nan
                            scientific.variables[name][:, y:stop_y, x:stop_x] = values
                            first_y = ((y + stride - 1) // stride) * stride
                            first_x = ((x + stride - 1) // stride) * stride
                            if first_y < stop_y and first_x < stop_x:
                                preview.variables[name][
                                    :,
                                    first_y // stride : (stop_y + stride - 1) // stride,
                                    first_x // stride : (stop_x + stride - 1) // stride,
                                ] = values[
                                    :, first_y - y :: stride, first_x - x :: stride
                                ]
                            del values
            _check_unchanged(definition, report, root)
        manifest = ProductManifest(
            product_id=product_id,
            source_id=definition.source_id,
            dataset_id=definition.dataset_id,
            source_version=definition.version,
            origin_url=definition.origin_url,
            input_md5=report.observed_md5,
            input_size_bytes=report.file_identity.size_bytes,
            input_modified_ns=report.file_identity.modified_ns,
            created_at=datetime.now(UTC),
            selection=request,
            data_mode=data_mode,
            variables=variables,
            latitude=axes["LAT"][ys].tolist(),
            longitude=axes["LON"][xs].tolist(),
            times=[timestamps[i].isoformat().replace("+00:00", "Z") for i in indices],
            time_units=time_units,
            calendar=calendar,
            preview_stride=stride,
            scientific_file=describe_file(
                scientific_path, limits.max_product_file_bytes
            ),
            preview_file=describe_file(preview_path, limits.max_product_file_bytes),
        )
        payload = manifest.model_dump_json(indent=2).encode() + b"\n"
        if len(payload) > limits.max_manifest_bytes:
            raise _error("metadata_limit", "Prepared manifest exceeds limits.")
        with (scientific_temp / "manifest.json").open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        _check_unchanged(definition, report, root)
        final_cache = contained(root, f"data/cache/{product_id}")
        final_scientific = contained(root, f"data/processed/{product_id}")
        if final_cache.exists() or final_scientific.exists():
            raise _error("product_conflict", "Another operator published this product.")
        # Publish cache first; processed directory (including manifest) is the
        # commit marker. A crash may leave an unreferenced cache, never ready data.
        _publish_directory(preview_temp, final_cache)
        preview_temp = None
        _publish_directory(scientific_temp, final_scientific)
        scientific_temp = None
        return manifest
    except ProductError:
        raise
    except (ImportError, OSError, RuntimeError, ValueError, TypeError, AttributeError):
        raise _error(
            "preparation_failed",
            "Local preparation failed; no complete product was published.",
        ) from None
    finally:
        _cleanup_private(scientific_temp, processed_parent)
        _cleanup_private(preview_temp, cache_parent)
