"""Offline static replay, binding and corruption tests using synthetic inputs."""

import hashlib
import json
import shutil
import socket

import netCDF4
import pytest
from numcodecs import Blosc
from pydantic import ValidationError

from backend.app.comparison import static_reader as reader
from backend.app.ingestion import static_support as acquisition
from backend.app.processing.prepare_model import prepare_model
from backend.app.storage.product_common import ProductError, describe_file
from backend.tests.test_model_preparation import local_model
from backend.tests.test_static_support import fixture as static_fixture
from scripts import inspect_static_support as cli


@pytest.fixture(scope="module")
def saved(tmp_path_factory):
    root = tmp_path_factory.mktemp("static_reader")
    with pytest.MonkeyPatch.context() as mp:
        _, _, request = local_model.__wrapped__(root, mp)
        model = prepare_model(request, root)
        metadata, chunks, arrays = static_fixture.__wrapped__()
        arrays["elevation"] += 0.5
        codec = Blosc(cname="lz4", clevel=5, shuffle=1, blocksize=0)
        chunks["elevation/0"] = bytes(codec.encode(arrays["elevation"]))
        catalogue = json.dumps(
            {
                "id": acquisition.DATASET,
                "assets": {"static": {"href": acquisition.BASE.rstrip("/")}},
            }
        ).encode()
        meta = json.dumps(metadata).encode()
        objects = {
            **chunks,
            "catalogue.json": catalogue,
            "catalogue_end.json": catalogue,
            ".zmetadata": meta,
            "metadata_end.json": meta,
        }

        class Transport:
            def __init__(self, stage):
                self.stage, self.records, self.total = stage, {}, 0

            def get(self, key):
                value = objects[key]
                path = self.stage / "source_read_set" / key
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(value)
                self.total += len(value)
                self.records[key] = {
                    "sha256": hashlib.sha256(value).hexdigest(),
                    "size_bytes": len(value),
                }
                return value

        mp.setattr(acquisition, "PublicReadSet", Transport)
        result = acquisition.acquire_static(root, model.model_id)
    return root, result["support_id"], model.model_id


@pytest.fixture
def copied(saved, tmp_path, monkeypatch):
    root, sid, mid = saved
    shutil.copytree(root, tmp_path, dirs_exist_ok=True)

    def forbidden(*args, **kwargs):
        pytest.fail("Offline reader attempted network/acquisition")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(acquisition, "PublicReadSet", forbidden)
    return tmp_path, sid, mid


def folder(root, sid):
    return root / "data/raw/static_copernicus" / sid


def republish(path, manifest):
    """Only synthetic temp snapshots: recompute IDs to test deeper validation."""
    raw = (json.dumps(manifest, sort_keys=True) + "\n").encode()
    (path / "manifest.json").write_bytes(raw)
    sid = "b_" + hashlib.sha256(raw).hexdigest()[:24]
    if path.name != sid:
        # The reader only needs a synthetic snapshot under its recomputed ID;
        # atomic publication is not under test here. Keep the original fixture
        # and avoid intermittent Windows directory-rename denial during setup.
        shutil.copytree(path, path.with_name(sid))
    return sid


def test_verified_read_only_and_explicit_mapping(copied):
    root, sid, mid = copied
    before = {p: describe_file(p, 4194320) for p in root.rglob("*") if p.is_file()}
    snapshot = reader.read_static_support(root, sid, mid)
    assert snapshot.model_depth_to_source_elevation_index == (49, 48)
    assert snapshot.source_elevation_m[:2] == (-49.5, -48.5)
    assert len(snapshot.mask) == 200
    assert snapshot.deptho_m == (500, 500, 500, 500)
    assert not snapshot.comparison_ready
    assert snapshot.manifest.checks.vertical_reference == "unresolved"
    assert snapshot.manifest.data_mode == "synthetic"
    assert before == {
        p: describe_file(p, 4194320) for p in root.rglob("*") if p.is_file()
    }
    with pytest.raises(ValidationError):
        snapshot.comparison_ready = True


@pytest.mark.parametrize(
    "target", ["manifest.json", "subset.nc", "source_read_set/mask/0.0.0"]
)
def test_corruption_rejected(copied, target):
    root, sid, mid = copied
    path = folder(root, sid) / target
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(ProductError):
        reader.read_static_support(root, sid, mid)


