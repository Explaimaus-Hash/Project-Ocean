"""Offline adjusted-data and quantity gates, independent of real downloads."""

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import netCDF4
import pytest
from pydantic import ValidationError
from test_observations import make_observations, normalized

from backend.app.processing.quantities import derive_quantities, potential_temperature
from backend.app.schemas.observations import ObservationCollection, ObservationRequest
from backend.app.schemas.quantities import QuantityEvidence, QuantityReport
from backend.app.storage.product_common import ProductError


@pytest.fixture
def collection(tmp_path):
    path = make_observations(tmp_path / "quantities.nc")
    with netCDF4.Dataset(path, "a") as ds:
        for name, low, high in (("PRES", 0, 12000), ("TEMP", -2, 40), ("PSAL", 0, 43)):
            ds[name + "_ADJUSTED"].valid_min = low
            ds[name + "_ADJUSTED"].valid_max = high
    return normalized(
        path,
        ObservationRequest(
            region={"west": 30, "east": 120, "south": -30, "north": 30},
            start_date="2024-01-01",
            end_date="2024-01-31",
            pressure_min_dbar=0,
            pressure_max_dbar=2000,
            variables=["PRES", "TEMP", "PSAL"],
            value_mode="raw",
        ),
    )


def evidence(collection, **changes):
    return QuantityEvidence.model_validate(
        {
            "client_input_sha256": collection.input_file.sha256,
            "provider_input_sha256": "1" * 64,
            "verification_evidence": "Synthetic fixture metadata and alignment",
            "model_identity": "synthetic_model",
            "model_evidence": "Synthetic explicitly verified fixture",
            "model_salinity": "practical_salinity_PSS78",
            "parameters": [
                {
                    "name": n,
                    "adjusted_name": n.lower() + "_adjusted",
                    "units": u,
                    "definition": d,
                    "definition_evidence": "Synthetic provider definition",
                    "valid_min": low,
                    "valid_max": high,
                }
                for n, u, d, low, high in (
                    ("PRES", "decibar", "sea_pressure_dbar", 0, 12000),
                    ("TEMP", "degree_Celsius", "in_situ_ITS90_C", -2.5, 40),
                    ("PSAL", "PSU", "practical_salinity_PSS78", 2, 41),
                )
            ],
            **changes,
        }
    )


def test_adjusted_policy_and_original_unchanged(collection):
    original = collection.model_dump_json()
    result = derive_quantities(collection, evidence(collection))
    row = result.results[0]
    assert row.practical_salinity == 35.5  # Not 0.0355 or Absolute Salinity.
    assert row.parameters[0].value == 5.5
    assert row.parameters[0].original.selected_kind == "raw"
    assert row.parameters[0].error == 0.1
    assert row.absolute_salinity_g_kg > row.practical_salinity
    assert row.potential_temperature_0_dbar_ITS90_C < 21.5
    assert len(row.temperature_exclusions) == 3
    assert row.converted_uncertainty is None
    assert not row.comparison_ready
    assert QuantityReport.model_validate_json(result.model_dump_json()) == result
    assert collection.model_dump_json() == original


def test_verified_model_definition_allows_only_quantity_gate(collection):
    result = derive_quantities(
        collection,
        evidence(
            collection,
            model_temperature="potential_temperature",
            model_temperature_scale="ITS90",
            model_reference_pressure_dbar=0,
        ),
    ).results[0]
    assert not result.temperature_exclusions
    assert not result.comparison_ready


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("data_mode", "R", "adjusted_mode_required"),
        ("adjusted", None, "missing_adjusted_value"),
        ("adjusted_qc", "4", "adjusted_qc_rejected"),
        ("adjusted", 41.5, "outside_provider_client_range"),
    ],
)
def test_no_raw_fallback(collection, field, value, reason):
    data = collection.model_dump(mode="json")
    data["samples"][0]["values"]["PSAL"][field] = value
    checked = ObservationCollection.model_validate(data)
    row = derive_quantities(checked, evidence(checked)).results[0]
    assert reason in row.parameters[2].exclusions
    assert row.practical_salinity is None
    assert row.potential_temperature_0_dbar_ITS90_C is None


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("definition", "unresolved", "source_definition_unresolved"),
        ("units", "g/kg", "unsupported_units"),
        ("valid_min", 44, "range_metadata_conflict"),
    ],
)
def test_provider_gates(collection, field, value, reason):
    data = evidence(collection).model_dump(mode="json")
    data["parameters"][2][field] = value
    if field == "valid_min":
        data["parameters"][2]["valid_max"] = 45
    row = derive_quantities(collection, QuantityEvidence.model_validate(data)).results[
        0
    ]
    assert reason in row.parameters[2].exclusions


