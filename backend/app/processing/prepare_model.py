"""Explicit bounded native Copernicus preparation; no network or API imports."""

from __future__ import annotations

import math
import os
import tempfile
from datetime import UTC, datetime
from itertools import islice
from pathlib import Path

from pydantic import ValidationError

from ..ingestion.acquisition import read_acquisition
from ..schemas.model_metadata import (
    ModelSourceMetadata,
    SourceAttribute,
    SourceVariableMetadata,
)
from ..schemas.models import (
    ModelAxes,
    ModelIdentity,
    ModelLimits,
    ModelManifest,
    ModelPreparationRequest,
    ModelProvenance,
    ModelVariableInfo,
    serialize_model_manifest,
)
from ..storage.product_common import (
    ProductError,
    describe_file,
    load_limits,
    read_json,
)

AXES = ("time", "depth", "latitude", "longitude")
FIELDS = {
    "thetao": ("degrees_C", "sea_water_potential_temperature"),
    "so": ("1e-3", "sea_water_salinity"),
    "uo": ("m s-1", "eastward_sea_water_velocity"),
    "vo": ("m s-1", "northward_sea_water_velocity"),
}


def fail(code: str) -> ProductError:
    return ProductError(
        code, "Local model preparation failed validation: " + code + "."
    )


def private_path(root: Path, relative: str) -> Path:
    """Reject alias/placeholder paths; no recursive deletion or cloud recalls."""
    base = root.resolve()
    target = base / relative
    if not target.resolve().is_relative_to(base) or target.resolve() == base:
        raise fail("unsafe_model_path")
    for part in (target, *target.parents):
        if part == base:
            break
        if part.is_symlink() or part.is_junction():
            raise fail("unsafe_model_path")
        if part.exists() and getattr(part.stat(), "st_file_attributes", 0) & (
            0x1000 | 0x40000 | 0x400000
        ):
            raise fail("model_not_local")
    return target


def _snapshot(source, limit, np) -> bytes:
    total = 0
    estimated_bytes = 0

    def attributes(owner):
        nonlocal total, estimated_bytes
        names = owner.ncattrs()
        total += len(names)
        if len(names) > 128 or total > 4096:
            raise fail("metadata_limit")
        result = {}
        for name in names:
            if any(
                word in name.lower() for word in ("password", "credential", "token")
            ):
                raise fail("unsafe_metadata")
            value = np.asarray(owner.getncattr(name))
            estimated_bytes += value.nbytes + len(name.encode("utf-8")) + 128
            if estimated_bytes > limit:
                raise fail("metadata_limit")
            if (
                value.size > 2048
                or value.nbytes > 65536
                or value.dtype.kind not in "iufSU"
                or value.ndim > 4
            ):
                raise fail("unsupported_metadata")
            values = []
            for item in value.reshape(-1):
                item = item.item()
                if isinstance(item, bytes):
                    item = item.decode("utf-8")
                if isinstance(item, float) and not math.isfinite(item):
                    item = (
                        "NaN" if math.isnan(item) else ("+Inf" if item > 0 else "-Inf")
                    )
                values.append(item)
            result[name] = SourceAttribute(
                dtype=value.dtype.str, shape=value.shape, values=tuple(values)
            )
        return result

    variables = {}
    for name, var in source.variables.items():
        variables[name] = SourceVariableMetadata(
            dtype=str(var.dtype),
            dimensions=var.dimensions,
            shape=var.shape,
            attributes=attributes(var),
        )
    snapshot = ModelSourceMetadata(
        global_attributes=attributes(source), variables=variables
    )
    payload = (snapshot.model_dump_json() + "\n").encode("utf-8")
    if len(payload) > limit:
        raise fail("metadata_limit")
    return payload


