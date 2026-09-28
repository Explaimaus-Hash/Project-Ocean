"""Synthetic local Argo/EGO fixtures, never live data or model comparisons."""

import json

import netCDF4
import numpy as np
import pytest
from pydantic import ValidationError

from backend.app.processing import observations
from backend.app.schemas.observations import ObservationCollection, ObservationRequest
from backend.app.storage.product_common import ProductError


@pytest.fixture
def observation_request():
    return ObservationRequest(
        region={"west": 30, "east": 120, "south": -30, "north": 30},
        start_date="2024-01-01",
        end_date="2024-01-31",
        pressure_min_dbar=0,
        pressure_max_dbar=2000,
        variables=["PRES", "TEMP", "PSAL"],
        value_mode="raw",
    )


def make_observations(path, *, layout="profiles", adjusted=True, sample_count=6):
    with netCDF4.Dataset(path, "w") as ds:
        if layout == "profiles":
            ds.createDimension("N_PROF", 2)
            ds.createDimension("N_LEVELS", 3)
            sample_dims = ("N_PROF", "N_LEVELS")
            position_dims = ("N_PROF",)
            time_name = "JULD"
            shape = (2, 3)
        else:
            sample_dims = ("N_POINTS" if layout == "points" else "N_MEASUREMENTS",)
            ds.createDimension(sample_dims[0], sample_count)
            position_dims = sample_dims
            time_name = "TIME"
            shape = (sample_count,)
        if layout == "glider":
            ds.data_type = "EGO glider time-series data"
            ds.format_version = "1.2"
            ds.platform_code = "TestGlider"
            ds.data_mode = "R"
        count = 2 if layout == "profiles" else sample_count
        for name, units, value in (
            ("LATITUDE", "degrees_north", 5),
            ("LONGITUDE", "degrees_east", 70),
            (time_name, "days since 2024-01-01 00:00:00", 1),
        ):
            variable = ds.createVariable(name, "f8", position_dims, fill_value=np.nan)
            variable.units = units
            variable[:] = [value] * count
        for name in (time_name + "_QC", "POSITION_QC"):
            ds.createVariable(name, "S1", position_dims)[:] = np.array([b"1"] * count)
        if layout != "glider":
            ds.createVariable("PLATFORM_NUMBER", "i8", position_dims)[:] = [
                6900001
            ] * count
            ds.createVariable("CYCLE_NUMBER", "i4", position_dims)[:] = [8] * count
            ds.createVariable("DIRECTION", "S1", position_dims)[:] = np.array(
                [b"A"] * count
            )
            ds.createVariable("DATA_MODE", "S1", position_dims)[:] = np.array(
                [b"D"] * count
            )
        for name, units, value in (
            ("PRES", "dbar", 5),
            ("TEMP", "degree_Celsius", 21),
            ("PSAL", "psu", 35),
        ):
            raw = ds.createVariable(name, "f8", sample_dims, fill_value=np.nan)
            raw.units = units
            raw[:] = np.full(shape, value)
            ds.createVariable(name + "_QC", "S1", sample_dims)[:] = np.full(shape, b"1")
            if adjusted:
                adj = ds.createVariable(
                    name + "_ADJUSTED", "f8", sample_dims, fill_value=np.nan
                )
                adj.units = units
                adj[:] = np.full(shape, value + 0.5)
                ds.createVariable(name + "_ADJUSTED_QC", "S1", sample_dims)[:] = (
                    np.full(shape, b"2")
                )
                error = ds.createVariable(name + "_ADJUSTED_ERROR", "f8", sample_dims)
                error.units = units
                error[:] = np.full(shape, 0.1)
    return path


def normalized(path, request, source_id="argo"):
    return observations.normalize_observations(
        path,
        request,
        source_id=source_id,
        dataset_id="fixture_observations",
        data_mode="synthetic",
    )


def test_profiles_identity_raw_adjusted_and_source_time(tmp_path, observation_request):
    path = make_observations(tmp_path / "profiles.nc")
    result = normalized(path, observation_request)
    assert result.counts.selected_samples == 6
    assert result.source_time_name == "JULD"
    assert result.samples[0].time == "2024-01-02T00:00:00Z"
    assert result.samples[0].profile_id != result.samples[3].profile_id
    assert result.samples[0].profile_id == result.samples[2].profile_id
    assert result.samples[1].source_level_index == 1
    assert result.samples[0].values["TEMP"].raw == 21
    assert result.samples[0].values["TEMP"].adjusted == 21.5
    assert result.samples[0].values["TEMP"].adjusted_error == 0.1
    assert result.samples[0].values["TEMP"].selected_source_name == "TEMP"
    assert result.samples[0].depth_m is None
    assert result.capabilities.comparison_ready is False
    assert result == normalized(path, observation_request)
    assert ObservationCollection.model_validate_json(result.model_dump_json()) == result


