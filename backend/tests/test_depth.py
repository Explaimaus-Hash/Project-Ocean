"""Pressure-depth reference values, QC, uncertainty and immutable source fixtures."""

import socket
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import gsw
import pytest
from pydantic import ValidationError

from backend.app.processing.depth import convert_pressures, pressure_input
from backend.app.schemas.depth import (
    DepthReport,
    DepthRequest,
    PressureSample,
    serialize_depth_report,
)
from backend.app.schemas.observations import ObservationSample
from backend.app.schemas.products import ProductFile
from backend.app.storage.product_common import ProductError
from scripts import convert_observation_depth as cli


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Depth conversion must not use network")

    monkeypatch.setattr(socket.socket, "connect", denied)


def sample(**changes):
    return PressureSample.model_validate(
        {
            "sample_id": "s_" + "1" * 24,
            "pressure_dbar": 10,
            "latitude": 4,
            "source_pressure_name": "PRES",
            "selected_kind": "raw",
            "source_data_mode": "D",
            "pressure_qc": "1",
            "position_qc": "1",
            "time_qc": "1",
            "source_qc_eligible": True,
            "pressure_error_dbar": None,
            "error_source": "unknown",
            "retained_adjusted_error_dbar": 2.4,
            "source_depth_m": None,
            **changes,
        }
    )


def request(*samples):
    return DepthRequest(
        pressure_units="dbar",
        pressure_reference="sea_pressure_zero_at_surface",
        reference_evidence="Synthetic sea-pressure fixture",
        assumptions="zero_dynamic_height_zero_surface_geopotential",
        samples=samples,
    )


@pytest.mark.parametrize(
    "p,expected",
    [
        (10, 9.9445834469453),
        (50, 49.7180897012550),
        (125, 124.2726219409978),
        (250, 248.4700576548589),
        (600, 595.8253480356214),
        (1000, 992.0919060719987),
    ],
)
def test_published_teos10_reference(p, expected):
    # https://www.teos-10.org/pubs/gsw/html/gsw_z_from_p.html, lat=4 example.
    result = convert_pressures(request(sample(pressure_dbar=p))).results[0]
    assert result.depth_m == pytest.approx(expected, abs=1e-9)
    assert result.input.pressure_dbar == p


@pytest.mark.parametrize("lat", [-90, -45, 0, 45, 90])
def test_zero_pressure_and_inverse(lat):
    zero = convert_pressures(request(sample(pressure_dbar=0, latitude=lat))).results[0]
    assert zero.depth_m == 0.0
    result = convert_pressures(
        request(sample(pressure_dbar=2000, latitude=lat))
    ).results[0]
    assert gsw.p_from_z(-result.depth_m, lat) == pytest.approx(2000, abs=1e-8)


def test_latitude_dependence_and_hemisphere_symmetry():
    depths = [
        convert_pressures(request(sample(pressure_dbar=1000, latitude=lat)))
        .results[0]
        .depth_m
        for lat in (0, 90, -45, 45)
    ]
    assert depths[0] > depths[1]
    assert depths[2] == depths[3]
    assert depths[0] != 1000


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"pressure_dbar": None}, "missing_pressure"),
        ({"latitude": None}, "missing_latitude"),
        ({"pressure_dbar": -0.1}, "pressure_outside_domain"),
        ({"pressure_dbar": 12001}, "pressure_outside_domain"),
        ({"latitude": 91}, "latitude_outside_domain"),
        ({"latitude": -91}, "latitude_outside_domain"),
        ({"pressure_qc": "4"}, "qc_rejected"),
        ({"time_qc": "9"}, "qc_rejected"),
        ({"position_qc": None}, "qc_rejected"),
        ({"source_qc_eligible": False}, "qc_rejected"),
        ({"source_data_mode": None}, "source_mode_unsupported"),
        (
            {"selected_kind": "adjusted", "source_data_mode": "R"},
            "source_mode_unsupported",
        ),
        ({"source_pressure_name": None}, "missing_source_identity"),
    ],
)
def test_rejections_do_not_become_zero_depth(changes, reason):
    source = sample(**changes)
    result = convert_pressures(request(source)).results[0]
    assert result.status == "rejected"
    assert result.reason == reason
    assert result.depth_m is None
    assert result.pressure_sensitivity.status == "not_converted"
    assert result.input == source