def _encoding(var, limits, np):
    """Support unambiguous native-domain packing only; reject unsigned ambiguity."""
    dtype = np.dtype(var.dtype)
    if dtype.kind not in "iuf" or dtype.itemsize > (8 if dtype.kind == "f" else 4):
        raise fail("unsupported_dtype")
    if any(
        name.startswith("flag_")
        or name
        in {
            "ancillary_variables",
            "bounds",
            "climatology",
            "formula_terms",
            "grid_mapping",
            "_Unsigned",
        }
        for name in var.ncattrs()
    ):
        raise fail("unsupported_metadata")
    if "coordinates" in var.ncattrs() and not set(
        str(var.getncattr("coordinates")).split()
    ).issubset(AXES):
        raise fail("unsupported_grid")
    chunks = var.chunking()
    if isinstance(chunks, (list, tuple)) and math.prod(chunks) * dtype.itemsize > (
        limits.max_source_chunk_bytes
    ):
        raise fail("source_chunk_limit")
    var.set_var_chunk_cache(
        size=limits.netcdf_cache_bytes, nelems=1009, preemption=0.75
    )
    var.set_auto_maskandscale(False)
    scale = np.asarray(getattr(var, "scale_factor", 1))
    offset = np.asarray(getattr(var, "add_offset", 0))
    if any(v.size != 1 or v.dtype.kind not in "iuf" for v in (scale, offset)):
        raise fail("invalid_packing")
    scale, offset = float(scale.item()), float(offset.item())
    if not math.isfinite(scale) or scale == 0 or not math.isfinite(offset):
        raise fail("invalid_packing")
    lower = upper = None
    if "valid_range" in var.ncattrs():
        if "valid_min" in var.ncattrs() or "valid_max" in var.ncattrs():
            raise fail("invalid_packing")
        bounds = np.asarray(var.getncattr("valid_range"))
        if bounds.shape != (2,) or bounds.dtype != dtype:
            raise fail("invalid_packing")
        lower, upper = bounds.tolist()
    else:
        for name in ("valid_min", "valid_max"):
            if name in var.ncattrs():
                value = np.asarray(var.getncattr(name))
                if value.size != 1 or value.dtype != dtype:
                    raise fail("invalid_packing")
                if name == "valid_min":
                    lower = value.item()
                else:
                    upper = value.item()
    if any(v is not None and not math.isfinite(v) for v in (lower, upper)) or (
        lower is not None and upper is not None and lower > upper
    ):
        raise fail("invalid_packing")
    fills = []
    for name in ("_FillValue", "missing_value"):
        if name in var.ncattrs():
            value = np.asarray(var.getncattr(name))
            if value.dtype != dtype or not 1 <= value.size <= 16:
                raise fail("invalid_packing")
            fills.extend(value.reshape(-1).tolist())
    # netCDF's default fill is meaningful even without an explicit attribute.
    if "_FillValue" not in var.ncattrs():
        from netCDF4 import default_fillvals

        fills.append(default_fillvals[dtype.kind + str(dtype.itemsize)])
    return scale, offset, lower, upper, fills


def _decoded(var, key, encoding, np):
    raw = np.asarray(var[key])
    scale, offset, lower, upper, fills = encoding
    invalid = ~np.isfinite(raw)
    for fill in fills:
        invalid |= raw == fill
    if lower is not None:
        invalid |= raw < lower
    if upper is not None:
        invalid |= raw > upper
    with np.errstate(over="ignore", invalid="ignore"):
        values = raw.astype("float64") * scale + offset
    values[invalid | ~np.isfinite(values)] = np.nan
    return values