def test_adjusted_selection_changes_pressure_and_identity(
    tmp_path, observation_request
):
    path = make_observations(tmp_path / "profiles.nc")
    raw = normalized(path, observation_request)
    adjusted = normalized(
        path, observation_request.model_copy(update={"value_mode": "adjusted"})
    )
    assert adjusted.collection_id != raw.collection_id
    assert adjusted.samples[0].sample_id == raw.samples[0].sample_id
    assert adjusted.samples[0].pressure_dbar == 5.5
    assert adjusted.samples[0].values["TEMP"].selected_value == 21.5
    assert adjusted.samples[0].values["TEMP"].qc_eligible


def test_missing_adjusted_pressure_never_falls_back(tmp_path, observation_request):
    path = make_observations(tmp_path / "raw.nc", adjusted=False)
    result = normalized(
        path, observation_request.model_copy(update={"value_mode": "adjusted"})
    )
    assert result.samples == []
    assert result.counts.missing_filter_coordinates == 6


def test_qc_rejections_retained_and_counted(tmp_path, observation_request):
    path = make_observations(tmp_path / "qc.nc")
    with netCDF4.Dataset(path, "a") as ds:
        ds["TEMP_QC"][0, 0] = b"4"
        ds["PRES_QC"][0, 1] = b"9"
        ds["POSITION_QC"][1] = b"8"
        ds["PSAL"][0, 2] = np.nan
    result = normalized(path, observation_request)
    assert result.counts.selected_samples == 6
    assert result.counts.coordinate_qc_rejected == 4
    assert result.counts.variable_qc_rejected == {"PRES": 4, "TEMP": 5, "PSAL": 5}
    assert result.samples[0].values["TEMP"].raw == 21
    assert not result.samples[0].values["TEMP"].qc_eligible
    assert result.samples[2].values["PSAL"].selected_value is None
    assert "NaN" not in result.model_dump_json()


def test_region_dates_pressure_filter_accounting(tmp_path, observation_request):
    path = make_observations(tmp_path / "filter.nc")
    with netCDF4.Dataset(path, "a") as ds:
        ds["LATITUDE"][0] = np.nan
        ds["JULD"][1] = 40
    result = normalized(path, observation_request)
    assert result.counts.missing_filter_coordinates == 3
    assert result.counts.outside_selection == 3
    assert result.samples == []
    assert not result.capabilities.profiles


def test_argo_points_do_not_invent_profile_identity(tmp_path, observation_request):
    path = make_observations(tmp_path / "points.nc", layout="points")
    result = normalized(path, observation_request)
    assert result.layout == "argo_points"
    assert all(
        sample.profile_identity_status == "ambiguous_points"
        for sample in result.samples
    )
    assert not result.capabilities.profiles
    assert "argopy_point_representation_is_not_untouched_gdac" in result.warnings


def test_argo_points_configuration_does_not_prove_profile(
    tmp_path, observation_request
):
    path = make_observations(tmp_path / "points.nc", layout="points")
    with netCDF4.Dataset(path, "a") as ds:
        ds.createVariable("CONFIG_MISSION_NUMBER", "i4", ("N_POINTS",))[:] = [
            1,
            1,
            1,
            2,
            2,
            2,
        ]
    result = normalized(path, observation_request)
    assert not result.capabilities.profiles
    assert result.samples[0].profile_discriminator == "1"


def test_argo_points_explicit_profile_identifier(tmp_path, observation_request):
    path = make_observations(tmp_path / "points.nc", layout="points")
    with netCDF4.Dataset(path, "a") as ds:
        ds.createVariable("PROFILE_NUMBER", "i4", ("N_POINTS",))[:] = [1, 1, 1, 2, 2, 2]
    result = normalized(path, observation_request)
    assert result.capabilities.profiles
    assert result.samples[0].profile_id != result.samples[3].profile_id


