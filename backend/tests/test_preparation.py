"""Tiny synthetic preparation fixtures, never the downloaded V2 source."""

import hashlib
import json
from datetime import date
from pathlib import Path

import netCDF4
import numpy as np
import pytest

from backend.app.ingestion.incois_bio_roms import inspect_local_dataset
from backend.app.ingestion.registry import find_dataset, load_registry
from backend.app.processing import prepare_bio_roms as prep
from backend.app.schemas.products import PerformanceLimits, PreparationRequest, Region
from backend.app.storage.inspection_reports import save_inspection_report
from backend.app.storage.product_common import ProductError


def selection(**changes):
    values = {
        "variables": ["SST", "SSS"],
        "region": Region(west=30, east=40, south=-5, north=5),
        "start_date": date(2019, 1, 1),
        "end_date": date(2019, 3, 31),
    }
    values.update(changes)
    return PreparationRequest(**values)


def refresh(root: Path):
    raw = root / "data/raw/v2.nc"
    digest = hashlib.md5(raw.read_bytes(), usedforsecurity=False).hexdigest()
    registry = {
        "schema_version": 1,
        "datasets": [
            {
                "source_id": "incois_bio_roms",
                "dataset_id": "incois_bio_roms_v2",
                "title": "Synthetic V2-shaped fixture",
                "role": "model",
                "access_method": "local_netcdf",
                "origin_url": "https://example.org/synthetic",
                "version": "v2",
                "local_path": "data/raw/v2.nc",
                "expected_md5": digest,
            }
        ],
    }
    (root / "config/data_sources.yaml").write_text(
        json.dumps(registry), encoding="utf-8"
    )
    definition = find_dataset(
        load_registry(root / "config/data_sources.yaml"), "incois_bio_roms_v2"
    )
    report = inspect_local_dataset(definition, root, verify_checksum=True)
    assert report.status == "not_prepared"
    save_inspection_report(report, root)
    return report


@pytest.fixture
def source_root(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config/performance.yaml").write_text(
        PerformanceLimits(max_preview_cells=4).model_dump_json(), encoding="utf-8"
    )
    raw = tmp_path / "data/raw/v2.nc"
    raw.parent.mkdir(parents=True)
    with netCDF4.Dataset(raw, "w") as ds:
        ds.title = "Synthetic test, not ocean observations"
        for name, units, values, axis in (
            ("TIME", "days since 2019-01-24 00:00:00", [0, 30, 60], "T"),
            ("LAT", "degrees_north", [-5, -2, 0, 2, 5], "Y"),
            ("LON", "degrees_east", [30, 32, 35, 38, 40], "X"),
        ):
            ds.createDimension(name, len(values))
            coord = ds.createVariable(name, "f8", (name,))
            coord.units = units
            coord.axis = axis
            if name == "TIME":
                coord.calendar = "standard"
            coord[:] = values
        for name, units in (("SST", "deg C"), ("SSS", "PSU")):
            var = ds.createVariable(
                name, "i2", prep.AXES, fill_value=-32767, chunksizes=(1, 5, 5)
            )
            var.units = units
            var.long_name = f"Synthetic {name}"
            var.scale_factor = 0.5
            var.add_offset = 10.0
            var.set_auto_maskandscale(False)
            values = np.arange(75, dtype="i2").reshape(3, 5, 5)
            values[0, 0, 0] = -32767
            var[:] = values
    refresh(tmp_path)
    return tmp_path


def test_archive_group_matches_raw_and_reuses_without_overwrite(source_root):
    from backend.app.processing.archive_bio_roms import prepare_archive_group

    requests = [
        selection(start_date=date(2019, month, 1), end_date=date(2019, month, 28))
        for month in (1, 2, 3)
    ]
    before = (source_root / "data/raw/v2.nc").read_bytes()
    products = prepare_archive_group(requests, source_root, data_mode="synthetic")
    assert len(products) == 3
    with netCDF4.Dataset(source_root / "data/raw/v2.nc") as source:
        for i, product in enumerate(products):
            with netCDF4.Dataset(
                source_root / f"data/processed/{product.product_id}/fields.nc"
            ) as output:
                for name in ("SST", "SSS"):
                    np.testing.assert_equal(
                        output[name][:].filled(np.nan),
                        source[name][i : i + 1].filled(np.nan),
                    )
            with netCDF4.Dataset(
                source_root / f"data/cache/{product.product_id}/preview.nc"
            ) as output:
                for name in ("SST", "SSS"):
                    np.testing.assert_equal(
                        output[name][:].filled(np.nan),
                        source[name][
                            i : i + 1,
                            :: product.preview_stride,
                            :: product.preview_stride,
                        ].filled(np.nan),
                    )
    assert (
        prepare_archive_group(requests, source_root, data_mode="synthetic") == products
    )
    assert before == (source_root / "data/raw/v2.nc").read_bytes()
    for invalid in (
        [],
        requests * 7,
        [requests[0], requests[0]],
        [requests[0], selection(variables=["SST"])],
    ):
        with pytest.raises(ProductError):
            prepare_archive_group(invalid, source_root, data_mode="synthetic")


