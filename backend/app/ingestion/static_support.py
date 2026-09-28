"""Narrow, operator-only public GLORYS static acquisition; never matching evidence.

Retains the exact compressed read set, not a complete global Zarr store. Decodes
one bounded chunk at a time, subsets without interpolation and publishes last.
"""

import hashlib
import itertools
import json
import math
import os
import re
import ssl
import struct
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import HTTPSHandler, Request, build_opener

from ..comparison.model_reader import read_native_field
from ..processing.prepare_model import private_path
from ..storage.product_common import ProductError, describe_file
from .base import NoRedirect

DATASET = "cmems_mod_glo_phy_my_0.083deg_static_202311--ext--bathy"
CATALOGUE = (
    "https://s3.waw3-1.cloudferro.com/mdl-metadata/metadata/"
    f"GLOBAL_MULTIYEAR_PHY_001_030/{DATASET}/dataset.stac.json"
)
BASE = (
    "https://s3.waw3-1.cloudferro.com/mdl-arco-time-026/arco/"
    f"GLOBAL_MULTIYEAR_PHY_001_030/{DATASET}/static.zarr/"
)
MAX_TRANSFER = 64 * 1024 * 1024
MAX_DECODED = 128 * 1024 * 1024
MAX_CHUNK = 4 * 1024 * 1024
KEY = re.compile(r"^(elevation|latitude|longitude|mask|deptho|deptho_lev)/\d+(\.\d+)*$")
NAMES = ("elevation", "latitude", "longitude", "mask", "deptho", "deptho_lev")


def reject(code="unsupported_static_source"):
    raise ProductError(
        code, "Static support acquisition/verification did not complete."
    )


class PublicReadSet:
    """No credentials, redirects, retries, arbitrary URLs or global-file fallback."""

    def __init__(self, stage: Path):
        import certifi

        self.stage = stage
        self.total = 0
        self.records = {}
        self.deadline = time.monotonic() + 160
        self.opener = build_opener(
            NoRedirect(),
            HTTPSHandler(context=ssl.create_default_context(cafile=certifi.where())),
        )

    def get(self, key: str) -> bytes:
        special = {
            "catalogue.json",
            ".zmetadata",
            "catalogue_end.json",
            "metadata_end.json",
        }
        if key not in special and not KEY.fullmatch(key):
            reject("unsafe_static_key")
        if key in self.records or len(self.records) >= 128:
            reject("static_request_limit")
        limit = 1048576 if key in special else MAX_CHUNK + 16
        if key in {"catalogue.json", "catalogue_end.json"}:
            url = CATALOGUE
        else:
            url = BASE + (".zmetadata" if key == "metadata_end.json" else key)
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            reject("static_deadline")
        request = Request(url, headers={"Accept-Encoding": "identity"})
        with self.opener.open(request, timeout=min(15, remaining)) as response:
            declared = response.headers.get("Content-Length")
            if (
                response.status != 200
                or response.headers.get("Content-Encoding", "identity") != "identity"
            ):
                reject("static_transport")
            if declared is not None and not 0 < int(declared) <= limit:
                reject("static_transfer_limit")
            blocks = []
            size = 0
            while True:
                if time.monotonic() > self.deadline:
                    reject("static_deadline")
                block = response.read(min(65536, limit - size + 1))
                if not block:
                    break
                size += len(block)
                self.total += len(block)
                if size > limit or self.total > MAX_TRANSFER:
                    reject("static_transfer_limit")
                blocks.append(block)
            if not size or (declared is not None and size != int(declared)):
                reject("static_incomplete_response")
        content = b"".join(blocks)
        target = self.stage / "source_read_set" / key
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(content)
        self.records[key] = {
            "sha256": hashlib.sha256(content).hexdigest(),
            "size_bytes": size,
        }
        return content