def test_glider_track_depth_and_fluorescence_metadata(tmp_path, observation_request):
    path = make_observations(tmp_path / "ego.nc", layout="glider")
    with netCDF4.Dataset(path, "a") as ds:
        depth = ds.createVariable("GLIDER_DEPTH", "f8", ("N_MEASUREMENTS",))
        depth.units = "m"
        depth.positive = "down"
        depth[:] = [4.9] * 6
        ds.createVariable("GLIDER_DEPTH_QC", "S1", ("N_MEASUREMENTS",))[:] = np.array(
            [b"1"] * 6
        )
        fluorescence = ds.createVariable("FLUORESCENCE_CHLA", "f8", ("N_MEASUREMENTS",))
        fluorescence.units = "counts"
        fluorescence[:] = [100] * 6
        ds.createVariable("FLUORESCENCE_CHLA_QC", "S1", ("N_MEASUREMENTS",))[:] = (
            np.array([b"1"] * 6)
        )
        ds.createDimension("N_GPS", 2)
        ds.createVariable("TIME_GPS", "f8", ("N_GPS",))[:] = [0, 1]
        ds.createVariable("LATITUDE_GPS", "f8", ("N_GPS",))[:] = [80, 80]
    request = observation_request.model_copy(
        update={
            "variables": [
                *observation_request.variables,
                "GLIDER_DEPTH",
                "FLUORESCENCE_CHLA",
            ]
        }
    )
    result = normalized(path, request, "ifremer_glider")
    assert result.layout == "ego_timeseries"
    assert not result.capabilities.profiles
    assert result.samples[0].depth_m == 4.9
    assert result.samples[0].pressure_dbar == 5
    assert result.samples[0].latitude == 5
    assert result.variables["FLUORESCENCE_CHLA"].units == "counts"
    assert not result.samples[0].values["FLUORESCENCE_CHLA"].qc_eligible
    assert "separate_gps_fixes_not_zipped_to_sensor_samples" in result.warnings


def test_glider_misaligned_sensor_positions_fail(tmp_path, observation_request):
    path = make_observations(tmp_path / "ego.nc", layout="glider")
    with netCDF4.Dataset(path, "a") as ds:
        ds.renameVariable("LATITUDE", "OLD_LATITUDE")
        ds.createDimension("N_GPS", 2)
        latitude = ds.createVariable("LATITUDE", "f8", ("N_GPS",))
        latitude.units = "degrees_north"
        latitude[:] = [5, 5]
    with pytest.raises(ProductError, match="sample-aligned"):
        normalized(path, observation_request, "ifremer_glider")


@pytest.mark.parametrize(
    ("variable", "attribute", "value", "code"),
    [
        ("TEMP", "units", "K", "unsupported_units"),
        ("JULD", "calendar", "360_day", "unsupported_calendar"),
        ("LONGITUDE", "units", "radians", "unsupported_coordinates"),
        ("TEMP_ADJUSTED", "units", "K", "unsupported_units"),
    ],
)
def test_unsupported_metadata(
    tmp_path, observation_request, variable, attribute, value, code
):
    path = make_observations(tmp_path / "bad.nc")
    with netCDF4.Dataset(path, "a") as ds:
        ds[variable].setncattr(attribute, value)
    with pytest.raises(ProductError) as error:
        normalized(path, observation_request)
    assert error.value.code == code


@pytest.mark.parametrize(
    "name,value,code",
    [("TEMP_QC", b"X", "unsupported_qc"), ("DATA_MODE", b"M", "unsupported_data_mode")],
)
def test_unsupported_flags(tmp_path, observation_request, name, value, code):
    path = make_observations(tmp_path / "bad.nc")
    with netCDF4.Dataset(path, "a") as ds:
        ds[name][:] = value
    with pytest.raises(ProductError) as error:
        normalized(path, observation_request)
    assert error.value.code == code


def test_selected_limit_checked_before_science_bundle(
    tmp_path, observation_request, monkeypatch
):
    path = make_observations(tmp_path / "bounded.nc")
    monkeypatch.setattr(observations, "MAX_OBSERVATION_SAMPLES", 5)
    monkeypatch.setattr(
        observations,
        "_value_bundle",
        lambda *args: pytest.fail("read science before limit"),
    )
    with pytest.raises(ProductError) as error:
        normalized(path, observation_request)
    assert error.value.code == "observation_limit"


def test_header_limit_before_xarray_open(tmp_path, observation_request, monkeypatch):
    import xarray as xr

    path = make_observations(tmp_path / "bounded.nc")
    monkeypatch.setattr(observations, "MAX_DECODED_BYTES", 1)
    monkeypatch.setattr(
        xr,
        "open_dataset",
        lambda *args, **kwargs: pytest.fail("opened before preflight"),
    )
    with pytest.raises(ProductError) as error:
        normalized(path, observation_request)
    assert error.value.code == "observation_limit"