def test_publication_retries_only_transient_windows_locks(tmp_path, monkeypatch):
    source, destination = tmp_path / "stage", tmp_path / "final"
    source.mkdir()
    original = Path.rename
    attempts, delays = [], []

    def locked(path, target):
        attempts.append(path)
        if len(attempts) < 3:
            error = PermissionError("Synthetic Windows sharing lock")
            error.winerror = 5
            raise error
        return original(path, target)

    monkeypatch.setattr(Path, "rename", locked)
    monkeypatch.setattr(prep, "sleep", delays.append)
    prep._publish_directory(source, destination)
    assert len(attempts) == 3 and delays == [0.1, 0.2]
    assert destination.is_dir() and not source.exists()
    with pytest.raises(ProductError, match="Another operator"):
        prep._publish_directory(source, destination)


@pytest.mark.parametrize("winerror, expected_attempts", [(32, 8), (5, 8), (None, 1)])
def test_publication_lock_retry_is_bounded(
    tmp_path, monkeypatch, winerror, expected_attempts
):
    source, destination = tmp_path / "stage", tmp_path / "final"
    source.mkdir()
    attempts = []

    def locked(path, target):
        attempts.append(path)
        error = PermissionError("Synthetic permanent failure")
        error.winerror = winerror
        raise error

    monkeypatch.setattr(Path, "rename", locked)
    monkeypatch.setattr(prep, "sleep", lambda _: None)
    with pytest.raises(PermissionError):
        prep._publish_directory(source, destination)
    assert len(attempts) == expected_attempts
    assert source.is_dir() and not destination.exists()


def test_prepare_preserves_decoded_values_masks_and_axes(source_root):
    raw = source_root / "data/raw/v2.nc"
    before = raw.read_bytes()
    manifest = prep.prepare_product(selection(), source_root, data_mode="synthetic")
    assert manifest.data_mode == "synthetic"
    assert manifest.times == [
        "2019-01-24T00:00:00Z",
        "2019-02-23T00:00:00Z",
        "2019-03-25T00:00:00Z",
    ]
    assert manifest.preview_stride == 3
    assert manifest.capabilities.depth_profiles is False
    assert manifest.capabilities.comparison_ready is False
    assert manifest.temporal_support == "source_timestamps_no_inferred_bounds"
    with netCDF4.Dataset(
        source_root / f"data/processed/{manifest.product_id}/fields.nc"
    ) as ds:
        values = ds.variables["SST"][:]
        assert values.dtype == np.dtype("float64")
        assert values.mask[0, 0, 0]
        assert values[0, 0, 1] == 10.5
        assert "scale_factor" not in ds.variables["SST"].ncattrs()
        assert "add_offset" not in ds.variables["SST"].ncattrs()
        encoding = json.loads(ds.variables["SST"].source_attributes_json)
        assert encoding["scale_factor"] == 0.5
        assert encoding["_FillValue"] == -32767
        np.testing.assert_array_equal(ds.variables["LAT"][:], manifest.latitude)
        np.testing.assert_array_equal(ds.variables["LON"][:], manifest.longitude)
        assert ds.qc_policy == "source_mask_and_nonfinite_only"
    with netCDF4.Dataset(
        source_root / f"data/cache/{manifest.product_id}/preview.nc"
    ) as ds:
        assert ds.variables["SST"].shape == (3, 2, 2)
        assert ds.variables["SST"][0, 0, 1] == 11.5
    assert raw.read_bytes() == before