def layouts(metadata):
    """Whitelist the inspected encoding before any field chunk is requested."""
    if metadata.get("zarr_consolidated_format") != 1:
        reject()
    source = metadata["metadata"]
    if set(source) != {".zattrs", ".zgroup"} | {
        f"{name}/{kind}" for name in NAMES for kind in (".zarray", ".zattrs")
    } or source[".zgroup"] != {"zarr_format": 2}:
        reject()
    dimensions = {
        "elevation": ["elevation"],
        "latitude": ["latitude"],
        "longitude": ["longitude"],
        "mask": ["elevation", "latitude", "longitude"],
        "deptho": ["latitude", "longitude"],
        "deptho_lev": ["latitude", "longitude"],
    }
    standards = {
        "elevation": ("depth", "m"),
        "latitude": ("latitude", "degrees_north"),
        "longitude": ("longitude", "degrees_east"),
        "mask": ("sea_binary_mask", "1"),
        "deptho": ("sea_floor_depth_below_geoid", "m"),
        "deptho_lev": ("model_level_number_at_sea_floor", "1"),
    }
    result = {}
    for name in NAMES:
        a, attrs = source[f"{name}/.zarray"], source[f"{name}/.zattrs"]
        dims = dimensions[name]
        if (
            a.get("zarr_format") != 2
            or a.get("dtype") != ("|i1" if name == "mask" else "<f4")
            or a.get("order") != "C"
            or a.get("filters") is not None
            or a.get("dimension_separator", ".") != "."
            or a.get("compressor")
            != {
                "id": "blosc",
                "cname": "lz4",
                "clevel": 5,
                "shuffle": 1,
                "blocksize": 0,
            }
            or attrs.get("_ARRAY_DIMENSIONS") != dims
            or (attrs.get("standard_name"), attrs.get("units")) != standards[name]
            or set(attrs)
            - {
                "_ARRAY_DIMENSIONS",
                "standard_name",
                "units",
                "long_name",
                "axis",
                "positive",
                "step",
            }
        ):
            reject()
        for axis in ("shape", "chunks"):
            values = a[axis]
            if len(values) != len(dims) or any(
                type(v) is not int or not 0 < v <= 5000 for v in values
            ):
                reject()
        if math.prod(a["chunks"]) * (1 if name == "mask" else 4) > MAX_CHUNK:
            reject("static_chunk_limit")
        if name in ("elevation", "latitude", "longitude") and a["chunks"] != a["shape"]:
            reject()
        if name == "mask" and (a["fill_value"] is not None or a["shape"][0] != 50):
            reject()
        if name in ("deptho", "deptho_lev") and a["fill_value"] != 9.969209968386869e36:
            reject()
        if name in ("elevation", "latitude", "longitude") and a["fill_value"] != "NaN":
            reject()
        result[name] = a
    sizes = {n: result[n]["shape"][0] for n in NAMES[:3]}
    if (
        sizes["elevation"] != 50
        or source["elevation/.zattrs"].get("positive") != "down"
    ):
        reject()
    if source["mask/.zattrs"].get("long_name") != "Land-sea mask: 1 = sea ; 0 = land":
        reject()
    for name in NAMES:
        if result[name]["shape"] != [sizes[d] for d in dimensions[name]]:
            reject()
    return result