@pytest.mark.parametrize(
    "field,value",
    [
        ("start_date", "2025-01-01"),
        ("pressure_min_dbar", -1),
        ("variables", ["TEMP"]),
        ("variables", ["PRES", "PRES"]),
        ("value_mode", "auto"),
    ],
)
def test_request_contract(observation_request, field, value):
    request = observation_request.model_dump(mode="json")
    request[field] = value
    with pytest.raises(ValidationError):
        ObservationRequest.model_validate(request)


@pytest.mark.parametrize(
    "mutation", ["time", "outside", "pressure", "eligible", "count", "profiles"]
)
def test_collection_rejects_inconsistent_serialized_payload(
    tmp_path, observation_request, mutation
):
    result = normalized(make_observations(tmp_path / "source.nc"), observation_request)
    payload = json.loads(result.model_dump_json())
    if mutation == "time":
        payload["samples"][0]["time"] = "not a date"
    elif mutation == "outside":
        payload["samples"][0]["longitude"] = 0
    elif mutation == "pressure":
        payload["samples"][0]["pressure_dbar"] = 900
    elif mutation == "eligible":
        payload["samples"][0]["values"]["TEMP"]["selected_qc"] = "4"
    elif mutation == "count":
        payload["counts"]["coordinate_qc_rejected"] = 5
    else:
        payload["capabilities"]["profiles"] = False
    with pytest.raises(ValidationError):
        ObservationCollection.model_validate(payload)


def test_fractional_source_seconds_preserved(tmp_path, observation_request):
    path = make_observations(tmp_path / "fractional.nc")
    with netCDF4.Dataset(path, "a") as ds:
        ds["JULD"].units = "seconds since 2024-01-01 00:00:00"
        ds["JULD"][:] = [1.125, 2.75]
    result = normalized(path, observation_request)
    assert result.samples[0].time == "2024-01-01T00:00:01.125000Z"
    assert result.samples[3].time == "2024-01-01T00:00:02.750000Z"


def test_fixed_width_xarray_client_text_roundtrip(tmp_path, observation_request):
    import xarray as xr

    source = make_observations(tmp_path / "points.nc", layout="points")
    target = tmp_path / "client_output.nc"
    with xr.open_dataset(source, decode_times=False) as ds:
        copy = ds.load()
        copy["DIRECTION"] = xr.DataArray(np.array(["A"] * 6), dims="N_POINTS")
        copy["DATA_MODE"] = xr.DataArray(np.array(["D"] * 6), dims="N_POINTS")
        copy["PLATFORM_NUMBER"] = xr.DataArray(
            np.array(["6900001"] * 6), dims="N_POINTS"
        )
        encoding = {
            name: {"dtype": "S1"}
            for name in copy.variables
            if copy[name].dtype.kind in "US"
        }
        copy.to_netcdf(target, engine="netcdf4", encoding=encoding)
    result = normalized(target, observation_request)
    assert result.counts.selected_samples == 6
    assert result.samples[0].platform_id == "6900001"
    assert result.samples[0].values["TEMP"].data_mode == "D"


def test_global_metadata_limit(tmp_path, observation_request):
    path = make_observations(tmp_path / "attrs.nc")
    with netCDF4.Dataset(path, "a") as ds:
        ds.title = "x" * 8193
    with pytest.raises(ProductError) as error:
        normalized(path, observation_request)
    assert error.value.code == "metadata_limit"


def test_raw_profile_station_parameter_modes(tmp_path, observation_request):
    path = make_observations(tmp_path / "modes.nc")
    with netCDF4.Dataset(path, "a") as ds:
        ds.createDimension("N_PARAM", 3)
        ds.createDimension("STRING16", 16)
        names = ds.createVariable(
            "STATION_PARAMETERS", "S1", ("N_PROF", "N_PARAM", "STRING16")
        )
        names[:] = (
            np.array([["PRES", "TEMP", "PSAL"]] * 2, dtype="S16")
            .view("S1")
            .reshape(2, 3, 16)
        )
        modes = ds.createVariable("PARAMETER_DATA_MODE", "S1", ("N_PROF", "N_PARAM"))
        modes[:] = np.array([[b"D", b"R", b"A"]] * 2)
    request = observation_request.model_copy(update={"value_mode": "adjusted"})
    result = normalized(path, request)
    assert result.samples[0].values["PRES"].qc_eligible
    assert not result.samples[0].values["TEMP"].qc_eligible
    assert result.samples[0].values["TEMP"].data_mode == "R"
    assert result.samples[0].values["PSAL"].qc_eligible


