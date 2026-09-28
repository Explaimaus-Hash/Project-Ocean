"""Verify a saved static read set offline and reproduce its selected arrays."""

import hashlib
import json
import math
import re
from pathlib import Path

from ..ingestion.static_support import (
    BASE,
    DATASET,
    MAX_CHUNK,
    NAMES,
    ChunkReader,
    layouts,
    select_axes,
    validate_values,
)
from ..processing.prepare_model import private_path
from ..schemas.static_support import StaticManifest, StaticSupportSnapshot
from ..storage.product_common import ProductError, describe_file
from .model_reader import read_native_field


def fail(code):
    raise ProductError(code, "Saved static input verification did not complete.")


def bounded_bytes(path, limit):
    with path.open("rb") as stream:
        content = stream.read(limit + 1)
    if len(content) > limit:
        fail("static_file_limit")
    return content


def verify_subset(path, metadata, arrays):
    """Reject changed interpretation even if an operator recomputed file hashes."""
    import numpy as np
    from netCDF4 import Dataset

    with Dataset(path, "r") as ds:
        ds.set_auto_maskandscale(False)
        expected_globals = {
            "source_dataset": DATASET,
            "source_asset": BASE,
            "interpretation": "native_source_subset_not_matching_ready",
        }
        if (
            ds.groups
            or ds.cmptypes
            or ds.vltypes
            or ds.enumtypes
            or set(ds.dimensions) != set(NAMES[:3])
            or set(ds.variables) != set(NAMES)
            or set(ds.ncattrs()) != set(expected_globals)
            or any(ds.getncattr(k) != v for k, v in expected_globals.items())
            or any(
                ds.dimensions[n].isunlimited()
                or len(ds.dimensions[n]) != len(arrays[n])
                for n in NAMES[:3]
            )
        ):
            fail("static_subset_header_mismatch")
        for name in NAMES:
            var = ds[name]
            attrs = dict(metadata["metadata"][f"{name}/.zattrs"])
            dims = tuple(attrs.pop("_ARRAY_DIMENSIONS"))
            encoding = metadata["metadata"][f"{name}/.zarray"]
            fill = encoding["fill_value"]
            if fill is not None:
                attrs["_FillValue"] = np.float32(np.nan if fill == "NaN" else fill)
            if (
                var.dimensions != dims
                or var.shape != arrays[name].shape
                or var.dtype != arrays[name].dtype
                or set(var.ncattrs()) != set(attrs)
            ):
                fail("static_subset_header_mismatch")
            for key, expected in attrs.items():
                actual = var.getncattr(key)
                matches = np.array_equal(
                    actual, expected, equal_nan=key == "_FillValue"
                )
                if not matches:
                    fail("static_subset_attribute_mismatch")
            chunks = var.chunking()
            if (
                isinstance(chunks, (list, tuple))
                and math.prod(chunks) * var.dtype.itemsize > MAX_CHUNK
            ):
                fail("static_subset_chunk_limit")
            var.set_var_chunk_cache(size=MAX_CHUNK, nelems=1009, preemption=0.75)
            if not np.array_equal(var[:], arrays[name]):
                fail("static_subset_values_mismatch")