class ChunkReader:
    def __init__(self, get, layout):
        self.get = get
        self.layout = layout
        self.decoded = 0

    def read(self, name, indices):
        """Cartesian native indices; missing remote chunks fail, never become dry."""
        import numpy as np
        from numcodecs import Blosc

        a = self.layout[name]
        dtype = np.dtype(a["dtype"])
        if len(indices) != len(a["shape"]):
            reject()
        if any(
            not len(ix) or any(i < 0 or i >= n for i in ix)
            for ix, n in zip(indices, a["shape"], strict=True)
        ):
            reject()
        if math.prod(map(len, indices)) > 250000:
            reject("static_selection_limit")
        out = np.empty(tuple(map(len, indices)), dtype=dtype)
        groups = [
            sorted({int(i) // c for i in ix})
            for ix, c in zip(indices, a["chunks"], strict=True)
        ]
        for chunk_index in itertools.product(*groups):
            size = math.prod(a["chunks"]) * dtype.itemsize
            self.decoded += size
            if size > MAX_CHUNK or self.decoded > MAX_DECODED:
                reject("static_decoded_limit")
            encoded = self.get(name + "/" + ".".join(map(str, chunk_index)))
            if len(encoded) < 16:
                reject("static_chunk_corrupt")
            nbytes, _, cbytes = struct.unpack_from("<III", encoded, 4)
            if nbytes != size or cbytes != len(encoded):
                reject("static_chunk_corrupt")
            decoded = bytearray(size)
            Blosc().decode(encoded, out=decoded)
            values = np.frombuffer(decoded, dtype=dtype).reshape(a["chunks"])
            positions = [
                np.flatnonzero(np.asarray(ix) // c == ci)
                for ix, c, ci in zip(indices, a["chunks"], chunk_index, strict=True)
            ]
            offsets = [
                np.asarray(ix)[pos] % c
                for ix, pos, c in zip(indices, positions, a["chunks"], strict=True)
            ]
            out[np.ix_(*positions)] = values[np.ix_(*offsets)]
        return out


def select_axes(reader, model_axes):
    import numpy as np

    axes = {n: reader.read(n, [range(reader.layout[n]["shape"][0])]) for n in NAMES[:3]}
    for values in axes.values():
        if not np.isfinite(values).all() or not (np.diff(values) > 0).all():
            reject("static_axis_invalid")
    if not (axes["elevation"] < 0).all():
        reject("static_elevation_unsupported")
    selected = {}
    for name, target in (
        ("latitude", model_axes.latitude),
        ("longitude", model_axes.longitude),
    ):
        if len(target) > 25:
            reject("static_selection_limit")
        indices = np.flatnonzero(
            (axes[name] >= min(target)) & (axes[name] <= max(target))
        )
        if not np.array_equal(axes[name][indices], target):
            reject("static_model_grid_mismatch")
        selected[name] = indices
    depth = -axes["elevation"][::-1]
    if any(np.count_nonzero(depth == value) != 1 for value in model_axes.depth_m):
        reject("static_model_depth_mismatch")
    return axes, selected


def validate_values(mask, deptho, levels):
    """Check structure only; bottom-level numbering/datum are NOT promoted."""
    import numpy as np

    if not np.isin(mask, [0, 1]).all():
        reject("static_mask_invalid")
    # Source elevation order is deepest to shallowest: wet must not become dry.
    if (np.diff(mask.astype("int16"), axis=0) < 0).any():
        reject("static_mask_noncontiguous")
    fill = np.float32(9.969209968386869e36)
    wet = mask[-1] == 1
    for data in (deptho, levels):
        valid = np.isfinite(data) & (data != fill)
        if (wet & ~valid).any():
            reject("static_bottom_missing")
    if (deptho[wet] <= 0).any() or not np.equal(
        levels[wet], np.floor(levels[wet])
    ).all():
        reject("static_bottom_invalid")
    if ((levels[wet] < 0) | (levels[wet] > 50)).any():
        reject("static_bottom_invalid")
    return {
        "surface_wet_count": int(wet.sum()),
        "surface_dry_count": int((~wet).sum()),
        "wet_level_count_equals_deptho_lev": bool(
            np.array_equal(mask.sum(axis=0)[wet], levels[wet])
        ),
        "bottom_level_numbering": "unresolved_not_inferred_from_numeric_agreement",
        "vertical_reference": "unresolved",
        "coastline_connectivity": "not_evaluated",
    }


def acquire_static(root: Path, model_id: str):
    """Explicit acquisition, immutable new directory; failed stages stay private."""
    import netCDF4
    import numpy as np

    field = read_native_field(root, model_id, "so")
    p = field.manifest.identity.provenance
    if (p.provider_dataset_id, p.source_version) != (
        "cmems_mod_glo_phy_my_0.083deg_P1D-m",
        "202311",
    ):
        reject("static_model_source_mismatch")
    parent = private_path(root, "data/raw/static_copernicus")
    parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".static_", dir=parent))
    transport = PublicReadSet(stage)
    catalogue_bytes = transport.get("catalogue.json")
    catalogue = json.loads(catalogue_bytes)
    if catalogue["id"] != DATASET or catalogue["assets"]["static"][
        "href"
    ] != BASE.rstrip("/"):
        reject("static_catalogue_changed")
    metadata_bytes = transport.get(".zmetadata")
    metadata = json.loads(metadata_bytes)
    reader = ChunkReader(transport.get, layouts(metadata))
    axes, selection = select_axes(reader, field.manifest.identity.axes)
    indices = [selection["latitude"], selection["longitude"]]
    values = {
        "mask": reader.read("mask", [range(50), *indices]),
        "deptho": reader.read("deptho", indices),
        "deptho_lev": reader.read("deptho_lev", indices),
    }
    checks = validate_values(values["mask"], values["deptho"], values["deptho_lev"])
    subset = stage / "subset.nc"
    arrays = {
        "elevation": axes["elevation"],
        "latitude": axes["latitude"][indices[0]],
        "longitude": axes["longitude"][indices[1]],
        **values,
    }
    with netCDF4.Dataset(subset, "w", format="NETCDF4") as ds:
        for name in NAMES[:3]:
            ds.createDimension(name, len(arrays[name]))
        for name, data in arrays.items():
            attrs = dict(metadata["metadata"][f"{name}/.zattrs"])
            dims = attrs.pop("_ARRAY_DIMENSIONS")
            fill = reader.layout[name]["fill_value"]
            fill = False if fill is None else (np.nan if fill == "NaN" else fill)
            v = ds.createVariable(name, data.dtype, dims, fill_value=fill, zlib=True)
            v.setncatts(attrs)
            v[:] = data
        ds.source_dataset = DATASET
        ds.source_asset = BASE
        ds.interpretation = "native_source_subset_not_matching_ready"
    with netCDF4.Dataset(subset) as ds:
        ds.set_auto_maskandscale(False)
        for name, data in arrays.items():
            if not np.array_equal(ds[name][:], data):
                reject("static_readback_failed")
    if read_native_field(root, model_id, "so") != field:
        reject("static_model_changed")
    if (
        transport.get("catalogue_end.json") != catalogue_bytes
        or transport.get("metadata_end.json") != metadata_bytes
    ):
        reject("static_remote_metadata_changed")
    # Recheck saved objects without assuming ETags are hashes. This does not
    # authenticate the publisher or guarantee remote chunks were immutable.
    for key, record in transport.records.items():
        info = describe_file(stage / "source_read_set" / key, MAX_CHUNK + 16)
        if info.sha256 != record["sha256"] or info.size_bytes != record["size_bytes"]:
            reject("static_saved_object_changed")
    manifest = {
        "schema_version": 1,
        "processing_version": "static_acquisition_1",
        "status": "acquired_grid_checked_not_matching_ready",
        "data_mode": p.data_mode,
        "model_id": model_id,
        "model_manifest": field.manifest_file.model_dump(mode="json"),
        "dataset_id": DATASET,
        "source_asset": BASE,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "source_read_set": transport.records,
        "source_read_set_is_complete_global_store": False,
        "source_latitude_indices": indices[0].tolist(),
        "source_longitude_indices": indices[1].tolist(),
        "source_elevation_indices": list(range(50)),
        "axis_interpretation": "original_negative_elevation_and_attributes_preserved",
        "transfer_bytes": transport.total,
        "decoded_chunk_bytes": reader.decoded,
        "subset": describe_file(subset, 4 * 1024 * 1024).model_dump(mode="json"),
        "checks": checks,
        "comparison_ready": False,
    }
    payload = (json.dumps(manifest, sort_keys=True, allow_nan=False) + "\n").encode()
    if len(payload) > 65536:
        reject("static_manifest_limit")
    support_id = "b_" + hashlib.sha256(payload).hexdigest()[:24]
    with (stage / "manifest.json").open("xb") as stream:
        stream.write(payload)
    target = private_path(root, f"data/raw/static_copernicus/{support_id}")
    if target.exists():
        reject("static_publication_conflict")
    os.rename(stage, target)
    return {
        "support_id": support_id,
        "status": manifest["status"],
        "transfer_bytes": transport.total,
        "checks": checks,
        "comparison_ready": False,
    }
