"""Read-only prepared fields; no acquisition, repair or support inference."""

import math
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import ValidationError

from ..processing.prepare_model import private_path
from ..schemas.model_metadata import ModelSourceMetadata
from ..schemas.model_reading import MAX_FIELD_VALUES, NativeFieldSnapshot
from ..schemas.models import ModelManifest
from ..storage.product_common import ProductError, describe_file, read_json

AXES = ("time", "depth", "latitude", "longitude")
ACTIVE_ENCODING = {
    "scale_factor",
    "add_offset",
    "valid_min",
    "valid_max",
    "valid_range",
    "_Unsigned",
    "missing_value",
}
AXIS_ATTRIBUTES = {"standard_name", "units"}
FIELD_ATTRIBUTES = {
    "_FillValue",
    "units",
    "standard_name",
    "long_name",
    "cell_methods",
    "unit_long",
}


def _fail(code: str) -> ProductError:
    return ProductError(code, "Native model read failed validation: " + code + ".")


def _metadata_matches(metadata, manifest):
    axes = manifest.identity.axes
    indices = (
        axes.source_time_indices,
        axes.source_depth_indices,
        axes.source_latitude_indices,
        axes.source_longitude_indices,
    )
    for info in manifest.identity.variables:
        source = metadata.variables.get(info.source_name)
        if source is None or source.dimensions != AXES or len(source.shape) != 4:
            raise _fail("model_metadata_mismatch")
        if source.dtype != info.source_dtype or any(
            index[-1] >= size for index, size in zip(indices, source.shape, strict=True)
        ):
            raise _fail("model_metadata_mismatch")
        for name, expected, fallback in (
            ("units", info.units, None),
            ("standard_name", info.standard_name, None),
            ("long_name", info.long_name, info.source_name),
            ("cell_methods", info.cell_methods, "not_declared"),
            ("unit_long", info.unit_long, None),
        ):
            attribute = source.attributes.get(name)
            if attribute is None:
                actual = fallback
            elif len(attribute.values) == 1 and isinstance(attribute.values[0], str):
                actual = attribute.values[0]
            else:
                raise _fail("model_metadata_mismatch")
            if actual != expected:
                raise _fail("model_metadata_mismatch")


def _read_fields(path, manifest, selected):
    import numpy as np
    from netCDF4 import Dataset, num2date

    identity = manifest.identity
    axes = identity.axes
    shape = tuple(map(len, (axes.times, axes.depth_m, axes.latitude, axes.longitude)))
    with Dataset(path, "r") as ds:
        ds.set_auto_maskandscale(False)
        if (
            ds.groups
            or ds.cmptypes
            or ds.vltypes
            or ds.enumtypes
            or set(ds.dimensions) != set(AXES)
            or set(ds.variables) != set(AXES) | set(identity.request.variables)
            or getattr(ds, "model_id", None) != manifest.model_id
            or getattr(ds, "processing_version", None) != "model_native_1"
            or any(ds.dimensions[name].isunlimited() for name in AXES)
            or tuple(len(ds.dimensions[name]) for name in AXES) != shape
        ):
            raise _fail("model_header_mismatch")
        for name, size in zip(AXES, shape, strict=True):
            var = ds[name]
            allowed = AXIS_ATTRIBUTES | (
                {"calendar"}
                if name == "time"
                else {"positive"}
                if name == "depth"
                else set()
            )
            if (
                var.dimensions != (name,)
                or var.shape != (size,)
                or str(var.dtype) != "float64"
                or set(var.ncattrs()) & (ACTIVE_ENCODING | {"_FillValue"})
                or not set(var.ncattrs()) <= allowed
                or getattr(var, "standard_name", None) != name
            ):
                raise _fail("model_axes_mismatch")
            var.set_var_chunk_cache(
                size=identity.limits.netcdf_cache_bytes, nelems=1009, preemption=0.75
            )
            actual = np.asarray(var[:])
            if not np.isfinite(actual).all():
                raise _fail("model_axes_mismatch")
            if name == "time":
                if (
                    getattr(var, "units", None) != axes.source_time_units
                    or getattr(var, "calendar", None) != axes.calendar
                ):
                    raise _fail("model_axes_mismatch")
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
                    for t in num2date(actual, axes.source_time_units, axes.calendar)
                )
                if times != axes.times:
                    raise _fail("model_axes_mismatch")
            else:
                expected, units = {
                    "depth": (axes.depth_m, "m"),
                    "latitude": (axes.latitude, "degrees_north"),
                    "longitude": (axes.longitude, "degrees_east"),
                }[name]
                if getattr(var, "units", None) != units or not np.array_equal(
                    actual, expected
                ):
                    raise _fail("model_axes_mismatch")
                if name == "depth" and getattr(var, "positive", None) != "down":
                    raise _fail("model_axes_mismatch")
        for info in identity.variables:
            var = ds[info.source_name]
            if (
                var.dimensions != AXES
                or var.shape != shape
                or str(var.dtype) != "float64"
                or set(var.ncattrs()) & ACTIVE_ENCODING
                or not set(var.ncattrs()) <= FIELD_ATTRIBUTES
                or getattr(var, "units", None) != info.units
                or getattr(var, "standard_name", None) != info.standard_name
                or getattr(var, "long_name", None) != info.long_name
                or getattr(var, "cell_methods", "not_declared") != info.cell_methods
                or getattr(var, "unit_long", None) != info.unit_long
                or not isinstance(
                    getattr(var, "_FillValue", None), (float, np.floating)
                )
                or not math.isnan(var._FillValue)
            ):
                raise _fail("model_field_mismatch")
            chunks = var.chunking()
            if (
                isinstance(chunks, (tuple, list))
                and math.prod(chunks) * 8 > identity.limits.max_source_chunk_bytes
            ):
                raise _fail("model_chunk_limit")
        var = ds[selected]
        var.set_var_chunk_cache(
            size=identity.limits.netcdf_cache_bytes, nelems=1009, preemption=0.75
        )
        values = []
        for ti in range(shape[0]):
            for zi in range(shape[1]):
                slab = np.asarray(var[ti, zi, :, :])
                values.extend(
                    float(value) if np.isfinite(value) else None for value in slab.flat
                )
        return tuple(values)