def test_row_alignment_and_empty_batch():
    rows = (sample(), sample(sample_id="s_" + "2" * 24, pressure_qc="4"))
    report = convert_pressures(request(*rows))
    assert tuple(r.input.sample_id for r in report.results) == tuple(
        r.sample_id for r in rows
    )
    assert [r.status for r in report.results] == ["converted", "rejected"]
    assert convert_pressures(request()).results == ()


def test_uncertainty_missing_is_not_zero_or_adjusted_error():
    result = convert_pressures(request(sample())).results[0]
    assert result.input.retained_adjusted_error_dbar == 2.4
    assert result.input.pressure_error_dbar is None
    assert result.pressure_sensitivity.status == "missing_error"
    assert result.total_depth_uncertainty_m is None


@pytest.mark.parametrize("error", [0, 2.4])
def test_explicit_error_endpoint_conversion(error):
    row = sample(
        selected_kind="adjusted",
        source_pressure_name="PRES_ADJUSTED",
        pressure_error_dbar=error,
        retained_adjusted_error_dbar=error,
        error_source="selected_adjusted_error",
    )
    result = convert_pressures(request(row)).results[0]
    bounds = result.pressure_sensitivity
    assert bounds.status == "evaluated"
    assert bounds.pressure_lower_dbar == 10 - error
    assert bounds.depth_lower_m == pytest.approx(-gsw.z_from_p(10 - error, 4))
    assert bounds.depth_upper_m == pytest.approx(-gsw.z_from_p(10 + error, 4))
    assert bounds.depth_lower_m <= result.depth_m <= bounds.depth_upper_m
    assert result.total_depth_uncertainty_m is None


@pytest.mark.parametrize("p", [0.5, 11999])
def test_outside_error_interval_is_not_clamped(p):
    row = sample(
        pressure_dbar=p, pressure_error_dbar=2.4, error_source="operator_raw_error"
    )
    result = convert_pressures(request(row)).results[0]
    assert result.status == "converted"
    assert result.pressure_sensitivity.status == "outside_pressure_domain"
    assert result.pressure_sensitivity.pressure_lower_dbar == p - 2.4
    assert result.pressure_sensitivity.depth_lower_m is None
    assert result.pressure_sensitivity.depth_upper_m is None


@pytest.mark.parametrize(
    "changes",
    [
        {"pressure_dbar": float("nan")},
        {"latitude": float("inf")},
        {"pressure_error_dbar": -1},
        {"pressure_error_dbar": 0},
        {"error_source": "selected_adjusted_error", "pressure_error_dbar": 2.4},
        {
            "selected_kind": "adjusted",
            "error_source": "operator_raw_error",
            "pressure_error_dbar": 1,
        },
    ],
)
def test_invalid_numbers_and_uncertainty_metadata(changes):
    with pytest.raises(ValidationError):
        sample(**changes)


@pytest.mark.parametrize(
    "field,value",
    [
        ("pressure_units", "Pa"),
        ("pressure_reference", "absolute_pressure"),
        ("assumptions", "unknown"),
        ("reference_evidence", ""),
    ],
)
def test_reference_must_be_explicit(field, value):
    data = request(sample()).model_dump(mode="json")
    data[field] = value
    with pytest.raises(ValidationError):
        DepthRequest.model_validate(data)


def test_duplicate_and_oversized_batches():
    with pytest.raises(ValidationError):
        request(sample(), sample())
    with pytest.raises(ValidationError):
        request(*([sample()] * 5001))


