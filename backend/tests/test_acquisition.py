"""Tiny offline acquisition fixtures; no live provider or real raw file is read."""

import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError

import netCDF4
import numpy as np
import pytest
import xarray as xr
from pydantic import ValidationError

from backend.app.ingestion import acquisition, argo, base, copernicus, glider
from backend.app.schemas.acquisition import AcquisitionRequest
from backend.app.schemas.datasets import DatasetDefinition
from backend.app.storage.product_common import ProductError


def request(provider="argo", **overrides):
    data = {
        "provider": provider,
        "dataset_id": "argo_gdac",
        "selection": {
            "region": {"west": 60, "east": 61, "south": 0, "north": 1},
            "start_time": "2019-01-01T00:00:00Z",
            "end_time": "2019-01-03T00:00:00Z",
            "vertical_min": 0,
            "vertical_max": 20,
            "vertical_kind": "pressure_dbar",
        },
    }
    if provider in {"godas", "copernicus"}:
        data["dataset_id"] = "incois_godas_2025"
        data["selection"]["vertical_kind"] = "depth_m"
        data["coordinates"] = {
            "longitude": "longitude",
            "latitude": "latitude",
            "time": "time",
            "depth": "depth",
        }
        data["variables"] = ["thetao"]
    if provider == "copernicus":
        data.update(
            dataset_id="copernicus_global_multiyear_phy",
            provider_dataset_id="cmems_mod_glo_phy_my_0.083deg_P1D-m",
            provider_version="202311",
        )
    if provider in {"local", "glider"}:
        data.pop("selection")
    if provider == "local":
        data["local_path"] = "data/raw/example.nc"
    if provider == "glider":
        data["dataset_id"] = "ifremer_glider_v2"
        data["remote_path"] = "/ifremer/glider/v2/bella/bella_20240206/Bella_626_R.nc"
    data.update(overrides)
    return AcquisitionRequest.model_validate(data)


def definition(provider="argo"):
    values = {
        "argo": ("argo", "argo_gdac", "argopy", "ftp://ftp.ifremer.fr/ifremer/argo"),
        "godas": (
            "incois_godas",
            "incois_godas_2025",
            "opendap",
            "https://las.incois.gov.in/thredds/dodsC/las/id-cbbdd5ab07/data_home_las_datasets_godas_2025.nc.jnl",
        ),
        "glider": (
            "ifremer_glider",
            "ifremer_glider_v2",
            "ftp",
            "ftp://ftp.ifremer.fr/ifremer/glider/v2/",
        ),
        "copernicus": (
            "copernicus",
            "copernicus_global_multiyear_phy",
            "copernicusmarine",
            "https://data.marine.copernicus.eu/product/GLOBAL_MULTIYEAR_PHY_001_030/description",
        ),
    }
    source, dataset, method, origin = values[provider]
    return DatasetDefinition(
        source_id=source,
        dataset_id=dataset,
        access_method=method,
        origin_url=origin,
        title=source,
        role="model" if provider in {"godas", "copernicus"} else "observation",
    )


def model_dataset():
    return xr.Dataset(
        {
            "thetao": (
                ("time", "depth", "latitude", "longitude"),
                np.arange(48, dtype=float).reshape(2, 2, 3, 4),
                {"units": "degrees_C"},
            )
        },
        coords={
            "time": np.array(["2019-01-01", "2019-01-02"], dtype="datetime64[ns]"),
            "depth": ("depth", [1.0, 10.0], {"units": "m", "positive": "down"}),
            "latitude": ("latitude", [-1.0, 0.0, 1.0], {"units": "degrees_north"}),
            "longitude": (
                "longitude",
                [59.0, 60.0, 61.0, 62.0],
                {"units": "degrees_east"},
            ),
        },
    )


