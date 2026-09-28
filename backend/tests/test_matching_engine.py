"""Bounded synthetic native collocation; never proof of real-source readiness."""

import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError
from test_quantities import collection as quantity_collection
from test_quantities import evidence

from backend.app.comparison.adjusted_depth import build_adjusted_depth
from backend.app.comparison.matching import (
    great_circle_m,
    match_native,
    serialize_matches,
)
from backend.app.processing.quantities import derive_quantities
from backend.app.schemas.matching import NativeMatchingInput
from backend.app.schemas.observations import ObservationCollection

DAY = datetime(2024, 1, 1, tzinfo=UTC)
MODEL = "m_" + "1" * 24
FILE_HASH = "4" * 64
VERIFIED = {
    "status": "verified_for_input_snapshot",
    "reference": "Synthetic independently prescribed support only",
}


@pytest.fixture(scope="module")
def collection(tmp_path_factory):
    # Every mutation uses a fresh validated copy; prepare the disk fixture once.
    return quantity_collection.__wrapped__(tmp_path_factory.mktemp("matching_engine"))


def make_request(
    collection, *, quantity="practical_salinity", model_temperature_known=False
):
    data = collection.model_dump(mode="json")
    for sample in data["samples"]:
        for parameter in sample["values"].values():
            parameter["data_mode"] = "D"
            parameter["adjusted_qc"] = "1"
    collection = ObservationCollection.model_validate(data)
    definitions = (
        {
            "model_temperature": "potential_temperature",
            "model_temperature_scale": "ITS90",
            "model_reference_pressure_dbar": 0,
        }
        if model_temperature_known
        else {}
    )
    quantities = derive_quantities(
        collection, evidence(collection, model_identity=MODEL, **definitions)
    )
    depths = build_adjusted_depth(collection, quantities, FILE_HASH)
    identity = {
        "model_id": MODEL,
        "collection_id": collection.collection_id,
        "acquisition_id": "a_" + "3" * 24,
        "data_mode": collection.data_mode,
        "quantity": quantity,
    }
    count = len(collection.samples)
    eligible = (
        count if quantity == "practical_salinity" or model_temperature_known else 0
    )
    return NativeMatchingInput.model_validate(
        {
            "policy": {
                **identity,
                "tolerances": {
                    "horizontal_m": 100000,
                    "vertical_m": 1,
                    "time_seconds": 43200,
                    "review": "reviewed_for_selection",
                    "rationale": "Synthetic boundary tests, not operational defaults",
                },
            },
            "context": {
                **identity,
                "model_manifest_sha256": "2" * 64,
                "collection_file_sha256": FILE_HASH,
                "collection_canonical_sha256": hashlib.sha256(
                    collection.model_dump_json().encode()
                ).hexdigest(),
                "client_input_sha256": collection.input_file.sha256,
                "provider_input_sha256": quantities.evidence.provider_input_sha256,
                "sample_count": count,
                "strict_qc_eligible_count": count,
                "quantity_eligible_count": eligible,
                "joint_eligible_count": eligible,
                "source_time_indices": (7, 8),
                "source_time_labels": (DAY, DAY + timedelta(days=1)),
                "time_cells": [
                    {
                        "source_time_index": 7 + i,
                        "label": DAY + timedelta(days=i),
                        "start": DAY + timedelta(days=i),
                        "end": DAY + timedelta(days=i + 1),
                    }
                    for i in range(2)
                ],
                **{
                    name: VERIFIED
                    for name in (
                        "time_support",
                        "vertical_reference",
                        "wet_mask",
                        "bottom_support",
                        "coastline_connectivity",
                        "adjusted_depth_alignment",
                    )
                },
            },
            "axes": {
                "times": (DAY, DAY + timedelta(days=1)),
                "depth_m": (0, 6, 10),
                "latitude": (5, 6),
                "longitude": (70, 71),
                "source_time_indices": (7, 8),
                "source_depth_indices": (10, 11, 12),
                "source_latitude_indices": (20, 21),
                "source_longitude_indices": (30, 31),
                "source_time_units": "days since 2024-01-01",
                "calendar": "standard",
            },
            "scientific_file_sha256": "5" * 64,
            "source_variable": "so" if quantity == "practical_salinity" else "thetao",
            "quantity_units": (
                "1 (PSS-78)"
                if quantity == "practical_salinity"
                else "degree_Celsius (ITS-90)"
            ),
            "values": [35.25] * 24,
            "valid_mask": [True] * 24,
            "columns": [
                {
                    "wet": True,
                    "shallowest_centre_m": 0,
                    "deepest_centre_m": 10,
                    "bottom_m": 20,
                }
                for _ in range(8)
            ],
            "collection": collection,
            "quantities": quantities,
            "depths": depths,
            "observation_support": [
                {
                    "sample_id": sample.sample_id,
                    "source_sample_index": sample.source_sample_index,
                    "wet": True,
                    "candidate_latitude_index": 20,
                    "candidate_longitude_index": 30,
                    "connected": True,
                }
                for sample in collection.samples
            ],
        }
    )