def read_static_support(
    root: Path, support_id: str, model_id: str
) -> StaticSupportSnapshot:
    """Read-only, no source acquisition, no observation/collocation assumptions."""
    if (
        not isinstance(support_id, str)
        or not re.fullmatch(r"b_[a-f0-9]{24}", support_id)
        or not isinstance(model_id, str)
        or not re.fullmatch(r"m_[a-f0-9]{24}", model_id)
    ):
        fail("invalid_static_identity")
    relative = f"data/raw/static_copernicus/{support_id}"
    manifest_path = private_path(root, relative + "/manifest.json")
    manifest_file = describe_file(manifest_path, 65536)
    raw = bounded_bytes(manifest_path, 65536)
    digest = hashlib.sha256(raw).hexdigest()
    if digest != manifest_file.sha256 or support_id != "b_" + digest[:24]:
        fail("static_manifest_identity_mismatch")
    m = StaticManifest.model_validate_json(raw)
    if m.model_id != model_id or m.source_asset != BASE:
        fail("static_model_binding_mismatch")
    field = read_native_field(root, model_id, "so")
    p = field.manifest.identity.provenance
    if (
        field.manifest_file != m.model_manifest
        or p.data_mode != m.data_mode
        or p.source_version != "202311"
        or p.provider_dataset_id != "cmems_mod_glo_phy_my_0.083deg_P1D-m"
    ):
        fail("static_model_binding_mismatch")
    paths = {
        key: private_path(root, relative + "/source_read_set/" + key)
        for key in m.source_read_set
    }
    identities = {}
    for key, record in m.source_read_set.items():
        limit = (
            1048576
            if key
            in {
                "catalogue.json",
                "catalogue_end.json",
                ".zmetadata",
                "metadata_end.json",
            }
            else MAX_CHUNK + 16
        )
        info = describe_file(paths[key], limit)
        if (info.sha256, info.size_bytes) != (record.sha256, record.size_bytes):
            fail("static_source_object_mismatch")
        identities[key] = info
    subset_path = private_path(root, relative + "/subset.nc")
    if describe_file(subset_path, 4194304) != m.subset:
        fail("static_subset_identity_mismatch")
    used = set()

    def get(key):
        if key not in paths or key in used:
            fail("static_read_set_incomplete")
        used.add(key)
        content = bounded_bytes(paths[key], identities[key].size_bytes)
        if hashlib.sha256(content).hexdigest() != identities[key].sha256:
            fail("static_input_changed")
        return content

    cat_bytes, meta_bytes = get("catalogue.json"), get(".zmetadata")
    if get("catalogue_end.json") != cat_bytes or get("metadata_end.json") != meta_bytes:
        fail("static_source_metadata_changed")
    cat, metadata = json.loads(cat_bytes), json.loads(meta_bytes)
    if cat["id"] != DATASET or cat["assets"]["static"]["href"] != BASE.rstrip("/"):
        fail("static_catalogue_mismatch")
    reader = ChunkReader(get, layouts(metadata))
    axes, selection = select_axes(reader, field.manifest.identity.axes)
    lat, lon = selection["latitude"], selection["longitude"]
    if (
        tuple(lat) != m.source_latitude_indices
        or tuple(lon) != m.source_longitude_indices
    ):
        fail("static_native_indices_mismatch")
    arrays = {
        "elevation": axes["elevation"],
        "latitude": axes["latitude"][lat],
        "longitude": axes["longitude"][lon],
        "mask": reader.read("mask", [range(50), lat, lon]),
        "deptho": reader.read("deptho", [lat, lon]),
        "deptho_lev": reader.read("deptho_lev", [lat, lon]),
    }
    if used != paths.keys() or reader.decoded != m.decoded_chunk_bytes:
        fail("static_read_set_count_mismatch")
    checks = validate_values(arrays["mask"], arrays["deptho"], arrays["deptho_lev"])
    if checks != m.checks.model_dump():
        fail("static_checks_mismatch")
    verify_subset(subset_path, metadata, arrays)
    if read_native_field(root, model_id, "so") != field:
        fail("static_model_changed")
    if (
        describe_file(manifest_path, 65536) != manifest_file
        or describe_file(subset_path, 4194304) != m.subset
    ):
        fail("static_input_changed")
    for key, path in paths.items():
        if describe_file(path, MAX_CHUNK + 16) != identities[key]:
            fail("static_input_changed")
    import numpy as np

    def bottom(name):
        fill = np.float32(metadata["metadata"][f"{name}/.zarray"]["fill_value"])
        return tuple(
            float(v) if np.isfinite(v) and v != fill else None
            for v in arrays[name].flat
        )

    z = tuple(map(float, arrays["elevation"]))
    return StaticSupportSnapshot(
        support_id=support_id,
        manifest_file=manifest_file,
        manifest=m,
        model_axes=field.manifest.identity.axes,
        source_elevation_m=z,
        model_depth_to_source_elevation_index=tuple(
            z.index(-depth) for depth in field.manifest.identity.axes.depth_m
        ),
        mask=tuple(map(int, arrays["mask"].flat)),
        deptho_m=bottom("deptho"),
        deptho_lev=bottom("deptho_lev"),
    )