def test_idempotence_and_corrupt_existing_file(source_root):
    first = prep.prepare_product(selection(), source_root, data_mode="synthetic")
    second = prep.prepare_product(selection(), source_root, data_mode="synthetic")
    assert first == second
    path = source_root / f"data/cache/{first.product_id}/preview.nc"
    path.write_bytes(b"broken")
    with pytest.raises(ProductError, match="Existing product") as error:
        prep.prepare_product(selection(), source_root, data_mode="synthetic")
    assert error.value.code == "product_conflict"
    assert path.read_bytes() == b"broken"


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "uninspected"),
        ("checksum_status", "not_checked"),
        ("observed_md5", "0" * 32),
        ("source_id", "different"),
        ("source_version", "v1"),
        ("local_path", "data/raw/other.nc"),
        ("metadata", None),
    ],
)
def test_inspection_guard_before_array_access(source_root, monkeypatch, field, value):
    path = source_root / "data/metadata/incois_bio_roms_v2.json"
    report = json.loads(path.read_text())
    report[field] = value
    path.write_text(json.dumps(report))

    def forbidden(*args, **kwargs):
        pytest.fail("NetCDF must not open before inspection guard")

    monkeypatch.setattr(netCDF4, "Dataset", forbidden)
    with pytest.raises(ProductError) as error:
        prep.prepare_product(selection(), source_root)
    assert error.value.code == "inspection_required"


def test_missing_report_and_changed_source(source_root):
    path = source_root / "data/metadata/incois_bio_roms_v2.json"
    path.unlink()
    with pytest.raises(ProductError) as error:
        prep.prepare_product(selection(), source_root)
    assert error.value.code == "inspection_required"
    refresh(source_root)
    with (source_root / "data/raw/v2.nc").open("ab") as stream:
        stream.write(b"changed")
    with pytest.raises(ProductError) as error:
        prep.prepare_product(selection(), source_root)
    assert error.value.code == "inspection_required"


@pytest.mark.parametrize(
    "axis,values",
    [
        ("LAT", [-5, -2, -2, 2, 5]),
        ("LAT", [5, 2, 0, -2, -5]),
        ("LAT", [-95, -2, 0, 2, 5]),
        ("LON", [30, 32, 35, 38, 180]),
        ("LON", [30, 32, np.nan, 38, 40]),
        ("TIME", [0, 30, 30]),
    ],
)
def test_invalid_axes(source_root, axis, values):
    with netCDF4.Dataset(source_root / "data/raw/v2.nc", "a") as ds:
        ds.variables[axis][:] = values
    refresh(source_root)
    with pytest.raises(ProductError) as error:
        prep.prepare_product(selection(), source_root)
    assert error.value.code == "invalid_coordinates"
    assert not (source_root / "data/processed").exists()


@pytest.mark.parametrize(
    "variable,attribute,value,code",
    [
        ("TIME", "calendar", "360_day", "unsupported_calendar"),
        ("TIME", "units", "not a time unit", "unsupported_time"),
        ("LAT", "units", "radians", "unsupported_units"),
        ("SST", "units", "kelvin", "unsupported_units"),
        ("SST", "ancillary_variables", "TEMP_QC", "unsupported_qc"),
        ("SST", "flag_values", [1, 2], "unsupported_qc"),
        ("TIME", "bounds", "time_bounds", "unsupported_qc"),
    ],
)
def test_unsupported_metadata(source_root, variable, attribute, value, code):
    with netCDF4.Dataset(source_root / "data/raw/v2.nc", "a") as ds:
        ds.variables[variable].setncattr(attribute, value)
    refresh(source_root)
    with pytest.raises(ProductError) as error:
        prep.prepare_product(selection(), source_root)
    assert error.value.code == code


@pytest.mark.parametrize(
    "changes",
    [
        {"region": Region(west=100, east=110, south=-5, north=5)},
        {"start_date": date(2000, 1, 1), "end_date": date(2000, 2, 1)},
    ],
)
def test_no_overlap(source_root, changes):
    with pytest.raises(ProductError) as error:
        prep.prepare_product(selection(**changes), source_root)
    assert error.value.code == "no_overlap"


@pytest.mark.parametrize(
    "setting,value,code",
    [
        ("max_time_steps", 2, "preparation_limit"),
        ("max_preparation_values", 100, "preparation_limit"),
        ("max_axis_values", 4, "axis_limit"),
        ("max_product_file_bytes", 1024, "product_size_limit"),
    ],
)
def test_limits_before_field_materialization(source_root, setting, value, code):
    limits = PerformanceLimits(**{setting: value})
    (source_root / "config/performance.yaml").write_text(limits.model_dump_json())
    with pytest.raises(ProductError) as error:
        prep.prepare_product(selection(), source_root)
    assert error.value.code == code