@pytest.fixture
def request_snapshot(collection):
    return make_request(collection)


def changed(request, change):
    data = request.model_dump(mode="json")
    change(data)
    return NativeMatchingInput.model_validate(data)


def test_match_preserves_adjusted_values_original_and_native_indices(request_snapshot):
    original = request_snapshot.model_dump_json()
    report = match_native(request_snapshot)
    assert report["matched_pair_count"] == 6
    assert report["status"] == "evaluated"
    assert report["overlap_status"] == "matched"
    assert report["comparison_ready"] is False
    row = report["results"][0]
    assert row["observation_value"] == 35.5
    assert row["candidate"]["model_value"] == 35.25
    assert row["candidate"]["source_time_index"] == 8
    assert row["candidate"]["source_depth_index"] == 11
    assert row["candidate"]["source_latitude_index"] == 20
    assert row["candidate"]["source_longitude_index"] == 30
    assert row["candidate"]["midpoint_offset_seconds"] == 43200
    assert row["reported_adjusted_errors"]["PRES"] == 0.1
    assert request_snapshot.collection.samples[0].pressure_dbar == 5
    assert request_snapshot.depths.results[0].input.pressure_dbar == 5.5
    assert request_snapshot.model_dump_json() == original
    assert json.loads(serialize_matches(request_snapshot)) == report
    assert "bias" not in report and "rmse" not in report


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("valid_mask", False, "nearest_cell_masked"),
        ("values", None, "nearest_value_missing"),
    ],
)
def test_nearest_invalid_cell_never_falls_back(request_snapshot, field, value, reason):
    request = changed(request_snapshot, lambda d: d[field].__setitem__(16, value))
    report = match_native(request)
    assert report["matched_pair_count"] == 0
    assert reason in report["results"][0]["exclusions"]
    assert report["results"][0]["candidate"]["source_depth_index"] == 11


@pytest.mark.parametrize(
    "name,value,reason",
    [
        ("wet", False, "dry_location"),
        ("deepest_centre_m", 5.5, "pressure_endpoints_outside_local_support"),
        ("bottom_m", None, "support_unresolved"),
    ],
)
def test_column_support_gates(request_snapshot, name, value, reason):
    request = changed(
        request_snapshot, lambda d: d["columns"][4].__setitem__(name, value)
    )
    report = match_native(request)
    assert report["matched_pair_count"] == 0
    assert reason in report["results"][0]["exclusions"]
    if value is None:
        assert report["status"] == "partially_blocked"
        assert report["overlap_status"] == "not_evaluated"


@pytest.mark.parametrize("name,value", [("connected", False), ("wet", False)])
def test_observation_support_gates(request_snapshot, name, value):
    request = changed(
        request_snapshot, lambda d: d["observation_support"][0].__setitem__(name, value)
    )
    report = match_native(request)
    assert report["matched_pair_count"] == 5
    assert not report["results"][0]["matched"]


def test_support_bound_to_chosen_candidate(request_snapshot):
    request = changed(
        request_snapshot,
        lambda d: d["observation_support"][0].__setitem__(
            "candidate_latitude_index", 21
        ),
    )
    assert "support_unresolved" in match_native(request)["results"][0]["exclusions"]


def test_time_tolerance_boundary_is_inclusive(request_snapshot):
    assert match_native(request_snapshot)["matched_pair_count"] == 6
    request = changed(
        request_snapshot,
        lambda d: d["policy"]["tolerances"].__setitem__("time_seconds", 43199.9),
    )
    report = match_native(request)
    assert report["matched_pair_count"] == 0
    assert "time_tolerance_exceeded" in report["results"][0]["exclusions"]


def test_vertical_zero_requires_exact_centre(request_snapshot):
    request = changed(
        request_snapshot,
        lambda d: d["policy"]["tolerances"].__setitem__("vertical_m", 0),
    )
    report = match_native(request)
    assert report["matched_pair_count"] == 0
    assert "vertical_tolerance_exceeded" in report["results"][0]["exclusions"]