def _preflight(source, request, provenance, limits, np):
    from netCDF4 import num2date

    if source.groups or source.cmptypes or source.vltypes or source.enumtypes:
        raise fail("unsupported_grid")
    if set(source.dimensions) != set(AXES) or len(source.variables) > 512:
        raise fail("unsupported_grid")
    payload = _snapshot(source, limits.max_manifest_bytes, np)
    axes, encodings = {}, {}
    units = {"depth": "m", "latitude": "degrees_north", "longitude": "degrees_east"}
    for name in AXES:
        if name not in source.variables:
            raise fail("unsupported_grid")
        var = source[name]
        if var.dimensions != (name,) or not 0 < var.size <= limits.max_axis_values:
            raise fail("axis_limit")
        if name in units and getattr(var, "units", None) != units[name]:
            raise fail("unsupported_units")
        if (
            getattr(
                var,
                "axis",
                {"time": "T", "depth": "Z", "latitude": "Y", "longitude": "X"}[name],
            )
            != {"time": "T", "depth": "Z", "latitude": "Y", "longitude": "X"}[name]
        ):
            raise fail("unsupported_grid")
        if getattr(var, "standard_name", name) != name:
            raise fail("unsupported_grid")
        if name == "depth" and getattr(var, "positive", None) != "down":
            raise fail("unsupported_vertical")
        encodings[name] = _encoding(var, limits, np)
        values = _decoded(var, slice(None), encodings[name], np)
        if not np.isfinite(values).all() or not (np.diff(values) > 0).all():
            raise fail("invalid_coordinates")
        if name == "depth" and (values[0] < 0 or values[-1] > 12000):
            raise fail("invalid_coordinates")
        if name == "latitude" and (values[0] < -90 or values[-1] > 90):
            raise fail("invalid_coordinates")
        if name == "longitude" and (values[0] < -180 or values[-1] >= 180):
            raise fail("invalid_coordinates")
        axes[name] = values
    time_units = getattr(source["time"], "units", "")
    calendar = getattr(source["time"], "calendar", "standard")
    if calendar not in {"standard", "gregorian", "proleptic_gregorian"}:
        raise fail("unsupported_calendar")
    times = tuple(
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
        for t in num2date(axes["time"], time_units, calendar)
    )
    selection, region = request.selection, request.selection.region
    indices = {
        "time": tuple(
            i
            for i, t in enumerate(times)
            if selection.start_time <= t <= selection.end_time
        )
    }
    for name, lo, hi in (
        ("depth", selection.vertical_min, selection.vertical_max),
        ("latitude", region.south, region.north),
        ("longitude", region.west, region.east),
    ):
        indices[name] = tuple(
            int(i) for i in np.flatnonzero((axes[name] >= lo) & (axes[name] <= hi))
        )
    if any(not v for v in indices.values()):
        raise fail("no_overlap")
    info = []
    for name in request.variables:
        if name not in source.variables or source[name].dimensions != AXES:
            raise fail("unsupported_grid")
        var = source[name]
        if (getattr(var, "units", None), getattr(var, "standard_name", None)) != FIELDS[
            name
        ]:
            raise fail("unsupported_units")
        encodings[name] = _encoding(var, limits, np)
        info.append(
            ModelVariableInfo(
                source_name=name,
                units=var.units,
                standard_name=var.standard_name,
                long_name=getattr(var, "long_name", name),
                source_dtype=str(var.dtype),
                cell_methods=getattr(var, "cell_methods", "not_declared"),
                unit_long=getattr(var, "unit_long", None),
                temperature_scale="unresolved"
                if name == "thetao"
                else "not_applicable",
            )
        )
    identity = ModelIdentity(
        request=request,
        provenance=provenance,
        limits=limits,
        variables=tuple(info),
        axes=ModelAxes(
            times=tuple(times[i] for i in indices["time"]),
            depth_m=tuple(axes["depth"][list(indices["depth"])]),
            latitude=tuple(axes["latitude"][list(indices["latitude"])]),
            longitude=tuple(axes["longitude"][list(indices["longitude"])]),
            source_time_indices=indices["time"],
            source_depth_indices=indices["depth"],
            source_latitude_indices=indices["latitude"],
            source_longitude_indices=indices["longitude"],
            source_time_units=time_units,
            calendar=calendar,
        ),
    )
    if (
        math.prod(len(v) for v in indices.values()) * len(info) * 8
        > limits.max_product_file_bytes
    ):
        raise fail("product_size_limit")
    return identity, axes, indices, encodings, payload


