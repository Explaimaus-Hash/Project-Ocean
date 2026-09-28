"""Tiny native-grid fixtures; no live sources or user data are used."""

import socket
from datetime import UTC, datetime

import netCDF4
import numpy as np
import pytest

from backend.app.processing import prepare_model as processor
from backend.app.schemas.acquisition import AcquisitionManifest, AcquisitionRequest
from backend.app.schemas.model_metadata import ModelSourceMetadata
from backend.app.schemas.models import ModelPreparationRequest
from backend.app.schemas.products import PerformanceLimits
from backend.app.storage.product_common import ProductError, describe_file
from scripts import prepare_model as cli


@pytest.fixture
def local_model(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Network access is forbidden")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    (tmp_path / "config").mkdir()
    (tmp_path / "config/performance.yaml").write_text(
        PerformanceLimits().model_dump_json()
    )
    aid = "a_" + "1" * 24
    folder = tmp_path / "data/raw/acquisitions" / aid
    folder.mkdir(parents=True)
    path = folder / "input.nc"
    with netCDF4.Dataset(path, "w") as ds:
        ds.title = "Synthetic; inherited z_max is not actual coverage"
        ds.z_max = np.float32(5000)
        for name, values, unit in (
            ("time", [0, 24], "hours since 2019-01-29"),
            ("depth", [0.5, 1.5], "m"),
            ("latitude", [-1, 0], "degrees_north"),
            ("longitude", [65, 66], "degrees_east"),
        ):
            ds.createDimension(name, 2)
            v = ds.createVariable(name, "f8", (name,), fill_value=np.nan)
            v.units, v.standard_name = unit, name
            if name == "time":
                v.calendar = "gregorian"
            if name == "depth":
                v.positive = "down"
            v[:] = values
        for name, (unit, standard) in processor.FIELDS.items():
            v = ds.createVariable(name, "i2", processor.AXES, fill_value=np.int16(-999))
            v.units, v.standard_name, v.long_name = unit, standard, name
            v.scale_factor, v.add_offset = np.float64(0.5), np.float64(10)
            v.valid_min, v.valid_max = np.int16(0), np.int16(10)
            v.cell_methods = "area: mean"
            v.set_auto_maskandscale(False)
            v[:] = np.arange(16, dtype="int16").reshape(2, 2, 2, 2)
        ds["thetao"][0, 0, 0, 0] = np.int16(-999)
    aq = AcquisitionRequest(
        provider="copernicus",
        dataset_id="copernicus_global_multiyear_phy",
        provider_dataset_id="cmems_mod_glo_phy_my_0.083deg_P1D-m",
        provider_version="202311",
        variables=list(processor.FIELDS),
        coordinates={k: k for k in processor.AXES},
        selection={
            "region": {"west": 65, "east": 66, "south": -1, "north": 0},
            "start_time": "2019-01-29T00:00:00Z",
            "end_time": "2019-01-30T23:59:59Z",
            "vertical_min": 0.49,
            "vertical_max": 10,
            "vertical_kind": "depth_m",
        },
    )
    manifest = AcquisitionManifest(
        acquisition_id=aid,
        source_id="copernicus",
        dataset_id=aq.dataset_id,
        origin_url="https://example.invalid/synthetic",
        source_version="202311",
        request=aq,
        input_file=describe_file(path, 134217728),
        created_at=datetime.now(UTC),
        retrieved_at=None,
        data_mode="synthetic",
        client="fixture",
        client_version="1",
        client_processing="synthetic",
        transport="local",
    )
    (folder / "manifest.json").write_text(manifest.model_dump_json())
    request = ModelPreparationRequest(
        acquisition_id=aid, variables=tuple(aq.variables), selection=aq.selection
    )
    return tmp_path, path, request


def refresh(path):
    mp = path.parent / "manifest.json"
    data = AcquisitionManifest.model_validate_json(mp.read_text()).model_dump(
        mode="json"
    )
    data["input_file"] = describe_file(path, 134217728).model_dump(mode="json")
    mp.write_text(AcquisitionManifest.model_validate(data).model_dump_json())


def test_native_values_masks_metadata_and_reuse(local_model):
    root, raw, request = local_model
    before = describe_file(raw, 134217728)
    result = processor.prepare_model(request, root)
    target = root / "data/models" / result.model_id
    snapshot = ModelSourceMetadata.model_validate_json(
        (target / "source_metadata.json").read_text()
    )
    assert snapshot.variables["depth"].attributes["_FillValue"].values == ("NaN",)
    assert snapshot.global_attributes["z_max"].values == (5000.0,)
    with netCDF4.Dataset(target / "fields.nc") as ds:
        assert ds["thetao"].shape == (2, 2, 2, 2)
        assert ds["thetao"].dtype == np.dtype("float64")
        assert "scale_factor" not in ds["thetao"].ncattrs()
        actual = np.ma.filled(ds["thetao"][:], np.nan).reshape(-1)
        expected = np.arange(16, dtype=float) * 0.5 + 10
        expected[0], expected[11:] = np.nan, np.nan
        np.testing.assert_array_equal(actual, expected)
        assert ds["so"][0, 0, 0, 0] == 10  # Masks remain per variable.
        np.testing.assert_array_equal(ds["depth"][:], [0.5, 1.5])
    assert result.identity.policy.comparison_ready is False
    assert processor.prepare_model(request, root) == result
    assert describe_file(raw, 134217728) == before
    assert not list((root / "data/models").glob(".prepare_*"))
    assert not (root / "data/models/.publish.lock").exists()


@pytest.mark.parametrize(
    "case",
    [
        "calendar",
        "descending",
        "duplicate",
        "missing_coord",
        "depth_units",
        "up",
        "temperature_units",
        "staggered",
        "bounds",
        "unsigned",
        "zero_scale",
        "nan_scale",
        "range_order",
        "range_dtype",
        "group",
        "secret_attribute",
    ],
)
def test_reject_bad_source_without_publication(local_model, case):
    root, path, request = local_model
    with netCDF4.Dataset(path, "a") as ds:
        if case == "calendar":
            ds["time"].calendar = "360_day"
        elif case == "descending":
            ds["latitude"][:] = [0, -1]
        elif case == "duplicate":
            ds["latitude"][:] = [0, 0]
        elif case == "missing_coord":
            ds["depth"][:] = [np.nan, 1.5]
        elif case == "depth_units":
            ds["depth"].units = "dbar"
        elif case == "up":
            ds["depth"].positive = "up"
        elif case == "temperature_units":
            ds["thetao"].units = "Kelvin"
        elif case == "staggered":
            ds.renameDimension("depth", "sigma")
        elif case == "bounds":
            ds["time"].bounds = "time_bounds"
        elif case == "unsigned":
            ds["thetao"]._Unsigned = "true"
        elif case == "zero_scale":
            ds["thetao"].scale_factor = 0.0
        elif case == "nan_scale":
            ds["thetao"].scale_factor = np.nan
        elif case == "range_order":
            ds["thetao"].valid_min = np.int16(99)
        elif case == "range_dtype":
            ds["thetao"].valid_min = np.float64(0.1)
        elif case == "group":
            ds.createGroup("unsupported")
        elif case == "secret_attribute":
            ds.credential = "fixture-not-a-secret"
    refresh(path)
    with pytest.raises(ProductError):
        processor.prepare_model(request, root)
    assert not list((root / "data/models").glob("m_*"))


@pytest.mark.parametrize(
    "limit,value",
    [
        ("max_axis_values", 1),
        ("max_time_steps", 1),
        ("max_preparation_values", 10),
        ("max_product_file_bytes", 1024),
        ("max_manifest_bytes", 1024),
    ],
)
def test_limits_enforced(local_model, limit, value):
    root, path, request = local_model
    limits = PerformanceLimits.model_validate({limit: value})
    (root / "config/performance.yaml").write_text(limits.model_dump_json())
    with pytest.raises(ProductError):
        processor.prepare_model(request, root)
    assert not list((root / "data/models").glob("m_*"))


def test_no_overlap(local_model):
    root, path, request = local_model
    data = request.model_dump(mode="json")
    data["selection"]["vertical_min"] = 9
    changed = ModelPreparationRequest.model_validate(data)
    with pytest.raises(ProductError, match="no_overlap"):
        processor.prepare_model(changed, root)


def test_smaller_selection_preserves_source_indices(local_model):
    root, path, request = local_model
    data = request.model_dump(mode="json")
    data["selection"]["vertical_min"] = 1
    result = processor.prepare_model(ModelPreparationRequest.model_validate(data), root)
    assert result.identity.axes.source_depth_indices == (1,)
    assert result.identity.axes.depth_m == (1.5,)


@pytest.mark.parametrize("file", ["fields.nc", "source_metadata.json", "manifest.json"])
def test_conflicting_output_not_overwritten(local_model, file):
    root, path, request = local_model
    result = processor.prepare_model(request, root)
    target = root / "data/models" / result.model_id / file
    target.write_bytes(b"conflicting-existing-output")
    with pytest.raises(ProductError):
        processor.prepare_model(request, root)
    assert target.read_bytes() == b"conflicting-existing-output"


def test_changed_source_hash(local_model):
    root, path, request = local_model
    with netCDF4.Dataset(path, "a") as ds:
        ds.title = "modified"
    with pytest.raises(ProductError):
        processor.prepare_model(request, root)


@pytest.mark.parametrize("point", ["write", "readback", "rename"])
def test_failed_stage_cleanup(local_model, monkeypatch, point):
    root, path, request = local_model

    def broken(*a, **kw):
        raise OSError("private diagnostic must be sanitized")

    if point == "rename":
        monkeypatch.setattr(processor.os, "rename", broken)
    else:
        monkeypatch.setattr(
            processor, "_write_fields" if point == "write" else "_readback", broken
        )
    with pytest.raises(ProductError) as error:
        processor.prepare_model(request, root)
    assert "private diagnostic" not in str(error.value)
    assert not list((root / "data/models").glob("m_*"))
    assert not list((root / "data/models").glob(".prepare_*"))
    assert not (root / "data/models/.publish.lock").exists()


def test_another_publication_lock_not_removed(local_model):
    root, path, request = local_model
    lock = root / "data/models/.publish.lock"
    lock.parent.mkdir()
    lock.write_bytes(b"other operator")
    with pytest.raises(ProductError, match="model_busy"):
        processor.prepare_model(request, root)
    assert lock.read_bytes() == b"other operator"


def test_negative_scale_and_valid_range(local_model):
    root, path, request = local_model
    with netCDF4.Dataset(path, "a") as ds:
        var = ds["thetao"]
        var.delncattr("valid_min")
        var.delncattr("valid_max")
        var.valid_range = np.array([0, 10], dtype="int16")
        var.scale_factor = -0.5
    refresh(path)
    result = processor.prepare_model(request, root)
    with netCDF4.Dataset(root / "data/models" / result.model_id / "fields.nc") as ds:
        assert ds["thetao"][0, 0, 0, 1] == 9.5
        assert np.ma.is_masked(ds["thetao"][1, 1, 1, 1])


def test_cli_success_and_invalid_request(local_model, monkeypatch, capsys):
    root, path, request = local_model
    monkeypatch.setattr(cli, "PROJECT_ROOT", root)
    request_path = root / "request.json"
    request_path.write_text(request.model_dump_json())
    assert cli.main(["--request", str(request_path)]) == 0
    assert '"comparison_ready": false' in capsys.readouterr().out
    request_path.write_text('{"password":"must-not-echo"}')
    assert cli.main(["--request", str(request_path)]) == 2
    captured = capsys.readouterr()
    assert "must-not-echo" not in captured.err