def test_native_envelope_no_half_cell_extension(request_snapshot):
    request = changed(
        request_snapshot, lambda d: d["axes"].__setitem__("longitude", [70.01, 71])
    )
    report = match_native(request)
    assert report["matched_pair_count"] == 0
    assert report["results"][0]["candidate"] is None
    assert "outside_horizontal_support" in report["results"][0]["exclusions"]


def test_missing_global_support_blocks_before_pair_search(request_snapshot):
    request = changed(
        request_snapshot,
        lambda d: d["context"].__setitem__("wet_mask", {"status": "unresolved"}),
    )
    report = match_native(request)
    assert report["status"] == "blocked"
    assert report["results"] == []
    assert report["overlap_status"] == "not_evaluated"


@pytest.mark.parametrize(
    "name",
    ["collection_canonical_sha256", "client_input_sha256", "provider_input_sha256"],
)
def test_provenance_mismatch_rejected(request_snapshot, name):
    request = changed(
        request_snapshot, lambda d: d["context"].__setitem__(name, "f" * 64)
    )
    with pytest.raises(ValueError, match="provenance"):
        match_native(request)


def test_claimed_eligible_counts_recomputed(request_snapshot):
    def alter(data):
        data["context"]["strict_qc_eligible_count"] = 5
        data["context"]["joint_eligible_count"] = 5

    with pytest.raises(ValueError, match="counts"):
        match_native(changed(request_snapshot, alter))


def test_temperature_quantity_gate_not_overridden_by_finite_conversion(collection):
    request = make_request(collection, quantity="potential_temperature_0_dbar_ITS90_C")
    assert (
        request.quantities.results[0].potential_temperature_0_dbar_ITS90_C is not None
    )
    report = match_native(request)
    assert report["matched_pair_count"] == 0
    assert "quantity_incompatible_or_no_eligible_observations" in report["blockers"]


def test_real_input_adapter_is_explicitly_blocked(collection):
    data = collection.model_dump(mode="json")
    data["data_mode"] = "real"
    request = make_request(ObservationCollection.model_validate(data))
    report = match_native(request)
    assert report["status"] == "blocked"
    assert "real_field_and_support_adapter_not_implemented" in report["blockers"]
    assert not report["results"]


def test_shape_mismatch_rejected_before_search(request_snapshot):
    with pytest.raises(ValidationError, match="shape"):
        changed(request_snapshot, lambda d: d["values"].pop())


def test_field_quantity_binding_rejected(request_snapshot):
    with pytest.raises(ValidationError):
        changed(request_snapshot, lambda d: d.__setitem__("source_variable", "thetao"))


def test_distance_uses_metres_and_antipodal_is_finite():
    assert great_circle_m(0, 0, 0, 0) == 0
    assert great_circle_m(0, 0, 0, 1) == pytest.approx(111195.0802335329)
    assert great_circle_m(90, 0, -90, 0) == pytest.approx(20015114.442035925)


def test_daily_final_end_exclusive(request_snapshot):
    def earlier(data):
        labels = [(DAY + timedelta(days=i - 1)).isoformat() for i in range(2)]
        data["axes"]["times"] = labels
        data["context"]["source_time_labels"] = labels
        for i, cell in enumerate(data["context"]["time_cells"]):
            cell["label"] = labels[i]
            cell["start"] = labels[i]
            cell["end"] = (DAY + timedelta(days=i)).isoformat()

    report = match_native(changed(request_snapshot, earlier))
    assert report["matched_pair_count"] == 0
    assert "outside_time_support" in report["results"][0]["exclusions"]


def test_geographic_tie_uses_lowest_source_index(request_snapshot):
    request = changed(
        request_snapshot,
        lambda d: d["axes"].__setitem__("longitude", [69.5, 70.5]),
    )
    report = match_native(request)
    assert report["matched_pair_count"] == 6
    assert report["results"][0]["candidate"]["source_longitude_index"] == 30


def test_exact_horizontal_zero_tolerance(request_snapshot):
    request = changed(
        request_snapshot,
        lambda d: d["policy"]["tolerances"].__setitem__("horizontal_m", 0),
    )
    assert match_native(request)["matched_pair_count"] == 6


def test_depth_tie_uses_lowest_native_level_without_mask_fallback(request_snapshot):
    centre = request_snapshot.depths.results[0].depth_m

    def tied(data):
        data["axes"]["depth_m"] = [centre - 0.5, centre + 0.5, 10]
        data["valid_mask"][12] = False

    report = match_native(changed(request_snapshot, tied))
    row = report["results"][0]
    assert row["candidate"]["source_depth_index"] == 10
    assert "nearest_cell_masked" in row["exclusions"]


