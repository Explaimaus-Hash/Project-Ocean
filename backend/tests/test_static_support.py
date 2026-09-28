"""Bounded public static reader; synthetic arrays, no provider network."""

import copy
import itertools
import json
import struct
from types import SimpleNamespace

import numpy as np
import pytest
from numcodecs import Blosc

from backend.app.ingestion import static_support as mod
from backend.app.storage.product_common import ProductError


@pytest.fixture
def fixture():
    arrays = {
        "elevation": -np.arange(50, 0, -1, dtype="float32"),
        "latitude": np.array([-1, 0, 1, 2], dtype="float32"),
        "longitude": np.array([65, 66, 67, 68], dtype="float32"),
        "mask": np.ones((50, 4, 4), dtype="int8"),
        "deptho": np.full((4, 4), 500, dtype="float32"),
        "deptho_lev": np.full((4, 4), 50, dtype="float32"),
    }
    standards = [
        ("depth", "m"),
        ("latitude", "degrees_north"),
        ("longitude", "degrees_east"),
        ("sea_binary_mask", "1"),
        ("sea_floor_depth_below_geoid", "m"),
        ("model_level_number_at_sea_floor", "1"),
    ]
    m = {".zgroup": {"zarr_format": 2}, ".zattrs": {}}
    chunks = {}
    codec = Blosc(cname="lz4", clevel=5, shuffle=1, blocksize=0)
    for (name, data), (standard, unit) in zip(arrays.items(), standards, strict=True):
        dims = [name] if data.ndim == 1 else list(mod.NAMES[:3])[-data.ndim :]
        shape = (
            list(data.shape)
            if data.ndim == 1
            else ([1, 2, 2] if data.ndim == 3 else [2, 2])
        )
        fill = (
            None
            if name == "mask"
            else ("NaN" if data.ndim == 1 else 9.969209968386869e36)
        )
        m[name + "/.zarray"] = {
            "zarr_format": 2,
            "dtype": data.dtype.str,
            "shape": list(data.shape),
            "chunks": shape,
            "filters": None,
            "order": "C",
            "fill_value": fill,
            "compressor": codec.get_config(),
        }
        attrs = {"_ARRAY_DIMENSIONS": dims, "standard_name": standard, "units": unit}
        if name == "elevation":
            attrs["positive"] = "down"
        if name == "mask":
            attrs["long_name"] = "Land-sea mask: 1 = sea ; 0 = land"
        m[name + "/.zattrs"] = attrs
        for ix in itertools.product(
            *(range(n // c) for n, c in zip(data.shape, shape, strict=True))
        ):
            slab = data[
                tuple(slice(i * c, (i + 1) * c) for i, c in zip(ix, shape, strict=True))
            ]
            chunks[name + "/" + ".".join(map(str, ix))] = bytes(
                codec.encode(slab.copy())
            )
    return {"zarr_consolidated_format": 1, "metadata": m}, chunks, arrays


def test_exact_selected_chunks_and_axes(fixture):
    metadata, chunks, arrays = fixture
    seen = []

    def get(key):
        seen.append(key)
        return chunks[key]

    reader = mod.ChunkReader(get, mod.layouts(metadata))
    axes, selection = mod.select_axes(
        reader, SimpleNamespace(latitude=(-1, 0), longitude=(65, 66), depth_m=(1, 2, 3))
    )
    assert selection["latitude"].tolist() == [0, 1]
    result = reader.read("mask", [range(50), [0, 1], [0, 1]])
    assert np.array_equal(result, arrays["mask"][:, :2, :2])
    assert len(seen) == 53
    assert np.array_equal(axes["elevation"], arrays["elevation"])


@pytest.mark.parametrize(
    "change",
    [
        "dtype",
        "filters",
        "order",
        "compressor",
        "chunks",
        "fill_value",
        "dimensions",
        "units",
        "packing",
        "mask_meaning",
    ],
)
def test_unsupported_metadata_rejected(fixture, change):
    m = copy.deepcopy(fixture[0])
    a = m["metadata"]["mask/.zarray"]
    attrs = m["metadata"]["mask/.zattrs"]
    if change == "dimensions":
        attrs["_ARRAY_DIMENSIONS"] = ["longitude", "latitude", "elevation"]
    elif change == "units":
        attrs["units"] = "m"
    elif change == "packing":
        attrs["scale_factor"] = 2
    elif change == "mask_meaning":
        attrs["long_name"] = "1=land"
    else:
        a[change] = {
            "dtype": "<f8",
            "filters": [],
            "order": "F",
            "compressor": None,
            "chunks": [50, 5000, 5000],
            "fill_value": 0,
        }[change]
    with pytest.raises(ProductError):
        mod.layouts(m)


@pytest.mark.parametrize("kind", ["tiny", "oversize", "truncated"])
def test_blosc_header_rejects_before_decode(fixture, kind):
    m, chunks, _ = fixture
    encoded = bytearray(chunks["mask/0.0.0"])
    if kind == "tiny":
        encoded = encoded[:8]
    elif kind == "oversize":
        struct.pack_into("<I", encoded, 4, 2**31)
    else:
        encoded = encoded[:-1]
    reader = mod.ChunkReader(lambda _: encoded, mod.layouts(m))
    with pytest.raises(ProductError, match="Static"):
        reader.read("mask", [[0], [0], [0]])


def test_decode_budget_before_fetch(fixture, monkeypatch):
    monkeypatch.setattr(mod, "MAX_DECODED", 1)
    reader = mod.ChunkReader(lambda _: pytest.fail("network"), mod.layouts(fixture[0]))
    with pytest.raises(ProductError):
        reader.read("mask", [[0], [0], [0]])


@pytest.mark.parametrize("field", ["latitude", "depth_m"])
def test_grid_mismatch_not_nearest_joined(fixture, field):
    args = dict(latitude=(-1, 0), longitude=(65, 66), depth_m=(1, 2))
    args[field] = (0.1, 0.2)
    reader = mod.ChunkReader(fixture[1].__getitem__, mod.layouts(fixture[0]))
    with pytest.raises(ProductError):
        mod.select_axes(reader, SimpleNamespace(**args))


@pytest.mark.parametrize(
    "kind", ["binary", "hole", "missing", "fractional", "negative"]
)
def test_invalid_values_rejected(fixture, kind):
    a = fixture[2]
    if kind == "binary":
        a["mask"][0, 0, 0] = 2
    elif kind == "hole":
        a["mask"][25, 0, 0] = 0
    elif kind == "missing":
        a["deptho"][0, 0] = np.nan
    elif kind == "fractional":
        a["deptho_lev"][0, 0] = 1.5
    else:
        a["deptho"][0, 0] = -1
    with pytest.raises(ProductError):
        mod.validate_values(a["mask"], a["deptho"], a["deptho_lev"])


def test_numeric_agreement_does_not_promote_support(fixture):
    a = fixture[2]
    result = mod.validate_values(a["mask"], a["deptho"], a["deptho_lev"])
    assert result["wet_level_count_equals_deptho_lev"]
    assert result["vertical_reference"] == "unresolved"
    assert result["coastline_connectivity"] == "not_evaluated"


@pytest.mark.parametrize(
    "key",
    [
        "../private",
        "https://evil.test",
        "mask/-1.0.0",
        "downsampled4/0",
        "mask/0?token=x",
    ],
)
def test_unsafe_keys_no_network(tmp_path, key):
    transport = mod.PublicReadSet(tmp_path)
    transport.opener = SimpleNamespace(open=lambda *a, **kw: pytest.fail("network"))
    with pytest.raises(ProductError):
        transport.get(key)


@pytest.mark.parametrize("changed", [False, True])
def test_publication_and_original_read_set(fixture, tmp_path, monkeypatch, changed):
    from backend.app.schemas.products import ProductFile

    m, chunks, arrays = fixture
    field = SimpleNamespace(
        manifest=SimpleNamespace(
            identity=SimpleNamespace(
                provenance=SimpleNamespace(
                    provider_dataset_id="cmems_mod_glo_phy_my_0.083deg_P1D-m",
                    source_version="202311",
                    data_mode="synthetic",
                ),
                axes=SimpleNamespace(
                    latitude=(-1, 0), longitude=(65, 66), depth_m=(1, 2)
                ),
            )
        ),
        manifest_file=ProductFile(size_bytes=10, modified_ns=1, sha256="a" * 64),
    )
    monkeypatch.setattr(mod, "read_native_field", lambda *args: field)
    catalogue = json.dumps(
        {"id": mod.DATASET, "assets": {"static": {"href": mod.BASE.rstrip("/")}}}
    ).encode()
    objects = {
        **chunks,
        "catalogue.json": catalogue,
        "catalogue_end.json": catalogue,
        ".zmetadata": json.dumps(m).encode(),
        "metadata_end.json": json.dumps(m).encode(),
    }
    if changed:
        objects["metadata_end.json"] += b" "

    class FakeTransport:
        def __init__(self, stage):
            self.stage = stage
            self.records = {}
            self.total = 0

        def get(self, key):
            import hashlib

            data = objects[key]
            self.total += len(data)
            path = self.stage / "source_read_set" / key
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            self.records[key] = {
                "sha256": hashlib.sha256(data).hexdigest(),
                "size_bytes": len(data),
            }
            return data

    monkeypatch.setattr(mod, "PublicReadSet", FakeTransport)
    if changed:
        with pytest.raises(ProductError) as error:
            mod.acquire_static(tmp_path, "m_" + "a" * 24)
        assert error.value.code == "static_remote_metadata_changed"
        assert not list((tmp_path / "data/raw/static_copernicus").glob("b_*"))
        return
    result = mod.acquire_static(tmp_path, "m_" + "a" * 24)
    directory = tmp_path / "data/raw/static_copernicus" / result["support_id"]
    manifest = json.loads((directory / "manifest.json").read_text())
    assert manifest["data_mode"] == "synthetic"
    assert not manifest["comparison_ready"]
    assert (directory / "source_read_set/mask/0.0.0").read_bytes() == chunks[
        "mask/0.0.0"
    ]
    assert (directory / "subset.nc").exists()


@pytest.mark.parametrize(
    "case", ["ok", "encoding", "status", "declared", "truncated", "total", "deadline"]
)
def test_bounded_transport(tmp_path, monkeypatch, case):
    import io

    class Response(io.BytesIO):
        status = 200
        headers = {"Content-Length": "3"}

    response = Response(b"abc")
    if case == "encoding":
        response.headers = {"Content-Encoding": "gzip"}
    if case == "status":
        response.status = 403
    if case == "declared":
        response.headers = {"Content-Length": str(2**40)}
    if case == "truncated":
        response.headers = {"Content-Length": "4"}
    if case == "total":
        monkeypatch.setattr(mod, "MAX_TRANSFER", 2)
    transport = mod.PublicReadSet(tmp_path)
    transport.opener = SimpleNamespace(open=lambda *a, **kw: response)
    if case == "deadline":
        transport.deadline = 0
    if case == "ok":
        assert transport.get("catalogue.json") == b"abc"
        assert transport.total == 3
        assert (tmp_path / "source_read_set/catalogue.json").read_bytes() == b"abc"
    else:
        with pytest.raises(ProductError):
            transport.get("catalogue.json")
        assert not (tmp_path / "source_read_set/catalogue.json").exists()


def test_missing_chunk_is_failure_not_zero(fixture):
    def missing(key):
        raise FileNotFoundError(key)

    reader = mod.ChunkReader(missing, mod.layouts(fixture[0]))
    with pytest.raises(FileNotFoundError):
        reader.read("mask", [[0], [0], [0]])