def test_missing_client_bounds_rejected(collection):
    data = collection.model_dump(mode="json")
    data["variables"]["PSAL"]["adjusted_valid_min"] = None
    checked = ObservationCollection.model_validate(data)
    row = derive_quantities(checked, evidence(checked)).results[0]
    assert "client_range_unresolved" in row.parameters[2].exclusions


def test_evidence_identity_mismatch(collection):
    with pytest.raises(ProductError, match="Evidence"):
        derive_quantities(
            collection, evidence(collection, client_input_sha256="0" * 64)
        )


@pytest.mark.parametrize(
    "sp,p,sa",
    [
        (34.5487, 10, 34.711778344814114),
        (34.7275, 50, 34.891522618230098),
        (34.8605, 125, 35.025544862476920),
        (34.6810, 250, 34.847229026189588),
        (34.5680, 600, 34.736628474576051),
        (34.5600, 1000, 34.732363065590846),
    ],
)
def test_published_absolute_salinity(sp, p, sa):
    # https://www.teos-10.org/pubs/gsw/html/gsw_SA_from_SP.html
    actual, _ = potential_temperature(sp, 10, p, 188, 4)
    # Website examples identify GSW 3.05 (2015), not pinned GSW 3.6.23.
    # Check cross-version agreement only; strict current checks are below.
    assert actual == pytest.approx(sa, abs=1e-4, rel=0)


def test_published_temperature_input_is_absolute_salinity(monkeypatch):
    # https://www.teos-10.org/pubs/gsw/html/gsw_pt0_from_t.html
    import gsw

    seen = []

    def sa(sp, p, lon, lat):
        return 34.7118

    def pt(salinity, t, p):
        seen.append(salinity)
        return gsw.pt0_from_t(salinity, t, p)

    monkeypatch.setattr(
        "backend.app.processing.quantities._gsw",
        lambda: SimpleNamespace(SA_from_SP=sa, pt0_from_t=pt),
    )
    _, actual = potential_temperature(34.5487, 28.7856, 10, 188, 4)
    assert seen == [34.7118]
    assert actual == pytest.approx(28.783196819670632, abs=1e-10)


@pytest.mark.parametrize(
    "index,value",
    [
        (0, -1),
        (0, 43),
        (1, -3),
        (1, 41),
        (2, -1),
        (2, 12001),
        (3, -181),
        (3, 361),
        (4, -91),
        (4, 91),
        (0, float("nan")),
        (1, float("inf")),
    ],
)
def test_domain_rejection(index, value):
    args = [35, 20, 10, 65, -1]
    args[index] = value
    with pytest.raises(ProductError):
        potential_temperature(*args)


def test_wrong_gsw_version(monkeypatch):
    monkeypatch.setitem(sys.modules, "gsw", SimpleNamespace(__version__="0"))
    with pytest.raises(ProductError, match="version"):
        potential_temperature(35, 20, 10, 65, -1)


def test_unique_evidence_and_finite_bounds(collection):
    data = evidence(collection).model_dump(mode="json")
    data["parameters"][1] = data["parameters"][0]
    with pytest.raises(ValidationError):
        QuantityEvidence.model_validate(data)


def test_import_is_lazy():
    code = (
        "import sys; import backend.app.processing.quantities; "
        "assert 'gsw' not in sys.modules; assert 'netCDF4' not in sys.modules; "
        "assert 'xarray' not in sys.modules"
    )
    subprocess.run(
        [sys.executable, "-c", code], check=True, capture_output=True, timeout=20
    )


def test_bundled_gsw_reference_casts():
    import gsw
    import numpy as np

    path = Path(gsw.__file__).parent / "tests" / "gsw_cv_v3_0.npz"
    with np.load(path) as data:
        count = 0
        for row in range(45):
            for col in range(3):
                sp, p, t = (
                    float(data[n][row, col])
                    for n in ("SP_chck_cast", "p_chck_cast", "t_chck_cast")
                )
                if not all(np.isfinite(v) for v in (sp, p, t)):
                    continue
                sa, pt = potential_temperature(
                    sp,
                    t,
                    p,
                    float(data["long_chck_cast"][col]),
                    float(data["lat_chck_cast"][col]),
                )
                assert sa == pytest.approx(
                    float(data["SA_from_SP"][row, col]), abs=1e-10, rel=0
                )
                # Bundled SA_chck_cast equals SA_from_SP for these reference casts.
                assert pt == pytest.approx(
                    float(data["pt0_from_t"][row, col]), abs=1e-10, rel=0
                )
                count += 1
        assert count > 50