def test_vertical_tolerance_inclusive_not_uncertainty_expanded(request_snapshot):
    offset = match_native(request_snapshot)["results"][0]["candidate"][
        "vertical_offset_m"
    ]
    exact = changed(
        request_snapshot,
        lambda d: d["policy"]["tolerances"].__setitem__("vertical_m", offset),
    )
    assert match_native(exact)["matched_pair_count"] == 6
    below = changed(
        exact,
        lambda d: d["policy"]["tolerances"].__setitem__("vertical_m", offset - 1e-9),
    )
    assert match_native(below)["matched_pair_count"] == 0


@pytest.mark.parametrize("field", ["valid_mask", "values"])
def test_nonfinite_or_unknown_model_cells_never_produce_pairs(request_snapshot, field):
    request = changed(request_snapshot, lambda d: d[field].__setitem__(16, None))
    report = match_native(request)
    assert report["matched_pair_count"] == 0
    assert not report["comparison_ready"]
    if field == "valid_mask":
        assert report["overlap_status"] == "not_evaluated"


def test_nonfinite_model_value_rejected(request_snapshot):
    with pytest.raises(ValidationError):
        changed(request_snapshot, lambda d: d["values"].__setitem__(0, float("nan")))


def test_local_native_level_support_is_not_inferred_from_finite_values(
    request_snapshot,
):
    request = changed(
        request_snapshot,
        lambda d: d["columns"][4].__setitem__("deepest_centre_m", 5.5),
    )
    row = match_native(request)["results"][0]
    assert row["candidate"]["model_value"] == 35.25
    assert "selected_level_outside_local_support" in row["exclusions"]
    assert not row["matched"]


def test_raw_depth_report_cannot_replace_adjusted_bridge(request_snapshot):
    from backend.app.processing.depth import convert_pressures, pressure_input
    from backend.app.schemas.depth import DepthRequest

    raw = convert_pressures(
        DepthRequest(
            pressure_units="dbar",
            pressure_reference="sea_pressure_zero_at_surface",
            reference_evidence="Synthetic raw pressure only",
            assumptions="zero_dynamic_height_zero_surface_geopotential",
            source_collection=request_snapshot.depths.source_collection,
            samples=tuple(
                pressure_input(s) for s in request_snapshot.collection.samples
            ),
        )
    )
    request = changed(
        request_snapshot, lambda d: d.__setitem__("depths", raw.model_dump())
    )
    with pytest.raises(ValueError, match="Adjusted depth"):
        match_native(request)


def test_canonical_hash_is_not_accepted_as_collection_file_hash(request_snapshot):
    request = changed(
        request_snapshot,
        lambda d: d["context"].__setitem__(
            "collection_file_sha256", d["context"]["collection_canonical_sha256"]
        ),
    )
    with pytest.raises(ValueError, match="Adjusted depth"):
        match_native(request)


def test_declared_grid_budget_rejected_before_search(request_snapshot):
    def large(data):
        data["axes"]["latitude"] = [i / 100 for i in range(1000)]
        data["axes"]["source_latitude_indices"] = list(range(1000))
        data["axes"]["longitude"] = [i / 100 for i in range(1000)]
        data["axes"]["source_longitude_indices"] = list(range(1000))

    with pytest.raises(ValidationError, match="budget"):
        changed(request_snapshot, large)


def test_report_budget_fails_without_truncated_success(request_snapshot, monkeypatch):
    from backend.app.comparison import matching

    monkeypatch.setattr(matching, "MAX_REPORT_BYTES", 500)
    with pytest.raises(ValueError, match="byte budget"):
        serialize_matches(request_snapshot)


def test_verified_synthetic_temperature_uses_converted_quantity(collection):
    request = make_request(
        collection,
        quantity="potential_temperature_0_dbar_ITS90_C",
        model_temperature_known=True,
    )
    report = match_native(request)
    row = report["results"][0]
    assert report["matched_pair_count"] == 6
    assert report["source_variable"] == "thetao"
    assert report["quantity_units"] == "degree_Celsius (ITS-90)"
    assert row["observation_value"] == (
        request.quantities.results[0].potential_temperature_0_dbar_ITS90_C
    )
    assert row["observation_value"] != request.quantities.results[0].practical_salinity
    assert not report["comparison_ready"]