def _write_fields(path, source, identity, axes, indices, encodings, np):
    from netCDF4 import Dataset

    with Dataset(path, "w", format="NETCDF4") as output:
        output.setncatts(
            {"model_id": identity.model_id(), "processing_version": "model_native_1"}
        )
        for name in AXES:
            output.createDimension(name, len(indices[name]))
            var = output.createVariable(name, "f8", (name,), fill_value=False)
            var[:] = axes[name][list(indices[name])]
            var.standard_name = name
            var.units = source[name].units
            if name == "time":
                var.calendar = identity.axes.calendar
            if name == "depth":
                var.positive = "down"
        ys = slice(indices["latitude"][0], indices["latitude"][-1] + 1)
        xs = slice(indices["longitude"][0], indices["longitude"][-1] + 1)
        for info in identity.variables:
            name = info.source_name
            var = output.createVariable(
                name,
                "f8",
                AXES,
                fill_value=np.nan,
                zlib=True,
                complevel=4,
                chunksizes=(
                    1,
                    1,
                    min(64, len(indices["latitude"])),
                    min(64, len(indices["longitude"])),
                ),
            )
            var.set_var_chunk_cache(
                size=identity.limits.netcdf_cache_bytes, nelems=1009, preemption=0.75
            )
            var.setncatts(
                {
                    "units": info.units,
                    "standard_name": info.standard_name,
                    "long_name": info.long_name,
                }
            )
            if info.cell_methods != "not_declared":
                var.cell_methods = info.cell_methods
            if info.unit_long is not None:
                var.unit_long = info.unit_long
            for ti, source_t in enumerate(indices["time"]):
                for zi, source_z in enumerate(indices["depth"]):
                    var[ti, zi, :, :] = _decoded(
                        source[name], (source_t, source_z, ys, xs), encodings[name], np
                    )
                    output.sync()
                    if path.stat().st_size > identity.limits.max_product_file_bytes:
                        raise fail("product_size_limit")


def _readback(path, source, identity, axes, indices, encodings, np):
    from netCDF4 import Dataset

    with Dataset(path) as output:
        if output.model_id != identity.model_id() or set(output.dimensions) != set(
            AXES
        ):
            raise fail("invalid_output")
        for name in AXES:
            if (
                output[name].dimensions != (name,)
                or not np.array_equal(output[name][:], axes[name][list(indices[name])])
                or output[name].units != source[name].units
            ):
                raise fail("invalid_output")
            if (
                str(output[name].dtype) != "float64"
                or output[name].standard_name != name
            ):
                raise fail("invalid_output")
        if (
            output["time"].calendar != identity.axes.calendar
            or output["depth"].positive != "down"
        ):
            raise fail("invalid_output")
        ys = slice(indices["latitude"][0], indices["latitude"][-1] + 1)
        xs = slice(indices["longitude"][0], indices["longitude"][-1] + 1)
        for info in identity.variables:
            var = output[info.source_name]
            if (
                var.standard_name != info.standard_name
                or getattr(var, "cell_methods", "not_declared") != info.cell_methods
            ):
                raise fail("invalid_output")
            if (
                var.dimensions != AXES
                or str(var.dtype) != "float64"
                or var.units != info.units
            ):
                raise fail("invalid_output")
            if any(
                a in var.ncattrs()
                for a in (
                    "scale_factor",
                    "add_offset",
                    "valid_min",
                    "valid_max",
                    "valid_range",
                )
            ):
                raise fail("invalid_output")
            var.set_var_chunk_cache(
                size=identity.limits.netcdf_cache_bytes, nelems=1009, preemption=0.75
            )
            for ti, st in enumerate(indices["time"]):
                for zi, sz in enumerate(indices["depth"]):
                    expected = _decoded(
                        source[info.source_name],
                        (st, sz, ys, xs),
                        encodings[info.source_name],
                        np,
                    )
                    observed = np.ma.filled(var[ti, zi, :, :], np.nan)
                    if not np.array_equal(expected, observed, equal_nan=True):
                        raise fail("invalid_output")