def observation(kind="raw"):
    return ObservationSample(
        sample_id="s_" + "1" * 24,
        source_sample_index=0,
        profile_id=None,
        profile_identity_status="ambiguous_points",
        platform_id="fixture",
        direction="A",
        time="2019-01-29T00:00:00Z",
        longitude=65,
        source_longitude=65,
        latitude=-1,
        pressure_dbar=3 if kind == "raw" else 2.93,
        depth_m=None,
        time_qc="1",
        position_qc="1",
        coordinate_qc_eligible=True,
        values={
            "PRES": {
                "raw": 3,
                "raw_qc": "1",
                "adjusted": 2.93,
                "adjusted_qc": "1",
                "adjusted_error": 2.4,
                "data_mode": "D",
                "selected_kind": kind,
                "selected_source_name": "PRES" if kind == "raw" else "PRES_ADJUSTED",
                "selected_value": 3 if kind == "raw" else 2.93,
                "selected_qc": "1",
                "qc_eligible": True,
                "exclusions": [],
            }
        },
    )


@pytest.mark.parametrize("kind", ["raw", "adjusted"])
def test_adapter_preserves_source_choice_and_error(kind):
    source = observation(kind)
    before = source.model_dump_json()
    row = pressure_input(source)
    assert row.pressure_dbar == source.pressure_dbar
    assert row.selected_kind == kind
    assert row.pressure_error_dbar == (None if kind == "raw" else 2.4)
    report = convert_pressures(request(row))
    assert source.model_dump_json() == before
    assert source.depth_m is None
    assert report.results[0].depth_m > 0


def test_report_provenance_roundtrip_and_immutable():
    report = convert_pressures(request(sample(source_depth_m=12.3)))
    assert report.gsw_version == "3.6.23"
    assert report.dynamic_height_m2_s2 == report.sea_surface_geopotential_m2_s2 == 0
    assert report.results[0].input.source_depth_m == 12.3
    assert report.comparison_ready is False
    assert DepthReport.model_validate_json(serialize_depth_report(report)) == report
    with pytest.raises(ValidationError):
        report.results[0].depth_m = 0


def test_wrong_dependency_version_fails_safely(monkeypatch):
    monkeypatch.setattr(gsw, "__version__", "unexpected")
    with pytest.raises(ProductError, match="Pinned GSW version"):
        convert_pressures(request(sample()))


def test_nonfinite_library_output_fails(monkeypatch):
    monkeypatch.setattr(gsw, "z_from_p", lambda *a, **kw: float("nan"))
    with pytest.raises(ProductError, match="invalid values"):
        convert_pressures(request(sample()))


def test_processing_import_does_not_load_gsw():
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import backend.app.processing.depth; "
            "assert 'gsw' not in sys.modules; assert 'numpy' not in sys.modules",
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0


@pytest.mark.parametrize("units,exit_code", [("decibar", 0), ("Pa", 2)])
def test_readonly_cli_reference_and_unit_boundary(
    monkeypatch, capsys, tmp_path, units, exit_code
):
    record = ProductFile(size_bytes=123, modified_ns=1, sha256="a" * 64)
    collection = SimpleNamespace(
        variables={"PRES": SimpleNamespace(units=units, adjusted_units=units)},
        selection=SimpleNamespace(value_mode="raw"),
        samples=[observation()],
        data_mode="synthetic",
    )
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(cli, "describe_file", lambda *a, **k: record)
    monkeypatch.setattr(cli.ObservationStore, "collection", lambda *a: collection)
    code = cli.main(
        [
            "--collection-id",
            "o_" + "1" * 24,
            "--reference-evidence",
            "Synthetic sea-pressure reference",
            "--assume-zero-geopotential",
        ]
    )
    assert code == exit_code
    capture = capsys.readouterr()
    if code == 0:
        result = DepthReport.model_validate_json(capture.out)
        assert result.source_collection.collection_sha256 == record.sha256
        assert result.results[0].input.selected_kind == "raw"
    else:
        assert "unsupported_pressure_units" in capture.err
    assert not list(tmp_path.iterdir())