def tiny_netcdf(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with netCDF4.Dataset(path, "w") as ds:
        ds.createDimension("row", 2)
        v = ds.createVariable("pres", "f8", ("row",))
        v.units = "dbar"
        v[:] = [1.0, 10.0]


@pytest.mark.parametrize(
    "change",
    [
        {"provider": "godas"},
        {"provider": "glider"},
        {"provider": "local"},
        {"max_values": 8_000_001},
        {"max_bytes": 134_217_729},
        {"deadline_seconds": 181},
        {"max_samples": 100_001},
        {"password": "secret"},
        {"variables": ["TEMP"]},
    ],
)
def test_bad_requests(change):
    data = request().model_dump(mode="json")
    data.update(change)
    with pytest.raises(ValidationError):
        AcquisitionRequest.model_validate(data)


@pytest.mark.parametrize(
    "path",
    [
        "../evil.nc",
        "data/raw/../../evil.nc",
        "C:/secret.nc",
        "data/raw/x.txt",
        "data\\raw\\a.nc",
        "/data/raw/a.nc",
    ],
)
def test_local_paths_reject_escape(path):
    with pytest.raises(ValidationError):
        request("local", local_path=path)


@pytest.mark.parametrize(
    "path",
    [
        "/ifremer/glider/v2/a/../x.nc",
        "/ifremer/glider/v2/a/b/x.nc\r\nDELE x",
        "ftp://ftp.ifremer.fr/x.nc",
        "/ifremer/argo/a/b/x.nc",
    ],
)
def test_ftp_path_rejects_commands_or_escape(path):
    with pytest.raises(ValidationError):
        request("glider", remote_path=path)


def test_dates_and_vertical_kind_are_explicit():
    data = request().model_dump(mode="json")
    for value in ["2019-01-01", "2018-01-01T00:00:00Z"]:
        data["selection"]["end_time"] = value
        with pytest.raises(ValidationError):
            AcquisitionRequest.model_validate(data)
    data = request("godas").model_dump(mode="json")
    data["selection"]["vertical_kind"] = "pressure_dbar"
    with pytest.raises(ValidationError):
        AcquisitionRequest.model_validate(data)


def test_model_subset_preserves_native_samples():
    ds = model_dataset()
    result = base.model_subset(ds, request("godas"))
    assert result.thetao.shape == (2, 2, 2, 2)
    np.testing.assert_array_equal(result.thetao.values, ds.thetao.values[:, :, 1:, 1:3])
    assert result.thetao.attrs["units"] == "degrees_C"


def test_descending_model_axis_is_preserved():
    ds = model_dataset().isel(latitude=slice(None, None, -1))
    result = base.model_subset(ds, request("godas"))
    assert result.latitude.values.tolist() == [1.0, 0.0]


@pytest.mark.parametrize(
    "mutation",
    [
        "wrong_units",
        "depth_up",
        "duplicate",
        "bad_longitude",
        "missing_var",
        "surface_only",
    ],
)
def test_model_metadata_rejects_unknown_support(mutation):
    ds = model_dataset()
    if mutation == "wrong_units":
        ds.longitude.attrs["units"] = "radians"
    elif mutation == "depth_up":
        ds.depth.attrs["positive"] = "up"
    elif mutation == "duplicate":
        ds = ds.assign_coords(
            latitude=("latitude", [0.0, 0.0, 1.0], {"units": "degrees_north"})
        )
    elif mutation == "bad_longitude":
        ds = ds.assign_coords(
            longitude=(
                "longitude",
                [59.0, 60.0, 61.0, 360.0],
                {"units": "degrees_east"},
            )
        )
    elif mutation == "missing_var":
        ds = ds.drop_vars("thetao")
    elif mutation == "surface_only":
        ds["thetao"] = ds.thetao.isel(depth=0, drop=True)
    with pytest.raises(ProductError, match="unsupported"):
        base.model_subset(ds, request("godas"))


def test_model_no_data_distinct_from_provider_failure():
    req = request("godas").model_dump(mode="json")
    req["selection"]["region"].update(west=100, east=101)
    with pytest.raises(ProductError) as found:
        base.model_subset(model_dataset(), AcquisitionRequest.model_validate(req))
    assert found.value.code == "no_data"


def test_counts_and_chunks_checked_before_model_load():
    with pytest.raises(ProductError) as found:
        base.model_subset(model_dataset(), request("godas", max_values=1))
    assert found.value.code == "acquisition_limit"
    ds = model_dataset()
    ds.thetao.encoding["chunksizes"] = (500, 500, 500, 500)
    with pytest.raises(ProductError) as found:
        base.model_subset(ds, request("godas"))
    assert found.value.code == "acquisition_limit"


def test_bounds_and_ancillary_qc_preserved():
    ds = model_dataset()
    ds["quality"] = xr.ones_like(ds.thetao, dtype="i1")
    ds.thetao.attrs["ancillary_variables"] = "quality"
    result = base.model_subset(ds, request("godas"))
    assert "quality" in result
    assert result.quality.shape == result.thetao.shape


def test_save_fixed_width_strings(tmp_path):
    ds = xr.Dataset(
        {
            "DIRECTION": ("N_POINTS", np.array(["A", "D"], dtype="U1")),
            "DATA_MODE": ("N_POINTS", np.array(["R", "D"], dtype="U1")),
        }
    )
    path = tmp_path / "input.nc"
    base.save_dataset(ds, path, request())
    with netCDF4.Dataset(path) as stored:
        assert stored.variables["DIRECTION"].dtype == np.dtype("S1")
    with xr.open_dataset(path) as stored:
        assert stored.DIRECTION.values.tolist() == ["A", "D"]


def test_string_width_bound_before_save(tmp_path):
    ds = xr.Dataset({"DIRECTION": ("N_POINTS", np.array(["A"], dtype="U129"))})
    with pytest.raises(ProductError):
        base.save_dataset(ds, tmp_path / "input.nc", request())
    assert not (tmp_path / "input.nc").exists()


def test_credentials_no_prompt_or_sdk_import(monkeypatch, tmp_path):
    monkeypatch.delenv("COPERNICUSMARINE_SERVICE_USERNAME", raising=False)
    monkeypatch.delenv("COPERNICUSMARINE_SERVICE_PASSWORD", raising=False)
    with pytest.raises(ProductError) as found:
        copernicus.fetch(
            request("copernicus"), definition("copernicus"), tmp_path / "a.nc"
        )
    assert found.value.code == "credentials_missing"


def test_credentials_repr_and_tls(monkeypatch):
    monkeypatch.setenv("COPERNICUSMARINE_SERVICE_USERNAME", "private-user")
    monkeypatch.setenv("COPERNICUSMARINE_SERVICE_PASSWORD", "private-password")
    monkeypatch.delenv("COPERNICUSMARINE_DISABLE_SSL_CONTEXT", raising=False)
    assert "private" not in repr(copernicus.credentials())
    monkeypatch.setenv("COPERNICUSMARINE_DISABLE_SSL_CONTEXT", "True")
    with pytest.raises(ProductError) as found:
        copernicus.credentials()
    assert found.value.code == "unsafe_transport"


def test_copernicus_explicit_call(monkeypatch, tmp_path):
    import copernicusmarine as installed

    captured = {}

    def open_dataset(**kwargs):
        captured.update(kwargs)
        return model_dataset()

    fake = SimpleNamespace(
        open_dataset=open_dataset,
        __version__="test",
        CoordinatesOutOfDatasetBounds=installed.CoordinatesOutOfDatasetBounds,
        VariableDoesNotExistInTheDataset=installed.VariableDoesNotExistInTheDataset,
        InvalidUsernameOrPassword=installed.InvalidUsernameOrPassword,
        CredentialsCannotBeNone=installed.CredentialsCannotBeNone,
        CouldNotConnectToAuthenticationSystem=(
            installed.CouldNotConnectToAuthenticationSystem
        ),
    )
    monkeypatch.setitem(sys.modules, "copernicusmarine", fake)
    monkeypatch.setenv("COPERNICUSMARINE_SERVICE_USERNAME", "private-user")
    monkeypatch.setenv("COPERNICUSMARINE_SERVICE_PASSWORD", "private-password")
    monkeypatch.delenv("COPERNICUSMARINE_DISABLE_SSL_CONTEXT", raising=False)
    details = copernicus.fetch(
        request("copernicus"), definition("copernicus"), tmp_path / "input.nc"
    )
    assert captured["dataset_version"] == "202311"
    assert captured["coordinates_selection_method"] == "strict-inside"
    assert captured["raise_if_updating"] is True
    assert captured["minimum_depth"] == 0
    assert captured["vertical_axis"] == "depth"
    assert "elevation-to-depth" in details["client_processing"]
    assert "CF mask/scale/time decoding" in details["client_processing"]
    assert "NetCDF re-encoding" in details["client_processing"]
    assert "private" not in json.dumps(details)


@pytest.mark.parametrize(
    ("exception_name", "expected_code"),
    [
        ("InvalidUsernameOrPassword", "provider_auth_failed"),
        ("CredentialsCannotBeNone", "credentials_missing"),
        ("CouldNotConnectToAuthenticationSystem", "provider_unavailable"),
        ("CoordinatesOutOfDatasetBounds", "provider_request_rejected"),
        ("VariableDoesNotExistInTheDataset", "unsupported_source"),
    ],
)
def test_copernicus_typed_errors_are_sanitized(
    monkeypatch, exception_name, expected_code
):
    import copernicusmarine as installed

    def rejected(**kwargs):
        raise getattr(installed, exception_name)("private-provider-detail")

    monkeypatch.setattr(installed, "open_dataset", rejected)
    with pytest.raises(ProductError) as found:
        copernicus._open(installed)
    assert found.value.code == expected_code
    assert "private-provider-detail" not in str(found.value)
    assert found.value.__cause__ is None
    assert found.value.__suppress_context__ is True


def test_copernicus_sdk_depth_cf_roundtrip(monkeypatch, tmp_path):
    import socket

    def reject_network(*args, **kwargs):
        pytest.fail("Network access attempted during offline Copernicus fixture")

    monkeypatch.setattr(socket.socket, "connect", reject_network)
    monkeypatch.setattr(socket, "create_connection", reject_network)

    from copernicusmarine.download_functions.subset_parameters import DepthParameters
    from copernicusmarine.download_functions.subset_xarray import _depth_subset

    raw = xr.Dataset(
        {
            "thetao": (
                ("time", "elevation", "latitude", "longitude"),
                np.array([50, 100, 200, -32767], dtype="i2").reshape(1, 4, 1, 1),
                {
                    "units": "degrees_C",
                    "standard_name": "sea_water_potential_temperature",
                    "cell_methods": "area: mean",
                    "scale_factor": 0.1,
                    "add_offset": 20.0,
                    "_FillValue": np.int16(-32767),
                },
            )
        },
        coords={
            "time": (
                "time",
                [1546300800000],
                {
                    "units": "milliseconds since 1970-01-01 00:00:00",
                    "calendar": "gregorian",
                },
            ),
            "elevation": (
                "elevation",
                [-30.0, -10.0, -1.5, -0.5],
                {"units": "m", "positive": "up", "standard_name": "elevation"},
            ),
            "latitude": ("latitude", [0.0], {"units": "degrees_north"}),
            "longitude": ("longitude", [60.0], {"units": "degrees_east"}),
        },
    )
    decoded = xr.decode_cf(raw)
    transformed = _depth_subset(
        decoded,
        DepthParameters(
            minimum_depth=0.5,
            maximum_depth=10.0,
            vertical_axis="depth",
            coordinate_id="elevation",
        ),
        "strict-inside",
    )
    req = request("copernicus")
    selected = base.model_subset(transformed, req)
    path = tmp_path / "input.nc"
    base.save_dataset(selected, path, req)

    # A backend class avoids discovery/import of unrelated provider plugins.
    with xr.open_dataset(path, engine=xr.backends.NetCDF4BackendEntrypoint) as stored:
        assert "elevation" not in stored.variables
        assert stored.thetao.dims == ("time", "depth", "latitude", "longitude")
        np.testing.assert_array_equal(stored.depth.values, [0.5, 1.5, 10.0])
        assert stored.depth.attrs == {
            "units": "m",
            "positive": "down",
            "standard_name": "depth",
            "long_name": "Depth",
        }
        np.testing.assert_allclose(
            stored.thetao.values.ravel(), [np.nan, 40.0, 30.0], equal_nan=True
        )
        assert stored.thetao.attrs["units"] == "degrees_C"
        assert stored.thetao.attrs["standard_name"] == "sea_water_potential_temperature"
        assert stored.thetao.attrs["cell_methods"] == "area: mean"
        assert stored.time.values[0] == np.datetime64("2019-01-01T00:00:00")
        assert stored.time.encoding["calendar"] == "gregorian"

    with netCDF4.Dataset(path) as stored:
        field = stored.variables["thetao"]
        field.set_auto_maskandscale(False)
        assert field.dtype == np.dtype("int16")
        assert field.scale_factor == 0.1
        assert field.add_offset == 20.0
        assert field._FillValue == -32767
        np.testing.assert_array_equal(field[:].ravel(), [-32767, 200, 100])


def test_copernicus_example_is_bounded_model_request():
    path = (
        Path(__file__).resolve().parents[2]
        / "config"
        / "acquisition.copernicus.example.json"
    )
    example = AcquisitionRequest.model_validate_json(path.read_text(encoding="utf-8"))
    assert example.provider == "copernicus"
    assert example.provider_dataset_id == "cmems_mod_glo_phy_my_0.083deg_P1D-m"
    assert example.provider_version == "202311"
    assert example.variables == ["thetao", "so", "uo", "vo"]
    assert example.coordinates.depth == "depth"
    assert example.selection.vertical_kind == "depth_m"
    assert 0 < example.selection.vertical_min <= example.selection.vertical_max <= 10
    assert (
        example.selection.end_time - example.selection.start_time
    ).total_seconds() <= 3 * 86400
    assert example.max_bytes <= 16_777_216
    assert example.max_values <= 2_000_000


def test_local_acquisition_atomic_unchanged_and_idempotent(monkeypatch, tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config/data_sources.yaml").write_text(
        "schema_version: 1\ndatasets:\n"
        + "  - "
        + json.dumps(definition().model_dump(mode="json"))
        + "\n"
    )
    raw = tmp_path / "data/raw/example.nc"
    tiny_netcdf(raw)
    before = raw.read_bytes()

    def local_worker(root, stage, req):
        return acquisition._import_local(req, definition(), stage / "input.nc", root)

    monkeypatch.setattr(acquisition, "_run_worker", local_worker)
    first = acquisition.acquire_dataset(
        request("local"), tmp_path, data_mode="synthetic"
    )
    second = acquisition.acquire_dataset(
        request("local"), tmp_path, data_mode="synthetic"
    )
    assert second == first
    assert first.status == "acquired_not_prepared"
    assert first.retrieved_at is None
    assert first.input_file.sha256 == hashlib.sha256(before).hexdigest()
    assert raw.read_bytes() == before
    assert acquisition.list_acquisitions(tmp_path) == [first]
    assert not list((tmp_path / "data/raw/acquisitions").glob(".acquire_*"))


def test_source_family_mismatch_blocks_before_worker(monkeypatch, tmp_path):
    (tmp_path / "config").mkdir()
    data = definition().model_dump(mode="json")
    data["dataset_id"] = "incois_godas_2025"
    (tmp_path / "config/data_sources.yaml").write_text(
        "schema_version: 1\ndatasets:\n  - " + json.dumps(data)
    )
    with pytest.raises(ProductError) as found:
        acquisition.acquire_dataset(request("godas"), tmp_path)
    assert found.value.code == "unsupported_source"
    assert not (tmp_path / "data/raw/acquisitions").exists()


def test_worker_deadline_kills_only_own_process(monkeypatch, tmp_path):
    calls = []

    class Process:
        def wait(self, timeout):
            calls.append(("wait", timeout))
            if len(calls) == 1:
                raise subprocess.TimeoutExpired("private", timeout)

        def kill(self):
            calls.append(("kill",))

    monkeypatch.setattr(acquisition.subprocess, "Popen", lambda *a, **k: Process())
    with pytest.raises(ProductError) as found:
        acquisition._run_worker(tmp_path, tmp_path, request(deadline_seconds=5))
    assert found.value.code == "acquisition_timeout"
    assert calls == [("wait", 5), ("kill",), ("wait", 10)]


def test_argo_store_rejects_samples_before_load(monkeypatch, tmp_path):
    def download(url, destination, cap):
        tiny_netcdf(destination)

    monkeypatch.setattr(argo, "bounded_http", download)
    store = argo.BoundedArgoStore(
        tmp_path / "provider_input.nc", request(max_samples=1)
    )
    with pytest.raises(ProductError) as found:
        store.open_dataset("https://erddap.ifremer.fr/erddap/tabledap/ArgoFloats.nc?")
    assert found.value.code == "acquisition_limit"


def test_argo_store_one_response_only(monkeypatch, tmp_path):
    monkeypatch.setattr(
        argo, "bounded_http", lambda url, destination, cap: tiny_netcdf(destination)
    )
    store = argo.BoundedArgoStore(tmp_path / "provider_input.nc", request())
    ds = store.open_dataset("https://erddap.ifremer.fr/erddap/tabledap/ArgoFloats.nc?")
    assert ds.pres.values.tolist() == [1.0, 10.0]
    with pytest.raises(ProductError):
        store.open_dataset("anything")


@pytest.mark.parametrize(
    "url",
    [
        "http://erddap.ifremer.fr/erddap/tabledap/ArgoFloats.nc",
        "https://example.com/erddap/tabledap/ArgoFloats.nc",
        "https://secret@erddap.ifremer.fr/erddap/tabledap/ArgoFloats.nc",
        "https://erddap.ifremer.fr/not-argo",
        "https://erddap.ifremer.fr:1234/erddap/tabledap/ArgoFloats.nc",
    ],
)
def test_http_destination_allowlist(url, tmp_path):
    with pytest.raises(ProductError) as found:
        base.bounded_http(url, tmp_path / "input.nc", 1024)
    assert found.value.code == "unsafe_transport"


def test_erddap_empty_distinct_from_http_failure(monkeypatch, tmp_path):
    class Opener:
        def open(self, *a, **k):
            raise HTTPError(
                "https://erddap.ifremer.fr",
                404,
                "not found",
                {},
                io.BytesIO(b"Your query produced no matching results. (nRows = 0)"),
            )

    monkeypatch.setattr(base, "build_opener", lambda *a: Opener())
    with pytest.raises(ProductError) as found:
        base.bounded_http(
            "https://erddap.ifremer.fr/erddap/tabledap/ArgoFloats.nc?",
            tmp_path / "input.nc",
            1024,
        )
    assert found.value.code == "no_data"


def test_ftp_hard_byte_cap(monkeypatch, tmp_path):
    class FTP:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def connect(self, *args, **kwargs):
            pass

        def login(self, *args, **kwargs):
            pass

        def voidcmd(self, *args):
            pass

        def size(self, *args):
            return 1024

        def retrbinary(self, command, callback, **kwargs):
            callback(b"x" * 1024)
            callback(b"x")

    monkeypatch.setattr(glider, "FTP", FTP)
    with pytest.raises(ProductError) as found:
        glider.fetch(
            request("glider", max_bytes=1024),
            definition("glider"),
            tmp_path / "input.nc",
        )
    assert found.value.code == "acquisition_limit"
    assert (tmp_path / "input.nc").stat().st_size == 1024


@pytest.mark.parametrize("text_encoding", [None, "ISO-8859-1"])
def test_real_argopy_expert_processing_offline(monkeypatch, tmp_path, text_encoding):
    """Run the installed SDK, replacing only the HTTP byte transfer with a fixture."""

    def download(url, destination, cap):
        ds = xr.Dataset(
            {
                "latitude": ("row", [0.5, 0.5], {"units": "degrees_north"}),
                "longitude": ("row", [60.5, 60.5], {"units": "degrees_east"}),
                "time": (
                    "row",
                    np.array(["2019-01-02", "2019-01-02"], dtype="datetime64[ns]"),
                ),
                "platform_number": (
                    "row",
                    np.array(["1234567", "1234567"], dtype="S7"),
                ),
                "cycle_number": ("row", [1, 1]),
                "direction": ("row", np.array(["A", "A"], dtype="S1")),
                "data_mode": ("row", np.array(["D", "D"], dtype="S1")),
                "pres": ("row", [1.0, 10.0]),
                "temp": ("row", [25.0, 24.0]),
                "psal": ("row", [35.0, 35.1]),
                "temp_adjusted": ("row", [25.1, 24.1]),
                "pres_qc": ("row", np.array(["1", "1"], dtype="S1")),
                "temp_qc": ("row", np.array(["4", "1"], dtype="S1")),
                "psal_qc": ("row", np.array(["1", "1"], dtype="S1")),
                "time_qc": ("row", np.array(["1", "1"], dtype="S1")),
                "position_qc": ("row", np.array(["1", "1"], dtype="S1")),
            }
        )
        ds.to_netcdf(
            destination,
            engine="netcdf4",
            encoding={
                name: {"dtype": "S1"}
                for name, var in ds.variables.items()
                if var.dtype.kind in "SU"
            },
        )
        if text_encoding is not None:
            with netCDF4.Dataset(destination, "a") as stored:
                for variable in stored.variables.values():
                    if variable.dtype.kind == "S":
                        variable.setncattr("_Encoding", text_encoding)

    monkeypatch.setattr(argo, "bounded_http", download)
    details = argo.fetch(request(), definition(), tmp_path / "input.nc")
    assert details["client"] == "argopy"
    assert "mode=expert" in details["client_processing"]
    with xr.open_dataset(tmp_path / "input.nc") as ds:
        assert ds.sizes["N_POINTS"] == 2
        assert ds.TEMP_QC.values.tolist() == [4, 1]
        assert ds.TEMP_ADJUSTED.values.tolist() == [25.1, 24.1]
        assert "Fetched_by" not in ds.attrs
    assert (tmp_path / "provider_input.nc").exists()
    from backend.app.processing.observations import normalize_observations
    from backend.app.schemas.observations import ObservationRequest

    observed = normalize_observations(
        tmp_path / "input.nc",
        ObservationRequest(
            region=request().selection.region,
            start_date="2019-01-01",
            end_date="2019-01-03",
            pressure_min_dbar=0,
            pressure_max_dbar=20,
            variables=["PRES", "TEMP", "PSAL"],
            value_mode="raw",
        ),
        source_id="argo",
        dataset_id="argo_gdac",
        data_mode="synthetic",
        client_processing="argopy_expert_no_qc_filter",
    )
    assert observed.counts.selected_samples == 2
    assert observed.samples[0].values["TEMP"].raw == 25.0
    assert observed.samples[0].values["TEMP"].raw_qc == "4"
    assert observed.samples[0].values["TEMP"].qc_eligible is False
    assert observed.samples[1].values["TEMP"].qc_eligible is True
    assert observed.samples[0].time == "2019-01-02T00:00:00Z"


def test_http_unknown_length_cannot_exceed_saved_bytes(monkeypatch, tmp_path):
    class Response(io.BytesIO):
        headers = {}

    class Opener:
        def open(self, *args, **kwargs):
            return Response(b"x" * 1025)

    monkeypatch.setattr(base, "build_opener", lambda *args: Opener())
    destination = tmp_path / "input.nc"
    with pytest.raises(ProductError) as found:
        base.bounded_http(
            "https://erddap.ifremer.fr/erddap/tabledap/ArgoFloats.nc?",
            destination,
            1024,
        )
    assert found.value.code == "acquisition_limit"
    assert destination.stat().st_size <= 1024


def test_http_verified_certifi_context(monkeypatch, tmp_path):
    import ssl
    from urllib.request import HTTPSHandler

    class Response(io.BytesIO):
        headers = {"Content-Length": "3"}

    def opener(*handlers):
        https = next(
            handler for handler in handlers if isinstance(handler, HTTPSHandler)
        )
        assert https._context.check_hostname is True
        assert https._context.verify_mode == ssl.CERT_REQUIRED
        assert https._context.get_ca_certs()

        def open_response(request, **kwargs):
            assert ">" not in request.full_url
            assert '"' not in request.full_url
            assert "%3E=" in request.full_url
            assert "%22" in request.full_url
            return Response(b"abc")

        return SimpleNamespace(open=open_response)

    monkeypatch.setattr(base, "build_opener", opener)
    assert (
        base.bounded_http(
            'https://erddap.ifremer.fr/erddap/tabledap/ArgoFloats.nc?pres&pres>=0&orderBy("time,pres")',
            tmp_path / "input.nc",
            1024,
        )
        == 3
    )