def prepare_model(request: ModelPreparationRequest, root: Path) -> ModelManifest:
    """Validate, prepare and re-read a local selection without overwriting."""
    stage = None
    try:
        import numpy as np
        from netCDF4 import Dataset

        request = ModelPreparationRequest.model_validate_json(request.model_dump_json())
        limits = ModelLimits.model_validate(load_limits(root).model_dump())
        relative = f"data/raw/acquisitions/{request.acquisition_id}"
        source_path = private_path(root, relative + "/input.nc")
        manifest_path = private_path(root, relative + "/manifest.json")
        manifest_record = describe_file(manifest_path, 65536)
        acquired = read_acquisition(root, request.acquisition_id)
        aq = acquired.request
        if (
            aq.provider != "copernicus"
            or acquired.source_id != "copernicus"
            or acquired.dataset_id != "copernicus_global_multiyear_phy"
            or acquired.source_version != aq.provider_version
            or aq.coordinates is None
            or aq.coordinates.model_dump() != dict(zip(AXES, AXES, strict=True))
            or not set(request.variables) <= set(aq.variables)
        ):
            raise fail("unsupported_source")
        input_record = describe_file(source_path, 134217728)
        if input_record != acquired.input_file:
            raise fail("input_changed")
        provenance = ModelProvenance(
            acquisition_id=request.acquisition_id,
            acquisition_manifest_sha256=manifest_record.sha256,
            input_sha256=input_record.sha256,
            input_size_bytes=input_record.size_bytes,
            dataset_id=acquired.dataset_id,
            provider_dataset_id=aq.provider_dataset_id,
            source_version=acquired.source_version,
            client=acquired.client,
            client_version=acquired.client_version,
            client_processing=acquired.client_processing,
            retrieved_at=acquired.retrieved_at,
            data_mode=acquired.data_mode,
        )
        with Dataset(source_path, "r") as source:
            identity, axes, indices, encodings, snapshot = _preflight(
                source, request, provenance, limits, np
            )
            parent = private_path(root, "data/models")
            parent.mkdir(parents=True, exist_ok=True)
            target = private_path(root, "data/models/" + identity.model_id())
            if target.exists():
                saved = ModelManifest.model_validate(
                    read_json(
                        private_path(
                            root, f"data/models/{identity.model_id()}/manifest.json"
                        ),
                        limits.max_manifest_bytes,
                    )
                )
                if saved.identity != identity:
                    raise fail("model_conflict")
                for name, record in (
                    ("fields.nc", saved.scientific_file),
                    ("source_metadata.json", saved.source_metadata_file),
                ):
                    path = private_path(
                        root, f"data/models/{identity.model_id()}/{name}"
                    )
                    if (
                        describe_file(
                            path,
                            max(
                                limits.max_product_file_bytes, limits.max_manifest_bytes
                            ),
                        )
                        != record
                    ):
                        raise fail("model_conflict")
                if (target / "source_metadata.json").read_bytes() != snapshot:
                    raise fail("model_conflict")
                _readback(
                    target / "fields.nc", source, identity, axes, indices, encodings, np
                )
                result = saved
            else:
                if (
                    len(list(islice(parent.iterdir(), limits.max_products)))
                    >= limits.max_products
                ):
                    raise fail("model_limit")
                stage = Path(tempfile.mkdtemp(prefix=".prepare_", dir=parent))
                (stage / "source_metadata.json").write_bytes(snapshot)
                _write_fields(
                    stage / "fields.nc", source, identity, axes, indices, encodings, np
                )
                _readback(
                    stage / "fields.nc", source, identity, axes, indices, encodings, np
                )
                result = ModelManifest(
                    model_id=identity.model_id(),
                    identity=identity,
                    created_at=datetime.now(UTC),
                    scientific_file=describe_file(
                        stage / "fields.nc", limits.max_product_file_bytes
                    ),
                    source_metadata_file=describe_file(
                        stage / "source_metadata.json", limits.max_manifest_bytes
                    ),
                )
                (stage / "manifest.json").write_bytes(serialize_model_manifest(result))
        if (
            describe_file(source_path, 134217728) != input_record
            or describe_file(manifest_path, 65536) != manifest_record
        ):
            raise fail("input_changed")
        if stage is not None:
            # Exclusive publication lock; no queue or replacement of existing data.
            lock = private_path(root, "data/models/.publish.lock")
            owned_lock = False
            try:
                with lock.open("xb"):
                    owned_lock = True
                    if target.exists():
                        raise fail("model_conflict")
                    os.rename(stage, target)
                    stage = None
            except FileExistsError:
                raise fail("model_busy") from None
            finally:
                # Only remove our lock, never one owned by another process.
                if owned_lock:
                    lock.unlink(missing_ok=True)
        return result
    except ProductError:
        raise
    except (
        ValidationError,
        ValueError,
        TypeError,
        OSError,
        RuntimeError,
        KeyError,
        AttributeError,
        OverflowError,
    ):
        raise fail("invalid_model") from None
    finally:
        if stage is not None:
            # Only this invocation's temporary outputs; never recursive raw cleanup.
            for name in ("fields.nc", "source_metadata.json", "manifest.json"):
                (stage / name).unlink(missing_ok=True)
            stage.rmdir()