def test_ego_scans_large_source_in_chunks_not_whole_arrays(
    tmp_path, observation_request, monkeypatch
):
    path = make_observations(
        tmp_path / "large_ego.nc", layout="glider", adjusted=False, sample_count=100005
    )
    with netCDF4.Dataset(path, "a") as ds:
        ds["LATITUDE"][:] = [-60] * 100005
        ds["LATITUDE"][100003] = 5
    calls = []
    original = observations._Reader.values

    def bounded_read(self, name, rows=None, **kwargs):
        assert rows is not None, "Chunked scanner must never request a full array"
        calls.append((name, len(rows)))
        return original(self, name, rows, **kwargs)

    monkeypatch.setattr(observations._Reader, "values", bounded_read)
    # This whole-file logical budget applies to Argo, not lazy EGO engineering arrays.
    monkeypatch.setattr(observations, "MAX_DECODED_BYTES", 1)
    result = normalized(path, observation_request, "ifremer_glider")
    assert result.counts.input_samples == 100005
    assert result.counts.outside_selection == 100004
    assert result.counts.selected_samples == 1
    assert result.samples[0].source_sample_index == 100003
    assert max(length for _, length in calls) <= observations.COORDINATE_SCAN_CHUNK
    assert all(length == 1 for name, length in calls if name in {"TEMP", "PSAL"})


def test_ego_scan_ceiling_before_coordinate_reads(
    tmp_path, observation_request, monkeypatch
):
    path = make_observations(tmp_path / "bounded_ego.nc", layout="glider")
    monkeypatch.setattr(observations, "MAX_EGO_SCAN_SAMPLES", 5)
    monkeypatch.setattr(
        observations._Reader,
        "values",
        lambda *args, **kwargs: pytest.fail("Coordinates read before scan ceiling"),
    )
    with pytest.raises(ProductError) as error:
        normalized(path, observation_request, "ifremer_glider")
    assert error.value.code == "observation_limit"


def test_coordinate_valid_range_conflict_is_not_silently_ignored(
    tmp_path, observation_request, monkeypatch
):
    path = make_observations(tmp_path / "bad_time.nc", layout="glider")
    with netCDF4.Dataset(path, "a") as ds:
        ds["TIME"].units = "seconds since 1970-01-01T00:00:00Z"
        ds["TIME"].valid_min = 0.0
        ds["TIME"].valid_max = 90000.0
        ds["TIME"][:] = [1707239420.3659995] * 6
    monkeypatch.setattr(
        observations,
        "_value_bundle",
        lambda *args: pytest.fail("Science read before coordinate validation"),
    )
    with pytest.raises(ProductError) as error:
        normalized(path, observation_request, "ifremer_glider")
    assert error.value.code == "invalid_coordinate_metadata"


def test_declared_science_bounds_mask_values_and_preserve_metadata(
    tmp_path, observation_request
):
    path = make_observations(tmp_path / "ranges.nc")
    with netCDF4.Dataset(path, "a") as ds:
        ds["TEMP"].valid_range = np.array([0, 20], dtype="f8")
    result = normalized(path, observation_request)
    assert result.samples[0].values["TEMP"].raw is None
    assert result.samples[0].values["TEMP"].adjusted == 21.5
    assert not result.samples[0].values["TEMP"].qc_eligible
    assert result.variables["TEMP"].valid_min == 0
    assert result.variables["TEMP"].valid_max == 20
    assert result.variables["TEMP"].raw_encoding.valid_max == 20
    assert "declared_valid_range_masks_applied" in result.warnings


@pytest.mark.parametrize(
    "scale,offset,bounds,expected",
    [(0.1, 20, [0, 20], [20, 22]), (-0.1, 20, [-20, 0], [20, 22])],
)
def test_packed_valid_bounds_decoded_like_values(
    tmp_path, observation_request, scale, offset, bounds, expected
):
    path = make_observations(tmp_path / "packed.nc")
    with netCDF4.Dataset(path, "a") as ds:
        variable = ds["TEMP"]
        variable.scale_factor = scale
        variable.add_offset = offset
        variable.valid_range = np.array(bounds, dtype="f8")
        # Assignment packs the requested decoded scientific value.
        variable[:] = np.full((2, 3), 21.0)
    result = normalized(path, observation_request)
    assert result.samples[0].values["TEMP"].raw == pytest.approx(21)
    assert result.samples[0].values["TEMP"].qc_eligible
    info = result.variables["TEMP"]
    assert [info.valid_min, info.valid_max] == expected
    assert info.raw_encoding.scale_factor == scale
    assert info.raw_encoding.valid_min == bounds[0]
