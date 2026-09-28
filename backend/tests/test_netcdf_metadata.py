"""Offline header-inspection checks using only tiny synthetic temporary files."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import netCDF4
import numpy as np
import pytest

from backend.app.ingestion import netcdf_metadata as metadata


@pytest.fixture
def synthetic_netcdf(tmp_path: Path) -> Path:
    path = tmp_path / "synthetic_surface_not_ocean_data.nc"
    with netCDF4.Dataset(path, "w") as dataset:
        dataset.title = "SYNTHETIC metadata fixture; not scientific source data"
        dataset.Conventions = "CF-1.8"
        dataset.geospatial_lat_min = -80.0
        dataset.geospatial_lat_max = 80.0
        dataset.time_coverage_start = "1980-01-01"
        dataset.createDimension("time", None)
        dataset.createDimension("lat", 3)
        dataset.createDimension("lon", 3)
        time = dataset.createVariable("time", "f8", ("time",))
        time.setncatts(
            {"units": "days since 1980-01-01", "calendar": "360_day", "axis": "T"}
        )
        time[:] = [0, 30]
        latitude = dataset.createVariable("lat", "f4", ("lat",))
        latitude.setncatts({"units": "degrees_north", "standard_name": "latitude"})
        latitude[:] = [20, -20, 0]
        longitude = dataset.createVariable("lon", "f4", ("lon",))
        longitude.setncatts({"units": "degrees_east", "axis": "X"})
        longitude[:] = [40, 90, 60]
        temperature = dataset.createVariable(
            "SST",
            "i2",
            ("time", "lat", "lon"),
            fill_value=-32767,
            chunksizes=(1, 3, 3),
        )
        temperature.setncatts(
            {
                "units": "K",
                "standard_name": "sea_surface_temperature",
                "scale_factor": np.float32(0.01),
                "add_offset": np.float32(273.15),
                "missing_value": np.int16(-32766),
                "_Unsigned": "true",
                "coordinates": "time lat lon",
                "ancillary_variables": "TEMP_QC",
                "cell_methods": "time: mean",
            }
        )
        qc = dataset.createVariable("TEMP_QC", "u1", ("time", "lat", "lon"))
        qc.setncatts(
            {
                "flag_values": np.array([1, 4, 9], dtype="u1"),
                "flag_meanings": "good bad missing",
            }
        )
        mixed_layer_depth = dataset.createVariable(
            "MLD", "f4", ("time", "lat", "lon"), fill_value=np.nan
        )
        mixed_layer_depth.setncatts(
            {
                "units": "m",
                "standard_name": "ocean_mixed_layer_thickness",
                "positive": "down",
                "synthetic_calibration": np.array([np.nan, np.inf, -np.inf, 1]),
            }
        )
    return path


def test_preserves_actual_packed_and_qc_metadata(synthetic_netcdf: Path) -> None:
    report = metadata.inspect_netcdf_metadata(synthetic_netcdf)
    assert report["inspection_mode"] == "header_only"
    assert report["data_values_read"] is False
    assert report["dimensions"]["time"] == {"length": 2, "unlimited": True}
    assert report["dimensions"]["lat"] == {"length": 3, "unlimited": False}
    assert set(report["variables"]) == {"time", "lat", "lon", "SST", "TEMP_QC", "MLD"}
    temperature = report["variables"]["SST"]
    assert temperature["dimensions"] == ["time", "lat", "lon"]
    assert temperature["shape"] == [2, 3, 3]
    assert temperature["dtype"] == "int16"
    assert temperature["chunking"] == [1, 3, 3]
    assert temperature["attributes"]["_FillValue"] == -32767
    assert temperature["attributes"]["missing_value"] == -32766
    assert temperature["attributes"]["scale_factor"] == pytest.approx(0.01)
    assert temperature["attributes"]["add_offset"] == pytest.approx(273.15)
    assert temperature["attributes"]["_Unsigned"] == "true"
    assert temperature["attributes"]["coordinates"] == "time lat lon"
    assert temperature["attributes"]["ancillary_variables"] == "TEMP_QC"
    assert temperature["attributes"]["cell_methods"] == "time: mean"
    qc = report["variables"]["TEMP_QC"]
    assert qc["attributes"]["flag_values"] == [1, 4, 9]
    assert qc["attributes"]["flag_meanings"] == "good bad missing"
    assert qc["observations"] == ["units_not_declared", "standard_name_not_declared"]
    assert report["variables"]["time"]["attributes"]["calendar"] == "360_day"
    assert report["variables"]["MLD"]["attributes"]["positive"] == "down"


def test_nonfinite_attributes_are_explicit_json_null(synthetic_netcdf: Path) -> None:
    report = metadata.inspect_netcdf_metadata(synthetic_netcdf)
    attributes = report["variables"]["MLD"]["attributes"]
    assert attributes["_FillValue"] is None
    assert attributes["synthetic_calibration"] == [None, None, None, 1.0]
    assert "non_finite_attribute_values_serialized_as_null" in report["observations"]
    json.dumps(report, allow_nan=False)


def test_coverage_is_declared_only_without_extents(synthetic_netcdf: Path) -> None:
    report = metadata.inspect_netcdf_metadata(synthetic_netcdf)
    coverage = report["coverage"]
    assert coverage["verification"] == "not_computed"
    assert coverage["coordinate_values_read"] is False
    assert coverage["declared_global_attributes"]["geospatial_lat_min"] == -80
    assert "axis_extents" not in coverage
    assert str(synthetic_netcdf) not in json.dumps(report)


def test_candidates_have_evidence_not_vertical_capabilities(
    synthetic_netcdf: Path,
) -> None:
    report = metadata.inspect_netcdf_metadata(synthetic_netcdf)
    candidates = report["coordinate_candidates"]
    assert any(
        candidate["name"] == "lat"
        and candidate["role"] == "latitude"
        and "standard_name=latitude" in candidate["evidence"]
        for candidate in candidates
    )
    assert not any(candidate["name"] in ("MLD", "SST") for candidate in candidates)
    assert not any(candidate["role"] == "vertical" for candidate in candidates)
    assert report["capability_status"] == "not_evaluated"
    assert "volume" not in report
    assert "profiles" not in report


def test_projected_axis_is_not_assumed_geographic(tmp_path: Path) -> None:
    path = tmp_path / "synthetic_projected.nc"
    with netCDF4.Dataset(path, "w") as dataset:
        dataset.createDimension("x", 2)
        variable = dataset.createVariable("x", "f4", ("x",))
        variable.setncatts({"axis": "X", "units": "m"})
    candidates = metadata.inspect_netcdf_metadata(path)["coordinate_candidates"]
    assert candidates == [{"name": "x", "role": "horizontal_x", "evidence": ["axis=X"]}]


class _NoReadVariable:
    def __init__(self, variable: Any) -> None:
        self._variable = variable

    def __getattr__(self, name: str) -> Any:
        return getattr(self._variable, name)

    def __getitem__(self, key: Any) -> Any:
        raise AssertionError("Header inspection must not read any variable values")


class _TrackedDataset:
    def __init__(self, dataset: Any) -> None:
        self._dataset = dataset
        self.variables = {
            name: _NoReadVariable(variable)
            for name, variable in dataset.variables.items()
        }

    def __getattr__(self, name: str) -> Any:
        return getattr(self._dataset, name)

    def __enter__(self) -> "_TrackedDataset":
        return self

    def __exit__(self, *args: Any) -> None:
        self._dataset.close()


@pytest.mark.parametrize("fail", [False, True])
def test_no_value_reads_and_handle_closed(
    synthetic_netcdf: Path, monkeypatch: pytest.MonkeyPatch, fail: bool
) -> None:
    original = netCDF4.Dataset
    opened = []

    def tracked_open(path: str, *, mode: str) -> _TrackedDataset:
        assert mode == "r"
        dataset = original(path, mode=mode)
        opened.append(dataset)
        return _TrackedDataset(dataset)

    monkeypatch.setattr(netCDF4, "Dataset", tracked_open)
    if fail:
        monkeypatch.setattr(metadata, "MAX_VARIABLES", 1)
        with pytest.raises(metadata.MetadataInspectionError):
            metadata.inspect_netcdf_metadata(synthetic_netcdf)
    else:
        metadata.inspect_netcdf_metadata(synthetic_netcdf)
    assert len(opened) == 1
    assert not opened[0].isopen()


def test_corrupt_file_has_safe_error(tmp_path: Path) -> None:
    path = tmp_path / "private_name_must_not_be_exposed.nc"
    path.write_bytes(b"not a NetCDF file")
    with pytest.raises(metadata.MetadataInspectionError) as error:
        metadata.inspect_netcdf_metadata(path)
    assert error.value.code == "invalid_netcdf"
    assert str(path) not in error.value.message
    assert path.name not in error.value.message


def test_groups_rejected_instead_of_ignored(tmp_path: Path) -> None:
    path = tmp_path / "synthetic_groups.nc"
    with netCDF4.Dataset(path, "w") as dataset:
        dataset.createGroup("observations")
    with pytest.raises(metadata.MetadataInspectionError) as error:
        metadata.inspect_netcdf_metadata(path)
    assert error.value.code == "unsupported_groups"


@pytest.mark.parametrize("custom_type", ["enum", "compound", "vlen"])
def test_custom_types_rejected(tmp_path: Path, custom_type: str) -> None:
    path = tmp_path / "synthetic_custom.nc"
    with netCDF4.Dataset(path, "w") as dataset:
        dataset.createDimension("sample", 1)
        if custom_type == "enum":
            datatype = dataset.createEnumType(np.uint8, "flag", {"good": 1, "bad": 4})
        elif custom_type == "compound":
            datatype = dataset.createCompoundType(np.dtype([("x", "f4")]), "compound")
        else:
            datatype = dataset.createVLType(np.int32, "variable_length")
        dataset.createVariable("unsupported", datatype, ("sample",))
    with pytest.raises(metadata.MetadataInspectionError) as error:
        metadata.inspect_netcdf_metadata(path)
    assert error.value.code == "unsupported_data_type"


@pytest.mark.parametrize("format_name", ["NETCDF4", "NETCDF3_CLASSIC"])
def test_basic_files_without_claimed_coverage(tmp_path: Path, format_name: str) -> None:
    path = tmp_path / "synthetic_basic.nc"
    with netCDF4.Dataset(path, "w", format=format_name) as dataset:
        dataset.createVariable("scalar", "f4")
    report = metadata.inspect_netcdf_metadata(path)
    assert report["data_model"] == format_name
    assert report["coverage"]["declared_global_attributes"] == {}
    assert report["variables"]["scalar"]["shape"] == []


@pytest.mark.parametrize(
    "limit",
    [
        "MAX_DIMENSIONS",
        "MAX_VARIABLES",
        "MAX_ATTRIBUTES_PER_OBJECT",
        "MAX_TOTAL_ATTRIBUTES",
        "MAX_ATTRIBUTE_ELEMENTS",
        "MAX_ATTRIBUTE_BYTES",
        "MAX_NAME_LENGTH",
        "MAX_SERIALIZED_NODES",
        "MAX_REPORT_BYTES",
    ],
)
def test_metadata_limits_are_explicit(
    synthetic_netcdf: Path, monkeypatch: pytest.MonkeyPatch, limit: str
) -> None:
    monkeypatch.setattr(metadata, limit, 1)
    with pytest.raises(metadata.MetadataInspectionError) as error:
        metadata.inspect_netcdf_metadata(synthetic_netcdf)
    assert error.value.code == "metadata_limit_exceeded"


def test_import_does_not_load_scientific_libraries(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[2]
    script = (
        "import sys; "
        f"sys.path.insert(0, {str(project_root)!r}); "
        "import backend.app.ingestion.netcdf_metadata; "
        "assert 'netCDF4' not in sys.modules; "
        "assert 'numpy' not in sys.modules; "
        "assert 'xarray' not in sys.modules"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", script],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