def read_native_field(
    root: Path, model_id: str, source_variable: Literal["so", "thetao"]
) -> NativeFieldSnapshot:
    """Verify all prepared files and read one bounded native field in C order.

    Input hashes/stat detect ordinary concurrent changes, not adversarial races.
    Values retain source definitions; a validity mask is not wet/bottom evidence.
    """
    try:
        if not isinstance(model_id, str) or not re.fullmatch(
            r"m_[a-f0-9]{24}", model_id
        ):
            raise _fail("invalid_model_id")
        if source_variable not in {"so", "thetao"}:
            raise _fail("unsupported_model_variable")
        relative = f"data/models/{model_id}/"
        paths = {
            name: private_path(root, relative + name)
            for name in ("manifest.json", "source_metadata.json", "fields.nc")
        }
        manifest_file = describe_file(paths["manifest.json"], 1048576)
        manifest = ModelManifest.model_validate(
            read_json(paths["manifest.json"], 1048576)
        )
        if manifest.model_id != model_id:
            raise _fail("model_identity_mismatch")
        identity, axes = manifest.identity, manifest.identity.axes
        if manifest_file.size_bytes > identity.limits.max_manifest_bytes:
            raise _fail("model_metadata_limit")
        if (
            math.prod(
                map(len, (axes.times, axes.depth_m, axes.latitude, axes.longitude))
            )
            > MAX_FIELD_VALUES
        ):
            raise _fail("model_field_limit")
        if source_variable not in identity.request.variables:
            raise _fail("unsupported_model_variable")
        expected = {
            "manifest.json": (manifest_file, identity.limits.max_manifest_bytes),
            "source_metadata.json": (
                manifest.source_metadata_file,
                identity.limits.max_manifest_bytes,
            ),
            "fields.nc": (
                manifest.scientific_file,
                identity.limits.max_product_file_bytes,
            ),
        }
        for name, (record, limit) in expected.items():
            if describe_file(paths[name], limit) != record:
                raise _fail("model_input_changed")
        metadata = ModelSourceMetadata.model_validate(
            read_json(paths["source_metadata.json"], identity.limits.max_manifest_bytes)
        )
        _metadata_matches(metadata, manifest)
        values = _read_fields(paths["fields.nc"], manifest, source_variable)
        for name, (record, limit) in expected.items():
            if (
                private_path(root, relative + name) != paths[name]
                or describe_file(paths[name], limit) != record
            ):
                raise _fail("model_input_changed")
        return NativeFieldSnapshot(
            manifest=manifest,
            manifest_file=manifest_file,
            source_variable=source_variable,
            values=values,
            valid_mask=tuple(value is not None for value in values),
        )
    except ProductError:
        raise
    except (
        ValidationError,
        OSError,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        RuntimeError,
        OverflowError,
    ):
        raise _fail("invalid_native_model") from None