def test_bounded_subselection_and_inclusive_dates(source_root):
    request = selection(
        region=Region(west=31, east=38, south=-2, north=2),
        start_date=date(2019, 2, 23),
        end_date=date(2019, 2, 23),
    )
    result = prep.prepare_product(request, source_root, data_mode="synthetic")
    assert result.latitude == [-2, 0, 2]
    assert result.longitude == [32, 35, 38]
    assert result.times == ["2019-02-23T00:00:00Z"]


def test_injected_write_failure_leaves_no_published_product(source_root, monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("private secret path")

    monkeypatch.setattr(prep, "_write_dataset", fail)
    with pytest.raises(ProductError) as error:
        prep.prepare_product(selection(), source_root)
    assert error.value.code == "preparation_failed"
    assert "secret" not in str(error.value)
    assert list((source_root / "data/processed").iterdir()) == []
    assert list((source_root / "data/cache").iterdir()) == []


def test_source_change_during_preparation_blocks_publish(source_root, monkeypatch):
    original = prep._check_unchanged
    calls = 0

    def check(*args):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ProductError("source_changed", "Source changed.")
        return original(*args)

    monkeypatch.setattr(prep, "_check_unchanged", check)
    with pytest.raises(ProductError) as error:
        prep.prepare_product(selection(), source_root)
    assert error.value.code == "source_changed"
    assert list((source_root / "data/processed").iterdir()) == []


def test_unsupported_variable_and_source(source_root):
    with pytest.raises(ProductError) as error:
        prep.prepare_product(selection(variables=["TEMP"]), source_root)
    assert error.value.code == "unsupported_variable"
    path = source_root / "config/data_sources.yaml"
    registry = json.loads(path.read_text())
    registry["datasets"][0]["version"] = "v1"
    path.write_text(json.dumps(registry))
    with pytest.raises(ProductError) as error:
        prep.prepare_product(selection(), source_root)
    assert error.value.code == "unsupported_source"


def test_cli_safe_validation(source_root, monkeypatch, capsys):
    from scripts import prepare_bio_roms as cli

    monkeypatch.setattr(cli, "PROJECT_ROOT", source_root)
    args = [
        "--variables",
        "SST",
        "--west",
        "30",
        "--east",
        "40",
        "--south",
        "-5",
        "--north",
        "5",
        "--start",
        "2019-01-01",
        "--end",
        "2019-03-31",
    ]
    assert cli.main(args) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "prepared"
    assert output["shape"] == [3, 5, 5]
    args[-1] = "not a date"
    assert cli.main(args) == 2
    assert json.loads(capsys.readouterr().err)["error"]["code"] == "invalid_selection"


def test_default_calendar_is_explicit_in_outputs(source_root):
    with netCDF4.Dataset(source_root / "data/raw/v2.nc", "a") as ds:
        ds.variables["TIME"].delncattr("calendar")
    refresh(source_root)
    manifest = prep.prepare_product(selection(), source_root, data_mode="synthetic")
    assert manifest.calendar == "standard"
    for path in (
        f"data/processed/{manifest.product_id}/fields.nc",
        f"data/cache/{manifest.product_id}/preview.nc",
    ):
        with netCDF4.Dataset(source_root / path) as ds:
            assert ds.variables["TIME"].calendar == "standard"


def test_chunk_limit_rejected_before_any_coordinate_read(source_root, monkeypatch):
    original = prep._check_storage

    def oversized(variable, limits):
        if variable.name == "SST":
            raise ProductError("source_chunk_limit", "Source chunk exceeds limits.")
        return original(variable, limits)

    def forbidden(*args, **kwargs):
        pytest.fail("Axes may not be read before selected source chunk validation")

    monkeypatch.setattr(prep, "_check_storage", oversized)
    monkeypatch.setattr(prep, "_axes", forbidden)
    with pytest.raises(ProductError) as error:
        prep.prepare_product(selection(), source_root)
    assert error.value.code == "source_chunk_limit"


def test_chunk_byte_calculation():
    class Chunked:
        dtype = np.dtype("float64")

        def chunking(self):
            return [10, 756, 1081]

    with pytest.raises(ProductError) as error:
        prep._check_storage(Chunked(), PerformanceLimits())
    assert error.value.code == "source_chunk_limit"


def test_private_leftovers_count_against_product_capacity(source_root):
    folder = source_root / "data/processed"
    folder.mkdir()
    for index in range(2):
        (folder / f".prepare_fixture_{index}").mkdir()
    limits = PerformanceLimits(max_products=2)
    (source_root / "config/performance.yaml").write_text(limits.model_dump_json())
    with pytest.raises(ProductError) as error:
        prep.prepare_product(selection(), source_root)
    assert error.value.code == "product_count_limit"


def test_nonfinite_float_field_is_missing(source_root):
    with netCDF4.Dataset(source_root / "data/raw/v2.nc", "a") as ds:
        var = ds.createVariable("MLD", "f4", prep.AXES)
        var.units = "m"
        values = np.ones((3, 5, 5), dtype="float32")
        values[0, 0, 0] = np.inf
        values[0, 0, 1] = np.nan
        var[:] = values
    refresh(source_root)
    manifest = prep.prepare_product(
        selection(variables=["MLD"]), source_root, data_mode="synthetic"
    )
    with netCDF4.Dataset(
        source_root / f"data/processed/{manifest.product_id}/fields.nc"
    ) as ds:
        values = ds.variables["MLD"][:]
        assert values.mask[0, 0, 0]
        assert values.mask[0, 0, 1]
        assert values[0, 0, 2] == 1


@pytest.mark.parametrize("chunks", [(3, 3, 4), None])
def test_archive_tile_boundaries_preserve_every_native_and_preview_value(
    source_root, chunks
):
    raw = source_root / "data/raw/v2.nc"
    with netCDF4.Dataset(raw, "w") as ds:
        for name, unit, values in (
            ("TIME", "days since 2019-01-24", [0, 30, 60]),
            ("LAT", "degrees_north", np.arange(-5, 6)),
            ("LON", "degrees_east", np.arange(30, 43)),
        ):
            ds.createDimension(name, len(values))
            v = ds.createVariable(name, "f8", (name,))
            v.units = unit
            v[:] = values
        for name, unit in (("SST", "deg C"), ("SSS", "PSU")):
            v = ds.createVariable(
                name,
                "f8",
                prep.AXES,
                fill_value=-999,
                chunksizes=chunks,
                contiguous=chunks is None,
            )
            v.units = unit
            values = np.arange(3 * 11 * 13, dtype=float).reshape(3, 11, 13)
            values[:, 4, 4] = -999
            v[:] = values
    refresh(source_root)
    manifest = prep.prepare_product(
        selection(region=Region(west=32, east=41, south=-3, north=4)),
        source_root,
        data_mode="synthetic",
    )
    with (
        netCDF4.Dataset(raw) as source,
        netCDF4.Dataset(
            source_root / f"data/processed/{manifest.product_id}/fields.nc"
        ) as full,
        netCDF4.Dataset(
            source_root / f"data/cache/{manifest.product_id}/preview.nc"
        ) as preview,
    ):
        for name in ("SST", "SSS"):
            expected = source[name][:, 2:10, 2:12].filled(np.nan)
            np.testing.assert_equal(full[name][:].filled(np.nan), expected)
            np.testing.assert_equal(
                preview[name][:].filled(np.nan),
                expected[:, :: manifest.preview_stride, :: manifest.preview_stride],
            )
    from backend.app.processing.archive_bio_roms import prepare_archive_group

    requests = [
        selection(
            region=Region(west=32, east=41, south=-3, north=4),
            start_date=date(2019, m, 1),
            end_date=date(2019, m, 28),
        )
        for m in (1, 2, 3)
    ]
    products = prepare_archive_group(requests, source_root, data_mode="synthetic")
    with netCDF4.Dataset(raw) as source:
        for i, product in enumerate(products):
            with (
                netCDF4.Dataset(
                    source_root / f"data/processed/{product.product_id}/fields.nc"
                ) as output,
                netCDF4.Dataset(
                    source_root / f"data/cache/{product.product_id}/preview.nc"
                ) as preview,
            ):
                for name in ("SST", "SSS"):
                    expected = source[name][i : i + 1, 2:10, 2:12].filled(np.nan)
                    np.testing.assert_equal(output[name][:].filled(np.nan), expected)
                    np.testing.assert_equal(
                        preview[name][:].filled(np.nan),
                        expected[
                            :, :: product.preview_stride, :: product.preview_stride
                        ],
                    )