@pytest.mark.parametrize("change", ["units", "positive", "packing", "value", "global"])
def test_rehashed_subset_not_trusted(copied, change):
    root, sid, mid = copied
    path = folder(root, sid)
    with netCDF4.Dataset(path / "subset.nc", "a") as ds:
        if change == "units":
            ds["deptho"].units = "km"
        elif change == "positive":
            ds["elevation"].positive = "up"
        elif change == "packing":
            ds["mask"].scale_factor = 2
        elif change == "value":
            ds["deptho"][0, 0] = 499
        else:
            ds.interpretation = "matching_ready"
    m = json.loads((path / "manifest.json").read_bytes())
    m["subset"] = describe_file(path / "subset.nc", 4194304).model_dump(mode="json")
    sid = republish(path, m)
    with pytest.raises(ProductError):
        reader.read_static_support(root, sid, mid)


@pytest.mark.parametrize(
    "change",
    [
        "model",
        "mode",
        "asset",
        "indices",
        "decoded",
        "checks",
        "extra",
        "transfer",
        "unsafe_key",
    ],
)
def test_rehashed_manifest_semantics(copied, change):
    root, sid, mid = copied
    path = folder(root, sid)
    m = json.loads((path / "manifest.json").read_bytes())
    if change == "model":
        m["model_id"] = "m_" + "f" * 24
    elif change == "mode":
        m["data_mode"] = "real"
    elif change == "asset":
        m["source_asset"] = "https://example.invalid/other"
    elif change == "indices":
        m["source_latitude_indices"] = [1, 2]
    elif change == "decoded":
        m["decoded_chunk_bytes"] += 1
    elif change == "checks":
        m["checks"]["wet_level_count_equals_deptho_lev"] = False
    elif change == "extra":
        m["trust_me"] = True
    elif change == "transfer":
        m["transfer_bytes"] += 1
    else:
        m["source_read_set"]["../private"] = m["source_read_set"].pop("mask/0.0.0")
    sid = republish(path, m)
    with pytest.raises((ProductError, ValidationError)):
        reader.read_static_support(root, sid, mid)


@pytest.mark.parametrize("change", ["missing", "extra", "metadata_end"])
def test_exact_read_set(copied, change):
    root, sid, mid = copied
    path = folder(root, sid)
    m = json.loads((path / "manifest.json").read_bytes())
    if change == "missing":
        m["source_read_set"].pop("mask/0.0.0")
    else:
        key = "mask/99.0.0" if change == "extra" else "metadata_end.json"
        value = (
            b"unexpected"
            if change == "extra"
            else (path / "source_read_set/.zmetadata").read_bytes() + b" "
        )
        (path / "source_read_set" / key).write_bytes(value)
        m["source_read_set"][key] = {
            "size_bytes": len(value),
            "sha256": hashlib.sha256(value).hexdigest(),
        }
    m["transfer_bytes"] = sum(r["size_bytes"] for r in m["source_read_set"].values())
    sid = republish(path, m)
    with pytest.raises(ProductError):
        reader.read_static_support(root, sid, mid)


@pytest.mark.parametrize(
    "sid,mid", [("../x", "m_" + "a" * 24), ("b_" + "a" * 24, "../x"), (None, None)]
)
def test_unsafe_ids_before_io(tmp_path, sid, mid):
    with pytest.raises(ProductError, match="Saved static"):
        reader.read_static_support(tmp_path, sid, mid)
    assert not list(tmp_path.iterdir())


def test_cli_safe_compact_output(copied, monkeypatch, capsys):
    root, sid, mid = copied
    monkeypatch.setattr(cli, "PROJECT_ROOT", root)
    assert cli.main(["--support-id", sid, "--model-id", mid]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "static_inputs_verified_not_matching_ready"
    assert not result["comparison_ready"]
    assert "mask" not in result and "source_asset" not in result
    assert cli.main(["--support-id", "../private"]) == 2
    error = capsys.readouterr().err
    assert "../private" not in error and str(root) not in error


def test_post_read_change_rejected(copied, monkeypatch):
    root, sid, mid = copied
    original = reader.verify_subset

    def changed(*args):
        original(*args)
        path = folder(root, sid) / "source_read_set/mask/0.0.0"
        path.write_bytes(path.read_bytes() + b"changed")

    monkeypatch.setattr(reader, "verify_subset", changed)
    with pytest.raises(ProductError):
        reader.read_static_support(root, sid, mid)
